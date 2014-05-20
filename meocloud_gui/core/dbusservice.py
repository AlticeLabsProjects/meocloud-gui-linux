import os.path
import dbus
import dbus.service
from meocloud_gui.preferences import Preferences
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH, LOGGER_NAME

# Logging
import logging
from meocloud_gui.protocol.shell.ttypes import FileState

log = logging.getLogger(LOGGER_NAME)


# TODO: Kill D-Bus. Requires the Dolphin and Thunar extensions to be rewritten.
class DBusService(dbus.service.Object):
    def __init__(self, status, app_path):
        bus_name = dbus.service.BusName('pt.meocloud.dbus',
                                        bus=dbus.SessionBus(),
                                        allow_replacement=True,
                                        replace_existing=True,
                                        do_not_queue=True)
        dbus.service.Object.__init__(self, bus_name, '/pt/meocloud/dbus')
        self.status = status
        self.shell = None
        self.app_path = app_path
        self.cloud_home = None
        self.update_prefs()
        log.info('DBusService: initialized')

    def update_prefs(self):
        prefs = Preferences()
        self.cloud_home = prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)
        log.info('DBusService.update_prefs: cloud_home is ' + self.cloud_home)

    @dbus.service.method('pt.meocloud.dbus')
    def Status(self):
        return self.status

    @dbus.service.method('pt.meocloud.dbus')
    def FileInCloud(self, path):
        cloud_home = self.cloud_home
        path = unicode(path).encode('utf-8')

        if os.path.samefile(path, cloud_home):
            return False, False, False, False
        elif path.startswith(cloud_home + "/"):
            if self.shell is None:
                is_syncing = False
                is_ignored = False
                is_shared = False
            else:
                short_path = path.replace(cloud_home, '')

                is_syncing = False
                is_ignored = False
                is_shared = False

                if short_path in self.shell.file_states:
                    if self.shell.file_states[short_path] == FileState.SYNCING:
                        is_syncing = True
                    if self.shell.file_states[short_path] == FileState.IGNORED:
                        is_ignored = True
                    if self.shell.file_states[short_path] == FileState.ERROR:
                        is_ignored = True

                    is_shared = short_path in self.shell.shared
                else:
                    self.shell.update_file_status(short_path)

            return True, is_syncing, \
                is_ignored, is_shared
        else:
            return False, False, False, False

    @dbus.service.method('pt.meocloud.dbus')
    def FileSyncing(self, path):
        cloud_home = self.cloud_home
        path = unicode(path).encode('utf-8')

        if os.path.samefile(path, cloud_home):
            return False
        else:
            if self.shell is None:
                is_syncing = False
            else:
                short_path = path.replace(cloud_home, '')

                if short_path in self.shell.file_states:
                    is_syncing = (
                        self.shell.file_states[short_path] == FileState.SYNCING)
                else:
                    is_syncing = False
                    self.shell.update_file_status(short_path)

            return is_syncing

    @dbus.service.method('pt.meocloud.dbus')
    def FileIgnored(self, path):
        cloud_home = self.cloud_home
        path = unicode(path).encode('utf-8')

        if os.path.samefile(path, cloud_home):
            return False
        else:
            short_path = path.replace(cloud_home, '')

            if short_path in self.shell.file_states:
                is_ignored = (
                    self.shell.file_states[short_path] == FileState.IGNORED)

                if not is_ignored:
                    is_ignored = (
                        self.shell.file_states[short_path] == FileState.ERROR)
            else:
                is_ignored = False
                self.shell.update_file_status(short_path)

            return is_ignored

    @dbus.service.method('pt.meocloud.dbus')
    def FileShared(self, path):
        cloud_home = self.cloud_home
        path = unicode(path).encode('utf-8')

        if os.path.samefile(path, cloud_home):
            return False
        else:
            if self.shell is None:
                is_shared = False
            else:
                is_shared = path.replace(cloud_home, '') in self.shell.shared

            return is_shared

    @dbus.service.method('pt.meocloud.dbus')
    def ShareFolder(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_folder(path)

    @dbus.service.method('pt.meocloud.dbus')
    def ShareLink(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.share_link(path)

    @dbus.service.method('pt.meocloud.dbus')
    def OpenInBrowser(self, path):
        path = unicode(path).encode('utf-8')
        if path.startswith(self.cloud_home):
            path = path.replace(self.cloud_home, '')
        if self.shell is not None:
            self.shell.open_in_browser(path)

    @dbus.service.method('pt.meocloud.dbus')
    def GetCloudHome(self):
        return self.cloud_home

    @dbus.service.method('pt.meocloud.dbus')
    def GetAppPath(self):
        return self.app_path
