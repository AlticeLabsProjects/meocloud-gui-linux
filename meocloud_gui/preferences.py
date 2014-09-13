import ConfigParser
import os
import errno

from meocloud_gui.constants import UI_CONFIG_PATH


class Preferences(object):
    def __init__(self):
        self.path = os.path.join(UI_CONFIG_PATH, 'prefs.ini')
        self._set_permissions()
        self.config = ConfigParser.ConfigParser()
        self.creds = None
        self._load()

    def _set_permissions(self):
        try:
            os.chmod(self.path, 0600)
        except OSError:
            pass

    def _load(self):
        self.config.read(self.path)

    def set_credential_store(self, creds):
        self.creds = creds

    def save(self):
        self._set_permissions()
        for i in xrange(2):
            try:
                prefsfile = open(self.path, 'wb')
            except EnvironmentError as enve:
                if enve.errno == errno.ENOENT and i == 0:
                    parent = os.path.dirname(self.path)
                    os.makedirs(parent)
            else:
                self.config.write(prefsfile)
                prefsfile.close()
                self._load()
                break

    def get(self, section, option, default=None):
        try:
            val = self.config.get(section, option)
            return val if val is not None else default
        except ConfigParser.Error:
            return default

    def put(self, section, option, val):
        if not self.config.has_section(section):
            self.config.add_section(section)
        self.config.set(section, option, val)

    def remove(self, section, option):
        try:
            self.config.remove_option(section, option)
        except ConfigParser.NoSectionError:
            pass
