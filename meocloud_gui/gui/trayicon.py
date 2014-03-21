import subprocess
import os
from gi.repository import GObject, Gtk


class TrayIcon (GObject.Object):
    __gtype_name__ = 'TrayIcon'

    def __init__(self, app):
        self.app = app

        self.icon = Gtk.StatusIcon()
        self.icon.set_from_stock(Gtk.STOCK_ABOUT)
        self.icon.connect("activate", self.tray_popup)
        self.icon.connect("popup_menu", self.tray_popup)

        self.menu = Gtk.Menu()

    def show(self):
        self.icon.set_visible(True)
        self.menu.show_all()

    def tray_quit(self, widget, data=None):
        self.app.release()
        self.app.quit()

    def tray_popup(self, widget, button=None, time=None, data=None):
        if time is None:
            time = Gtk.get_current_event().get_time()

        self.menu.show_all()
        self.menu.popup(None, None, lambda w, x:
                        self.icon.position_menu(self.menu, self.icon),
                        self.icon, 3, time)

    def add_menu_item(self, menuitem, hide=False):
        self.menu.append(menuitem)

        if hide:
            menuitem.set_no_show_all(True)
            menuitem.hide()

    def hide(self):
        self.icon.set_visible(False)
