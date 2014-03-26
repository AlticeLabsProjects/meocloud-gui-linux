import subprocess
import os
from gi.repository import GObject, Gtk, GLib


class TrayIcon (GObject.Object):
    __gtype_name__ = 'TrayIcon'

    def __init__(self, app):
        self.app = app

        self.icon = Gtk.StatusIcon()
        self.set_icon("meocloud-ok")
        self.icon.connect("activate", self.tray_popup)
        self.icon.connect("popup_menu", self.tray_popup)

        self.menu = Gtk.Menu()

    def set_icon(self, name):
        icon_file = os.path.join(self.app.app_path, "icons/" + name + ".svg")
        print icon_file
        GLib.idle_add(lambda: self.icon.set_from_file(icon_file))

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
