import os
import webbrowser
from gi.repository import Gtk, Gio, Gdk, GLib, Notify
from meocloud_gui import utils
from meocloud_gui.exceptions import ListenerConnectionFailedException
from meocloud_gui.loghandler import LogHandler
from meocloud_gui.stoppablethread import StoppableThread
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.missingdialog import MissingDialog
from meocloud_gui.gui.aboutdialog import AboutDialog
from meocloud_gui.preferences import Preferences
from meocloud_gui.core.core import Core
from meocloud_gui.core.shell import Shell
from meocloud_gui.core.core_client import CoreClient
from meocloud_gui.core.core_listener import CoreListener
from meocloud_gui.core.shellproxy import ShellProxy
from meocloud_gui.credentials import CredentialStore
import meocloud_gui.core.api

from meocloud_gui.constants import (
    CORE_LISTENER_SOCKET_ADDRESS,
    LOGGER_NAME,
    CLOUD_HOME_DEFAULT_PATH,
    CONFIG_PATH, UI_CONFIG_PATH,
    VERSION)
from meocloud_gui import codes

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)

try:
    kde_running = os.environ.get('KDE_FULL_SESSION') == 'true'
    assert(not kde_running)
    from gi import Repository
    if not Repository.get_default().enumerate_versions('AppIndicator3'):
        assert False
    from meocloud_gui.gui.indicator import Indicator as TrayIcon

    log.info('Application: using Indicator')
except (ImportError, AssertionError):
    from meocloud_gui.gui.trayicon import TrayIcon
    log.info('Application: using TrayIcon')


