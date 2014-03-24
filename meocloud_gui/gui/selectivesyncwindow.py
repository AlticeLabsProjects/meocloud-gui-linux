import os.path
import os
from gi.repository import Gtk, Gio, GLib
from meocloud_gui.preferences import Preferences
from meocloud_gui.gui.spinnerbox import SpinnerBox
import meocloud_gui.utils

from meocloud_gui.constants import (CORE_LISTENER_SOCKET_ADDRESS,
                                    LOGGER_NAME, DAEMON_PID_PATH,
                                    DAEMON_LOCK_PATH,  DEV_MODE,
                                    VERSION, DAEMON_VERSION_CHECKER_PERIOD,
                                    CLOUD_HOME_DEFAULT_PATH, UI_CONFIG_PATH)


class SelectiveSyncWindow(Gtk.Window):
    __gtype_name__ = 'SelectiveSyncWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.set_title(_("Selective Sync"))

        self.app = app
        self.first_column = True

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        scrolled_win = Gtk.ScrolledWindow()
        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        scrolled_win.add_with_viewport(self.hbox)
        vbox.pack_start(scrolled_win, True, True, 0)

        self.spinner = SpinnerBox()
        self.hbox.pack_start(self.spinner, True, True, 0)
        self.spinner.start()

        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(button_box, False, False, 5)

        cancel_button = Gtk.Button(_("Cancel"))
        cancel_button.connect("clicked", lambda w: self.destroy())
        save_button = Gtk.Button(_("Save"))
        save_button.connect("clicked", self.save_ignored_directories)

        button_box.pack_start(Gtk.Label(), True, True, 0)
        button_box.pack_start(cancel_button, False, False, 0)
        button_box.pack_start(save_button, False, False, 5)

        self.set_default_size(500, 300)
        self.columns = []
        self.separators = []
        self.cell_toggled = False

        self.ignored_directories = self.app.ignored_directories[:]

    def add_column(self, folders, path='/'):
        if not self.first_column:
            separator = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
            self.separators.append(separator)
            self.hbox.pack_start(separator, False, False, 0)
        else:
            self.first_column = False

        liststore = Gtk.ListStore(str, bool, str)

        treeview = Gtk.TreeView(model=liststore)
        treeview.connect("row-activated", lambda w, r, c:
                         self.on_row_activated(w, r, c, liststore))

        # only works with Gtk >= 3.8
        try:
            treeview.set_activate_on_single_click(True)
        except:
            pass

        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", lambda w, p:
                                self.on_cell_toggled(w, p, liststore))
        column_toggle = Gtk.TreeViewColumn(_("Sync"), renderer_toggle,
                                           active=1)
        treeview.append_column(column_toggle)

        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn(_("Folder"), renderer_text, text=0)
        treeview.append_column(column_text)

        self.hbox.remove(self.spinner)
        self.hbox.pack_start(treeview, True, True, 0)

        for folder in folders:
            if folder in self.ignored_directories:
                liststore.append([os.path.basename(folder), False, folder])
            else:
                liststore.append([os.path.basename(folder), True, folder])

        self.columns.append(treeview)
        self.show_all()

    def on_row_activated(self, widget, row, col, liststore):
        if not self.cell_toggled:
            path = liststore[row][2]

            for i in range(len(path.split('/')) - 1, len(self.columns)):
                self.hbox.remove(self.columns[len(path.split('/')) - 1])
                col = self.columns[len(path.split('/')) - 1]
                col.destroy()
                self.columns.remove(col)

            for i in range(len(path.split('/')) - 2, len(self.separators)):
                self.hbox.remove(self.separators[len(path.split('/')) - 2])
                sep = self.separators[len(path.split('/')) - 2]
                sep.destroy()
                self.separators.remove(sep)

            self.hbox.pack_start(self.spinner, True, True, 0)
            self.spinner.start()
            self.app.core_client.requestRemoteDirectoryListing(path)
        else:
            self.cell_toggled = False

    def on_cell_toggled(self, widget, path, liststore):
        self.cell_toggled = True

        liststore[path][1] = not liststore[path][1]

        if liststore[path][2] in self.ignored_directories:
            self.ignored_directories.remove(liststore[path][2])
        else:
            self.ignored_directories.append(liststore[path][2])

    def save_ignored_directories(self, w):
        self.app.ignored_directories = self.ignored_directories

        self.app.core_client.setIgnoredDirectories(
            self.app.ignored_directories)

        f = open(os.path.join(UI_CONFIG_PATH, 'ignored_directories'), "w")
        for directory in self.app.ignored_directories:
            f.write(directory + "\n")
        f.close()

        self.destroy()
