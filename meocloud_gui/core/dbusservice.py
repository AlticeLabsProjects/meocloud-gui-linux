import os.path
import dbus
import dbus.service
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH


class DBusService(dbus.service.Object):
    def __init__(self, status):
        bus_name = dbus.service.BusName('pt.meocloud.dbus',
                                        bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/pt/meocloud/dbus')
        self.status = status
        self.prefs = Preferences()

    @dbus.service.method('pt.meocloud.dbus')
    def status(self):
        return self.status

    @dbus.service.method('pt.meocloud.dbus')
    def file_in_cloud(self, path):
        cloud_home = Preferences().get('Advanced', 'Folder',
                                       CLOUD_HOME_DEFAULT_PATH)

        if os.path.samefile(path, cloud_home):
            return False
        else:
            return path.startswith(cloud_home)

    @dbus.service.method('pt.meocloud.dbus')
    def get_cloud_home(self):
        return self.prefs.get('Advanced', 'Folder',
                              CLOUD_HOME_DEFAULT_PATH)
