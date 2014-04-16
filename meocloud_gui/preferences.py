import ConfigParser
import os
from meocloud_gui.constants import UI_CONFIG_PATH


class Preferences(object):
    def __init__(self):
        path = os.path.join(UI_CONFIG_PATH, 'prefs.ini')
        self.config = ConfigParser.ConfigParser()
        self.config.read(path)

    def get(self, section, option, default=None):
        try:
            val = self.config.get(section, option)

            if val is None:
                return default
            else:
                return val
        except (ConfigParser.NoSectionError, ConfigParser.NoOptionError):
            return default

    def put(self, section, option, val):
        file_path = os.path.join(UI_CONFIG_PATH, 'prefs.ini')

        if not os.path.exists(UI_CONFIG_PATH):
            os.makedirs(UI_CONFIG_PATH)

        prefsfile = open(file_path, 'w')

        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, option, val)
        self.config.write(prefsfile)

        prefsfile.close()
