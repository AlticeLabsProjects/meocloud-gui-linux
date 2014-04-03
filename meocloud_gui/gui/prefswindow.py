import os.path
import os
from gi.repository import Gtk, GLib
from meocloud_gui.preferences import Preferences
from meocloud_gui.gui.progressdialog import ProgressDialog
from meocloud_gui.gui.selectivesyncwindow import SelectiveSyncWindow
import meocloud_gui.utils

from meocloud_gui.core import api
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH


class PrefsWindow(Gtk.Window):
    __gtype_name__ = 'PrefsWindow'

    def __init__(self, app, embed=False):
        Gtk.Window.__init__(self)
        self.set_title(_("Preferences"))
        self.set_position(Gtk.WindowPosition.CENTER)

        prefs = Preferences()
        self.app = app
        self.selective_sync = None

        # notebook boxes
        general_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        general_box.set_margin_left(10)
        general_box.set_margin_right(10)
        account_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        account_box.set_margin_left(10)
        account_box.set_margin_right(10)
        network_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        network_box.set_margin_left(10)
        network_box.set_margin_right(10)
        advanced_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        advanced_box.set_margin_left(10)
        advanced_box.set_margin_right(10)

        # display notifications
        display_notif = prefs.get("General", "Notifications", "True") == "True"
        display_notifications = Gtk.CheckButton(_("Display notifications"))
        display_notifications.set_active(display_notif)
        display_notifications.connect("toggled",
                                      self.toggle_display_notifications)
        general_box.pack_start(display_notifications, False, True, 10)

        # use dark icons
        display_dark = prefs.get("General", "DarkIcons", "False") == "True"
        display_darkicons = Gtk.CheckButton(_("Use dark icons"))
        display_darkicons.set_active(display_dark)
        display_darkicons.connect("toggled",
                                  self.toggle_icons)
        general_box.pack_start(display_darkicons, False, True, 0)

        # start at login
        start_at_login = Gtk.CheckButton(_("Start MEO Cloud at login"))
        start_at_login_path = os.path.join(os.path.expanduser('~'),
                                           '.config/autostart/' +
                                           'meocloud.desktop')
        start_at_login.set_active(os.path.isfile(start_at_login_path))
        start_at_login.connect("toggled", self.toggle_start_at_login)
        general_box.pack_start(start_at_login, False, True, 10)

        # account
        login_label = Gtk.Label(_("You are logged in with {0}.").format(
            prefs.get('Account', 'email', '')))
        self.logout_button = Gtk.Button(_("Unlink"))
        account_box.pack_start(login_label, False, True, 10)
        account_box.pack_start(self.logout_button, False, True, 10)

        # proxy label
        proxy_label = Gtk.Label("<b>" + _("Proxy") + "</b>")
        proxy_label.set_use_markup(True)
        proxy_label.set_alignment(0, 0)

        # proxy radio buttons
        self.proxy_none = Gtk.RadioButton.new_with_label(None, _("None"))
        self.proxy_none.connect("toggled", lambda w: self.set_proxy(w,
                                                                    "None"))
        self.proxy_automatic = Gtk.RadioButton.new_with_label_from_widget(
            self.proxy_none, _("Automatic"))
        self.proxy_automatic.connect("toggled", lambda w:
                                     self.set_proxy(w, "Automatic"))
        self.proxy_manual = Gtk.RadioButton.new_with_label_from_widget(
            self.proxy_none, _("Manual"))
        self.proxy_manual.connect("toggled", lambda w:
                                  self.set_proxy(w, "Manual"))

        # proxy automatic configuration
        self.proxy_automatic_url = Gtk.Entry()
        self.proxy_automatic_url.set_placeholder_text("http://www.example.com")
        self.proxy_automatic_url.set_text(prefs.get("Network", "ProxyURL", ""))
        self.proxy_automatic_url.set_no_show_all(True)
        self.proxy_automatic_url.connect("changed",
                                         self.proxy_automatic_value_changed)

        # proxy manual configuration
        self.proxy_manual_address = Gtk.Entry()
        self.proxy_manual_address.set_placeholder_text("Address")
        self.proxy_manual_address.set_text(
            prefs.get("Network", "ProxyAddress", ""))
        self.proxy_manual_address.set_no_show_all(True)
        self.proxy_manual_address.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyAddress"))

        self.proxy_manual_port = Gtk.Entry()
        self.proxy_manual_port.set_placeholder_text("Port")
        self.proxy_manual_port.set_text(
            prefs.get("Network", "ProxyPort", ""))
        self.proxy_manual_port.set_no_show_all(True)
        self.proxy_manual_port.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyPort"))

        self.proxy_manual_user = Gtk.Entry()
        self.proxy_manual_user.set_placeholder_text("User")
        self.proxy_manual_user.set_text(
            prefs.get("Network", "ProxyUser", ""))
        self.proxy_manual_user.set_no_show_all(True)
        self.proxy_manual_user.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyUser"))

        self.proxy_manual_password = Gtk.Entry()
        self.proxy_manual_password.set_visibility(False)
        self.proxy_manual_password.set_placeholder_text("Password")
        self.proxy_manual_password.set_text(
            prefs.get("Network", "ProxyPassword", ""))
        self.proxy_manual_password.set_no_show_all(True)
        self.proxy_manual_password.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyPassword"))

        # bandwidth label
        bandwidth_label = Gtk.Label("<b>" + _("Bandwidth") + "</b>")
        bandwidth_label.set_use_markup(True)
        bandwidth_label.set_alignment(0, 0)

        # download limit
        download_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        download_entry = Gtk.Entry()
        download_entry.set_sensitive(int(prefs.get("Network",
                                                   "ThrottleDownload",
                                                   "0")) > 0)
        download_text = prefs.get("Network", "ThrottleDownload", "128")
        if download_text == "0":
            download_text = "128"
        download_entry.set_text(download_text)
        download_entry.set_alignment(1)
        download_entry.connect("changed", lambda w:
                               self.throttle_value_changed(w, "Download"))
        download_check_active = int(prefs.get("Network", "ThrottleDownload",
                                              "0")) > 0
        download_check = Gtk.CheckButton(_("Download"))
        download_check.set_active(download_check_active)
        download_check.connect("toggled", lambda w:
                               self.toggle_throttle(download_entry,
                                                    "Download"))

        # upload limit
        upload_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        upload_entry = Gtk.Entry()
        upload_entry.set_sensitive(int(prefs.get("Network", "ThrottleUpload",
                                   "0")) > 0)
        upload_text = prefs.get("Network", "ThrottleUpload", "64")
        if upload_text == "0":
            upload_text = "64"
        upload_entry.set_text(upload_text)
        upload_entry.set_alignment(1)
        upload_entry.connect("changed", lambda w:
                             self.throttle_value_changed(w, "Upload"))

        upload_check_active = int(prefs.get("Network", "ThrottleUpload",
                                            "0")) > 0
        upload_check = Gtk.CheckButton(_("Upload"))
        upload_check.set_active(upload_check_active)
        upload_check.connect("toggled", lambda w:
                             self.toggle_throttle(upload_entry, "Upload"))

        # pack it all up
        download_box.pack_start(download_check, False, False, 0)
        upload_box.pack_start(upload_check, False, False, 0)
        download_box.pack_start(Gtk.Label(), True, True, 0)
        upload_box.pack_start(Gtk.Label(), True, True, 0)
        download_box.pack_start(download_entry, False, False, 5)
        upload_box.pack_start(upload_entry, False, False, 5)
        download_box.pack_start(Gtk.Label("KB/s"), False, False, 5)
        upload_box.pack_start(Gtk.Label("KB/s"), False, False, 5)

        network_box.pack_start(proxy_label, False, False, 5)
        network_box.pack_start(self.proxy_none, False, False, 0)
        network_box.pack_start(self.proxy_automatic, False, False, 0)
        network_box.pack_start(self.proxy_automatic_url, False, False, 5)
        network_box.pack_start(self.proxy_manual, False, False, 0)
        network_box.pack_start(self.proxy_manual_address, False, False, 5)
        network_box.pack_start(self.proxy_manual_port, False, False, 5)
        network_box.pack_start(self.proxy_manual_user, False, False, 5)
        network_box.pack_start(self.proxy_manual_password, False, False, 5)
        network_box.pack_start(bandwidth_label, False, False, 5)
        network_box.pack_start(download_box, False, False, 0)
        network_box.pack_start(upload_box, False, False, 5)

        # set the proxy settings
        if prefs.get("Network", "Proxy", "None") == "Automatic":
            self.proxy_automatic.set_active(True)
            self.proxy_automatic_url.show()
        elif prefs.get("Network", "Proxy", "None") == "Manual":
            self.proxy_manual.set_active(True)
            self.proxy_manual_address.show()
            self.proxy_manual_port.show()
            self.proxy_manual_user.show()
            self.proxy_manual_password.show()
        else:
            self.proxy_none.set_active(True)

        # advanced
        folder_button = Gtk.Button(prefs.get("Advanced", "Folder",
                                   _("Choose Folder")))
        folder_button.connect("clicked", self.on_choose_folder)
        selective_button = Gtk.Button(_("Selective Sync"))
        selective_button.connect("clicked", self.on_selective_sync)
        advanced_box.pack_start(folder_button, False, True, 10)
        advanced_box.pack_start(selective_button, False, True, 0)

        self.notebook = Gtk.Notebook()

        # change the contents according to where the preferences will be
        if embed:
            self.notebook.append_page(general_box, Gtk.Label(_("General")))
            self.notebook.append_page(network_box, Gtk.Label(_("Network")))
            self.notebook.append_page(advanced_box, Gtk.Label(_("Sync")))
        else:
            self.notebook.append_page(general_box, Gtk.Label(_("General")))
            self.notebook.append_page(account_box, Gtk.Label(_("Account")))
            self.notebook.append_page(network_box, Gtk.Label(_("Network")))
            self.notebook.append_page(advanced_box, Gtk.Label(_("Advanced")))

        self.add(self.notebook)

        self.set_size_request(300, 360)

    def toggle_display_notifications(self, w):
        prefs = Preferences()
        old_val = prefs.get("General", "Notifications", "True")

        if old_val == "True":
            prefs.put("General", "Notifications", "False")
        else:
            prefs.put("General", "Notifications", "True")

    def toggle_icons(self, w):
        prefs = Preferences()
        old_val = prefs.get("General", "DarkIcons", "False")

        if old_val == "True":
            prefs.put("General", "DarkIcons", "False")
        else:
            prefs.put("General", "DarkIcons", "True")

        self.app.dark_icons = not (old_val == "True")
        self.app.update_menu(None, True)

    def toggle_start_at_login(self, w):
        folder_path = os.path.join(os.path.expanduser('~'),
                                   '.config/autostart')
        file_path = os.path.join(folder_path, 'meocloud.desktop')

        if os.path.isfile(file_path):
            os.remove(file_path)
        else:
            meocloud_gui.utils.create_startup_file(self.app.app_path)

    def on_selective_sync(self, w, force_destroy=False):
        if force_destroy:
            self.selective_sync.destroy()

        if self.selective_sync is None:
            self.selective_sync = SelectiveSyncWindow(self.app)
            self.selective_sync.connect("destroy", self.on_selective_destroy)
            self.app.core_client.requestRemoteDirectoryListing('/')
            self.selective_sync.show_all()

    def on_selective_destroy(self, w):
        selective_sync = self.selective_sync
        self.selective_sync = None
        selective_sync.destroy()

    def on_choose_folder(self, w):
        dialog = Gtk.FileChooserDialog(_("Please choose a folder"), self,
                                       Gtk.FileChooserAction.SELECT_FOLDER,
                                       (Gtk.STOCK_CANCEL,
                                        Gtk.ResponseType.CANCEL,
                                        _("Select"), Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            new_path = os.path.join(dialog.get_filename())
            dialog.destroy()
            prefs = Preferences()
            self.app.stop_threads()
            meocloud_gui.utils.purge_meta()

            prog = ProgressDialog()
            prog.show_all()

            def end(prog, timeout, new_path, error=False):
                if error:
                    GLib.source_remove(timeout)
                    GLib.idle_add(prog.destroy)

                    error_dialog = Gtk.Dialog("MEO Cloud", self, 0,
                                              (Gtk.STOCK_OK,
                                               Gtk.ResponseType.OK))

                    error_dialog.set_default_size(150, 100)

                    label = Gtk.Label(_("An error occurred while moving your "
                                        "MEO Cloud folder."))

                    box = error_dialog.get_content_area()
                    box.add(label)
                    error_dialog.show_all()
                    error_dialog.run()
                    error_dialog.destroy()
                else:
                    meocloud_gui.utils.clean_bookmark()
                    self.app.restart_core()
                    w.set_label(new_path)
                    prefs.put("Advanced", "Folder", new_path)
                    meocloud_gui.utils.create_bookmark()
                    GLib.source_remove(timeout)
                    prog.destroy()

            def pulse():
                prog.progress.pulse()
                return True
            timeout = GLib.timeout_add(200, pulse)

            old_path = prefs.get("Advanced", "Folder", CLOUD_HOME_DEFAULT_PATH)
            meocloud_gui.utils.move_folder_async(old_path, new_path,
                                                 lambda p, e:
                                                 end(prog, timeout, p, e))
        else:
            dialog.destroy()

    def toggle_throttle(self, w, throttle):
        prefs = Preferences()

        if w.get_sensitive():
            prefs.put("Network", "Throttle" + throttle, "0")
            w.set_sensitive(False)
            val = 0
        else:
            try:
                val = int(w.get_text())
            except:
                val = 128

            prefs.put("Network", "Throttle" + throttle, str(val))
            w.set_sensitive(True)

        if throttle == "Download":
            self.app.core_client.networkSettingsChanged(
                api.get_network_settings(prefs, download=val))
        elif throttle == "Upload":
            self.app.core_client.networkSettingsChanged(
                api.get_network_settings(prefs, upload=val))

    def throttle_value_changed(self, w, throttle):
        prefs = Preferences()

        try:
            val = int(w.get_text())
        except:
            val = 128

        prefs.put("Network", "Throttle" + throttle, str(val))

        if throttle == "Download":
            self.app.core_client.networkSettingsChanged(
                api.get_network_settings(prefs, download=val))
        elif throttle == "Upload":
            self.app.core_client.networkSettingsChanged(
                api.get_network_settings(prefs, upload=val))

    def proxy_automatic_value_changed(self, w):
        prefs = Preferences()
        prefs.put("Network", "ProxyURL", self.proxy_automatic_url.get_text())
        self.app.core_client.networkSettingsChanged(
            api.get_network_settings(prefs))

    def proxy_manual_value_changed(self, w, pref_name):
        prefs = Preferences()
        prefs.put("Network", pref_name, w.get_text())
        self.app.core_client.networkSettingsChanged(
            api.get_network_settings(prefs))

    def set_proxy(self, w, proxy):
        if w.get_active():
            prefs = Preferences()
            prefs.put("Network", "Proxy", proxy)

            if proxy == "None":
                self.proxy_automatic_url.hide()
                self.proxy_manual_address.hide()
                self.proxy_manual_port.hide()
                self.proxy_manual_user.hide()
                self.proxy_manual_password.hide()
                prefs.put("Network", "ProxyURL", "")
                prefs.put("Network", "ProxyAddress", "")
                prefs.put("Network", "ProxyPort", "")
                prefs.put("Network", "ProxyUser", "")
                prefs.put("Network", "ProxyPassword", "")
            elif proxy == "Automatic":
                self.proxy_manual_address.hide()
                self.proxy_manual_port.hide()
                self.proxy_manual_user.hide()
                self.proxy_manual_password.hide()
                prefs.put("Network", "ProxyAddress", "")
                prefs.put("Network", "ProxyPort", "")
                prefs.put("Network", "ProxyUser", "")
                prefs.put("Network", "ProxyPassword", "")
                self.proxy_automatic_url.show()
                prefs.put("Network", "ProxyURL",
                          self.proxy_automatic_url.get_text())
            else:
                self.proxy_automatic_url.hide()
                self.proxy_manual_address.show()
                self.proxy_manual_port.show()
                self.proxy_manual_user.show()
                self.proxy_manual_password.show()
                prefs.put("Network", "ProxyURL", "")
