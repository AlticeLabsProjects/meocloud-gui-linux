import os
import sys
from settings import BRAND, BRAND_FOLDER_NAME

# Timeouts
DEFAULT_TIMEOUT = 3
CONNECTION_REQUIRED_TIMEOUT = 15

HOME_PATH = os.path.expanduser('~')
CONFIG_PATH = os.path.join(HOME_PATH, '.{0}'.format(BRAND))
CLOUD_HOME_DEFAULT_PATH = os.path.join(HOME_PATH, BRAND_FOLDER_NAME)

CLIENT_ID = "clientID"
AUTH_KEY = "authKey"

DEV_MODE = os.getenv('CLD_DEV', False)
DEV_SUFFIX = '-dev'
if DEV_MODE:
    CONFIG_PATH += DEV_SUFFIX
    CLOUD_HOME_DEFAULT_PATH += DEV_SUFFIX
    CLIENT_ID += DEV_SUFFIX
    AUTH_KEY += DEV_SUFFIX

# TODO Find a way to set this during the build process
BETA_MODE = True

CORE_BINARY_FILENAME = '{0}d'.format(BRAND)
CORE_LOCK_PATH = os.path.join(CONFIG_PATH, 'daemon.lock')
CORE_PID_PATH = os.path.join(CONFIG_PATH, 'daemon.pid')

PURGEMETA_PATH = os.path.join(CONFIG_PATH, 'purgemeta')
PURGEALL_PATH = os.path.join(CONFIG_PATH, 'purgeall')
DEBUG_ON_PATH = os.path.join(CONFIG_PATH, 'debug.on')
DEBUG_OFF_PATH = os.path.join(CONFIG_PATH, 'debug.off')

UI_CONFIG_PATH = os.path.join(CONFIG_PATH, 'gui')

CORE_LISTENER_SOCKET_ADDRESS = os.path.join(UI_CONFIG_PATH,
                                            'meocloud_core_listener.socket')
DAEMON_LISTENER_SOCKET_ADDRESS = os.path.join(UI_CONFIG_PATH,
                                              'meocloud_daemon_listener.socket'
                                              )
SHELL_LISTENER_SOCKET_ADDRESS = os.path.join(UI_CONFIG_PATH,
                                             'meocloud_shell_listener.socket'
                                             )
SHELL_PROXY_SOCKET_ADDRESS = os.path.join(UI_CONFIG_PATH,
                                          'meocloud_shell_proxy.socket'
                                          )

LOGGER_NAME = '{0}_gui'.format(BRAND)
LOG_PATH = os.path.join(UI_CONFIG_PATH, '{0}_gui.log'.format(BRAND))

READBUF_SIZE = 16 * 1024
CHUNK_SIZE = 4 * 1024
MAX_WRITE_BATCH_SIZE = 64 * 1024


def get_own_dir(own_filename):
    if getattr(sys, "frozen", False):
        own_path = sys.executable
    else:
        own_path = os.path.join(os.getcwd(), own_filename)
    return os.path.dirname(own_path)


def _get_current_version():
    if not DEV_MODE:
        own_dir = get_own_dir(__file__)
        version_path = os.path.join(own_dir, 'VERSION')
        try:
            with open(version_path) as f:
                current_version = f.read().strip()
        except IOError:
            current_version = 'unknown version'
    else:
        current_version = '0.0.0 dev'
    return current_version

VERSION = _get_current_version()
