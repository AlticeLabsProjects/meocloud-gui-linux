import sys
import os
import math
import urlparse
import urllib
import logging
import logging.handlers
import shutil
from threading import Thread
from gi.repository import GLib, Gio
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (CLOUD_HOME_DEFAULT_PATH, UI_CONFIG_PATH,
                                    LOGGER_NAME, LOG_PATH, DEBUG_ON_PATH,
                                    DEBUG_OFF_PATH, DEV_MODE, BETA_MODE,
                                    PURGEMETA_PATH, PURGEALL_PATH,
                                    CONFIG_PATH)


def init_logging():
    debug_off = os.path.isfile(DEBUG_OFF_PATH)

    if debug_off:
        try:
            os.remove(DEBUG_ON_PATH)
        except OSError:
            pass
    elif DEV_MODE or BETA_MODE:
        logger = logging.getLogger(LOGGER_NAME)
        logger.propagate = False
        fmt_str = '%(asctime)s %(levelname)s %(process)d %(message)s'
        formatter = logging.Formatter(fmt_str)
        # (automatically rotated every week)
        handler = logging.handlers.TimedRotatingFileHandler(LOG_PATH,
                                                            when='W6',
                                                            backupCount=1)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        # touch
        with open(DEBUG_ON_PATH, 'a'):
            pass


def purge_all():
    if os.path.exists(CONFIG_PATH):
        purge_file = open(PURGEALL_PATH, 'w')
        purge_file.close()


def purge_meta():
    if os.path.exists(CONFIG_PATH):
        purge_file = open(PURGEMETA_PATH, 'w')
        purge_file.close()


def touch(fname, times=None):
    try:
        destination = 'pt.meocloud.shell'
        path = '/pt/meocloud/shell'
        interface = 'pt.meocloud.shell'
        method = 'UpdateFile'
        args = GLib.Variant('(s)',
                            (fname,))
        answer_fmt = None
        proxy_prpty = Gio.DBusCallFlags.NONE
        timeout = 5
        cancellable = None

        # Connect to DBus, send the DBus message
        bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        bus.call(destination, path, interface,
                 method, args, answer_fmt,
                 proxy_prpty, timeout, cancellable, None, None)
    except:
        pass


def create_required_folders():
    prefs = Preferences()

    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)

    if not os.path.exists(cloud_home):
        os.makedirs(cloud_home)
        purge_meta()
    if not os.path.exists(UI_CONFIG_PATH):
        os.makedirs(UI_CONFIG_PATH)


def clean_cloud_path():
    prefs = Preferences()

    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)

    if os.path.exists(cloud_home):
        shutil.rmtree(cloud_home)
    if not os.path.exists(cloud_home):
        os.makedirs(cloud_home)


def create_startup_file(base_path=None):
    folder_path = os.path.join(os.path.expanduser('~'),
                               '.config/autostart')
    file_path = os.path.join(folder_path, 'meocloud.desktop')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if base_path is None:
        base_path = os.getcwd()

    try:
        desktop_file = open(file_path, 'w')
        desktop_file.write("[Desktop Entry]\n")
        desktop_file.write("Type=Application\n")
        desktop_file.write("Name=MEO Cloud\n")
        desktop_file.write("Exec=" + os.path.join(base_path,
                           "meocloud-gui") + "\n")
        desktop_file.close()
    except (IOError, OSError):
        logging.getLogger(LOGGER_NAME).warning(
            "utils.create_startup_file: error creating startup file")


def clean_bookmark():
    cloud_home = Preferences().get('Advanced', 'Folder',
                                   CLOUD_HOME_DEFAULT_PATH)
    cloud_home = urlparse.urljoin('file:', urllib.pathname2url(cloud_home))

    folder_path = os.path.join(os.path.expanduser('~'),
                               '.config/gtk-3.0')
    file_path = os.path.join(folder_path, 'bookmarks')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    f = open(file_path, 'r')
    text = f.read()
    f.close()

    f = open(file_path, 'w')
    f.write(text.replace("" + cloud_home + " MEOCloud", ""))
    f.close()


def create_bookmark():
    cloud_home = Preferences().get('Advanced', 'Folder',
                                   CLOUD_HOME_DEFAULT_PATH)
    cloud_home = urlparse.urljoin('file:', urllib.pathname2url(cloud_home))

    folder_path = os.path.join(os.path.expanduser('~'),
                               '.config/gtk-3.0')
    file_path = os.path.join(folder_path, 'bookmarks')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    try:
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                if cloud_home in f.read():
                    return

            f = open(file_path, 'a')
            f.write("\n" + cloud_home + " MEOCloud\n")
            f.close()
        else:
            f = open(file_path, 'w')
            f.write(cloud_home + " MEOCloud\n")
            f.close()
    except (IOError, OSError):
        logging.getLogger(LOGGER_NAME).warning(
            "utils.create_bookmark: error creating gtk bookmark")


def test_already_running(pid_path, proc_name):
    try:
        with open(pid_path) as f:
            pid = int(f.read())
        with open('/proc/{0}/cmdline'.format(pid)) as f:
            if proc_name in f.read():
                assert pid != 0
                return pid
    except Exception:
        # Either the application is not running or we have no way
        # to find it, so assume it is not running.
        pass
    return False


def get_own_dir(own_filename):
    if getattr(sys, "frozen", False):
        own_path = sys.executable
    else:
        own_path = os.path.join(os.getcwd(), own_filename)
    return os.path.dirname(own_path)


def get_proxy(ui_config):
    proxy_url = ui_config.get('Network', 'ProxyURL', None)
    if proxy_url is None or proxy_url == "":
        proxy_url = os.getenv('http_proxy') or os.getenv('https_proxy')
    return proxy_url


def get_ratelimits(ui_config):
    download_limit = int(ui_config.get('Network', 'ThrottleDownload', 0))
    upload_limit = int(ui_config.get('Network', 'ThrottleUpload', 0))

    return download_limit, upload_limit


def convert_size(size):
    if size > 0:
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(math.floor(math.log(size, 1024)))
        p = math.pow(1024, i)
        s = round(size/p, 2)
        if (s > 0):
            return '%s %s' % (s, size_name[i])
        else:
            return '0 B'
    else:
        return '0 B'


def move_folder_async(src, dst, callback=None):
    def move_folder_thread(src, dst, callback):
        if os.listdir(dst) == []:
            os.rmdir(dst)
            cloud_home = dst
        else:
            cloud_home = os.path.join(dst, "MEOCloud")
            dst = cloud_home

        try:
            shutil.move(src, dst)

            logging.getLogger(LOGGER_NAME).warning(
                "utils.move_folder_async: Moved folder " +
                src + " to " + dst)

            if callback is not None:
                GLib.idle_add(lambda: callback(cloud_home, False))
        except (OSError, IOError, Exception):
            logging.getLogger(LOGGER_NAME).warning(
                "utils.move_folder_async: Error while moving folder " +
                src + " to " + dst)

            if callback is not None:
                GLib.idle_add(lambda: callback(cloud_home, True))

    Thread(target=move_folder_thread, args=(src, dst, callback)).start()


def get_error_code(status_code):
    # most significant byte
    return status_code >> 24
