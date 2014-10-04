import locale
import sys
import base64
import os
import math
import urlparse
import urllib
import logging
import logging.handlers
import shutil
import dbus
import hashlib
import hmac

from contextlib import contextmanager
from functools import partial

from gi.repository import GLib, Gio, Gtk, Gdk
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import (CLOUD_HOME_DEFAULT_PATH, CONFIG_PATH,
                                    UI_CONFIG_PATH, LOGGER_NAME, LOG_PATH,
                                    DEBUG_ON_PATH, DEBUG_OFF_PATH,
                                    DEV_MODE, BETA_MODE,
                                    PURGEMETA_PATH, PURGEALL_PATH)
from meocloud_gui.stoppablethread import StoppableThread


MACALGO = hashlib.sha256
MACSIZE = len(MACALGO().digest())

@contextmanager
def gdk_threads_lock():
    Gdk.threads_enter()
    try:
        yield
    finally:
        Gdk.threads_leave()


def init_logging(log_handler):
    debug_off = os.path.isfile(DEBUG_OFF_PATH)

    if debug_off:
        force_remove(DEBUG_ON_PATH)
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
        logger.addHandler(log_handler)
        logger.setLevel(logging.DEBUG)
        touch(DEBUG_ON_PATH)


def purge_all():
    touch(PURGEALL_PATH)


def purge_meta():
    touch(PURGEMETA_PATH)


def create_required_folders(prefs):
    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)

    if not os.path.exists(cloud_home):
        os.makedirs(cloud_home)
        os.chmod(cloud_home, 0700)
        purge_meta()
    if not os.path.exists(CONFIG_PATH):
        os.makedirs(CONFIG_PATH)
        os.chmod(CONFIG_PATH, 0700)
    if not os.path.exists(UI_CONFIG_PATH):
        os.makedirs(UI_CONFIG_PATH)
        os.chmod(UI_CONFIG_PATH, 0700)


def clean_cloud_path(prefs):

    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)

    if os.path.exists(cloud_home):
        if os.listdir(cloud_home):
            dialog = Gtk.MessageDialog(
                None, 0, Gtk.MessageType.QUESTION,
                Gtk.ButtonsType.YES_NO,
                _("The MEOCloud folder ({0}) already exists. If you want to "
                  "use it, the contents will be synchronized to your account. "
                  "Would you like to continue?").format(cloud_home))
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.NO:
                assert False
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
    except EnvironmentError:
        logging.getLogger(LOGGER_NAME).warning(
            "utils.create_startup_file: error creating startup file")


def clean_bookmark(prefs):
    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)
    cloud_home = urlparse.urljoin('file:', urllib.pathname2url(cloud_home))

    folder_path = os.path.join(os.path.expanduser('~'),
                               '.config/gtk-3.0')
    file_path = os.path.join(folder_path, 'bookmarks')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    if os.path.isfile(file_path):
        f = open(file_path, 'r')
        text = f.read()
        f.close()

        f = open(file_path, 'w')
        f.write(text.replace("" + cloud_home + " MEOCloud", ""))
        f.close()


def create_bookmark(prefs):
    cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)
    cloud_home = urlparse.urljoin('file:', urllib.pathname2url(cloud_home))

    folder_path = os.path.join(os.path.expanduser('~'), '.config/gtk-3.0')
    file_path = os.path.join(folder_path, 'bookmarks')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    try:
        if os.path.isfile(file_path):
            with open(file_path, 'r') as f:
                text = f.read()
                if cloud_home in text:
                    return
                elif " MEOCloud" in text:
                    file(cloud_home, 'w').writelines(
                        [l for l in file(cloud_home).readlines()
                         if ' MEOCloud' not in l])

            f = open(file_path, 'a')
            f.write("\n" + cloud_home + " MEOCloud\n")
            f.close()
        else:
            f = open(file_path, 'w')
            f.write(cloud_home + " MEOCloud\n")
            f.close()
    except EnvironmentError:
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
        s = round(size / p, 2)
        if s > 0:
            return '%s %s' % (s, size_name[i])
        else:
            return '0 B'
    else:
        return '0 B'


