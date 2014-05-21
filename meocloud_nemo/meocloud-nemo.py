import ConfigParser
import socket
import sys
import errno

from gi.repository import GLib
import urlparse

sys.path.insert(0, '/opt/meocloud/libs/')
sys.path.insert(0, '/opt/meocloud/gui/meocloud_gui/protocol/')

from shell.ttypes import OpenMessage, OpenType, \
    ShareMessage, ShareType, SubscribeMessage, SubscribeType

from shell.ttypes import Message, FileState, MessageType, \
    FileStatusMessage, FileStatusType, FileStatus, FileState

from gi.repository import Nemo, GObject
from thrift.protocol import TBinaryProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.transport import TTransport

import urllib
import os
import gettext
import locale


FILE_STATE_TO_EMBLEM = {
    FileState.READY: 'emblem-default',
    FileState.SYNCING: 'emblem-synchronizing',
    FileState.IGNORED: 'emblem-important',
    FileState.ERROR: 'emblem-important'
}

READBUF_SIZE = 16 * 1024
CHUNK_SIZE = 4 * 1024
MAX_WRITE_BATCH_SIZE = 64 * 1024


PREFS_PATH = os.path.expanduser("~/.meocloud/gui/prefs.ini")
SHARED_PATH = os.path.expanduser("~/.meocloud/gui/shared_directories")

def deserialize(msg, data):
    transport = TTransport.TMemoryBuffer(data)
    protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
    msg.read(protocol)
    msg.validate()
    remaining = data[transport.cstringio_buf.tell():]
    transport.close()

    return msg, remaining


def deserialize_thrift_msg(data, read_buffer, msgobj):
    '''
    Try to deserialize data (or buf + data) into a valid
    'Message' (msgobj), as defined in the thrift ShellHelper specification
    '''

    if read_buffer:
        data = ''.join((read_buffer, data))
        read_buffer = None
    try:
        msg, remaining = deserialize(msgobj, data)
    except (TProtocolException, EOFError, TypeError) as dex:
        if len(data) <= READBUF_SIZE:
            read_buffer = data
            msg = None
            remaining = None
        else:
            raise OverflowError('Message does not fit buffer.')

    return msg, remaining, read_buffer


def serialize(msg):
    msg.validate()
    transport = TTransport.TMemoryBuffer()
    protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
    msg.write(protocol)

    data = transport.getvalue()
    transport.close()
    return data


def serialize_thrift_msg(msg):
    '''
    Try to serialize a 'Message' (msg) into a byte stream
    'Message' is defined in the thrift ShellHelper specification
    '''
    try:
        data = serialize(msg)
    except TProtocolException as tpe:
        raise

    return data


def init_localization():
    '''prepare l10n'''
    locale.setlocale(locale.LC_ALL, '')
    filename = "meocloud_mo/%s.mo" % locale.getlocale()[0][0:2]
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)

    try:
        trans = gettext.GNUTranslations(open(path, "rb"))
    except IOError:
        trans = gettext.NullTranslations()

    trans.install()


