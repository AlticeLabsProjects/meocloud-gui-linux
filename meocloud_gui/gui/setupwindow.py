import os
from gi.repository import Gtk, Gio
from meocloud_gui.preferences import Preferences
import meocloud_gui.utils

class SetupWindow(Gtk.Window):
    __gtype_name__ = 'SetupWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.app = app
        self.set_title("Setup")

        folder_path = os.path.join(os.path.expanduser('~'), 'MEOCloud')

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(box)

        box.add(Gtk.Label("Welcome"))

        login_button = Gtk.Button("Login")
        login_button.connect("clicked", self.on_login)
        box.add(login_button)

        self.set_size_request(400, 300)

    def on_login(self, w):
        prefs = Preferences()
        prefs.put("Account", "LoggedIn", "True")

        meocloud_gui.utils.create_startup_file()

        self.app.on_activate()
        self.destroy()
