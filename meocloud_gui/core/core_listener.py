# Python standard library imports
import os
import subprocess
import keyring
import locale

# GLib, Gdk and Gtk
from gi.repository import GLib, Gdk, Gtk

# Notifications
from gi.repository import Notify

# Thrift related imports
from meocloud_gui.protocol.daemon_core import UI
from meocloud_gui.protocol.daemon_core.ttypes import Account
from meocloud_gui.thrift_utils import ThriftListener

# Application specific imports
from meocloud_gui.constants import LOGGER_NAME, CLOUD_HOME_DEFAULT_PATH
from meocloud_gui.core import api
from meocloud_gui.preferences import Preferences
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.strings import NOTIFICATIONS
import meocloud_gui.utils

from meocloud_gui import codes

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class CoreListener(ThriftListener):
    def __init__(self, socket, core_client, ui_config, app, ignore_sync):
        handler = CoreListenerHandler(core_client, ui_config, app, ignore_sync)
        processor = UI.Processor(handler)
        super(CoreListener, self).__init__('CoreListener', socket, processor)


class CoreListenerHandler(UI.Iface):
    def __init__(self, core_client, ui_config, app, ignore_sync):
        super(CoreListenerHandler, self).__init__()
        self.core_client = core_client
        self.ui_config = ui_config
        self.app = app
        self.setup = None
        self.ignore_sync = ignore_sync

        Notify.init('MEOCloud')

    def start_sync(self):
        self.app.core_client.setIgnoredDirectories(
            self.app.ignored_directories)

        cloud_home = self.ui_config.get('Advanced', 'Folder',
                                        CLOUD_HOME_DEFAULT_PATH)
        if not cloud_home:
            log.warning('CoreListener.start_sync: no cloud_home in config,'
                        ' will unlink and shutdown')
            api.unlink(self.core_client, self.ui_config)
        else:
            if not os.path.isdir(cloud_home):
                log.warning('CoreListener.start_sync: cloud_home was found '
                            'in config with value {0} but it is not '
                            'there'.format(cloud_home))
            else:
                self.core_client.startSync(cloud_home)

    ### THRIFT METHODS ###

    def account(self):
        log.debug('CoreListener.account() <<<<')

        account_dict = api.get_account_dict(self.ui_config)

        return Account(**account_dict)

    def beginAuthorization(self):
        log.debug('CoreListener.beginAuthorization() <<<<')
        GLib.idle_add(self.beginAuthorizationIdle)

    def beginAuthorizationIdle(self):
        self.setup = SetupWindow(self.app)
        self.setup.login_button.connect("clicked",
                                        self.beginAuthorizationBrowser)
        self.setup.show_all()

    def beginAuthorizationBrowser(self, w):
        self.setup.start_waiting()

        subprocess.Popen(["xdg-open",
                         self.core_client.authorizeWithDeviceName
                         (self.setup.device_entry.get_text())])

    def authorized(self, account):
        log.debug('CoreListener.authorized({0}) <<<<'.format(account))
        account_dict = {
            'clientID': account.clientID,
            'authKey': account.authKey,
            'email': account.email,
            'name': account.name,
            'deviceName': account.deviceName
        }

        GLib.idle_add(lambda: keyring.set_password("meocloud", "clientID",
                                                   account_dict['clientID']))
        GLib.idle_add(lambda: keyring.set_password("meocloud", "authKey",
                                                   account_dict['authKey']))
        self.ui_config.put('Account', 'email', account_dict['email'])
        self.ui_config.put('Account', 'name', account_dict['name'])
        self.ui_config.put('Account', 'deviceName', account_dict['deviceName'])

        if self.setup.setup_easy.get_active():
            GLib.idle_add(self.setup.spinner.stop)
            GLib.idle_add(self.setup.pages.last_page)

            meocloud_gui.utils.clean_cloud_path()
            meocloud_gui.utils.create_startup_file(self.app.app_path)
            meocloud_gui.utils.create_bookmark()
            self.app.restart_core()
        else:
            GLib.idle_add(self.setup.pages.next_page)
            meocloud_gui.utils.clean_cloud_path()
            meocloud_gui.utils.create_startup_file(self.app.app_path)
            meocloud_gui.utils.create_bookmark()
            self.app.restart_core(True)

    def endAuthorization(self):
        log.debug('CoreListener.endAuthorization() <<<<')

    def notifySystem(self, note):
        log.debug('CoreListener.notifySystem({0}, {1}) <<<<'.format(note.code,
                  note.parameters))

        if note.code == codes.SHARE_LINK:
            clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
            GLib.idle_add(lambda: clipboard.set_text(note.parameters[2], -1))

            notification = Notify.Notification.new("MEO Cloud",
                                                   _("Link copied to "
                                                     "clipboard."),
                                                   os.path.join(
                                                       self.app.app_path,
                                                       "icons/"
                                                       "meocloud-ok.svg"))
            notification.show()
        elif (note.code == codes.SHARE_FOLDER or
                note.code == codes.OPEN_IN_BROWSER):
            subprocess.Popen(["xdg-open",
                             note.parameters[2]])

        self.app.update_menu(None, self.ignore_sync)

    def notifyUser(self, note):  # UserNotification note
        log.debug('CoreListener.notifyUser({0}) <<<<'.format(note))

        display_notifications = Preferences().get("General", "Notifications",
                                                  "True")
        if note.type != 0 and display_notifications == "True":
            loc = locale.getlocale()
            if 'pt' in loc or 'pt_PT' in loc or 'pt_BR' in loc:
                lang = 'pt'
            else:
                lang = 'en'

            notif_icon = os.path.join(
                self.app.app_path, "icons/meocloud-ok.svg")
            notif_title = NOTIFICATIONS[lang][str(note.code) + "_title"]
            notif_string = NOTIFICATIONS[lang][str(note.code) +
                                               "_description"].format(
                *note.parameters)
            notification = Notify.Notification.new(notif_title, notif_string,
                                                   notif_icon)
            notification.show()

    def remoteDirectoryListing(self, statusCode, path, listing):
        log.debug(
            'CoreListener.remoteDirectoryListing({0}, {1}, {2}) <<<<'.format(
                statusCode, path, listing))
        if self.app.prefs_window:
            GLib.idle_add(lambda:
                          self.app.prefs_window.selective_sync.add_column(
                              listing, path))

    def networkSettings(self):
        log.debug('CoreListener.networkSettings() <<<<')
        return api.get_network_settings(self.ui_config)
