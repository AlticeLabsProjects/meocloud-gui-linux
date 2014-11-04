# Python standard library imports
import os
import webbrowser
import locale

# GLib, Gdk and Gtk
from gi.repository import GLib, Gdk, Gtk

# Notifications
from gi.repository import Notify

# Thrift related imports
from meocloud_gui.codes import USER_NOTIFY_TYPE_MASK_PERSISTENT, \
    USER_NOTIFY_TYPE_MASK_MENU_BAR, USER_NOTIFY_TYPE_RESET, \
    USER_NOTIFY_TYPE_MASK_BALLOON, USER_NOTIFY_CANNOT_WATCH_FS,\
    USER_NOTIFY_TYPE_MASK_ALERT_WINDOW
from meocloud_gui.protocol.daemon_core import UI
from meocloud_gui.protocol.daemon_core.ttypes import Account
from meocloud_gui.thrift_utils import ThriftListener

# Application specific imports
from meocloud_gui.constants import (LOGGER_NAME, UI_CONFIG_PATH)
from meocloud_gui.core import api
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.strings import NOTIFICATIONS
from meocloud_gui.exceptions import ListenerConnectionFailedException
from meocloud_gui import utils

from meocloud_gui import codes

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


SHORTEN_PATH_CODES = frozenset((
    200, 201, 202, 250, 251, 252
))


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
                '{0}: An uncaught error occurred!'.format(self.name))


