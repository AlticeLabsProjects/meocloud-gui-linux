import subprocess
import os
from gi.repository import GObject, Gtk, GLib
from gi.repository import AppIndicator3 as appindicator


class Indicator (GObject.Object):
    __gtype_name__ = 'Indicator'

    def __init__(self, app):
        self.app = app

        self.ind = appindicator.Indicator.new(
            "meocloud",
            "meocloud-ok",
            appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.set_icon("meocloud-ok")

        self.menu = Gtk.Menu()

        self.ind.set_menu(self.menu)

    def set_icon(self, name):
        GLib.idle_add(lambda: self.ind.set_icon(os.path.join(self.app.app_path,
                                                             "icons/" + name +
                                                             ".svg")))

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
