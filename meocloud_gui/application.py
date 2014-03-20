import subprocess
import os
import keyring
from threading import Thread
from time import sleep
from gi.repository import Gtk, Gio
from meocloud_gui import utils
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.preferences import Preferences
from meocloud_gui.core.core import Core
from meocloud_gui.core.core_client import CoreClient
from meocloud_gui.core.core_listener import CoreListener
import meocloud_gui.core.api

from meocloud_gui.settings import (CORE_LISTENER_SOCKET_ADDRESS,
                                   LOGGER_NAME, DAEMON_PID_PATH,
                                   DAEMON_LOCK_PATH,  DEV_MODE,
                                   VERSION, DAEMON_VERSION_CHECKER_PERIOD,
                                   CLOUD_HOME_DEFAULT_PATH, UI_CONFIG_PATH)

try:
    from meocloud_gui.gui.indicator import Indicator as TrayIcon
except:
    from meocloud_gui.gui.trayicon import TrayIcon


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id="pt.meocloud",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

        self.prefs_window = None
        self.trayicon = TrayIcon(self)
        self.trayicon.show()

        self.running = False
        self.core_client = None
        self.core_listener = None
        self.core = None
        self.setup = None
        
        self.sync_thread = None
        self.menu_thread = None
        self.listener_thread = None
        self.watchdog_thread = None
        
        utils.create_required_folders()
        utils.init_logging()

    def on_activate(self, data=None):
        if not self.running:
            self.running = True
            prefs = Preferences()

            if not os.path.isfile(os.path.join(UI_CONFIG_PATH, 'prefs.ini')):
                run_setup = True
            
                try:
                    keyring.delete_password('meocloud', 'clientID')
                    keyring.delete_password('meocloud', 'authKey')
                except:
                    pass
            else:
                run_setup = False
                    
            self.setup = SetupWindow()

            menuitem_folder = Gtk.MenuItem("Open Folder")
            menuitem_site = Gtk.MenuItem("Open Website")
            self.menuitem_storage = Gtk.MenuItem("0 GB used of 16 GB")
            self.menuitem_status = Gtk.MenuItem("Unknown")
            menuitem_changestatus = Gtk.MenuItem("Pause/Resume")
            menuitem_prefs = Gtk.MenuItem("Preferences")
            menuitem_quit = Gtk.MenuItem("Quit")

            self.trayicon.add_menu_item(menuitem_folder)
            self.trayicon.add_menu_item(menuitem_site)
            self.trayicon.add_menu_item(self.menuitem_storage)
            self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
            self.trayicon.add_menu_item(self.menuitem_status)
            self.trayicon.add_menu_item(menuitem_changestatus)
            self.trayicon.add_menu_item(Gtk.SeparatorMenuItem())
            self.trayicon.add_menu_item(menuitem_prefs)
            self.trayicon.add_menu_item(menuitem_quit)

            menuitem_folder.connect("activate", self.open_folder)
            menuitem_site.connect("activate", self.open_website)
            menuitem_prefs.connect("activate", self.show_prefs)
            menuitem_quit.connect("activate", lambda w: self.quit())

            self.restart_core(run_setup)

            self.hold()

    def update_menu(self, status=None):
        if self.watchdog_thread.isAlive:
            try:
                if status == None:
                    status = self.core_client.currentStatus()
                self.update_storage(status.usedQuota, status.totalQuota)
                sync_status = self.core_client.currentSyncStatus()
                self.update_status(str(sync_status.pendingUploads) +
                                   " uploads/" +
                                   str(sync_status.pendingDownloads) +
                                    " downloads")
            except:
                pass
                
    def start_menu(self):
        while True:
            try:
                status = self.core_client.currentStatus()
                if status.usedQuota or status.totalQuota:
                    self.update_menu(status)
                    break
                sleep(1)
            except:
                sleep(1)

    def start_sync(self, prefs):
        cloud_home = prefs.get('Advanced', 'Folder', CLOUD_HOME_DEFAULT_PATH)

        while True:
            try:
                self.core_client.startSync(cloud_home)
                if self.sync_thread.isAlive:
                    self.sync_thread._Thread__stop()
                break
            except:
                sleep(1)

    def update_status(self, status):
        self.menuitem_status.set_label(status)

    def update_storage(self, used, total):
        used = utils.convert_size(used)
        total = utils.convert_size(total)

        self.menuitem_storage.set_label(str(used) +
                                        " used of " +
                                        str(total))

    def prefs_window_destroyed(self, w):
        self.prefs_window = None

    def show_prefs(self, w):
        if not self.prefs_window:
            self.prefs_window = PrefsWindow(self)
            self.prefs_window.connect("destroy", self.prefs_window_destroyed)
            self.prefs_window.logout_button.connect("clicked", self.on_logout)
            self.prefs_window.show_all()
        else:
            self.prefs_window.present()

    def on_logout(self, w):
        self.prefs_window.destroy()
        Thread(target=self.on_logout_thread).start()
        
    def on_logout_thread(self):
        meocloud_gui.core.api.unlink(self.core_client, Preferences())
        
        os.remove(os.path.join(UI_CONFIG_PATH, 'prefs.ini'))
        utils.purge_all()

        self.restart_core(True)

    def open_folder(self, w):
        prefs = Preferences()
        subprocess.Popen(["xdg-open", prefs.get('Advanced', 'Folder',
                        CLOUD_HOME_DEFAULT_PATH)])

    def open_website(self, w):
        subprocess.Popen(["xdg-open", self.core_client.webLoginURL()])

    def restart_core(self, ignore_sync=False):
        prefs = Preferences()
    
        self.core_client = CoreClient()
        self.core_listener = CoreListener(CORE_LISTENER_SOCKET_ADDRESS,
                                          self.core_client, prefs,
                                          None, self)
        self.core = Core(self.core_client)

        # Make sure core isn't running
        self.stop_threads()

        # Start the core
        self.listener_thread = Thread(target=self.core_listener.start)
        self.watchdog_thread = Thread(target=self.core.watchdog)
        self.sync_thread = Thread(target=self.start_sync, args=(prefs,))
        self.menu_thread = Thread(target=self.start_menu)
        self.listener_thread.start()
        self.watchdog_thread.start()
        if not ignore_sync:
            self.sync_thread.start()
            self.menu_thread.start()

    def stop_threads(self):
        try:
            if self.sync_thread.isAlive:
                self.sync_thread._Thread__stop()
            if self.menu_thread.isAlive:
                self.menu_thread._Thread__stop()
            if self.listener_thread.isAlive:
                self.listener_thread._Thread__stop()
            if self.watchdog_thread.isAlive:
                self.watchdog_thread._Thread__stop()
        except:
            pass

        self.core.stop()

    def quit(self):
        self.stop_threads()
        self.running = False
        Gtk.Application.quit(self)
