import socket
import os
from threading import Thread
from meocloud_gui import thrift_utils
from meocloud_gui import utils
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
    FileState)

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class Shell(object):
    def __init__(self, isDaemon):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        self.s.connect(os.path.join(UI_CONFIG_PATH,
                                    'meocloud_shell_listener.socket'))

        self.syncing = []
        self.ignored = []

        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)

        log.info('Shell: starting the shell listener thread')
        self._thread = Thread(target=self._listener)
        self._thread.setDaemon(isDaemon)
        self._thread.start()

    @staticmethod
    def start():
        return Shell(isDaemon=False)

    def clean_syncing(self):
        for path in self.syncing:
            self.syncing.remove(path)
            utils.touch(os.path.join(self.cloud_home, path[1:]))

    def _listener(self):
        log.info('Shell: shell listener ready')

        while True:
            try:
                msg = self.s.recvfrom(2048)[0]
                msg = thrift_utils.deserialize(Message(), msg)
            except EOFError:
                log.info('Shell._listener: lost connection to socket')
                break

            if len(msg) > 0:
                msg = msg[0]

            if msg.fileStatus.status.path != "/":
                if msg.fileStatus.status.state == FileState.SYNCING:
                    self.syncing.append(msg.fileStatus.status.path)
                elif msg.fileStatus.status.state == FileState.IGNORED:
                    self.ignored.append(msg.fileStatus.status.path)
                elif msg.fileStatus.status.path in self.syncing:
                    self.syncing.remove(msg.fileStatus.status.path)
                utils.touch(os.path.join(self.cloud_home,
                                         msg.fileStatus.status.path[1:]))
            else:
                utils.touch(self.cloud_home)

    def _send(self, data):
        self.s.sendall(data)

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