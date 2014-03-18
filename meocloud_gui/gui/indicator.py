import subprocess
import os
from gi.repository import GObject, Gtk
from gi.repository import AppIndicator3 as appindicator


class Indicator (GObject.Object):
    __gtype_name__ = 'Indicator'

    def __init__(self, app):
        self.app = app

        self.ind = appindicator.Indicator.new(
            "meocloud",
            "indicator-messages",
            appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)
        self.ind.set_attention_icon("indicator-messages-new")

        self.menu = Gtk.Menu()

        self.ind.set_menu(self.menu)

    def show(self):
        self.menu.show_all()

    def tray_quit(self, widget, data=None):
        self.app.release()
        self.app.quit()

    def add_menu_item(self, menuitem):
        self.menu.append(menuitem)
        menuitem.show()
        self.ind.set_menu(self.menu)

    def hide(self):
        pass
