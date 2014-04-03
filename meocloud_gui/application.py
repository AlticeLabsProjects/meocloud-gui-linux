import subprocess
import os
import keyring
from threading import Thread
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import Gtk, Gio, GLib, Notify
from meocloud_gui import utils
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.missingdialog import MissingDialog
from meocloud_gui.gui.aboutdialog import AboutDialog
from meocloud_gui.preferences import Preferences
from meocloud_gui.core.core import Core
from meocloud_gui.core.shell import Shell
from meocloud_gui.core.core_client import CoreClient
from meocloud_gui.core.core_listener import CoreListener
from meocloud_gui.core.dbusservice import DBusService
import meocloud_gui.core.api

from meocloud_gui.constants import (CORE_LISTENER_SOCKET_ADDRESS,
                                    LOGGER_NAME, CLOUD_HOME_DEFAULT_PATH,
                                    UI_CONFIG_PATH)

from meocloud_gui import codes

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)

try:
    from meocloud_gui.gui.indicator import Indicator as TrayIcon
    log.info('Application: using Indicator')
except:
    from meocloud_gui.gui.trayicon import TrayIcon
    log.info('Application: using TrayIcon')


class Application(Gtk.Application):
    def __init__(self, app_path):
        Gtk.Application.__init__(self, application_id="pt.meocloud",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

        self.app_path = app_path
        self.prefs_window = None
        self.trayicon = TrayIcon(self)
        self.trayicon.show()

        self.missing_quit = False
        self.running = False
        self.paused = False
        self.offline = False
        self.requires_authorization = True
        self.core_client = None
        self.core_listener = None
        self.shell = None
        self.core = None
        self.ignored_directories = []
        self.dark_icons = False

        self.sync_thread = None
        self.menu_thread = None
        self.listener_thread = None
        self.watchdog_thread = None

        # initialize dbus
        DBusGMainLoop(set_as_default=True)
        self.dbus_service = DBusService(codes.CORE_INITIALIZING, self.app_path)

    def on_activate(self, data=None):
        if not self.running:
            self.running = True
            prefs = Preferences()

            self.dark_icons = prefs.get(
                "General", "DarkIcons", "False") == "True"
            self.trayicon.set_icon("meocloud-ok")

            if not os.path.isfile(os.path.join(UI_CONFIG_PATH, 'prefs.ini')):
                log.info('Application.on_activate: prefs.ini missing')

                if keyring.get_password('meocloud', 'clientID') is not None:
                    keyring.delete_password('meocloud', 'clientID')
                if keyring.get_password('meocloud', 'authKey') is not None:
                    keyring.delete_password('meocloud', 'authKey')

                if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                               'ignored_directories')):
                    os.remove(os.path.join(UI_CONFIG_PATH,
                                           'ignored_directories'))
            else:
                if not os.path.exists(prefs.get("Advanced", "Folder",
                                                CLOUD_HOME_DEFAULT_PATH)):
                    log.info('Application.on_activate: cloud_home missing')
                    missing = MissingDialog(self)
                    missing.run()

            if not self.missing_quit:
                utils.create_required_folders()
                utils.init_logging()

                if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                               'ignored_directories')):
                    log.info('Application.on_activate: loading ignored '
                             'directories')
                    f = open(os.path.join(UI_CONFIG_PATH,
                                          'ignored_directories'), "r")
                    for line in f.readlines():
                        self.ignored_directories.append(line.rstrip('\n'))
                    f.close()

                recentfiles_nothing = Gtk.MenuItem(_("No Recent Files"))
                recentfiles_nothing.show()
                self.recentfiles_menu = Gtk.Menu()
                self.recentfiles_menu.add(recentfiles_nothing)

                menuitem_folder = Gtk.MenuItem(_("Open Folder"))
                menuitem_site = Gtk.MenuItem(_("Open Website"))
                self.menuitem_recent = Gtk.MenuItem(_("Recent Files"))
                self.menuitem_recent.set_submenu(self.recentfiles_menu)
                self.menuitem_storage = Gtk.MenuItem(_("0 GB used of 16 GB"))
                self.menuitem_storage.set_sensitive(False)
                self.menuitem_status = Gtk.MenuItem(_("Unauthorized"))
                self.menuitem_status.set_sensitive(False)
                self.menuitem_changestatus = Gtk.MenuItem(_("Authorize"))
                self.menuitem_prefs = Gtk.MenuItem(_("Preferences"))
                menuitem_about = Gtk.MenuItem(_("About"))
                menuitem_quit = Gtk.MenuItem(_("Quit"))

                self.trayicon.add_menu_item(menuitem_folder)
                self.trayicon.add_menu_item(menuitem_site)
                self.trayicon.add_menu_item(self.menuitem_recent)
                self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
                self.trayicon.add_menu_item(self.menuitem_storage)
                self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
                self.trayicon.add_menu_item(self.menuitem_status)
                self.trayicon.add_menu_item(self.menuitem_changestatus)
                self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
                self.trayicon.add_menu_item(self.menuitem_prefs, True)
                self.trayicon.add_menu_item(menuitem_about)
                self.trayicon.add_menu_item(menuitem_quit)

                menuitem_folder.connect("activate", self.open_folder)
                menuitem_site.connect("activate", self.open_website)
                self.menuitem_changestatus.connect("activate",
                                                   self.toggle_status)
                self.menuitem_prefs.connect("activate", self.show_prefs)
                menuitem_about.connect(
                    "activate", lambda w: AboutDialog(self.app_path))
                menuitem_quit.connect("activate", lambda w: self.quit())

                self.restart_core()

                self.hold()

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

        subprocess.Popen(["xdg-open", path])

    def file_changed(self):
        if self.prefs_window is not None:
            print "prefs"
            if self.prefs_window.selective_sync is not None:
                print "selective"
                GLib.idle_add(self.prefs_window.selective_sync.panic)

    def update_menu(self, status=None, ignore_sync=False):
        if self.requires_authorization:
            self.requires_authorization = False

        if status is None:
            status = self.core_client.currentStatus()
        self.update_storage(status.usedQuota, status.totalQuota)

        cloud_home = Preferences().get('Advanced', 'Folder',
                                       CLOUD_HOME_DEFAULT_PATH)

        self.dbus_service.status = status.state

        if (status.state == codes.CORE_WAITING) and (not ignore_sync):
            self.core_client.startSync(cloud_home)

        if ((status.state == codes.CORE_SYNCING or
                status.state == codes.CORE_READY) and self.shell is None):
            self.shell = Shell.start(self.file_changed)
            self.shell.subscribe_path('/')
            self.dbus_service.shell = self.shell
            self.dbus_service.update_prefs()

        if (status.state == codes.CORE_INITIALIZING or
           status.state == codes.CORE_AUTHORIZING or
           status.state == codes.CORE_WAITING):
            GLib.idle_add(lambda: self.menuitem_prefs.hide())
            self.trayicon.set_icon("meocloud-ok")
            self.paused = True
            self.update_status(_("Initializing"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_SYNCING:
            GLib.idle_add(lambda: self.menuitem_prefs.show())
            self.trayicon.set_icon("meocloud-sync-1")
            self.paused = False
            self.update_status(_("Syncing"))
            self.update_menu_action(_("Pause"))
        elif status.state == codes.CORE_READY:
            GLib.idle_add(lambda: self.menuitem_prefs.show())
            self.trayicon.set_icon("meocloud-ok")
            self.paused = False
            self.update_status(_("Synced"))
            self.update_menu_action(_("Pause"))

            # clean the list of files that are syncing,
            # just in case we missed a notification
            if self.shell is not None:
                self.shell.clean_syncing()

            recently_changed = self.core_client.recentlyChangedFilePaths()
            GLib.idle_add(lambda: self.update_recent_files(recently_changed,
                                                           cloud_home))
        elif status.state == codes.CORE_PAUSED:
            GLib.idle_add(lambda: self.menuitem_prefs.show())
            self.trayicon.set_icon("meocloud-pause")
            self.paused = True
            self.update_status(_("Paused"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_OFFLINE:
            GLib.idle_add(lambda: self.menuitem_prefs.show())
            self.trayicon.set_icon("meocloud-error")
            self.paused = True
            self.offline = True
            self.update_status(_("Offline"))
            self.update_menu_action(_("Resume"))
        elif status.state == codes.CORE_ERROR:
            GLib.idle_add(lambda: self.menuitem_prefs.show())
            self.trayicon.set_icon("meocloud-error")
            self.paused = True
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

                notif_icon = os.path.join(
                    self.app_path, "icons/meocloud.svg")
                notif_title = _('Cloud Folder Missing')
                notif_string = _('Your cloud folder is missing.')
                notification = Notify.Notification.new(notif_title,
                                                       notif_string,
                                                       notif_icon)
                notification.show()

                os.system("killall meocloud-gui && " +
                          os.path.join(self.app_path, "meocloud-gui &"))
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

        utils.touch(cloud_home)

    def update_status(self, status):
        GLib.idle_add(lambda: self.menuitem_status.set_label(status))

    def update_menu_action(self, action):
        GLib.idle_add(lambda: self.menuitem_changestatus.set_label(action))

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
        used = utils.convert_size(used)
        total = utils.convert_size(total)

        self.menuitem_storage.set_label(
            _("{0} used of {1}").format(str(used), str(total)))

    def prefs_window_destroyed(self, w):
        self.prefs_window = None

    def show_prefs(self, w):
        if not self.prefs_window:
            self.prefs_window = PrefsWindow(self)
            self.prefs_window.connect("destroy", self.prefs_window_destroyed)
            self.prefs_window.logout_button.connect("clicked", self.on_logout)
        self.prefs_window.show_all()
        self.prefs_window.present()

    def on_logout(self, w):
        log.info('Application.on_logout: initiating logout')
        self.prefs_window.destroy()
        Thread(target=self.on_logout_thread).start()

    def on_logout_thread(self):
        meocloud_gui.core.api.unlink(self.core_client, Preferences())

        if os.path.isfile(os.path.join(UI_CONFIG_PATH, 'prefs.ini')):
            os.remove(os.path.join(UI_CONFIG_PATH, 'prefs.ini'))
        if os.path.isfile(os.path.join(UI_CONFIG_PATH,
                                       'ignored_directories')):
            os.remove(os.path.join(UI_CONFIG_PATH, 'ignored_directories'))
        utils.purge_all()

        self.ignored_directories = []
        self.requires_authorization = True
        self.update_status(_("Unauthorized"))
        self.update_menu_action(_("Authorize"))
        GLib.idle_add(lambda: self.clean_recent_files())
        GLib.idle_add(lambda: self.menuitem_prefs.hide())
        log.info('Application.on_logout_thread: completing logout')
        self.restart_core()

    def open_folder(self, w):
        prefs = Preferences()
        subprocess.Popen(["xdg-open", prefs.get('Advanced', 'Folder',
                                                CLOUD_HOME_DEFAULT_PATH)])

    def open_website(self, w):
        subprocess.Popen(["xdg-open", self.core_client.webLoginURL()])

    def restart_core(self, ignore_sync=False):
        log.info('Application.restart_core: initiating core restart')
        prefs = Preferences()

        self.core_client = CoreClient()
        self.core_listener = CoreListener(CORE_LISTENER_SOCKET_ADDRESS,
                                          self.core_client, prefs, self,
                                          ignore_sync)
        self.core = Core(self.core_client)

        # Make sure core isn't running
        self.stop_threads()

        # Start the core
        self.listener_thread = Thread(target=self.core_listener.start)
        self.watchdog_thread = Thread(target=self.core.watchdog)
        self.listener_thread.start()
        self.watchdog_thread.start()

        # Restart DBus
        self.dbus_service.update_prefs()
        log.info('Application.restart_core: core restart completed')

    def stop_threads(self):
        if self.listener_thread is not None and self.listener_thread.isAlive:
            self.listener_thread._Thread__stop()
        if self.watchdog_thread is not None and self.watchdog_thread.isAlive:
            self.watchdog_thread._Thread__stop()
        if self.shell is not None and self.shell._thread.isAlive:
            self.shell._thread._Thread__stop()
        self.shell = None

        if self.core is not None:
            self.core.stop()

        log.info('Application.stop_threads: threads stopped')

    def quit(self):
        self.stop_threads()
        log.info('Application.quit: shutting down')
        self.running = False
        Gtk.Application.quit(self)
