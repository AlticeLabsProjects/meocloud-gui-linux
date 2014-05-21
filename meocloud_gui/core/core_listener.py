# Python standard library imports
import os
import webbrowser
import keyring
import locale

# GLib, Gdk and Gtk
from gi.repository import GLib, Gdk, Gtk

# Notifications
from gi.repository import Notify

# Thrift related imports
from meocloud_gui.codes import USER_NOTIFY_TYPE_MASK_PERSISTENT, \
    USER_NOTIFY_TYPE_MASK_MENU_BAR, USER_NOTIFY_TYPE_RESET, \
    USER_NOTIFY_TYPE_MASK_BALLOON, USER_NOTIFY_CANNOT_WATCH_FS
from meocloud_gui.protocol.daemon_core import UI
from meocloud_gui.protocol.daemon_core.ttypes import Account
from meocloud_gui.thrift_utils import ThriftListener

# Application specific imports
from meocloud_gui.constants import (LOGGER_NAME, UI_CONFIG_PATH, CLIENT_ID,
                                    AUTH_KEY)
from meocloud_gui.core import api
from meocloud_gui.preferences import Preferences
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.strings import NOTIFICATIONS
from meocloud_gui.exceptions import ListenerConnectionFailedException
import meocloud_gui.utils

from meocloud_gui import codes

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class CoreListener(ThriftListener):
    def __init__(self, socket, core_client, ui_config, app, ignore_sync):
        handler = CoreListenerHandler(core_client, ui_config, app, ignore_sync)
        processor = UI.Processor(handler)
        self.core_client = core_client
        super(CoreListener, self).__init__('CoreListener', socket, processor)

    def start(self):
        log.info('{0}: Starting to serve...'.format(self.name))
        try:
            self.listener_server.serve()
        except ListenerConnectionFailedException:
            pass
        except Exception:
            log.exception(
                '{0}: An uncatched error occurred!'.format(self.name))


