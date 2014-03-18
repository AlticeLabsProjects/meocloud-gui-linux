import subprocess
import os
from gi.repository import Gtk, Gio
from meocloud_gui.gui.trayicon import TrayIcon
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.setupwindow import SetupWindow
from meocloud_gui.preferences import Preferences

try:
    from meocloud_gui.gui.indicator import Indicator
except:
    print "AppIndicator not supported."


class Application(Gtk.Application):
    def __init__(self):
        Gtk.Application.__init__(self, application_id="pt.meocloud",
                                 flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.connect("activate", self.on_activate)

        self.prefs_window = None
        self.trayicon = Indicator(self)

    def on_activate(self, data=None):
        # TODO run_setup only if there's no valid config file
        prefs = Preferences()
        run_setup = prefs.get("Account", "LoggedIn", "False") == "False"

        if run_setup:
            setup = SetupWindow(self)
            setup.show_all()

            self.add_window(setup)
        else:
            # TODO switch between trayicon and indicator automatically
            #trayicon = TrayIcon(self)
            #trayicon.show()

            # TODO update sync statusi
            menuitem_folder = Gtk.MenuItem("Open Folder")
            menuitem_site = Gtk.MenuItem("Open Website")
            menuitem_space = Gtk.MenuItem("0 GB used of 16GB")
            self.menuitem_status = Gtk.MenuItem("Unknown")
            menuitem_changestatus = Gtk.MenuItem("Pause/Resume")
            menuitem_prefs = Gtk.MenuItem("Preferences")
            menuitem_quit = Gtk.MenuItem("Quit")

            self.trayicon.add_menu_item(menuitem_folder)
            self.trayicon.add_menu_item(menuitem_site)
            self.trayicon.add_menu_item(menuitem_space)
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

            self.hold()

    def update_status(self, status):
        self.menuitem_status.set_label(status)

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