class Application(Gtk.Application):
    def __init__(self, app_path):
        Gtk.Application.__init__(self, application_id="pt.meocloud",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

        Notify.init('MEO Cloud')

        self.app_path = app_path
        self.prefs_window = None

        self.prefs = Preferences()
        creds = CredentialStore(self.prefs, utils.rc4_drop768,
                                utils.rc4_drop768, utils.mac, utils.MACSIZE)
        self.prefs.set_credential_store(creds)

        # for some reason this only works in __init__
        self.trayicon = TrayIcon(self)
        self.trayicon.show()

        self.missing_quit = False
        self.running = False
        self.paused = False
        self.in_selective_sync = False
        self.offline = False
        self.force_preferences_visible = False
        self.requires_authorization = True
        self.enable_sync = True
        self.core_client = None
        self.core_listener = None
        self.log_handler = None
        self.shell = None
        self.core = None
        self.icon_type = ""
        self.problem_text = ""
        self.shared = None

        self.recentfiles_menu = None
        self.menuitem_recent = None
        self.menuitem_storage = None
        self.menuitem_problem = None
        self.menuitem_moreinfo = None
        self.menuitem_status = []
        self.menuitem_changestatus = None
        self.menuitem_prefs = None
        self.storage_separator = None

        self.sync_thread = None
        self.menu_thread = None
        self.listener_thread = None
        self.watchdog_thread = None

        self.shell_proxy = ShellProxy(codes.CORE_INITIALIZING, self)

        # are we running GNOME or elementary OS?
        self.use_headerbar = utils.use_headerbar()

        # check if app has been updated every hour
        self.update_app_timeout = GLib.timeout_add(60000,
                                                   self.update_app_version)
        self.update_sync_status_timeout = None

    def _migrate_cli_settings(self):
        cli_config_path = os.path.join(CONFIG_PATH, "ui/ui_config.yaml")
        try:
            import yaml
            stream = open(cli_config_path, 'rb')
            cli_config = yaml.load(stream)
        except (ImportError, EnvironmentError):
            return
        except yaml.YAMLError:
            log.info('Found invalid CLI configuration.')
            utils.force_remove(cli_config_path, log.warn)
        else:
            cli_rc4_key = '8025c571541a64bccd00135f87dec11a' \
                          '83a8c5de69c94ec6b642dbdc6a2aebdd'
            account_dict = cli_config['account']
            account_dict['authKey'] = utils.decrypt(
                account_dict['authKey'], cli_rc4_key)
            account_dict['clientID'] = utils.decrypt(
                account_dict['clientID'], cli_rc4_key)

            self.prefs.creds.cid = account_dict['clientID']
            self.prefs.creds.ckey = account_dict['authKey']

            self.prefs.put('Account', 'email',
                           unicode(account_dict['email']).encode('utf-8'))
            self.prefs.put('Account', 'name',
                           unicode(account_dict['name']).encode('utf-8'))
            self.prefs.put('Account', 'deviceName',
                           unicode(account_dict['deviceName']).encode('utf-8'))
            self.prefs.put('Advanced', 'Folder',
                           unicode(cli_config['cloud_home']).encode('utf-8'))
            self.prefs.save()

            utils.purge_meta()
            utils.force_remove(cli_config_path, log.warn)

    def on_activate(self, data=None):
        if not self.running:
            self.running = True

            self.icon_type = self.prefs.get("General", "Icons", "")
            self.trayicon.set_icon("meocloud-init")

            self.force_preferences_visible = \
                self.prefs.get("Network", "Proxy", "None") != "None"

            if not self.prefs.get('Account', 'email'):
                log.info('Application.on_activate: prefs not initialized.')
                utils.force_remove(os.path.join(UI_CONFIG_PATH,
                                                'shared_directories'))
            else:
                if not os.path.exists(self.prefs.get("Advanced", "Folder",
                                                     CLOUD_HOME_DEFAULT_PATH)):
                    log.info('Application.on_activate: cloud_home missing')
                    missing = MissingDialog(self)
                    Gdk.threads_enter()
                    missing.run()
                    Gdk.threads_leave()

            # migrations
            if self.prefs.creds.cid is None:
                self._migrate_cli_settings()

            if not self.missing_quit:
                try:
                    self.shared = set()
                    path = os.path.join(UI_CONFIG_PATH, 'shared_directories')
                    with open(path, 'rb') as fobj:
                        for line in fobj.readlines():
                            self.shared.add(line.rstrip('\n'))
                except EnvironmentError:
                    self.shared = set()

                utils.create_required_folders(self.prefs)
                self.log_handler = LogHandler(self.core_client)
                utils.init_logging(self.log_handler)

                recentfiles_nothing = Gtk.MenuItem(_("No Recent Files"))
                recentfiles_nothing.show()
                self.recentfiles_menu = Gtk.Menu()
                self.recentfiles_menu.add(recentfiles_nothing)

                menuitem_folder = Gtk.MenuItem(_("Open Folder"))
                menuitem_site = Gtk.MenuItem(_("Open Website"))
                self.menuitem_recent = Gtk.MenuItem(_("Recent Files"))
                self.menuitem_recent.set_submenu(self.recentfiles_menu)
                self.menuitem_storage = Gtk.MenuItem("-")
                self.menuitem_storage.set_sensitive(False)
                problem_moreinfo_menu = Gtk.Menu()
                self.menuitem_moreinfo = Gtk.MenuItem(_("More info"))
                self.menuitem_problem = Gtk.MenuItem(
                    _("There is a problem synchronizing your files"))
                problem_moreinfo_menu.append(self.menuitem_moreinfo)
                self.menuitem_problem.set_submenu(problem_moreinfo_menu)
                self.menuitem_status.append(Gtk.MenuItem(_("Unauthorized")))
                self.menuitem_status.append(Gtk.MenuItem("-"))
                self.menuitem_status.append(Gtk.MenuItem("-"))
                self.menuitem_status.append(Gtk.MenuItem("-"))
                self.menuitem_status[0].set_sensitive(False)
                self.menuitem_status[1].set_sensitive(False)
                self.menuitem_status[2].set_sensitive(False)
                self.menuitem_status[3].set_sensitive(False)
                self.menuitem_changestatus = Gtk.MenuItem(_("Authorize"))
                self.menuitem_prefs = Gtk.MenuItem(_("Preferences"))
                menuitem_about = Gtk.MenuItem(_("About"))
                menuitem_bug = Gtk.MenuItem(_("Report a Bug"))
                menuitem_quit = Gtk.MenuItem(_("Quit"))
                self.storage_separator = Gtk.SeparatorMenuItem()

                self.trayicon.add_menu_item(menuitem_folder)
                self.trayicon.add_menu_item(menuitem_site)
                self.trayicon.add_menu_item(self.menuitem_recent)
                self.trayicon.add_menu_item(self.storage_separator, True)
                self.trayicon.add_menu_item(self.menuitem_storage, True)
                self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
                self.trayicon.add_menu_item(self.menuitem_problem, True)
                self.trayicon.add_menu_item(self.menuitem_status[0], True)
                self.trayicon.add_menu_item(self.menuitem_status[1], True)
                self.trayicon.add_menu_item(self.menuitem_status[2], True)
                self.trayicon.add_menu_item(self.menuitem_status[3], True)
                self.trayicon.add_menu_item(self.menuitem_changestatus)
                self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
                self.trayicon.add_menu_item(self.menuitem_prefs, True)
                self.trayicon.add_menu_item(menuitem_bug)
                self.trayicon.add_menu_item(menuitem_about)
                self.trayicon.add_menu_item(menuitem_quit)

                menuitem_folder.connect("activate", self.open_folder)
                menuitem_site.connect("activate", self.open_website)
                self.menuitem_moreinfo.connect("activate", self.show_problem)
                self.menuitem_changestatus.connect("activate",
                                                   self.toggle_status)
                self.menuitem_prefs.connect("activate", self.show_prefs)
                menuitem_about.connect(
                    "activate", lambda w: AboutDialog(self.app_path))
                menuitem_bug.connect("activate", self.report_bug)
                menuitem_quit.connect("activate", lambda w: self.quit())

                self.shell_proxy.start()
                self.restart_core()

                self.hold()
        elif self.shell is not None:
            self.show_prefs(None)

    def update_app_version(self):
        try:
            version_file = open(
                os.path.join(self.app_path, 'meocloud_gui/VERSION'), 'rb')
        except IOError:
            return True
        else:
            version = version_file.read().strip()
            version_file.close()
            if version != VERSION:
                cmd = "kill {0} && {1} &".format(
                    os.getpid(), os.path.join(self.app_path, "meocloud-gui"))
                os.system(cmd)
                return False
            else:
                return True

    def report_bug(self, w):
        webbrowser.open("http://ajuda.cld.pt")

    def show_problem(self, w):
        messagedialog = Gtk.MessageDialog(parent=None,
                                          flags=Gtk.DialogFlags.MODAL,
                                          type=Gtk.MessageType.WARNING,
                                          buttons=Gtk.ButtonsType.OK,
                                          message_format=self.problem_text)
        messagedialog.run()
        messagedialog.destroy()

    def clean_recent_files(self):
        for menuitem in self.recentfiles_menu.get_children():
            self.recentfiles_menu.remove(menuitem)

        recentfiles_nothing = Gtk.MenuItem(_("No Recent Files"))
        self.recentfiles_menu.add(recentfiles_nothing)
        recentfiles_nothing.show()

    def update_recent_files(self, recently_changed, cloud_home):
        if len(recently_changed) > 0:
            for menuitem in self.recentfiles_menu.get_children():
                self.recentfiles_menu.remove(menuitem)

            for path in recently_changed:
                display_path = path[2:]

                menuitem = Gtk.MenuItem(display_path)
                menuitem.connect("activate", lambda w:
                                 self.open_recent_file(w, cloud_home))

                if path.startswith("-/"):
                    menuitem.set_sensitive(False)

                self.recentfiles_menu.add(menuitem)
                menuitem.show()

    def open_recent_file(self, w, cloud_home):
        path = os.path.join(cloud_home, w.get_label())
        path = path.replace(os.path.basename(path), '')

        webbrowser.open(path)

    def update_menu(self):
        if self.requires_authorization:
            self.requires_authorization = False

        status = self.core_client.currentStatus()
        self.update_storage(status.usedQuota, status.totalQuota)

        cloud_home = self.prefs.get('Advanced', 'Folder',
                                    CLOUD_HOME_DEFAULT_PATH)

        self.shell_proxy.status = status.state

        if (status.state == codes.CORE_WAITING) and self.enable_sync:
            self.core_client.startSync(cloud_home)

        if (self.in_selective_sync and
                status.state != codes.CORE_SELECTIVE_SYNC):
            self.in_selective_sync = False
            if self.prefs_window is not None:
                GLib.idle_add(
                    self.prefs_window.selective_button.set_sensitive, True)

        if ((status.state == codes.CORE_SYNCING or
                status.state == codes.CORE_READY) and self.shell is None):
            self.shell = Shell(self.shell_proxy)
            self.shell_proxy.update_prefs()

        if ((status.state == codes.CORE_SYNCING or
                status.state == codes.CORE_READY) and
                self.log_handler.core_client is None):
            self.log_handler.core_client = self.core_client

        if status.state != codes.CORE_SYNCING:
            self.trayicon.wrapper(lambda: self.menuitem_status[0].show())
            self.trayicon.wrapper(lambda: self.menuitem_status[1].hide())
            self.trayicon.wrapper(lambda: self.menuitem_status[2].hide())
            self.trayicon.wrapper(lambda: self.menuitem_status[3].hide())

        if (status.state == codes.CORE_INITIALIZING or
           status.state == codes.CORE_AUTHORIZING or
           status.state == codes.CORE_WAITING):
            self.trayicon.wrapper(self.hide_gui_elements)
            self.trayicon.set_icon("meocloud-init")
            self.paused = True
            self.update_sync_status_stop()
            self.update_status(_("Initializing"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_SYNCING:
            self.trayicon.wrapper(self.show_gui_elements)
            self.trayicon.set_icon("meocloud-sync-1")
            self.paused = False

            sync_code = utils.get_sync_code(status.statusCode)
            self.menu_from_sync_code(sync_code)

            self.update_sync_status_start()
            self.update_menu_action(_("Pause"))
        elif status.state == codes.CORE_READY:
            self.core_client.ignore_logs = False
            self.trayicon.wrapper(lambda: self.show_gui_elements(True))
            self.trayicon.set_icon("meocloud-ok")
            self.paused = False
            self.update_sync_status_stop()
            self.update_status(_("Synced"))
            self.update_menu_action(_("Pause"))

            recently_changed = self.core_client.recentlyChangedFilePaths()
            self.trayicon.wrapper(
                lambda: self.update_recent_files(recently_changed, cloud_home))
        elif status.state == codes.CORE_PAUSED:
            self.paused = True
            self.trayicon.wrapper(self.show_gui_elements)
            self.trayicon.set_icon("meocloud-pause")
            self.update_sync_status_stop()
            self.update_status(_("Paused"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_SELECTIVE_SYNC:
            self.in_selective_sync = True
            if self.prefs_window is not None:
                GLib.idle_add(
                    self.prefs_window.selective_button.set_sensitive, False)
            self.trayicon.wrapper(self.show_gui_elements)
            self.trayicon.set_icon("meocloud-sync-1")
            self.paused = False
            self.update_menu_action(_("Applying selective sync settings..."))
        elif status.state == codes.CORE_OFFLINE:
            self.trayicon.wrapper(self.show_gui_elements)
            self.trayicon.set_icon("meocloud-offline")
            self.paused = True
            self.offline = True
            self.update_sync_status_stop()
            self.update_status(_("Offline"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_ERROR:
            self.trayicon.wrapper(self.show_gui_elements)
            self.trayicon.set_icon("meocloud-error")
            self.paused = True
            self.update_sync_status_stop()
            self.update_status(_("Error"))
            self.update_menu_action(_("Resume"))

            error_code = meocloud_gui.utils.get_error_code(
                status.statusCode)

            log.warning('CoreListener: Got error code: {0}'.format(
                error_code))
            if error_code == codes.ERROR_AUTH_TIMEOUT:
                pass
            elif error_code == codes.ERROR_ROOTFOLDER_GONE:
                log.warning('CoreListener: Root folder is gone, '
                            'will now shutdown')

                # send a notification about the issue
                notif_icon = os.path.join(
                    self.app_path, "icons/meocloud.svg")
                notif_title = _('MEO Cloud Folder Missing')
                notif_string = _('Your MEO Cloud folder is missing.')
                with utils.gdk_threads_lock():
                    notification = Notify.Notification.new(notif_title,
                                                           notif_string,
                                                           notif_icon)
                    notification.show()

                # restart the app so we can deal with the missing folder
                cmd = "kill {0} && {1} &".format(
                    os.getpid(), os.path.join(self.app_path, "meocloud-gui"))
                os.system(cmd)
            elif error_code == codes.ERROR_UNKNOWN:
                pass
            elif error_code == codes.ERROR_THREAD_CRASH:
                pass
            elif error_code == codes.ERROR_CANNOT_WATCH_FS:
                log.warning('CoreListener: Cannot watch filesystem, '
                            'will now shutdown')
            else:
                log.error(
                    'CoreListener: Got unknown error code: {0}'.format(
                        error_code))
                assert False

    def update_sync_status(self):
        if self.update_sync_status_timeout is None:
            return False

        try:
            syncstatus = self.core_client.currentSyncStatus()
            status = self.core_client.currentStatus()
        except ListenerConnectionFailedException:
            self.update_status(_("Syncing"), 0)
            self.trayicon.wrapper(lambda: self.menuitem_status[0].show())
            return False

        sync_code = utils.get_sync_code(status.statusCode)
        self.menu_from_sync_code(sync_code)

        if syncstatus.downloadRate > 0 and syncstatus.pendingDownloads > 0:
            self.update_status(
                _("Downloading {0} file(s) at {1}/s... ({2})").format(
                    syncstatus.pendingDownloads,
                    utils.convert_size(syncstatus.downloadRate),
                    utils.convert_time(syncstatus.downloadETASecs)), 1)
        elif syncstatus.pendingDownloads > 0:
            self.update_status(
                _("Downloading {0} file(s)...").format(
                    syncstatus.pendingDownloads), 1)

        if syncstatus.uploadRate > 0 and syncstatus.pendingUploads > 0:
            self.update_status(
                _("Uploading {0} file(s) at {1}/s... ({2})").format(
                    syncstatus.pendingUploads,
                    utils.convert_size(syncstatus.uploadRate),
                    utils.convert_time(syncstatus.uploadETASecs)), 2)
        elif syncstatus.pendingUploads > 0:
            self.update_status(
                _("Uploading {0} file(s)...").format(
                    syncstatus.pendingUploads), 2)

        if syncstatus.pendingIndexes > 0:
            self.update_status(
                _("Indexing {0} file(s)...").format(
                    syncstatus.pendingIndexes), 3)

        return True

    def menu_from_sync_code(self, sync_code):
        if sync_code & codes.SYNC_LISTING_CHANGES:
            self.update_status(_("Listing remote changes..."), 0)
            self.trayicon.wrapper(lambda: self.menuitem_status[0].show())
        else:
            self.trayicon.wrapper(lambda: self.menuitem_status[0].hide())

        if sync_code & codes.SYNC_DOWNLOADING:
            self.update_status(_("Downloading files..."), 1)
            self.trayicon.wrapper(lambda: self.menuitem_status[1].show())
        else:
            self.trayicon.wrapper(lambda: self.menuitem_status[1].hide())

        if sync_code & codes.SYNC_UPLOADING:
            self.update_status(_("Uploading files..."), 2)
            self.trayicon.wrapper(lambda: self.menuitem_status[2].show())
        else:
            self.trayicon.wrapper(lambda: self.menuitem_status[2].hide())

        if sync_code & codes.SYNC_INDEXING:
            self.update_status(_("Indexing files..."), 3)
            self.trayicon.wrapper(lambda: self.menuitem_status[3].show())
        else:
            self.trayicon.wrapper(lambda: self.menuitem_status[3].hide())

    def update_sync_status_stop(self):
        if self.update_sync_status_timeout is not None:
            GLib.source_remove(self.update_sync_status_timeout)
            self.update_sync_status_timeout = None

    def update_sync_status_start(self):
        if self.update_sync_status_timeout is None:
            self.update_sync_status()
            self.update_sync_status_timeout = \
                GLib.timeout_add(5000, self.update_sync_status)

    def hide_gui_elements(self):
        self.storage_separator.hide()
        if self.force_preferences_visible:
            self.menuitem_prefs.show()
        else:
            self.menuitem_prefs.hide()
        self.menuitem_storage.hide()

    def show_gui_elements(self, storage=False):
        self.menuitem_prefs.show()
        if storage:
            self.storage_separator.show()
            self.menuitem_storage.show()

    def update_status(self, status, num=0):
        self.trayicon.wrapper(
            lambda: self.menuitem_status[num].set_label(status))

    def update_menu_action(self, action):
        self.trayicon.wrapper(
            lambda: self.menuitem_changestatus.set_label(action))

    def toggle_status(self, w):
        if self.offline:
            self.offline = False
            self.paused = False
            self.restart_core()
        elif self.requires_authorization:
            self.restart_core()
        elif self.paused:
            self.core_client.unpause()
        else:
            self.core_client.pause()

    def update_storage(self, used, total):
        if total > 0:
            used_percentage = (used * 100) / total
        else:
            used_percentage = 100
        used_percentage = str(used_percentage) + "%"
        total = utils.convert_size(total)

        self.menuitem_storage.set_label(
            _("{0} of {1} used").format(str(used_percentage), str(total)))

    def show_prefs(self, w):
        if not self.prefs_window:
            self.prefs_window = PrefsWindow(self)
            self.prefs_window.logout_button.connect("clicked", self.on_logout)
        self.prefs_window.show_all()
        self.prefs_window.present()

    def on_logout(self, w):
        log.info('Application.on_logout: initiating logout')
        self.prefs_window.destroy()
        StoppableThread(target=self.on_logout_thread).start()

    def on_logout_thread(self):
        meocloud_gui.core.api.unlink(self.core_client, self.prefs)

        utils.force_remove(os.path.join(UI_CONFIG_PATH, 'prefs.ini'))
        utils.force_remove(os.path.join(UI_CONFIG_PATH, 'shared_directories'))
        utils.purge_all()

        self.requires_authorization = True
        self.update_status(_("Unauthorized"))
        self.update_menu_action(_("Authorize"))
        self.trayicon.wrapper(self.clean_recent_files)
        self.trayicon.wrapper(self.hide_gui_elements)
        log.info('Application.on_logout_thread: completing logout')
        self.restart_core()

    def open_folder(self, w):
        if self.prefs:
            cloud_home = self.prefs.get('Advanced', 'Folder',
                                        CLOUD_HOME_DEFAULT_PATH)
        else:
            cloud_home = CLOUD_HOME_DEFAULT_PATH

        webbrowser.open(cloud_home)

    def open_website(self, w):
        webbrowser.open(self.core_client.webLoginURL())

    def restart_core(self, ignore_sync=False):
        log.info('Application.restart_core: initiating core restart')

        self.trayicon.wrapper(self.hide_gui_elements)
        self.trayicon.set_icon("meocloud-init")

        self.core_client = CoreClient()
        self.core_listener = CoreListener(CORE_LISTENER_SOCKET_ADDRESS,
                                          self.core_client, self.prefs, self,
                                          ignore_sync)
        self.core = Core(self.core_client)

        # Make sure core isn't running
        self.stop_threads()

        # Start the core
        self.listener_thread = StoppableThread(target=self.core_listener.start)
        self.watchdog_thread = StoppableThread(target=self.core.watchdog)
        self.core.thread = self.watchdog_thread
        self.listener_thread.start()
        self.watchdog_thread.start()

        # Restart Shell Proxy and update logging
        self.shell_proxy.update_prefs()
        log.info('Application.restart_core: core restart completed')

    def stop_threads(self):
        self.log_handler.core_client = None

        if (self.listener_thread is not None and
                not self.listener_thread.stopped()):
            self.listener_thread.stop()
        if (self.watchdog_thread is not None and
                not self.watchdog_thread.stopped()):
            self.watchdog_thread.stop()
        self.shell = None

        if (self.core.thread is not None and
                not self.core.thread.stopped()):
            self.core.thread.stop()
        if self.core is not None:
            self.core.stop()

        log.info('Application.stop_threads: threads stopped')

    def quit(self):
        self.stop_threads()
        log.info('Application.quit: shutting down')
        self.running = False
        Gtk.Application.quit(self)
