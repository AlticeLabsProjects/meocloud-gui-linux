import subprocess
import os
from gi.repository import GObject, Gtk, GLib
from gi.repository import AppIndicator3 as appindicator


class Indicator (GObject.Object):
    __gtype_name__ = 'Indicator'

    def __init__(self, app):
        self.app = app
        self.syncing = 0
        self.timeout = None

        self.ind = appindicator.Indicator.new(
            "meocloud",
            "meocloud-ok",
            appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.set_icon("meocloud-ok")

        self.menu = Gtk.Menu()

        self.ind.set_menu(self.menu)

    def set_icon(self, name):
        if self.syncing > 0 and "sync" not in name:
            self.syncing = 0
        elif self.syncing < 1 and "sync" in name:
            self.syncing = 2
            if self.timeout is not None:
                GLib.source_remove(self.timeout)
            self.timeout = GLib.timeout_add(1000, self.cycle_sync_icon)

        GLib.idle_add(lambda: self.ind.set_icon(os.path.join(self.app.app_path,
                                                             "icons/" + name +
                                                             ".svg")))

    def cycle_sync_icon(self):
        if self.syncing < 1:
            return False

        icon_name = "meocloud-sync-" + str(self.syncing)
        if self.app.dark_icons:
            icon_name = icon_name + "-black"

        self.set_icon(icon_name)

        if self.syncing < 4:
            self.syncing = self.syncing + 1
        else:
            self.syncing = 1

        return True

    def show(self):
        self.menu.show_all()

    def tray_quit(self, widget, data=None):
        self.app.release()
        self.app.quit()

    def add_menu_item(self, menuitem, hide=False):
        self.menu.append(menuitem)

        if hide:
            menuitem.set_no_show_all(True)
            menuitem.hide()
        else:
            menuitem.show()

    def hide(self):
        pass