class CoreListenerHandler(UI.Iface):
    def __init__(self, core_client, ui_config, app, ignore_sync):
        super(CoreListenerHandler, self).__init__()
        self.core_client = core_client
        self.ui_config = ui_config
        self.app = app
        self.setup = None
        self.ignore_sync = ignore_sync
        self.last_notify = 0

        image_path = os.path.join(self.app.app_path, 'icons/meocloud.svg')
        self.app_icon_path = image_path

    ### THRIFT METHODS ###
    def account(self):
        log.debug('CoreListener.account() <<<<')

        account_dict = api.get_account_dict(self.ui_config)
        account = Account(**account_dict)
        account_dict['authKey'] = '*' * 10
        log.debug('CoreListener.account(): {0} <<<<'.format(account_dict))

        return account

    def beginAuthorization(self):
        log.debug('CoreListener.beginAuthorization() <<<<')

        try:
            os.remove(os.path.join(UI_CONFIG_PATH, 'prefs.ini'))
        except EnvironmentError:
            pass

        GLib.idle_add(self.beginAuthorizationIdle)

    # Runs in the GUI thread
    def beginAuthorizationIdle(self):
        self.setup = SetupWindow(self.app)
        self.setup.login_button.connect('clicked',
                                        self.beginAuthorizationBrowser)
        self.setup.show_all()

    # Runs in the GUI thread
    def beginAuthorizationBrowser(self, w):
        if not self.setup.setup_easy.get_active():
            self.ui_config.put('Advanced', 'Folder',
                               self.setup.cloud_home_select.get_label())
            self.ui_config.save()

        try:
            utils.clean_cloud_path(self.ui_config)
        except (EnvironmentError, AssertionError):
            return

        self.setup.start_waiting()

        device_name = self.setup.device_entry.get_text()

        if len(device_name) > 0:
            webbrowser.open(self.core_client.authorizeWithDeviceName
                            (device_name))
        else:
            self.setup.pages.set_current_page(1)

    def authorized(self, account):
        account_dict = {
            'clientID': account.clientID,
            'authKey': account.authKey,
            'email': account.email,
            'name': account.name,
            'deviceName': account.deviceName
        }

        if account.authKey:
            account.authKey = '*' * len(account.authKey)

        log.debug('CoreListener.authorized({0}) <<<<'.format(account))
        self.ui_config.creds.clear()
        self.ui_config.creds.init()
        self.ui_config.creds.cid = account_dict['clientID']
        self.ui_config.creds.ckey = account_dict['authKey']
        self.ui_config.put('Account', 'email', account_dict['email'])
        self.ui_config.put('Account', 'name', account_dict['name'])
        self.ui_config.put('Account', 'deviceName', account_dict['deviceName'])
        self.ui_config.save()

        if self.setup.setup_easy.get_active():
            self.app.enable_sync = True
            GLib.idle_add(self.setup.spinner.stop)
            GLib.idle_add(self.setup.pages.last_page)
            utils.create_startup_file(self.app.app_path)
            utils.create_bookmark(self.ui_config)
        else:
            self.app.enable_sync = False
            utils.create_startup_file(self.app.app_path)
            utils.create_bookmark(self.ui_config)
            GLib.idle_add(self.setup.pages.next_page)

        GLib.idle_add(self.setup.present)

    def endAuthorization(self):
        log.debug('CoreListener.endAuthorization() <<<<')

    def _build_notification(self, msg, title):
        title = title if title else 'MEO Cloud'
        return Notify.Notification.new(title, msg, self.app_icon_path)

    def _build_notify_and_clipboard_cb(self, msg, title=None, url=None):
        def callback():
            with utils.gdk_threads_lock():
                if url:
                    clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                    clipboard.set_text(url, -1)
                notification = self._build_notification(msg, title)
                try:
                    notification.show()
                except GLib.GError:
                    log.warn('Timeout during notification.')
        return callback

    def notifySystem(self, note):
        log.debug('CoreListener.notifySystem({0}, {1}) <<<<'.format(note.code,
                  note.parameters))

        if note.code == codes.SHARE_LINK:
            result = note.parameters[0]
            path = os.path.basename(note.parameters[1])
            url = note.parameters[2]

            if result == codes.STR_OK:
                msg = (_("A link to \"{0}\" was copied to the clipboard").
                       format(path))
                cb = self._build_notify_and_clipboard_cb(msg, url=url)
                GLib.idle_add(cb)

            elif result == codes.STR_NOTFOUND:
                msg = _("\"{0}\" isn't synchronized yet. "
                        "Please try again once the synchronization finishes")
                msg = msg.format(path)
                cb = self._build_notify_and_clipboard_cb(msg, url=url)
                GLib.idle_add(cb)

            elif result == codes.STR_ERROR:
                msg = _("An error occurred while trying to complete the "
                        "operation. Please try again later")
                cb = self._build_notify_and_clipboard_cb(msg, url=url)
                GLib.idle_add(cb)

        elif (note.code == codes.SHARE_FOLDER or
              note.code == codes.OPEN_IN_BROWSER):
            result = note.parameters[0]
            path = os.path.basename(note.parameters[1])
            url = note.parameters[2]

            if result == codes.STR_OK:
                GLib.idle_add(webbrowser.open, url)

            elif result == codes.STR_NOTFOUND:
                msg = ("\"{0}\" isn't synchronized yet. "
                       "Please try again once the synchronization finishes")
                msg = msg.format(path)
                cb = self._build_notify_and_clipboard_cb(msg, url)
                GLib.idle_add(cb)

            elif result == codes.STR_ERROR:
                msg = _("An error occurred while trying to complete the "
                        "operation. Please try again later")
                msg = msg.format(path)
                cb = self._build_notify_and_clipboard_cb(msg, url)
                GLib.idle_add(cb)

        elif note.code == codes.SHARED_FOLDER_ADDED:
            path = note.parameters[0]
            if self.app.shared is not None and path not in self.app.shared:
                self.app.shared.add(path)
                self._save_shared_folders()

        elif note.code == codes.SHARED_FOLDER_UNSHARED:
            path = note.parameters[0]
            if self.app.shared is not None and path in self.app.shared:
                self.app.shared.remove(path)
                self._save_shared_folders()

        GLib.idle_add(self.app.update_menu)

    def _save_shared_folders(self):
        try:
            f = open(os.path.join(UI_CONFIG_PATH, 'shared_directories'), 'wb')
            for directory in self.app.shared:
                f.write(directory + '\n')
            f.close()
        except EnvironmentError as err:
            log.warning(
                'CoreListener.notifySystem: unable to save '
                'shared directories list: {0}'.format(err))

    def notifyUser(self, note):  # UserNotification note
        log.debug('CoreListener.notifyUser({0}) <<<<'.format(note))

        display_notifications = self.ui_config.get("General", "Notifications",
                                                   "True")

        if (self.last_notify != USER_NOTIFY_CANNOT_WATCH_FS or (
                self.last_notify == USER_NOTIFY_CANNOT_WATCH_FS and
                note.code != self.last_notify)):
            if note.type != 0:
                loc = locale.getlocale()
                if 'pt' in loc or 'pt_PT' in loc or 'pt_BR' in loc:
                    lang = 'pt'
                else:
                    lang = 'en'

                # Shorten path name
                if note.code in SHORTEN_PATH_CODES:
                    note.parameters[0] = os.path.basename(note.parameters[0])

                code_str = str(note.code)
                notif_title = NOTIFICATIONS[lang].get(code_str + '_title')
                if notif_title:
                    notif_title = notif_title.format(*note.parameters)

                notif_string = NOTIFICATIONS[lang].get(
                    code_str + '_description')
                if notif_string:
                    notif_string = notif_string.format(*note.parameters)

                if (note.type & USER_NOTIFY_TYPE_MASK_PERSISTENT or
                        note.type & USER_NOTIFY_TYPE_MASK_ALERT_WINDOW):
                    self.app.problem_text = notif_string
                    self.app.trayicon.wrapper(self.app.menuitem_problem.show)
                    self.app.trayicon.wrapper(self.app.menuitem_moreinfo.show)

                if note.type & USER_NOTIFY_TYPE_MASK_MENU_BAR:
                    GLib.idle_add(self.app.trayicon.set_icon,
                                  'meocloud-activity')

                if (note.type & USER_NOTIFY_TYPE_MASK_BALLOON and
                        display_notifications == "True"):
                    cb = self._build_notify_and_clipboard_cb(
                        notif_string, notif_title)
                    GLib.idle_add(cb)

            elif note.type == USER_NOTIFY_TYPE_RESET:
                self.app.trayicon.wrapper(self.app.menuitem_problem.hide)
                self.app.trayicon.wrapper(self.app.update_menu)

        self.last_notify = note.code

    def remoteDirectoryListing(self, statusCode, path, listing):
        log.debug(
            'CoreListener.remoteDirectoryListing({0}, {1}, {2}) <<<<'.
            format(statusCode, path, listing))
        if self.app.prefs_window:
            GLib.idle_add(self.app.prefs_window.selective_sync.add_column,
                          listing)

    def networkSettings(self):
        log.debug('CoreListener.networkSettings() <<<<')
        return api.get_network_settings(self.ui_config)
