import os.path
from gi.repository import Gtk, Gio
from meocloud_gui.preferences import Preferences
import meocloud_gui.utils


class PrefsWindow(Gtk.Window):
    __gtype_name__ = 'PrefsWindow'

    def __init__(self):
        Gtk.Window.__init__(self)
        self.set_title("Preferences")

        prefs = Preferences()

        general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        account_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        network_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # general
        start_at_login = Gtk.CheckButton("Start MEO Cloud at login")
        start_at_login_path = os.path.join(os.path.expanduser('~'),
                                           '.config/autostart/' +
                                           'meocloud.desktop')
        start_at_login.set_active(os.path.isfile(start_at_login_path))
        start_at_login.connect("toggled", self.toggle_start_at_login)
        general_box.add(start_at_login)

        # account
        login_label = Gtk.Label("You are logged in with " + prefs.get('Account', 'email', '') + ".")
        self.logout_button = Gtk.Button("Logout")
        account_box.add(login_label)
        account_box.add(self.logout_button)

        # network
        proxy_label = Gtk.Label(" <b>Proxy</b>")
        proxy_label.set_use_markup(True)
        proxy_label.set_alignment(0, 0)

        proxy_automatic = Gtk.RadioButton.new_with_label(None, "Automatic")
        proxy_automatic.connect("toggled", lambda w: self.set_proxy(w,
                                "Automatic"))
        proxy_manual = Gtk.RadioButton.new_with_label_from_widget(
            proxy_automatic, "Manual")
        proxy_manual.connect("toggled", lambda w: self.set_proxy(w,
                             "Manual"))
        if prefs.get("Network", "Proxy", "Automatic") == "Manual":
            proxy_manual.set_active(True)
        else:
            proxy_automatic.set_active(True)

        bandwidth_label = Gtk.Label(" <b>Bandwidth</b>")
        bandwidth_label.set_use_markup(True)
        bandwidth_label.set_alignment(0, 0)

        download_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        upload_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        download_entry = Gtk.Entry()
        upload_entry = Gtk.Entry()
        download_entry.set_sensitive(int(prefs.get("Network", "ThrottleDownload",
                                     "0")) > 0)
        download_entry.set_text(prefs.get("Network", "ThrottleDownload", "100"))
        download_entry.connect("changed", lambda w: self.throttle_value_changed(w, "Download"))
        upload_entry.set_sensitive(int(prefs.get("Network", "ThrottleUpload",
                                   "0")) > 0)
        upload_entry.set_text(prefs.get("Network", "ThrottleUpload", "100"))
        upload_entry.connect("changed", lambda w: self.throttle_value_changed(w, "Upload"))

        upload_check_active = int(prefs.get("Network", "ThrottleUpload",
                                        "0")) > 0
        download_check_active = int(prefs.get("Network", "ThrottleDownload",
                                          "0")) > 0
        upload_check = Gtk.CheckButton("Upload")
        upload_check.set_active(upload_check_active)
        upload_check.connect("toggled", lambda w:
                             self.toggle_throttle(upload_entry, "Upload"))
        download_check = Gtk.CheckButton("Download")
        download_check.set_active(download_check_active)
        download_check.connect("toggled", lambda w:
                               self.toggle_throttle(download_entry,
                                                    "Download"))
        download_box.pack_start(download_check, False, False, 0)
        upload_box.pack_start(upload_check, False, False, 0)

        download_box.pack_start(download_entry, False, False, 5)
        upload_box.pack_start(upload_entry, False, False, 5)

        network_box.pack_start(proxy_label, False, False, 5)
        network_box.pack_start(proxy_automatic, False, False, 0)
        network_box.pack_start(proxy_manual, False, False, 0)
        network_box.pack_start(bandwidth_label, False, False, 5)
        network_box.pack_start(download_box, False, False, 0)
        network_box.pack_start(upload_box, False, False, 5)

        # advanced
        folder_button = Gtk.Button(prefs.get("Advanced", "Folder",
                                   "Choose Folder"))
        folder_button.connect("clicked", self.on_choose_folder)
        selective_button = Gtk.Button("Selective Sync")
        advanced_box.add(folder_button)
        advanced_box.add(selective_button)

        notebook = Gtk.Notebook()
        notebook.append_page(general_box, Gtk.Label("General"))
        notebook.append_page(account_box, Gtk.Label("Account"))
        notebook.append_page(network_box, Gtk.Label("Network"))
        notebook.append_page(advanced_box, Gtk.Label("Advanced"))
        self.add(notebook)

        self.set_size_request(300, 350)

    def toggle_start_at_login(self, w):
        folder_path = os.path.join(os.path.expanduser('~'),
                                   '.config/autostart')
        file_path = os.path.join(folder_path, 'meocloud.desktop')

        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            meocloud_gui.utils.create_startup_file()

    def on_choose_folder(self, w):
        dialog = Gtk.FileChooserDialog("Please choose a folder", self,
                                       Gtk.FileChooserAction.SELECT_FOLDER,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        "Select", Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            w.set_label(dialog.get_filename())
            prefs = Preferences()
            prefs.put("Advanced", "Folder", dialog.get_filename())

        dialog.destroy()

    def toggle_throttle(self, w, throttle):
        prefs = Preferences()
        old_val = prefs.get("Network", "Throttle" + throttle, "0")

        if int(old_val) > 0:
            prefs.put("Network", "Throttle" + throttle, "0")
            w.set_sensitive(False)
        else:
            try:
                val = int(w.get_text())
            except:
                val = 100

            prefs.put("Network", "Throttle" + throttle, val)
            w.set_sensitive(True)

    def throttle_value_changed(self, w, throttle):
        prefs = Preferences()

        try:
            val = int(w.get_text())
        except:
            val = 100

        prefs.put("Network", "Throttle" + throttle, val)

    def set_proxy(self, w, proxy):
        if w.get_active():
            prefs = Preferences()
            prefs.put("Network", "Proxy", proxy)
