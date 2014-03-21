import os.path
import os
from gi.repository import Gtk, Gio, GLib
from meocloud_gui.preferences import Preferences
import meocloud_gui.utils

from meocloud_gui.settings import (CORE_LISTENER_SOCKET_ADDRESS,
                                   LOGGER_NAME, DAEMON_PID_PATH,
                                   DAEMON_LOCK_PATH,  DEV_MODE,
                                   VERSION, DAEMON_VERSION_CHECKER_PERIOD,
                                   CLOUD_HOME_DEFAULT_PATH, UI_CONFIG_PATH)


class SelectiveSyncWindow(Gtk.Window):
    __gtype_name__ = 'SelectiveSyncWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.set_title("Selective Sync")

        self.app = app

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.add(self.hbox)

        self.spinner = Gtk.Spinner()
        self.hbox.pack_start(self.spinner, True, True, 0)
        self.spinner.start()

        self.liststore = None
        self.set_default_size(200, 200)

    def fill_with_folders(self, folders):
        if self.liststore is None:
            self.liststore = Gtk.ListStore(str, bool)

            treeview = Gtk.TreeView(model=self.liststore)

            renderer_toggle = Gtk.CellRendererToggle()
            renderer_toggle.connect("toggled", self.on_cell_toggled)
            column_toggle = Gtk.TreeViewColumn("Sync", renderer_toggle,
                                               active=1)
            treeview.append_column(column_toggle)

            renderer_text = Gtk.CellRendererText()
            column_text = Gtk.TreeViewColumn("Folder", renderer_text, text=0)
            treeview.append_column(column_text)

            self.hbox.remove(self.spinner)
            self.hbox.pack_start(treeview, True, True, 0)

        for folder in folders:
            if folder in self.app.ignored_directories:
                self.liststore.append([folder, False])
            else:
                self.liststore.append([folder, True])

        self.show_all()

    def on_cell_toggled(self, widget, path):
        self.liststore[path][1] = not self.liststore[path][1]

        if self.liststore[path][0] in self.app.ignored_directories:
            self.app.ignored_directories.remove(self.liststore[path][0])
        else:
            self.app.ignored_directories.append(self.liststore[path][0])

        self.app.core_client.setIgnoredDirectories(
            self.app.ignored_directories)

        f = open(os.path.join(UI_CONFIG_PATH, 'ignored_directories'), "w")
        for directory in self.app.ignored_directories:
            f.write(directory + "\n")
        f.close()
