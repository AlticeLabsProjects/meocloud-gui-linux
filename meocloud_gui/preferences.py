import ConfigParser
import os
import errno

from meocloud_gui.constants import UI_CONFIG_PATH


class Preferences(object):
    def __init__(self):
        self.path = os.path.join(UI_CONFIG_PATH, 'prefs.ini')
        self.config = ConfigParser.ConfigParser()
        self.config.read(self.path)

    def get(self, section, option, default=None):
        try:
            val = self.config.get(section, option)
            return val if val is not None else default
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def put(self, section, option, val):
        for i in xrange(2):
            try:
                prefsfile = open(self.path, 'wb')
            except EnvironmentError as enve:
                if enve.errno == errno.ENOENT and i == 0:
                    parent = os.path.dirname(self.path)
                    os.makedirs(parent)
            else: 
                if not self.config.has_section(section):
                    self.config.add_section(section)
                self.config.set(section, option, val)
                self.config.write(prefsfile)
                prefsfile.close()
                break

