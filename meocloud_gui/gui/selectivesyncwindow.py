import os.path
import os
from gi.repository import Gtk, Gio, GLib
from meocloud_gui.preferences import Preferences
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

        scrolled_win = Gtk.ScrolledWindow()
        self.add(scrolled_win)

        self.hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        scrolled_win.add_with_viewport(self.hbox)

        self.spinner = Gtk.Spinner()
        self.hbox.pack_start(self.spinner, True, True, 0)
        self.spinner.start()

        self.set_default_size(500, 300)
        self.columns = []
        self.separators = []

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
            if folder in self.app.ignored_directories:
                liststore.append([os.path.basename(folder), False, folder])
            else:
                liststore.append([os.path.basename(folder), True, folder])

        self.columns.append(treeview)
        self.show_all()

    def on_row_activated(self, widget, row, col, liststore):
        path = liststore[row][2]

        for i in range(len(path.split('/')) - 1, len(self.columns)):
            self.hbox.remove(self.columns[len(path.split('/')) - 1])
            col = self.columns[len(path.split('/')) - 1]
            col.destroy()
            self.columns.remove(col)

        for i in range(len(path.split('/')) - 1, len(self.separators)):
            self.hbox.remove(self.separators[len(path.split('/')) - 1])
            sep = self.separators[len(path.split('/')) - 1]
            sep.destroy()
            self.separators.remove(sep)

        self.hbox.pack_start(self.spinner, True, True, 0)
        self.spinner.start()
        self.app.core_client.requestRemoteDirectoryListing(path)

    def on_cell_toggled(self, widget, path, liststore):
        liststore[path][1] = not liststore[path][1]

        if liststore[path][2] in self.app.ignored_directories:
            self.app.ignored_directories.remove(liststore[path][2])
        else:
            self.app.ignored_directories.append(liststore[path][2])

        self.app.core_client.setIgnoredDirectories(
            self.app.ignored_directories)

        f = open(os.path.join(UI_CONFIG_PATH, 'ignored_directories'), "w")
        for directory in self.app.ignored_directories:
            f.write(directory + "\n")
        f.close()
