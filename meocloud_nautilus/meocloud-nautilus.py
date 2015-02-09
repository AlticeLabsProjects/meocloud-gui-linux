import ConfigParser
import socket
import sys
import errno

from gi.repository import GLib
import urlparse

import os
from importlib import import_module

cur_file, _ = os.path.splitext(os.path.basename(__file__))
BRAND = cur_file.replace('-nautilus', '')
settings = import_module('{brand}_settings'.format(brand=BRAND))

sys.path.insert(0, '/opt/{0}/libs/'.format(BRAND))
sys.path.insert(0, '/opt/{0}/gui/meocloud_gui/protocol/'.format(BRAND))

from shell.ttypes import OpenMessage, OpenType, \
    ShareMessage, ShareType, SubscribeMessage, SubscribeType

from shell.ttypes import Message, FileState, MessageType, \
    FileStatusMessage, FileStatusType, FileStatus, FileState

from gi.repository import Nautilus, GObject
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
MAX_WRITE_BATCH_SIZE = 32 * 1024


PREFS_PATH = os.path.expanduser("~/.{0}/gui/prefs.ini".format(BRAND))
SHARED_PATH = os.path.expanduser("~/.{0}/gui/shared_directories".format(BRAND))

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
    filename = "mo/%s.mo" % (locale.getlocale()[0])
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), filename)

    try:
        trans = gettext.GNUTranslations(open(path, "rb"))
    except IOError:
        trans = gettext.NullTranslations()

    trans.install()


class MEOCloudNautilus(Nautilus.InfoProvider, Nautilus.MenuProvider,
                       GObject.GObject):
    def __init__(self):
        init_localization()
        self.nautilus_items = {}
        self.file_states = {}
        self.shared = set()

        self.read_buffer = None
        self.write_buffer = []
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
            if platform.dist()[0].lower() == 'ubuntu':
                FILE_STATE_TO_EMBLEM[FileState.SYNCING] = \
                    'emblem-synchronizing-symbolic'
        except (ImportError, IndexError):
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
                        os.path.expanduser("~/{0}".format(settings.BRAND_FOLDER_NAME))))
            else:
                return 'file://' + val.replace('file://', '')
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return urlparse.urljoin(
                'file:', urllib.pathname2url(
                    os.path.expanduser("~/{0}".format(settings.BRAND_FOLDER_NAME))))

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
                '~/.{0}/gui/meocloud_shell_listener.socket'.format(BRAND))
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
        item = self.nautilus_items.get(path, None)
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
            if path in self.nautilus_items:
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
        write_buffer = ''.join(self.write_buffer)
        del self.write_buffer[:]
        bytes_total = len(write_buffer)
        try:
            while bytes_sent < MAX_WRITE_BATCH_SIZE:
                data = write_buffer[bytes_sent:bytes_sent + CHUNK_SIZE]
                if len(data) == 0:
                    break
                self.sock.send(data)
                bytes_sent += len(data)
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
        finally:
            self.write_buffer = [write_buffer[bytes_sent:], ]

    def _send(self, data):
        if not self._check_connection():
            return
 
        self.write_buffer.append(data)
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

    def changed_cb(self, item):
        del item

    def add_emblem(self, path, state):
        try:
            item = self.nautilus_items[path]
        except KeyError:
            return
        item.add_emblem(FILE_STATE_TO_EMBLEM.get(state,
                                                 'emblem-important'))
        if path in self.shared:
            item.add_emblem('emblem-shared')

    def update_file_info_full(self, provider, handle, closure, item):
        uri = item.get_uri()
        if not self.valid_uri(uri):
            return Nautilus.OperationResult.FAILED

        path = self.uri_to_path(uri)
        state = self.file_states.get(path)
        saved_item = self.nautilus_items.get(path)
        if saved_item is None:
            self.nautilus_items[path] = item
            item.connect('changed', self.changed_cb)
        elif saved_item != item:
            del self.nautilus_items[path]
            self.nautilus_items[path] = item
            item.connect('changed', self.changed_cb)

        if state is not None:
           self.add_emblem(path, state)
           return Nautilus.OperationResult.COMPLETE
 
        GLib.idle_add(self._update_file_info, provider, handle, closure, item,
                      priority=GLib.PRIORITY_LOW)
        return Nautilus.OperationResult.IN_PROGRESS

    def _update_file_info(self, provider, handle, closure, item):
        path = self.uri_to_path(item.get_uri())
        state = self.file_states.get(path)
        item.connect('changed', self.changed_cb)

        self.fetch_file_state(path)
        Nautilus.info_provider_update_complete_invoke(
            closure, provider, handle,
            Nautilus.OperationResult.COMPLETE)

        return False 

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

        top_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::MEOCloud',
                                             settings.BRAND_PROGRAM_NAME, '', '')

        submenu = Nautilus.Menu()
        top_menuitem.set_submenu(submenu)

        link_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::Copy',
                                              _('Copy Link'), '', '')
        link_menuitem.connect("activate", lambda w: self.share_link(uri))
        submenu.append_item(link_menuitem)

        if not os.path.isfile(full_path):
            share_menuitem = Nautilus.MenuItem.new(
                'MEOCloudMenuProvider::Share', _('Share Folder'), '', '')
            share_menuitem.connect("activate", lambda w:
                                   self.share_folder(uri))
            submenu.append_item(share_menuitem)

        browser_menuitem = Nautilus.MenuItem.new(
            'MEOCloudMenuProvider::Browser', _('Open in Browser'), '', '')
        browser_menuitem.connect("activate", lambda w:
                                 self.open_in_browser(uri))
        submenu.append_item(browser_menuitem)

        return top_menuitem,

    def get_background_items(self, window, item):
        return None,
