import os
from gi.repository import Gtk, Gio
from meocloud_gui.preferences import Preferences
from meocloud_gui.gui.pages import Pages
from meocloud_gui.gui.prefswindow import PrefsWindow


class SetupWindow(Gtk.Window):
    __gtype_name__ = 'SetupWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.set_title("Setup")

        self.app = app
        self.pages = Pages()
        self.add(self.pages)
        
        # First page

        first_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        first_page_box.pack_start(Gtk.Label("Welcome to MEO Cloud"), False, True, 10)
        
        self.setup_easy = Gtk.RadioButton.new_with_label(None, "Easy")
        self.setup_advanced = Gtk.RadioButton.new_with_label_from_widget(
            self.setup_easy, "Advanced")
        
        first_page_box.pack_start(self.setup_easy, False, True, 10)
        first_page_box.pack_start(self.setup_advanced, False, True, 10)
        
        first_page_next_button = Gtk.Button("Next")
        first_page_next_button.connect("clicked", self.on_second_page)
        first_page_box_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        first_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        first_page_box_horizontal.pack_start(first_page_next_button, False, False, 0)
        first_page_box.pack_end(first_page_box_horizontal, False, False, 10)
        
        self.pages.append_page(first_page_box, Gtk.Label())

        # Second page (device info)

        second_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pages.append_page(second_page_box, Gtk.Label())
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.device_entry = Gtk.Entry()
        device_box.pack_start(Gtk.Label(""), True, True, 0)
        device_box.pack_start(Gtk.Label("Device name: "), False, False, 0)
        device_box.pack_start(self.device_entry, False, False, 0)
        device_box.pack_start(Gtk.Label(""), True, True, 0)
        second_page_box.pack_start(device_box, False, False, 10)
        
        second_page_back_button = Gtk.Button("Back")
        second_page_back_button.connect("clicked", self.on_first_page)
        self.login_button = Gtk.Button("Authorize")
        second_page_box_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        second_page_box_horizontal.pack_start(second_page_back_button, False, False, 0)
        second_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        second_page_box_horizontal.pack_start(self.login_button, False, False, 0)
        second_page_box.pack_end(second_page_box_horizontal, False, False, 10)
        
        # Spinner page
        
        self.spinner = Gtk.Spinner()
        self.pages.append_page(self.spinner, Gtk.Label())

        # Advanced setup page
        
        advanced_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        app.prefs_window = PrefsWindow(app, True)
        app.prefs_window.remove(app.prefs_window.notebook)
        advanced_page_box.pack_start(app.prefs_window.notebook, False, False, 0)
        
        advanced_page_finish_button = Gtk.Button("Finish")
        advanced_page_finish_button.connect("clicked", self.finish_advanced_setup)
        advanced_page_box_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        advanced_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        advanced_page_box_horizontal.pack_start(advanced_page_finish_button, False, False, 0)
        advanced_page_box.pack_end(advanced_page_box_horizontal, False, False, 10)
        
        self.pages.append_page(advanced_page_box, Gtk.Label())

        # Success page

        success_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        success_label = Gtk.Label("Your computer has been successfuly linked.")
        success_page_box.pack_start(success_label, False, False, 10)
        
        success_page_finish_button = Gtk.Button("Finish")
        success_page_finish_button.connect("clicked", lambda w: self.destroy())
        success_page_box_horizontal = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        success_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        success_page_box_horizontal.pack_start(success_page_finish_button, False, False, 0)
        success_page_box.pack_end(success_page_box_horizontal, False, False, 10)
        
        self.pages.append_page(success_page_box, Gtk.Label())

        self.set_size_request(400, 300)

    def on_first_page(self, widget):
        self.pages.first_page()

    def on_second_page(self, widget):
        self.pages.next_page()

    def start_waiting(self):
        self.pages.next_page()
        self.spinner.start()

    def stop_waiting(self):
        self.pages.next_page()
        self.spinner.stop()

    def finish_advanced_setup(self, widget):
        self.app.restart_core()
        self.destroy()

    def destroy(self):
        self.app.prefs_window.destroy()
        self.app.prefs_window = None
        Gtk.Window.destroy(self)
