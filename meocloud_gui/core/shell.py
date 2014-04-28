import socket
import os
from time import sleep
from gi.repository import GLib
from threading import Thread
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
    def __init__(self, isDaemon, cb_file_changed=None):
        self.s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

        self.s.connect(os.path.join(UI_CONFIG_PATH,
                                    'meocloud_shell_listener.socket'))

        self.cb_file_changed = cb_file_changed
        self.syncing = []
        self.ignored = []
        self.shared = None

        try:
            self.shared = []

            if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                           'shared_directories')):
                f = open(os.path.join(UI_CONFIG_PATH,
                                      'shared_directories'), "r")
                for line in f.readlines():
                    self.shared.append(line.rstrip('\n'))
                f.close()
        except (OSError, IOError):
            self.shared = []

        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)

        self.cached = False

        log.info('Shell: starting the shell listener thread')
        self.thread = StoppableThread(target=self._listener)
        self.thread.start()

    @staticmethod
    def start(cb_file_changed):
        return Shell(False, cb_file_changed)

    def clean_syncing(self):
        for path in self.syncing:
            self.syncing.remove(path)
            utils.touch(os.path.join(self.cloud_home, path[1:]))

    def cache(self):
        del self.syncing
        self.syncing = []

        query_files = utils.get_all_paths()

        for status_file in query_files:
            status_file.path = status_file.path.replace(self.cloud_home, "")

            if status_file.path != "":
                data = Message(type=MessageType.FILE_STATUS,
                               fileStatus=FileStatusMessage(
                                   type=FileStatusType.REQUEST,
                                   status=status_file))

                self._send(thrift_utils.serialize_thrift_msg(data))

    def _listener(self):
        log.info('Shell: shell listener ready')

        while not self.thread.stopped():
            try:
                msg = self.s.recvfrom(4096)[0]
                msg = thrift_utils.deserialize(Message(), msg)
            except (EOFError, TypeError):
                log.info('Shell._listener: lost connection to socket')
                break

            if len(msg) > 0:
                msg = msg[0]

            if not hasattr(msg, 'fileStatus'):
                break

            if self.cloud_home in msg.fileStatus.status.path:
                msg.fileStatus.status.path = \
                    msg.fileStatus.status.path.replace(self.cloud_home, "")

            if msg.fileStatus.status.path != "/":
                if msg.fileStatus.status.state == FileState.SYNCING:
                    self.syncing.append(msg.fileStatus.status.path)
                elif msg.fileStatus.status.state == FileState.IGNORED:
                    if not msg.fileStatus.status.path in self.ignored:
                        self.ignored.append(msg.fileStatus.status.path)
                elif msg.fileStatus.status.path in self.syncing:
                    self.syncing.remove(msg.fileStatus.status.path)
                utils.touch(os.path.join(self.cloud_home,
                                         msg.fileStatus.status.path[1:]))

                if self.cb_file_changed is not None:
                    GLib.idle_add(self.cb_file_changed)
            else:
                utils.touch(self.cloud_home)

            if (not self.cached and
                    msg.fileStatus.status.state == FileState.READY):
                data = Message(type=MessageType.FILE_STATUS,
                               fileStatus=FileStatusMessage(
                                   type=FileStatusType.REQUEST,
                                   status=FileStatus(path="/.cloudcontrol")))

                self._send(thrift_utils.serialize_thrift_msg(data))

            if not self.cached and "/.cloudcontrol" in self.ignored:
                self.cached = True
                Thread(target=self.cache).start()

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
