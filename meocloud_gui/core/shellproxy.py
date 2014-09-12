import os
import socket
import select
import threading
import errno

from meocloud_gui.stoppablethread import StoppableThread
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (
    CLOUD_HOME_DEFAULT_PATH,
    LOGGER_NAME,
    SHELL_PROXY_SOCKET_ADDRESS)

# Logging
import logging
from meocloud_gui.protocol.shell.ttypes import FileState

log = logging.getLogger(LOGGER_NAME)

PROTO_EOL = '\n'
PROTO_SEP = '\t'
CHUNK_SIZE = 8192

ESCAPE_MAP = {
    '\t': '\\t',
    '\n': '\\n',
    '\\': '\\\\',
}


class Client(object):
    __slots__ = ('recvbuf', 'sendbuf', 'socket', 'epoll')

    def __init__(self, socket, epoll):
        self.socket = socket
        self.epoll = epoll
        self.recvbuf = b''
        self.sendbuf = b''


class ShellProxy(object):
    errormask = select.EPOLLERR | select.EPOLLHUP
    readmask = select.EPOLLIN | errormask
    writemask = select.EPOLLOUT

    def __init__(self, status, app):
        self.app = app
        self.status = status
        self.shell = None
        self.app_path = app.app_path
        self.cloud_home = None
        self.clients_lock = threading.Lock()
        self.clients = {}

        try:
            os.remove(SHELL_PROXY_SOCKET_ADDRESS)
        except EnvironmentError:
            pass

        self.update_prefs()

        self.thread = StoppableThread(target=self.listen)

        self.command_to_handler = {
            'status': self.broadcast_file_status,
            'link': self.share_link,
            'folder': self.share_folder,
            'browser': self.open_in_browser,
            'home': self.send_cloud_home,
            'subscribe': self.subscribe_path,
        }

    def _disconnect(self, client):
        fd = client.socket.fileno()
        try:
            client.epoll.unregister(fd)
        except IOError:
            pass
        try:
            client.socket.close()
        except socket.error:
            pass
        try:
            with self.clients_lock:
                del self.clients[fd]
        except KeyError:
            pass

    def listen(self):
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(SHELL_PROXY_SOCKET_ADDRESS)
        server_socket.listen(10)
        server_socket.setblocking(0)

        epoll = select.epoll()
        epoll.register(server_socket.fileno(), self.readmask)

        while not self.thread.stopped():
            try:
                events = epoll.poll(10)
            except (IOError, OSError) as ioe:
                if ioe.errno == errno.EINTR:
                    continue
                break

            for fd, event in events:
                # New connection
                if fd == server_socket.fileno():
                    sock, _ = server_socket.accept()
                    sock.setblocking(0)
                    epoll.register(sock.fileno(), self.readmask)
                    with self.clients_lock:
                        self.clients[sock.fileno()] = Client(sock, epoll)
                    continue

                client = self.clients.get(fd)
                if client is None:
                    log.warn('Got activity for unknown client.')
                    epoll.unregister(fd)
                    continue

                # Socket has data to read
                if event & select.EPOLLIN:
                    try:
                        received = client.socket.recv(CHUNK_SIZE)
                    except socket.error as se:
                        if se.errno != errno.EINTR:
                            self._disconnect(client)
                        continue

                    # Check for EOF (0 bytes read)
                    if len(received) > 0:
                        client.recvbuf += received
                    else:
                        self._disconnect(client)
                        continue

                    self.process_client_requests(client)

                    # Check if there is data to send
                    if client.sendbuf:
                        epoll.modify(fd, self.readmask | self.writemask)

                # Socket is ready to write
                elif event & select.EPOLLOUT:
                    with self.clients_lock:
                        try:
                            bytes_sent = client.socket.send(client.sendbuf)
                        except socket.error as se:
                            if se.errno != errno.EINTR:
                                self._disconnect(client)
                            continue

                        client.sendbuf = client.sendbuf[bytes_sent:]
                        if not client.sendbuf:
                            # No more data to write. Wait for requests only
                            epoll.modify(fd, self.readmask)

                # Errors and disconnects
                elif event & self.errormask:
                    self._disconnect(client)

        for fd, client in self.clients.iteritems():
            epoll.unregister(fd)
            client.socket.close()

        self.clients.clear()
        epoll.close()
        server_socket.close()

    def process_client_requests(self, client):
        while True:
            eol_offset = client.recvbuf.find(PROTO_EOL)
            if eol_offset == -1:
                return

            msg = client.recvbuf[:eol_offset]
            # + 1 to skip the EOL character
            client.recvbuf = client.recvbuf[eol_offset + 1:]

            parts = msg.split(PROTO_SEP)
            if len(parts) > 1: 
                command = parts[0]
                path = self.unescape(parts[1])
            else:
                continue

            handler = self.command_to_handler.get(command)
            if self.shell and handler:
                handler(path, client)
 
    def unescape(self, path):
        return path.replace(
            '\\t', '\t').replace('\\n', '\n').replace('\\\\', '\\')

    def escape(self, path):
        escaped = []
        for c in path:
            escaped.append(ESCAPE_MAP.get(c, c))
        return ''.join(escaped)

    filestate_to_code = {
        FileState.SYNCING: '1',
        FileState.IGNORED: '2',
        FileState.ERROR: '2',
    }

    def broadcast_file_status(self, path, client=None):
        state = self.shell.file_states.get(path, None)
        if state is not None:
            code = self.filestate_to_code.get(state, '0')
            msg = PROTO_SEP.join(('status', self.escape(path), code)) + \
                  PROTO_EOL
            self._broadcast_msg(msg)
        else:
            self.shell.update_file_status(path)

    def _broadcast_msg(self, msg):
        with self.clients_lock:
            for client in self.clients.itervalues():
                client.sendbuf += msg
                client.epoll.modify(client.socket.fileno(), self.readmask|self.writemask)

    def update_prefs(self):
        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)
        log.info(
            'ShellProxy.update_prefs: cloud_home is {0!r}'.
            format(self.cloud_home))

        msg = PROTO_SEP.join(('home', self.cloud_home, '0')) + PROTO_EOL
        self._broadcast_msg(msg)

    def share_folder(self, path, client=None):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.share_folder(path)

    def share_link(self, path, client=None):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.share_link(path)

    def open_in_browser(self, path, client=None):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.open_in_browser(path)

    def send_cloud_home(self, path, client=None):
        msg = PROTO_SEP.join(('home', self.cloud_home, '0')) + PROTO_EOL
        with self.clients_lock:
            client.sendbuf += msg
            client.epoll.modify(client.socket.fileno(),
                                self.readmask|self.writemask)
 
    def subscribe_path(self, path, client=None):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.subscribe_path(path)

    def start(self):
       self.thread.start()
