import ConfigParser
import os


class Preferences(object):
    def __init__(self):
        path = os.path.join(os.path.expanduser('~'), '.meocloud/gui/prefs.ini')
        self.config = ConfigParser.ConfigParser()
        self.config.read(path)

    def get(self, section, option, default=None):
        try:
            val = self.config.get(section, option)

            if val is None:
                return default
            else:
                return val
        except:
            return default

    def put(self, section, option, val):
        folder_path = os.path.join(os.path.expanduser('~'), '.meocloud/gui')
        file_path = os.path.join(folder_path, 'prefs.ini')

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        prefsfile = open(file_path, 'w')

        if not self.config.has_section(section):
            self.config.add_section(section)

        self.config.set(section, option, val)
        self.config.write(prefsfile)

        prefsfile.close()
