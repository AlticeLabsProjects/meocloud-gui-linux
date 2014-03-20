import os
import sys

# Timeouts
DEFAULT_TIMEOUT = 3
CONNECTION_REQUIRED_TIMEOUT = 15
USER_ACTION_REQUIRED_TIMEOUT = 1200

HOME_PATH = os.path.expanduser('~')
CONFIG_PATH = os.path.join(HOME_PATH, '.meocloud')
CLOUD_HOME_DEFAULT_PATH = os.path.join(HOME_PATH, 'MEOCloud')

DEV_MODE = os.getenv('CLD_DEV', False)
DEV_SUFFIX = '-dev'
if DEV_MODE:
    CONFIG_PATH += DEV_SUFFIX
    CLOUD_HOME_DEFAULT_PATH += DEV_SUFFIX

# TODO Find a way to set this during the build process
BETA_MODE = True

CORE_BINARY_FILENAME = 'meocloudd'
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

UI_CONFIG_DB_FILE = os.path.join(UI_CONFIG_PATH, 'ui_config.yaml')

LOGGER_NAME = 'meocloud_gui'
LOG_PATH = os.path.join(UI_CONFIG_PATH, 'meocloud_gui.log')
NOTIFICATIONS_LOG_PATH = os.path.join(UI_CONFIG_PATH, 'user_notifications.log')

DAEMON_BINARY_FILENAME = 'daemon'
DAEMON_LOCK_PATH = os.path.join(UI_CONFIG_PATH, 'ui.lock')
DAEMON_PID_PATH = os.path.join(UI_CONFIG_PATH, 'ui.pid')

# seconds
CORE_WATCHDOG_PERIOD = 20
DAEMON_VERSION_CHECKER_PERIOD = 3600

DEFAULT_NOTIFS_TAIL_LINES = 10


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
        with open(version_path) as f:
            current_version = f.read().strip()
    else:
        current_version = '0.0.0 dev'
    return current_version

VERSION = _get_current_version()
