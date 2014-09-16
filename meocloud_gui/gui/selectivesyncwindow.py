import os.path
import os
from gi.repository import Gtk
from meocloud_gui.gui.spinnerbox import SpinnerBox

from meocloud_gui.constants import (LOGGER_NAME, UI_CONFIG_PATH)

# Logging
import logging

log = logging.getLogger(LOGGER_NAME)


class SelectiveSyncWindow(Gtk.Window):
    __gtype_name__ = 'SelectiveSyncWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.set_title(_("Selective Sync"))
        self.set_position(Gtk.WindowPosition.CENTER)

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

        self.ignored_directories = self.app.core_client.ignoredDirectories()[:]

    def add_column(self, folders):
        log.info('SelectiveSyncWindow.add_column: received data, '
                 'adding column')
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
        except AttributeError:
            log.warning('SelectiveSyncWindow.add_column: Gtk older than 3.8, '
                        'falling back')

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
        scrolled_tree = Gtk.ScrolledWindow()
        scrolled_tree.add_with_viewport(treeview)
        self.hbox.pack_start(scrolled_tree, True, True, 0)

        for folder in folders:
            if folder in self.ignored_directories:
                liststore.append([os.path.basename(folder), False, folder])
            else:
                liststore.append([os.path.basename(folder), True, folder])

        self.columns.append(scrolled_tree)
        self.show_all()
        log.info('SelectiveSyncWindow.add_column: column ready')

    def on_row_activated(self, widget, row, col, liststore):
        if not self.cell_toggled:
            path = liststore[row][2]

            for i in range(len(path.split('/')) - 1, len(self.columns)):
                self.hbox.remove(self.columns[len(path.split('/')) - 1])
                col = self.columns[len(path.split('/')) - 1]
                col.destroy()
                self.columns.remove(col)

            for i in xrange(len(path.split('/')) - 2, len(self.separators)):
                self.hbox.remove(self.separators[len(path.split('/')) - 2])
                sep = self.separators[len(path.split('/')) - 2]
                sep.destroy()
                self.separators.remove(sep)

            self.hbox.pack_start(self.spinner, True, True, 0)
            self.spinner.start()
            log.info('SelectiveSyncWindow.on_row_activated: requesting '
                     'remote directory listing')
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
        self.app.core_client.setIgnoredDirectories(
            self.ignored_directories)

        log.info('SelectiveSyncWindow.save_ignored_directories: '
                 'ignored directories saved')
        self.destroy()
