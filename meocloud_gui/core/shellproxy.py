import os
import socket
import select
import threading

from meocloud_gui.stoppablethread import StoppableThread
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (CLOUD_HOME_DEFAULT_PATH,
                                    LOGGER_NAME,
                                    SHELL_PROXY_SOCKET_ADDRESS)

# Logging
import logging
from meocloud_gui.protocol.shell.ttypes import FileState

log = logging.getLogger(LOGGER_NAME)

class Client(object):
    __slots__ = ('recvbuf', 'sendbuf', 'socket', 'epoll')

    def __init__(self, socket, epoll):
        self.socket = socket
        self.epoll = epoll
        self.recvbuf = b''
        self.sendbuf = b''


class ShellProxy(object):
    def __init__(self, status, app):
        self.app = app
        self.status = status
        self.shell = None
        self.app_path = app.app_path
        self.cloud_home = None

        self.clients = {}

        try:
            os.remove(SHELL_PROXY_SOCKET_ADDRESS)
        except EnvironmentError:
            pass

        self.update_prefs()

        self.thread = StoppableThread(target=self.listen)

        self.command_to_handler = {
            'status': self.broadcast_file,
            'link': self.share_link,
            'folder': self.share_folder,
            'browser': self.open_in_browser,
            'home': self.send_cloud_home,
            'subscribe': self.subscribe_path, 
        }

    def listen(self):
        server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(SHELL_PROXY_SOCKET_ADDRESS)
        server_socket.listen(10)
        server_socket.setblocking(0)

        errormask = select.EPOLLERR|select.EPOLLHUP
        readmask = select.EPOLLIN|errormask
        writemask = select.EPOLLOUT

        epoll = select.epoll()
        epoll.register(serversock.fileno(), readmask)

        while not self.thread.stopped():
            events = epoll.poll(10)
            for fd, event in events:
                # New connection
                if fd == serversocket.fileno():
                    sock, addr = serversocket.accept()
                    sock.setblocking(0)
                    epoll.register(sock.fileno(), readmask)
                    self.clients[socket.fileno()] = Client(socket, epoll)
                    continue

               client = self.clients.get(fd)
               if client is None:
                    log.warn('Got activity for unknown client.')
                    epoll.unregister(fd)
                    continue

                # Socket has data to read
                if event & select.EPOLLIN:
                    client.recvbuf += client.socket.recv(CHUNK_SIZE)
                    bytes_consumed = self.process_client_requests(client)

                    # Check if we want to send responses
                    if client.sendbuf:
                        epoll.modify(fd, readmask|writemask)

                # Socket is ready to write
                elif event & select.EPOLLOUT:
                    bytes_sent = client.socket.send(client.sendbuf)
                    client.sendbuf = client.sendbuf[:bytes_sent]
                    if not client.sendbuf:
                        # No more data to write. Wait for requests only
                        epoll.modify(fd, readmask)

                # Errors and disconnects
                elif event & errormask:
                    epoll.unregister(fd)
                    client.socket.close()
                    del self.clients[fd]

        epoll.unregister(serversocket.fileno())
        for fd, client in self.clients.iteritems():
            epoll.unregiser(fd)
            client.socket.close()

        self.clients.clear()
        epoll.close()
        serversocket.close()

    def process_client_requests(self, client):
       while True:
            eol_offset = client.recvbuf.find('\n')
            if eol_offset == -1:
                return

            msg = client.recvbuf[:eol_offset]
            # + 1 to strip EOL character
            client.recvbuf = client.recvbuf[:eol_offset + 1]

            parts = client.split('\t')
            command = parts[0]
            path = self.unescape(parts[1])

            handler = self.command_to_handler.get(command)
            if handler:
                handler(client, path)
 
    def unescape(self, path):
        return path.replace(
            '\\t', '\t').replace('\\n', '\n').replace('\\\\', '\\')

    def escape(self, path):
        return path.replace(
            '\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')

    filestate_to_code = {
        FileState.SYNCING: '1',
        FileState.IGNORED: '2',
        FileState.ERROR: '2',
    }

    def broadcast_file(self, short_path):
        state = self.shell.file_states.get(short_path, None)
        if state is not None:
            code = filestate_to_code.get(state, '0')
            
                self.socket_send('status', short_path, code)
        else:
            self.shell.update_file_status(short_path)

    def update_prefs(self):
        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)
        log.info(
            'ShellProxy.update_prefs: cloud_home is {0!r}'.
            format(self.cloud_home))
        self.socket_send('home', self.cloud_home, '0')

    def share_folder(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_folder(path)

    def share_link(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_link(path)

    def open_in_browser(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.open_in_browser(path)

    def start(self):
       self.thread.start()
