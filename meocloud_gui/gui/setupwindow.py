import os
from gi.repository import Gtk, Gio
from meocloud_gui.preferences import Preferences


class SetupWindow(Gtk.Window):
    __gtype_name__ = 'SetupWindow'

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title("Setup")

        folder_path = os.path.join(os.path.expanduser('~'), 'MEOCloud')

        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.add(box)

        box.add(Gtk.Label("Welcome"))
        
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.device_entry = Gtk.Entry()
        device_box.pack_start(Gtk.Label(""), True, True, 0)
        device_box.pack_start(Gtk.Label("Device name:"), False, False, 0)
        device_box.pack_start(self.device_entry, False, False, 0)
        device_box.pack_start(Gtk.Label(""), True, True, 0)
        box.add(device_box)
        
        self.login_button = Gtk.Button("Login")
        box.add(self.login_button)

        self.set_size_request(400, 300)