class MEOCloudNemo(Nemo.InfoProvider, Nemo.MenuProvider,
                   GObject.GObject):
    def __init__(self):
        init_localization()
        self.nemo_items = {}
        self.file_states = {}
        self.shared = set()

        self.read_buffer = None
        self.write_buffer = None
        self.writing = False
        self.sock = None
        self.last_prefs_mtime = 0
        self.last_shared_mtime = 0
        self.cloud_folder_uri = ""
 
        self.recv_msg = Message()
        self.file_status_msg = \
            Message(type=MessageType.FILE_STATUS,
                    fileStatus=FileStatusMessage(
                        type=FileStatusType.REQUEST,
                        status=FileStatus()))

        self.config = ConfigParser.ConfigParser()
        self.config.read(PREFS_PATH)

        try:
            import platform
            if platform.dist() == ('Ubuntu', '12.04', 'precise'):
                FILE_STATE_TO_EMBLEM[FileState.SYNCING] = \
                    'emblem-synchronizing-symbolic'
        except ImportError:
            pass

        self.update_config()
        GLib.timeout_add_seconds(30, self.update_config,
                                 priority=GLib.PRIORITY_LOW)

    def update_config(self):
        if os.path.isfile(PREFS_PATH):
            mtime = os.path.getmtime(PREFS_PATH)

            if mtime != self.last_prefs_mtime:
                self.cloud_folder_uri = self.get_cloud_folder()
                self.last_prefs_mtime = mtime

        if os.path.isfile(SHARED_PATH):
            mtime = os.path.getmtime(SHARED_PATH)

            if mtime != self.last_shared_mtime:
                f = open(SHARED_PATH, "r")
                self.shared.clear()
                for line in f.readlines():
                    self.shared.add(line.rstrip('\n'))
                f.close()
                self.last_shared_mtime = mtime

        return True

    def get_cloud_folder(self):
        try:
            val = self.config.get("Advanced", "Folder")

            if val is None:
                return urlparse.urljoin(
                    'file:', urllib.pathname2url(
                        os.path.expanduser("~/MEOCloud")))
            else:
                return 'file://' + val.replace('file://', '')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return urlparse.urljoin(
                'file:', urllib.pathname2url(
                    os.path.expanduser("~/MEOCloud")))

    def _check_connection(self):
        if self.sock is not None:
            return True
        return self._connect_to_helper()

    def _connect_to_helper(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except socket.error:
                pass
            self.sock = None
 
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.setblocking(0)
        try:
            path = os.path.expanduser(
                '~/.meocloud/gui/meocloud_shell_listener.socket')
            self.sock.connect(path)
        except socket.error as error:
            return False
        else:
            self.subscribe_path('/')
            GLib.io_add_watch(self.sock.fileno(), GLib.IO_IN|GLib.IO_HUP,
                              self.on_msg_read, priority=GLib.PRIORITY_LOW)
            return True

    def _clear_state(self):
        self.file_states.clear()

    def _handle_connection_error(self, error):
        self.sock = None
        self._clear_state()
        return self._connect_to_helper()

    def on_msg_read(self, source, condition):
        '''
        This function is called whenever there is data
        available on the shell helper socket.

        Important note:
        If this function returns False it will be automatically removed
        from the list of event sources and will not be called again.
        If it returns True it will be called again when the condition is
        matched.
        '''

        # TODO: other IO_ states (NVAL, etc)

        if condition & GLib.IO_HUP:
            self.sock = None
            self._clear_state()
            return False
 
        data_buffer = []
        while True:
            try:
                data = self.sock.recv(CHUNK_SIZE)
            except socket.error as error:
                # No more data available.
                if error.errno == errno.EAGAIN:
                    break
                else:
                    # Try to re-establish connection
                    if self._handle_connection_error(error):
                        continue
                    return False
                # Not reached
                break
            else:
                data_buffer.append(data)
                if len(data) < CHUNK_SIZE:
                    break

        data = ''.join(data_buffer)
        del data_buffer[:]
        self._process_data(data)

        return True

    def touch(self, path):
        item = self.nemo_items.get(path, None)
        if item is not None:
            item.invalidate_extension_info()

    def fetch_file_state(self, path):
        msg = self.file_status_msg
        msg.fileStatus.status.path = path
        self._send(serialize_thrift_msg(msg))

    def _process_data(self, data):
        paths = []
        while data:
            msg, remaining, self.read_buffer = deserialize_thrift_msg(
                data, self.read_buffer, self.recv_msg)

            if not msg:
                break

            path = msg.fileStatus.status.path
            if path in self.nemo_items:
                prev_state = self.file_states.get(path)
                state = msg.fileStatus.status.state
                if state != prev_state:
                    self.file_states[path] = state
                    paths.append(path)

            data = remaining

        while paths:
            self.touch(paths.pop())

    def on_msg_write(self, source, condition):
        # Ensure socket is alive
        if self.sock is None:
            return False

        bytes_sent = 0
        bytes_total = len(self.write_buffer)
        try:
            while self.write_buffer and bytes_sent < MAX_WRITE_BATCH_SIZE:
                data = self.write_buffer[:CHUNK_SIZE]
                self.sock.send(data)
                bytes_sent += len(data)
                self.write_buffer = self.write_buffer[CHUNK_SIZE:]
        except socket.error as error:
            if error.errno == errno.EAGAIN:
                return True
            elif self._handle_connection_error(error):
                GLib.io_add_watch(self.sock.fileno(), GLib.IO_OUT,
                                  self.on_msg_write,
                                  priority=GLib.PRIORITY_LOW)
                return False

            else:
                self.writing = False
                return False
        else:
            self.writing = bytes_sent < bytes_total
            return self.writing

    def _send(self, data):
        if not self._check_connection():
            return

        if self.write_buffer:
            self.write_buffer += data
        else:
            self.write_buffer = data

        if self.writing:
            return

        self.writing = True
        GLib.io_add_watch(self.sock.fileno(), GLib.IO_OUT,
                          self.on_msg_write,
                          priority=GLib.PRIORITY_LOW)

    def open_in_browser(self, open_path):
        data = Message(type=MessageType.OPEN,
                       open=OpenMessage(type=OpenType.BROWSER, path=open_path))

        self._send(serialize_thrift_msg(data))

    def share_link(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.LINK,
                                          path=share_path))

        self._send(serialize_thrift_msg(data))

    def share_folder(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.FOLDER,
                                          path=share_path))

        self._send(serialize_thrift_msg(data))

    def subscribe_path(self, sub_path):
        data = Message(type=MessageType.SUBSCRIBE_PATH,
                       subscribe=SubscribeMessage(type=SubscribeType.SUBSCRIBE,
                                                  path=sub_path))

        self._send(serialize_thrift_msg(data))

    def uri_to_full_path(self, uri):
        path = urllib.unquote(uri)
        path = path.replace('file://', '')
        return path if path else '/'

    def uri_to_path(self, uri):
        path = urllib.unquote(uri)
        path = path.replace(self.cloud_folder_uri, '')
        return path if path else '/'

    def valid_uri(self, uri):
        return uri.startswith(self.cloud_folder_uri)

    def changed_cb(self, i):
        del i

    def update_file_info(self, item):
        uri = item.get_uri()
        if not self.valid_uri(uri):
            return Nemo.OperationResult.FAILED

        path = self.uri_to_path(uri)

        self.nemo_items[path] = item
        state = self.file_states.get(path)
        if state is not None:
            item.add_emblem(FILE_STATE_TO_EMBLEM.get(state,
                                                     'emblem-important'))
            item.connect('changed', self.changed_cb)

            if path in self.shared:
                item.add_emblem('emblem-shared')
            return Nemo.OperationResult.COMPLETE

        self.fetch_file_state(path)
        return Nemo.OperationResult.FAILED
 
    def get_file_items(self, window, files):
        if len(files) != 1:
            return

        item = files[0]
        uri = item.get_uri()

        if uri == self.cloud_folder_uri:
            return
        if not self.valid_uri(uri):
            return

        full_path = self.uri_to_full_path(uri)
        uri = self.uri_to_path(uri)

        top_menuitem = Nemo.MenuItem.new('MEOCloudMenuProvider::MEOCloud',
                                         'MEO Cloud', '', '')

        submenu = Nemo.Menu()
        top_menuitem.set_submenu(submenu)

        link_menuitem = Nemo.MenuItem.new('MEOCloudMenuProvider::Copy',
                                          _('Copy Link'), '', '')
        link_menuitem.connect("activate", lambda w: self.share_link(uri))
        submenu.append_item(link_menuitem)

        if not os.path.isfile(full_path):
            share_menuitem = Nemo.MenuItem.new(
                'MEOCloudMenuProvider::Share', _('Share Folder'), '', '')
            share_menuitem.connect("activate", lambda w:
                                   self.share_folder(uri))
            submenu.append_item(share_menuitem)

        browser_menuitem = Nemo.MenuItem.new(
            'MEOCloudMenuProvider::Browser', _('Open in Browser'), '', '')
        browser_menuitem.connect("activate", lambda w:
                                 self.open_in_browser(uri))
        submenu.append_item(browser_menuitem)

        return top_menuitem,

    def get_background_items(self, window, item):
        return None,