class CoreListenerHandler(UI.Iface):
    def __init__(self, core_client, ui_config, app, ignore_sync):
        super(CoreListenerHandler, self).__init__()
        self.core_client = core_client
        self.ui_config = ui_config
        self.app = app
        self.setup = None
        self.ignore_sync = ignore_sync
        self.last_notify = 0

        Notify.init('MEOCloud')

    ### THRIFT METHODS ###

    def account(self):
        log.debug('CoreListener.account() <<<<')

        account_dict = api.get_account_dict(self.ui_config)

        return Account(**account_dict)

    def beginAuthorization(self):
        log.debug('CoreListener.beginAuthorization() <<<<')

        if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                       'prefs.ini')):
            try:
                os.remove(os.path.join(UI_CONFIG_PATH, 'prefs.ini'))
            except (OSError, IOError):
                pass

        GLib.idle_add(self.beginAuthorizationIdle)

    def beginAuthorizationIdle(self):
        self.setup = SetupWindow(self.app)
        self.setup.login_button.connect("clicked",
                                        self.beginAuthorizationBrowser)
        self.setup.show_all()

    def beginAuthorizationBrowser(self, w):
        if not self.setup.setup_easy.get_active():
            self.ui_config.put('Advanced', 'Folder',
                               self.setup.cloud_home_select.get_label())

        try:
            meocloud_gui.utils.clean_cloud_path()
        except (OSError, IOError, AssertionError):
            return

        self.setup.start_waiting()

        device_name = self.setup.device_entry.get_text()

        if len(device_name) > 0:
            webbrowser.open(self.core_client.authorizeWithDeviceName
                            (device_name))
        else:
            self.setup.pages.set_current_page(1)

    def authorized(self, account):
        log.debug('CoreListener.authorized({0}) <<<<'.format(account))
        account_dict = {
            'clientID': account.clientID,
            'authKey': account.authKey,
            'email': account.email,
            'name': account.name,
            'deviceName': account.deviceName
        }

        GLib.idle_add(lambda: keyring.set_password("meocloud", CLIENT_ID,
                                                   account_dict['clientID']))
        GLib.idle_add(lambda: keyring.set_password("meocloud", AUTH_KEY,
                                                   account_dict['authKey']))
        self.ui_config.put('Account', 'email', account_dict['email'])
        self.ui_config.put('Account', 'name', account_dict['name'])
        self.ui_config.put('Account', 'deviceName', account_dict['deviceName'])

        if self.setup.setup_easy.get_active():
            self.app.enable_sync = True
            GLib.idle_add(self.setup.spinner.stop)
            GLib.idle_add(self.setup.pages.last_page)
            meocloud_gui.utils.create_startup_file(self.app.app_path)
            meocloud_gui.utils.create_bookmark()
        else:
            self.app.enable_sync = False
            meocloud_gui.utils.create_startup_file(self.app.app_path)
            meocloud_gui.utils.create_bookmark()
            GLib.idle_add(self.setup.pages.next_page)

        GLib.idle_add(lambda: self.setup.present())

    def endAuthorization(self):
        log.debug('CoreListener.endAuthorization() <<<<')

    def notifySystem(self, note):
        log.debug('CoreListener.notifySystem({0}, {1}) <<<<'.format(note.code,
                  note.parameters))

        if note.code == codes.SHARE_LINK:
            if note.parameters[0] == codes.STR_OK:
                def set_clipboard(text):
                    Gdk.threads_enter()
                    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                    clipboard.set_text(text, -1)
                    Gdk.threads_leave()

                GLib.idle_add(lambda: set_clipboard(note.parameters[2]))

                Gdk.threads_enter()
                notification = Notify.Notification.new("MEO Cloud",
                                                       _("Link copied to "
                                                         "clipboard."),
                                                       os.path.join(
                                                           self.app.app_path,
                                                           "icons/"
                                                           "meocloud.svg"))
                notification.show()
                Gdk.threads_leave()
            elif note.parameters[0] == codes.STR_NOTFOUND:
                Gdk.threads_enter()
                notification = Notify.Notification.new(
                    "MEO Cloud",
                    _("File isn't synchronized yet. "
                      "Please try again once synchronization finishes."),
                    os.path.join(
                        self.app.app_path,
                        "icons/"
                        "meocloud.svg"))
                notification.show()
                Gdk.threads_leave()
            elif note.parameters[0] == codes.STR_ERROR:
                Gdk.threads_enter()
                notification = Notify.Notification.new(
                    "MEO Cloud",
                    _("An error ocurred while trying to complete the "
                      "operation. Please try again later."),
                    os.path.join(
                        self.app.app_path,
                        "icons/"
                        "meocloud.svg"))
                notification.show()
                Gdk.threads_leave()
        elif (note.code == codes.SHARE_FOLDER or
                note.code == codes.OPEN_IN_BROWSER):
            if note.parameters[0] == codes.STR_OK:
                webbrowser.open(note.parameters[2])
            elif note.parameters[0] == codes.STR_NOTFOUND:
                Gdk.threads_enter()
                notification = Notify.Notification.new(
                    "MEO Cloud",
                    _("File isn't synchronized yet. "
                      "Please try again once synchronization finishes."),
                    os.path.join(
                        self.app.app_path,
                        "icons/"
                        "meocloud.svg"))
                notification.show()
                Gdk.threads_leave()
            elif note.parameters[0] == codes.STR_ERROR:
                Gdk.threads_enter()
                notification = Notify.Notification.new(
                    "MEO Cloud",
                    _("An error ocurred while trying to complete the "
                      "operation. Please try again later."),
                    os.path.join(
                        self.app.app_path,
                        "icons/"
                        "meocloud.svg"))
                notification.show()
                Gdk.threads_leave()
        elif note.code == codes.SHARED_FOLDER_ADDED:
            if not note.parameters[0] in self.app.shared:
                if self.app.shared is not None:
                    self.app.shared.add(note.parameters[0])

                    try:
                        f = open(os.path.join(UI_CONFIG_PATH,
                                              'shared_directories'), "w")
                        for directory in self.app.shared:
                            f.write(directory + "\n")
                        f.close()
                    except (OSError, IOError):
                        log.warning(
                            'CoreListener.notifySystem: unable to save '
                            'shared directories list')
        elif note.code == codes.SHARED_FOLDER_UNSHARED:
            if note.parameters[0] in self.app.shared:
                if self.app.shared is not None:
                    self.app.shared.remove(note.parameters[0])

                    try:
                        f = open(os.path.join(UI_CONFIG_PATH,
                                              'shared_directories'), "w")
                        for directory in self.app.shared:
                            f.write(directory + "\n")
                        f.close()
                    except (OSError, IOError):
                        log.warning(
                            'CoreListener.notifySystem: unable to save '
                            'shared directories list')

        self.app.update_menu()

    def notifyUser(self, note):  # UserNotification note
        log.debug('CoreListener.notifyUser({0}) <<<<'.format(note))

        display_notifications = Preferences().get("General", "Notifications",
                                                  "True")

        if (self.last_notify != USER_NOTIFY_CANNOT_WATCH_FS or (
                self.last_notify == USER_NOTIFY_CANNOT_WATCH_FS and
                self.code != self.last_notify)):
            if note.type != 0:
                loc = locale.getlocale()
                if 'pt' in loc or 'pt_PT' in loc or 'pt_BR' in loc:
                    lang = 'pt'
                else:
                    lang = 'en'

                notif_title = NOTIFICATIONS[lang][
                    str(note.code) + "_title"].format(*note.parameters)
                notif_string = NOTIFICATIONS[lang][
                    str(note.code) + "_description"].format(*note.parameters)

                if note.type & USER_NOTIFY_TYPE_MASK_PERSISTENT:
                    self.app.problem_text = notif_string
                    self.app.trayicon.wrapper(
                        lambda: self.app.menuitem_problem.show())
                    self.app.trayicon.wrapper(
                        lambda: self.app.menuitem_moreinfo.show())

                if note.type & USER_NOTIFY_TYPE_MASK_MENU_BAR:
                    self.app.trayicon.set_icon("meocloud-activity")

                if (note.type & USER_NOTIFY_TYPE_MASK_BALLOON and
                        display_notifications == "True"):
                    notif_icon = os.path.join(
                        self.app.app_path, "icons/meocloud.svg")
                    Gdk.threads_enter()
                    notification = Notify.Notification.new(notif_title,
                                                           notif_string,
                                                           notif_icon)
                    notification.show()
                    Gdk.threads_leave()
            elif note.type == 0:
                self.app.trayicon.wrapper(
                    lambda: self.app.menuitem_problem.hide())
                self.app.trayicon.wrapper(lambda: self.app.update_menu())

        self.last_notify = note.code

    def remoteDirectoryListing(self, statusCode, path, listing):
        log.debug(
            'CoreListener.remoteDirectoryListing({0}, {1}, {2}) <<<<'.format(
                statusCode, path, listing))
        if self.app.prefs_window:
            GLib.idle_add(lambda:
                          self.app.prefs_window.selective_sync.add_column(
                              listing))

    def networkSettings(self):
        log.debug('CoreListener.networkSettings() <<<<')
        return api.get_network_settings(self.ui_config)
