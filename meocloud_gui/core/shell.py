from _socket import SHUT_RD
import socket
import os
from thrift.protocol.TProtocol import TProtocolException
from time import sleep
from collections import namedtuple
from gi.repository import GLib
from meocloud_gui import thrift_utils
from meocloud_gui import utils
from meocloud_gui.stoppablethread import StoppableThread
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (UI_CONFIG_PATH, CLOUD_HOME_DEFAULT_PATH,
                                    LOGGER_NAME)
from meocloud_gui.protocol.shell.ttypes import (
    Message,
    MessageType,
    SubscribeMessage,
    SubscribeType,
    ShareMessage,
    OpenMessage,
    ShareType,
    OpenType,
    FileState,
    FileStatusMessage,
    FileStatusType,
    FileStatus)

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class Shell(object):
    def __init__(self):
        self.syncing = set()
        self.cached = set()
        self.ignored = set()
        self.shared = None
        self.disconnected = False
        self.failed = 0

        try:
            self.shared = set()

            if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                           'shared_directories')):
                f = open(os.path.join(UI_CONFIG_PATH,
                                      'shared_directories'), "r")
                for line in f.readlines():
                    self.shared.add(line.rstrip('\n'))
                f.close()
        except (OSError, IOError):
            self.shared = set()

        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)

        log.info('Shell: starting the shell listener thread')
        self.thread = StoppableThread(target=self._listener)

        #try:
        #    self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)#

 #           self.s.connect(os.path.join(UI_CONFIG_PATH,
 #                                       'meocloud_shell_listener.socket'))
 #       except socket.error:
 #           self.failed += 1
 #           log.warning("Shell: failed to connect")
 #           self.retry()
 #           return

 #       self.thread.start()

    def update_file_status(self, path):
        data = Message(type=MessageType.FILE_STATUS,
                       fileStatus=FileStatusMessage(
                           type=FileStatusType.REQUEST,
                           status=FileStatus(path=path)))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def retry(self):
        while self.failed < 5:
            sleep(1)
            log.debug("Shell: retrying")

            try:
                self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.s.connect(os.path.join(UI_CONFIG_PATH,
                                            'meocloud_shell_listener.socket'))
                self.thread.start()
                return
            except socket.error:
                self.failed += 1
                log.warning("Shell: failed to connect")

        log.exception("Shell: reached max retries for shell socket")

    def clean_syncing(self):
        to_notify = list(self.syncing)
        while to_notify:
            utils.touch(os.path.join(self.cloud_home, to_notify.pop()[1:]))
        self.syncing.clear()

    def process_data(self, data, socket_state):
        while data:
            msg, remaining = thrift_utils.deserialize_thrift_msg(
                data, socket_state, Message())

            if not msg:
                log.warning('Shell.process_data: invalid message')
                return

            if not hasattr(msg, 'fileStatus'):
                return

            if self.cloud_home in msg.fileStatus.status.path:
                msg.fileStatus.status.path = \
                    msg.fileStatus.status.path.replace(self.cloud_home, "")

            if msg.fileStatus.status.path != "/":
                self.cached.add(msg.fileStatus.status.path)

                if msg.fileStatus.status.state == FileState.SYNCING:
                    self.syncing.add(msg.fileStatus.status.path)
                elif msg.fileStatus.status.state == FileState.IGNORED:
                    if not msg.fileStatus.status.path in self.ignored:
                        self.ignored.add(msg.fileStatus.status.path)
                elif msg.fileStatus.status.path in self.syncing:
                    self.syncing.remove(msg.fileStatus.status.path)
                utils.touch(os.path.join(self.cloud_home,
                                         msg.fileStatus.status.path[1:]))
            else:
                utils.touch(self.cloud_home)

            data = remaining

    def _listener(self):
        log.info('Shell: shell listener ready')

        class SocketState(object):
            def __init__(self, buffer=None):
                self.buffer = buffer

        socket_state = SocketState(buffer=None)

        try:
            while not self.thread.stopped():
                try:
                    data = self.s.recvfrom(4096)
                    self.process_data(data[0], socket_state)
                except OverflowError:
                    log.info('Shell._listener: lost connection to socket')
                    return
        except Exception:
            log.exception(
                'Shell._listener: An uncatched error occurred!')

    def _send(self, data):
        #self.s.sendall(data)
        pass

    def open_in_browser(self, open_path):
        data = Message(type=MessageType.OPEN,
                       open=OpenMessage(type=OpenType.BROWSER, path=open_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def share_link(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.LINK,
                                          path=share_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def share_folder(self, share_path):
        data = Message(type=MessageType.SHARE,
                       share=ShareMessage(type=ShareType.FOLDER,
                                          path=share_path))

        self._send(thrift_utils.serialize_thrift_msg(data))

    def subscribe_path(self, sub_path):
        data = Message(type=MessageType.SUBSCRIBE_PATH,
                       subscribe=SubscribeMessage(type=SubscribeType.SUBSCRIBE,
                                                  path=sub_path))

        self._send(thrift_utils.serialize_thrift_msg(data))
