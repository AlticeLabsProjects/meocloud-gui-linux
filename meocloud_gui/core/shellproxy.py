import os
import socket, select
from meocloud_gui.stoppablethread import StoppableThread
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH, LOGGER_NAME, SHELL_PROXY_SOCKET_ADDRESS

# Logging
import logging
from meocloud_gui.protocol.shell.ttypes import FileState

log = logging.getLogger(LOGGER_NAME)


class ShellProxy(object):
    def __init__(self, status, app):
        self.app = app
        self.enabled = True
        self.status = status
        self.shell = None
        self.app_path = app.app_path
        self.cloud_home = None
        self.buffer = ''
        
        self.CONNECTION_LIST = []    # list of socket clients
        self.RECV_BUFFER = 8192 # Advisable to keep it as an exponent of 2

        try:
            os.remove(SHELL_PROXY_SOCKET_ADDRESS)
        except (OSError, IOError):
            pass
        
        self.update_prefs()

        self.server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(SHELL_PROXY_SOCKET_ADDRESS)
        self.server_socket.listen(10)
     
        # Add server socket to the list of readable connections
        self.CONNECTION_LIST.append(self.server_socket)
        
        self.thread = StoppableThread(target=self.listen)
        self.thread.start()

    def listen(self):
        while not self.thread.stopped():
            # Get the list sockets which are ready to be read through select
            read_sockets,write_sockets,error_sockets = select.select(self.CONNECTION_LIST,[],[])
     
            for sock in read_sockets:
                #New connection
                if sock == self.server_socket:
                    sockfd, addr = self.server_socket.accept()
                    self.CONNECTION_LIST.append(sockfd)
                    print "Client (%s) connected" % addr
                else:
                    try:
                        data = sock.recv(self.RECV_BUFFER)
                        while data:
                            for i, c in enumerate(data):
                                if c == '\n':
                                    self.process_msg(self.buffer + data[:i])
                                    self.buffer = ''
                                    data = data[i:]
                                    break
                            self.buffer += data
                            break
                    except:
                        print "Client (%s) is offline" % addr
                        sock.close()
                        self.CONNECTION_LIST.remove(sock)
                        continue
             
        self.server_socket.close()
        
    def process_msg(self, data):
        command = data.split('\t')[0]
        path = self.unescape(data.split('\t')[1])
        
        if command.startswith('\n'):
            command = command[1:]
        
        if command == "status":
            self.broadcast_file(path)
        elif command == "link":
            self.share_link(path)
        elif command == "folder":
            self.share_folder(path)
        elif command == "browser":
            self.open_in_browser(path)
        elif command == "home":
            self.socket_send("home", self.cloud_home, "0")
        elif command == "subscribe":
            self.shell.subscribe_path(path);

    def socket_send(self, cmd, parm, parm2):
        for sock in self.CONNECTION_LIST:
            if sock is self.server_socket:
                continue
            
            print "parm is " + parm

            msg = cmd + "\t" + self.escape(parm) + "\t" + parm2 + "\n";
            print "sending " + msg
            
            try:
                sock.send(msg)
            except socket.error:
                sock.close()
                self.CONNECTION_LIST.remove(sock)

    def unescape(self, path):
        return path.replace('\\t', '\t').replace('\\n', '\n').replace('\\\\', '\\')

    def escape(self, path):
        return path.replace('\\', '\\\\').replace('\t', '\\t').replace('\n', '\\n')

    def broadcast_file(self, short_path):
        print "broadcasting " + short_path
        
        if short_path in self.shell.file_states:
            if self.shell.file_states[short_path] == FileState.SYNCING:
                self.socket_send("status", short_path, "1")
            elif self.shell.file_states[short_path] == FileState.IGNORED:
                self.socket_send("status", short_path, "2")
            elif self.shell.file_states[short_path] == FileState.ERROR:
                self.socket_send("status", short_path, "2")
            else:
                self.socket_send("status", short_path, "0")
        else:
            self.shell.update_file_status(short_path)

    def update_prefs(self):
        if self.enabled:
            prefs = Preferences()
            self.cloud_home = prefs.get('Advanced', 'Folder',
                                        CLOUD_HOME_DEFAULT_PATH)
            log.info(
                'ShellProxy.update_prefs: cloud_home is ' + self.cloud_home)
            self.socket_send("home", self.cloud_home, "0")

    def share_folder(self, path):
        self.enable()
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_folder(path)

    def share_link(self, path):
        self.enable()
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_link(path)

    def open_in_browser(self, path):
        self.enable()
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.open_in_browser(path)