def convert_time(n):
    locale.setlocale(locale.LC_ALL, '')

    if locale.getlocale()[0][0:2] == "pt":
        time_units = [(60, 'minuto'), (60, 'hora'), (24, 'dia')]
        final_unit_name = 'segundo'
    else:
        time_units = [(60, 'minute'), (60, 'hour'), (24, 'day')]
        final_unit_name = 'second'

    for unit_size, unit_name in time_units:
        if n >= unit_size:
            n //= unit_size
            final_unit_name = unit_name
        else:
            break
    if n != 1:
        final_unit_name += 's'
    return '{0} {1}'.format(n, final_unit_name)


def move_folder_async(src, dst, callback=None):
    def move_folder_thread(src, dst, callback):
        error = True
        if not os.listdir(dst):
            os.rmdir(dst)
            cloud_home = dst
        else:
            srcname = os.path.basename(src)
            cloud_home = os.path.join(dst, srcname)
            dst = cloud_home

        try:
            log = logging.getLogger(LOGGER_NAME)
            shutil.move(src, dst)
            log.info('Moved folder {0!r} to {1!r}'.format(src, dst))
            error = False
        except EnvironmentError as err:
            log.warn('Error while moving folder {0!r} to {1!r}: {2}'.
                     format(src, dst, err))

        if callback is not None:
            GLib.idle_add(lambda: callback(cloud_home, error))

    StoppableThread(
        target=move_folder_thread, args=(src, dst, callback)).start()


def get_error_code(status_code):
    # most significant byte
    return status_code >> 24


def get_sync_code(status_code):
    # least significant byte
    return status_code & 0xff


def use_headerbar():
    try:
        with open('/etc/lsb-release', 'rb') as lsb_f:
            lsb = lsb_f.read()
            if 'elementary OS' in lsb:
                return True
    except EnvironmentError:
        pass

    try:
        bus = dbus.SessionBus()
        versionservice = bus.get_object('org.gnome.Shell', '/org/gnome/Shell')
        properties_manager = dbus.Interface(
            versionservice, 'org.freedesktop.DBus.Properties')
        version = properties_manager.Get('org.gnome.Shell', 'ShellVersion')
        return True if version is not None else False
    except dbus.exceptions.DBusException:
        return False


#RC4 Implementation
def rc4_crypt(data, key, drop_n=0):
    S = range(256)
    j = 0
    out = []

    # KSA Phase
    for i in xrange(256):
        j = (j + S[i] + ord(key[i % len(key)])) % 256
        S[i], S[j] = S[j], S[i]

    i = j = 0

    # Ignore first bytes in keystream due to known bias
    if drop_n > 0:
        for b in xrange(drop_n):
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]

    # PRGA Phase
    for char in data:
        if drop_n == 0:
            i = j = 0
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(chr(ord(char) ^ S[(S[i] + S[j]) % 256]))

    return ''.join(out)

rc4_drop768 = partial(rc4_crypt, drop_n=768)


# function that encrypts data with RC4 and decodes it in base64 as default
# for other types of data encoding use a different encode parameter
# Use None for no encoding
def encrypt(data, key, encode=base64.b64encode):
    data = rc4_crypt(data, key)

    if encode:
        data = encode(data)

    return data


# function that decrypts data with RC4 and decodes it in base64 as default
# for other types of data encoding use a different decode parameter
# Use None for no decoding
def decrypt(data, key, decode=base64.b64decode):
    if decode:
        data = decode(data)

    return rc4_crypt(data, key)


def mac(data, key):
    _mac = hmac.new(key, msg=data, digestmod=MACALGO)
    return _mac.digest()


def force_remove(path, log=None):
    try:
        os.remove(path)
    except EnvironmentError as enve:
        if log:
            log('Could not remove {0!r}: {1}'.format(path, enve))


def touch(path, log=None):
    try:
        with open(path, 'a') as _:
            pass
    except EnvironmentError as enve:
        if log:
            log('Could not touch {0!r}: {1}'.
                format(path, enve))
