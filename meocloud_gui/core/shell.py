import socket

from gi.repository import GLib
import errno
from meocloud_gui import thrift_utils

from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (
    CLOUD_HOME_DEFAULT_PATH,
    LOGGER_NAME,
    SHELL_LISTENER_SOCKET_ADDRESS,
    CHUNK_SIZE,
    MAX_WRITE_BATCH_SIZE)

from meocloud_gui.protocol.shell.ttypes import (
    Message,
    MessageType,
    SubscribeMessage,
    SubscribeType,
    ShareMessage,
    OpenMessage,
    ShareType,
    OpenType,
    FileStatusMessage,
    FileStatusType,
    FileStatus)

from meocloud_gui.data_structures import BoundedOrderedDict

# Logging
import logging
from meocloud_gui.thrift_utils import (
    serialize_thrift_msg,
    deserialize_thrift_msg)

log = logging.getLogger(LOGGER_NAME)


# TODO: Kill ShellHelper socket handling. Requires D-Bus to be killed.
class Shell(object):
    def __init__(self, proxy):
        self.proxy = proxy
        self.proxy.shell = self

        self.prefs = proxy.prefs

        self.file_states = BoundedOrderedDict(maxsize=10000)

        self.read_buffer = None
        self.write_buffer = None
        self.writing = False
        self.sock = None

        self.recv_msg = Message()
        self.file_status_msg = \
            Message(type=MessageType.FILE_STATUS,
                    fileStatus=FileStatusMessage(
                        type=FileStatusType.REQUEST,
                        status=FileStatus()))

        self.disconnected = False
        self.failed = 0

        self.cloud_home = self.prefs.get('Advanced', 'Folder',
                                         CLOUD_HOME_DEFAULT_PATH)

        log.info('Shell: started the shell listener')

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
            self.sock.connect(SHELL_LISTENER_SOCKET_ADDRESS)
        except socket.error:
            return False
        else:
            GLib.io_add_watch(self.sock.fileno(), GLib.IO_IN | GLib.IO_HUP,
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

    def update_file_status(self, path):
        GLib.idle_add(lambda: self._update_file_status(path))

    def open_in_browser(self, path):
        GLib.idle_add(lambda: self._open_in_browser(path))

    def share_link(self, path):
        GLib.idle_add(lambda: self._share_link(path))

    def share_folder(self, path):
        GLib.idle_add(lambda: self._share_folder(path))

    def subscribe_path(self, path):
        GLib.idle_add(lambda: self._subscribe_path(path))

    def _update_file_status(self, path):
        msg = self.file_status_msg
        msg.fileStatus.status.path = path
        self._send(serialize_thrift_msg(msg))

    def _open_in_browser(self, open_path):
        data = Message(type=MessageType.OPEN,
                       open=OpenMessage(type=OpenType.BROWSER, path=open_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def _share_link(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.LINK,
                                          path=share_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def _share_folder(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.FOLDER,
                                          path=share_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def _subscribe_path(self, sub_path):
        data = Message(type=MessageType.SUBSCRIBE_PATH,
                       subscribe=SubscribeMessage(type=SubscribeType.SUBSCRIBE,
                                                  path=sub_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def _process_data(self, data):
        paths = []
        while data:
            msg, remaining, self.read_buffer = deserialize_thrift_msg(
                data, self.read_buffer, self.recv_msg)

            if not msg:
                break

            path = msg.fileStatus.status.path
            prev_state = self.file_states.get(path)
            state = msg.fileStatus.status.state
            if state != prev_state:
                self.file_states[path] = state
                paths.append(path)

            data = remaining

        while paths:
            self.proxy.broadcast_file_status(paths.pop())

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
