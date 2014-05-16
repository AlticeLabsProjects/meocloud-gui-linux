import os
import errno
import socket as socket_module
from threading import BoundedSemaphore
from thrift.protocol.TProtocol import TProtocolException
from time import sleep

from thrift.transport import TSocket, TTransport
from thrift.protocol import TBinaryProtocol
from thrift.server.TServer import TServer

from meocloud_gui.constants import LOGGER_NAME, DEFAULT_TIMEOUT
from meocloud_gui.exceptions import ListenerConnectionFailedException
from meocloud_gui.decorators import retry, RetryFailed, TooManyRetries

import logging
log = logging.getLogger(LOGGER_NAME)

MAX_RETRIES = 3
SLEEP_TIME = 0.1
BACKOFF = 2


def serialize(msg):
    msg.validate()
    transport = TTransport.TMemoryBuffer()
    protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
    msg.write(protocol)

    data = transport.getvalue()
    transport.close()
    return data


def deserialize(msg, data):
    transport = TTransport.TMemoryBuffer(data)
    protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
    msg.read(protocol)
    msg.validate()
    remaining = data[transport.cstringio_buf.tell():]
    transport.close()

    return msg, remaining


def deserialize_thrift_msg(data, socket_state, msgobj):
    '''
    Try to deserialize data (or buf + data) into a valid
    "Message" (msgobj), as defined in the thrift ShellHelper specification
    '''
    if socket_state.buffer:
        data = ''.join((socket_state.buffer, data))
        socket_state.buffer = None
    try:
        msg, remaining = deserialize(msgobj, data)
    except (TProtocolException, EOFError, TypeError) as dex:
        log.error('Could not deserialize message: {0}'.format(dex))
        if len(data) <= 8192:
            socket_state.buffer = data
            msg = None
            remaining = None
        else:
            raise OverflowError('Message does not fit buffer.')

    return msg, remaining


def serialize_thrift_msg(msg):
    '''
    Try to serialize a "Message" (msg) into a byte stream
    "Message" is defined in the thrift ShellHelper specification
    '''
    try:
        data = serialize(msg)
    except TProtocolException as tpe:
        log.debug('Could not deserialize message: {0}'.format(tpe))
        raise

    return data


class TSimpleServer(TServer):
    """Simple single-threaded server that just pumps around one transport."""

    def __init__(self, name, *args):
        TServer.__init__(self, *args)
        self.name = name

    def serve(self):
        self.serverTransport.listen()
        while True:
            client = self.serverTransport.accept()
            itrans = self.inputTransportFactory.getTransport(client)
            otrans = self.outputTransportFactory.getTransport(client)
            iprot = self.inputProtocolFactory.getProtocol(itrans)
            oprot = self.outputProtocolFactory.getProtocol(otrans)
            try:
                while True:
                    self.processor.process(iprot, oprot)
            except (socket_module.error, TTransport.TTransportException):
                # This occurs all the time, just ignore it
                # and keep waiting for more connections
                # log.debug('{0}: Server error, will restart serving:
                # {1}'.format(self.name, e))
                pass
            finally:
                itrans.close()
                otrans.close()


class ThriftListener(object):
    def __init__(self, name, socket, processor):
        super(ThriftListener, self).__init__()
        #log.debug('{0}: Initializing...'.format(name))
        self.name = name
        self.listener_server = self.init_thrift_server(socket, processor)

    def init_thrift_server(self, socket, processor):
        """
        Creates a thrift server that listens in the given socket and
        uses the given processor
        """
        try:
            os.unlink(socket)
        except OSError as oerr:
            if oerr.errno != errno.ENOENT:
                raise

        transport = TSocket.TServerSocket(unix_socket=socket)
        tfactory = TTransport.TBufferedTransportFactory()
        pfactory = TBinaryProtocol.TBinaryProtocolAcceleratedFactory()
        listener_server = TSimpleServer(self.name, processor, transport,
                                        tfactory, pfactory)
        return listener_server

    def start(self):
        log.info('{0}: Starting to serve...'.format(self.name))
        try:
            self.listener_server.serve()
        except ListenerConnectionFailedException:
            pass
        except Exception:
            log.exception(
                '{0}: An uncatched error occurred!'.format(self.name))


class ThriftClient(object):
    def __init__(self, socket, client_class):
        self.socket = None
        self.mutex = BoundedSemaphore(1)
        self.socket = TSocket.TSocket(unix_socket=socket)
        self.transport = TTransport.TBufferedTransport(self.socket)
        self.protocol = TBinaryProtocol.TBinaryProtocolAccelerated(
            self.transport)
        self.client = client_class(self.protocol)
        self.connected = False

    def reconnect(self):
        self.close()
        self.open()

    def close(self):
        if self.transport.isOpen():
            self.transport.close()
        self.connected = False

    def open(self):
        self.transport.open()
        self.connected = True


def wrap_client_call(timeout=DEFAULT_TIMEOUT, max_retries=MAX_RETRIES,
                     sleep_time=SLEEP_TIME, backoff=BACKOFF):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            args_str_list = ['{0}'.format(arg) for arg in args]
            kwargs_str_list = \
                ['{0}={1}'.format(k, v) for k, v in kwargs.items()]
            all_args_str = ', '.join(args_str_list + kwargs_str_list)
            log.debug('{0}.{1}({2}) >>>>'.format(self.__class__.__name__,
                      f.__name__, all_args_str))
            with self.mutex:
                try:
                    self.socket.setTimeout(timeout * 1000)
                    retry_deco = retry(max_retries, sleep_time, backoff, sleep)
                    result = \
                        retry_deco(attempt_client_call)(self, f,
                                                        *args, **kwargs)
                except TooManyRetries:
                    log.warning(
                        ('{0}.{1}: Too many retries. Gave up trying to connect'
                         ' to daemon.').format(self.__class__.__name__,
                                               f.__name__))
                    raise ListenerConnectionFailedException()
            return result
        return wrapper
    return decorator


def attempt_client_call(self, f, *args, **kwargs):
    try:
        if not self.connected:
            self.reconnect()
            log.debug('{0}.{1}: reconnected'.format(self.__class__.__name__,
                                                    f.__name__))
        log.debug('{0}.{1}: will call function'.format(self.__class__.__name__,
                                                       f.__name__))
        result = f(self, *args, **kwargs)
        log.debug('{0}.{1}: result: {2}'.format(self.__class__.__name__,
                                                f.__name__, result))
        return result
    except socket_module.timeout:
        log.debug('{0}.{1}: connection attempt timed out'.format(
            self.__class__.__name__, f.__name__))
        raise
    except (socket_module.error, TTransport.TTransportException) as e:
        log.debug(('{0}.{1}: an error occurred while trying '
                  'to connect: {2}').format(self.__class__.__name__,
                                            f.__name__, e))
        # Mark client as not connected so it reconnects the next time
        self.connected = False
    raise RetryFailed()
