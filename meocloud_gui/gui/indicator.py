import os
from gi.repository import GObject, Gtk, GLib, Gdk
from gi.repository import AppIndicator3 as appindicator


class Indicator (GObject.Object):
    __gtype_name__ = 'Indicator'

    def __init__(self, app):
        self.app = app
        self.syncing = 0
        self.timeout = None
        self.icon_name = "meocloud-init"
        self.icon_theme = Gtk.IconTheme()

        self.ind = appindicator.Indicator.new(
            "meocloud",
            "meocloud-init",
            appindicator.IndicatorCategory.APPLICATION_STATUS)
        self.ind.set_status(appindicator.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()

        self.ind.set_menu(self.menu)

    def wrapper_run(self, func):
        Gdk.threads_enter()
        try:
            func()
            self.ind.set_menu(self.menu)
        finally:
            Gdk.threads_leave()

    def wrapper(self, func):
        GLib.idle_add(self.wrapper_run, func)

    def set_icon(self, name):
        if self.app.icon_type != "":
            name += "-" + self.app.icon_type
            use_icon_name = False
        else:
            icon_info = self.icon_theme.lookup_icon(name, 32, 0)
            if icon_info is not None:
                use_icon_name = True
            else:
                use_icon_name = False

        self.icon_name = name

        if self.syncing > 0 and "sync" not in name:
            self.syncing = 0
        elif self.syncing < 1 and "sync" in name:
            self.syncing = 2
            if self.timeout is not None:
                GLib.source_remove(self.timeout)
            self.timeout = GLib.timeout_add(500, self.cycle_sync_icon)

        if use_icon_name:
            GLib.idle_add(self.ind.set_icon, name)
        else:
            GLib.idle_add(
                self.ind.set_icon,
                os.path.join(self.app.app_path, "icons/{brand}/{name}.svg".format(brand=self.app.brand, name=name)))

    def cycle_sync_icon(self):
        if self.syncing < 1:
            GLib.source_remove(self.timeout)
            self.timeout = None
            return False

        icon_name = "meocloud-sync-" + str(self.syncing)

        self.set_icon(icon_name)

        if self.syncing < 4:
            self.syncing += 1
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
