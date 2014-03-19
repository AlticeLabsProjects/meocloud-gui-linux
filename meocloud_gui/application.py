import subprocess
import os
import keyring
from threading import Thread
from time import sleep
from gi.repository import Gtk, Gio
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.preferences import Preferences
from meocloud_gui.core.core import Core
from meocloud_gui.core.core_client import CoreClient
from meocloud_gui.core.core_listener import CoreListener

from meocloud_gui.settings import (CORE_LISTENER_SOCKET_ADDRESS,
                                            LOGGER_NAME, DAEMON_PID_PATH, DAEMON_LOCK_PATH, DEV_MODE,
                                            VERSION, DAEMON_VERSION_CHECKER_PERIOD)

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

    def on_activate(self, data=None):
        if not self.running:
            self.running = True

            prefs = Preferences()
            run_setup = prefs.get("Account", "LoggedIn", "False") == "False"

            if run_setup:
                try:
                    keyring.delete_password("meocloud", "clientID")
                    keyring.delete_password("meocloud", "authKey")
                except:
                    pass
            
                setup = SetupWindow(self)
                setup.show_all()

                self.add_window(setup)
            else:
                # TODO update sync status
                menuitem_folder = Gtk.MenuItem("Open Folder")
                menuitem_site = Gtk.MenuItem("Open Website")
                self.menuitem_storage = Gtk.MenuItem("0 GB used of 16GB")
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

                self.core_client = CoreClient()
                self.core_listener = CoreListener(CORE_LISTENER_SOCKET_ADDRESS, 
                                                  self.core_client, prefs, None)
                self.core = Core(self.core_client)
        
                # Make sure core isn't running
                self.core.stop()
        
                # Start the core
                self.listener_thread = Thread(target=self.core_listener.start)
                self.watchdog_thread = Thread(target=self.core.watchdog)
                self.listener_thread.start()
                self.watchdog_thread.start()
                
                self.status_thread = Thread(target=self.update_status_loop)
                self.status_thread.start()

                self.hold()

    def update_status_loop(self):
        # test code, remove later
        #sleep(5)
        #print self.core_client.requestRemoteDirectoryListing("")
    
        while True:
            sleep(1)
            if self.watchdog_thread.isAlive:
                status = self.core_client.currentStatus()
                self.update_storage(status.usedQuota, status.totalQuota)
                sync_status = self.core_client.currentSyncStatus()
                self.update_status(str(sync_status.pendingUploads) + 
                                   " uploads/" + str(sync_status.pendingDownloads) +
                                   " downloads")
            sleep(9)

    def update_status(self, status):
        self.menuitem_status.set_label(status)
        
    def update_storage(self, used, total):
        self.menuitem_storage.set_label(str(used) + " GB used of " + str(total) + " GB")

    def prefs_window_destroyed(self, w):
        self.prefs_window = None

    def show_prefs(self, w):
        if not self.prefs_window:
            self.prefs_window = PrefsWindow()
            self.prefs_window.connect("destroy", self.prefs_window_destroyed)
            self.prefs_window.show_all()
        else:
            self.prefs_window.present()

    def open_folder(self, w):
        prefs = Preferences()

        subprocess.call(["xdg-open", prefs.get('Advanced', 'Folder',
                        os.path.join(os.path.expanduser('~'), 'MEOCloud'))])

    def open_website(self, w):
        prefs = Preferences()

        subprocess.call(["xdg-open", "http://www.meocloud.pt"])
        
    def quit(self):
        if self.status_thread.isAlive:
            self.status_thread._Thread__stop()
        if self.listener_thread.isAlive:
            self.listener_thread._Thread__stop()
        if self.watchdog_thread.isAlive:
            self.watchdog_thread._Thread__stop()
        self.core.stop()
        Gtk.Application.quit(self)
