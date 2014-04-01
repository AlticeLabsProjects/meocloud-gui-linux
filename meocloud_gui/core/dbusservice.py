import os.path
import dbus
import dbus.service
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH, LOGGER_NAME

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class DBusService(dbus.service.Object):
    def __init__(self, status):
        bus_name = dbus.service.BusName('pt.meocloud.dbus',
                                        bus=dbus.SessionBus(),
                                        allow_replacement=True,
                                        replace_existing=True,
                                        do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, '/pt/meocloud/dbus')
        self.status = status
        self.shell = None
        self.update_prefs()
        log.info('DBusService: initialized')

    def update_prefs(self):
        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)

    @dbus.service.method('pt.meocloud.dbus')
    def Status(self):
        return self.status

    @dbus.service.method('pt.meocloud.dbus')
    def FileInCloud(self, path):
        cloud_home = self.cloud_home
        path = unicode(path).encode('utf-8')

        if os.path.samefile(path, cloud_home):
            return False, False
        else:
            if self.shell is None:
                is_syncing = False
            else:
                is_syncing = path.replace(cloud_home, '') in self.shell.syncing

            return path.startswith(cloud_home), is_syncing

    @dbus.service.method('pt.meocloud.dbus')
    def ShareFolder(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.share_folder(path)

    @dbus.service.method('pt.meocloud.dbus')
    def ShareLink(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.share_link(path)

    @dbus.service.method('pt.meocloud.dbus')
    def OpenInBrowser(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        self.shell.open_in_browser(path)

    @dbus.service.method('pt.meocloud.dbus')
    def GetCloudHome(self):
        return self.cloud_home
