import os.path

from gi.repository import Gtk, GLib
from meocloud_gui.gui.progressdialog import ProgressDialog
from meocloud_gui.gui.selectivesyncwindow import SelectiveSyncWindow
import meocloud_gui.utils

from meocloud_gui.core import api
from meocloud_gui.constants import CLOUD_HOME_DEFAULT_PATH, BRAND, BRAND_PROGRAM_NAME


class PrefsWindow(Gtk.Window):
    __gtype_name__ = 'PrefsWindow'

    def __init__(self, app, embed=False):
        Gtk.Window.__init__(self)
        self.set_title(_("Preferences"))
        self.set_position(Gtk.WindowPosition.CENTER)

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # (ugly) hack to keep a decent look everywhere... or at least try.
        global use_headerbar
        use_headerbar = app.use_headerbar
        customnotebook = __import__("meocloud_gui.gui.customnotebook")
        from customnotebook import CustomNotebook
        self.notebook = CustomNotebook()

        if embed and app.use_headerbar:
            try:
                stack = Gtk.StackSwitcher()
                stack.set_stack(self.notebook)
                stack.set_margin_right(5)
                stack.set_margin_left(5)

                hor_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

                hor_box.pack_start(Gtk.Label(), True, True, 0)
                hor_box.pack_start(stack, False, False, 0)
                hor_box.pack_start(Gtk.Label(), True, True, 0)

                self.box.pack_start(hor_box, False, False, 10)
            except AttributeError:
                pass
        elif app.use_headerbar:
            try:
                headerbar = Gtk.HeaderBar()
                stack = Gtk.StackSwitcher()
                stack.set_stack(self.notebook)
                stack.set_margin_right(5)
                headerbar.set_custom_title(stack)
                headerbar.set_show_close_button(True)
                self.set_titlebar(headerbar)
            except AttributeError:
                pass

        self.prefs = app.prefs
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

        # icon type
        icons_label = Gtk.Label("<b>Icons</b>")
        icons_label.set_use_markup(True)
        icons_label.set_alignment(0, 0)
        icons_label.set_margin_bottom(5)
        icons_label.set_margin_top(5)
        self.icon_type = self.prefs.get("General", "Icons", "")

        self.icon_normal = Gtk.RadioButton.new_with_label(
            None, _("Use default icons"))
        self.icon_black = Gtk.RadioButton.new_with_label_from_widget(
            self.icon_normal, _("Use dark icons"))
        self.icon_white = Gtk.RadioButton.new_with_label_from_widget(
            self.icon_normal, _("Use white icons"))

        general_box.pack_start(icons_label, False, True, 0)
        general_box.pack_start(self.icon_normal, False, True, 0)
        general_box.pack_start(self.icon_black, False, True, 0)
        general_box.pack_start(self.icon_white, False, True, 0)

        if self.icon_type == "black":
            self.icon_black.set_active(True)
        elif self.icon_type == "white":
            self.icon_white.set_active(True)
        else:
            self.icon_normal.set_active(True)

        # display notifications
        self.display_notif = self.prefs.get("General",
                                       "Notifications", "True") == "True"
        display_notifications = Gtk.CheckButton(_("Display notifications"))
        display_notifications.set_active(self.display_notif)

        general_box.pack_start(display_notifications, False, True, 10)

        # start at login
        start_at_login = Gtk.CheckButton(_("Start {brand_app} Cloud at login").format(brand_app=BRAND_PROGRAM_NAME))
        start_at_login_path = os.path.join(os.path.expanduser('~'),
                                           '.config/autostart/' +
                                           '{brand}.desktop'.format(brand=BRAND))
        if embed:
            start_at_login.set_active(True)
        else:
            start_at_login.set_active(os.path.isfile(start_at_login_path))

        general_box.pack_start(start_at_login, False, True, 10)

        # account
        login_label = Gtk.Label(_("You are logged in as {0}.").format(
            self.prefs.get('Account', 'email', '')))
        self.logout_button = Gtk.Button(_("Unlink"))
        account_box.pack_start(login_label, False, True, 10)
        account_box.pack_start(self.logout_button, False, True, 10)

        # proxy label
        proxy_label = Gtk.Label("<b>" + _("Proxy") + "</b>")
        proxy_label.set_use_markup(True)
        proxy_label.set_alignment(0, 0)

        # proxy radio buttons
        self.proxy_none = Gtk.RadioButton.new_with_label(None, _("None"))

        self.proxy_automatic = Gtk.RadioButton.new_with_label_from_widget(
            self.proxy_none, _("Automatic"))

        self.proxy_manual = Gtk.RadioButton.new_with_label_from_widget(
            self.proxy_none, _("Manual"))

        # proxy manual configuration
        self.proxy = {}
        self.proxy_manual_address = Gtk.Entry()
        self.proxy_manual_address.set_placeholder_text("Address")
        self.proxy["ProxyAddress"] = self.prefs.get("Network", "ProxyAddress", "")
        self.proxy_manual_address.set_text(self.proxy["ProxyAddress"])
        self.proxy_manual_address.set_no_show_all(True)

        self.proxy_manual_port = Gtk.Entry()
        self.proxy_manual_port.set_placeholder_text("Port")
        self.proxy["ProxyPort"] = self.prefs.get("Network", "ProxyPort", "")
        self.proxy_manual_port.set_text(self.proxy["ProxyPort"])
        self.proxy_manual_port.set_no_show_all(True)

        self.proxy_manual_user = Gtk.Entry()
        self.proxy_manual_user.set_placeholder_text("User")
        self.proxy["ProxyUser"] = self.prefs.get("Network", "ProxyUser", "")
        self.proxy_manual_user.set_text(self.proxy["ProxyUser"])
        self.proxy_manual_user.set_no_show_all(True)

        self.proxy_manual_password = Gtk.Entry()
        self.proxy_manual_password.set_visibility(False)
        self.proxy_manual_password.set_placeholder_text("Password")
        self.proxy["ProxyPassword"] = self.prefs.creds.proxy_password
        self.proxy_manual_password.set_text(self.proxy["ProxyPassword"])
        self.proxy_manual_password.set_no_show_all(True)

        # bandwidth label
        bandwidth_label = Gtk.Label("<b>" + _("Bandwidth") + "</b>")
        bandwidth_label.set_use_markup(True)
        bandwidth_label.set_alignment(0, 0)

        # download limit
        download_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        download_entry = Gtk.Entry()
        self.throttle = dict()
        self.throttle["Download"] = self.prefs.get(
            "Network", "ThrottleDownload", "0")
        download_entry.set_sensitive(int(self.throttle["Download"]) > 0)
        download_text = self.throttle["Download"]
        if download_text == "0":
            download_text = "128"
        download_entry.set_text(download_text)
        download_entry.set_alignment(1)

        download_check_active = int(self.throttle["Download"]) > 0
        download_check = Gtk.CheckButton(_("Download"))
        download_check.set_active(download_check_active)

        # upload limit
        upload_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        upload_entry = Gtk.Entry()
        self.throttle["Upload"] = self.prefs.get("Network", "ThrottleUpload", "0")
        upload_entry.set_sensitive(int(self.throttle["Upload"]) > 0)
        upload_text = self.throttle["Upload"]
        if upload_text == "0":
            upload_text = "64"
        upload_entry.set_text(upload_text)
        upload_entry.set_alignment(1)

        upload_check_active = int(self.throttle["Upload"]) > 0
        upload_check = Gtk.CheckButton(_("Upload"))
        upload_check.set_active(upload_check_active)

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
        network_box.pack_start(self.proxy_manual, False, False, 0)
        network_box.pack_start(self.proxy_manual_address, False, False, 5)
        network_box.pack_start(self.proxy_manual_port, False, False, 5)
        network_box.pack_start(self.proxy_manual_user, False, False, 5)
        network_box.pack_start(self.proxy_manual_password, False, False, 5)
        network_box.pack_start(bandwidth_label, False, False, 5)
        network_box.pack_start(download_box, False, False, 0)
        network_box.pack_start(upload_box, False, False, 5)

        # proxy settings
        self.proxy["Proxy"] = self.prefs.get("Network", "Proxy", "Automatic")

        if self.proxy["Proxy"] == "Manual":
            self.proxy_manual.set_active(True)
            self.proxy_manual_address.show()
            self.proxy_manual_port.show()
            self.proxy_manual_user.show()
            self.proxy_manual_password.show()
        elif self.proxy['Proxy'] == "Automatic":
            self.proxy_automatic.set_active(True)
        else:
            self.proxy_none.set_active(True)

        # advanced
        if not embed:
            folder_button = Gtk.Button(self.prefs.get("Advanced", "Folder",
                                       CLOUD_HOME_DEFAULT_PATH))
            folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            folder_box.pack_start(Gtk.Label(_("{brand_app} Folder: ").format(brand_app=BRAND_PROGRAM_NAME)),
                                  False, False, 0)
            folder_box.pack_start(folder_button, True, True, 0)
            advanced_box.pack_start(folder_box, False, True, 10)
            folder_button.connect("clicked", self.on_choose_folder)
            selective_box_pad = 0
        else:
            selective_box_pad = 10

        self.selective_button = Gtk.Button(_("Select Synced Folders"))
        selective_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        selective_box.pack_start(Gtk.Label(_("Selective Sync: ")),
                                 False, False, 0)
        selective_box.pack_start(self.selective_button, True, True, 0)
        advanced_box.pack_start(selective_box, False, True, selective_box_pad)

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

        self.box.pack_start(self.notebook, True, True, 0)

        if not embed and not app.use_headerbar:
            close_button = Gtk.Button(_("Close"))
            close_button.connect("clicked", self.destroy)
            close_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            close_box.pack_end(close_button, False, False, 10)
            self.box.pack_end(close_box, False, False, 10)

        self.icon_normal.connect(
            "toggled", lambda w: self.toggle_icons(w, ""))
        self.icon_black.connect("toggled", lambda w:
                                self.toggle_icons(w, "black"))
        self.icon_white.connect("toggled", lambda w:
                                self.toggle_icons(w, "white"))
        display_notifications.connect("toggled",
                                      self.toggle_display_notifications)
        start_at_login.connect("toggled", self.toggle_start_at_login)
        self.proxy_none.connect("toggled", lambda w: self.set_proxy(w,
                                                                    "None"))
        self.proxy_automatic.connect("toggled", lambda w:
                                     self.set_proxy(w, "Automatic"))
        self.proxy_manual.connect("toggled", lambda w:
                                  self.set_proxy(w, "Manual"))
        self.proxy_manual_address.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyAddress"))
        self.proxy_manual_port.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyPort"))
        self.proxy_manual_user.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyUser"))
        self.proxy_manual_password.connect(
            "changed", lambda w: self.proxy_manual_value_changed(
                w, "ProxyPassword"))
        download_entry.connect("changed", lambda w:
                               self.throttle_value_changed(w, "Download"))
        download_check.connect("toggled", lambda w:
                               self.toggle_throttle(download_entry,
                                                    "Download"))
        upload_entry.connect("changed", lambda w:
                             self.throttle_value_changed(w, "Upload"))
        upload_check.connect("toggled", lambda w:
                             self.toggle_throttle(upload_entry, "Upload"))
        self.selective_button.connect("clicked", self.on_selective_sync)
        self.connect("destroy", self.destroy)

        self.add(self.box)
        self.set_size_request(300, 360)

    def destroy(self, w=None):
        prefs = self.prefs

        prefs.put("General", "Notifications", self.display_notif)
        prefs.put("General", "Icons", self.icon_type)

        prefs.put("Network", "ThrottleUpload", self.throttle["Upload"])
        prefs.put("Network", "ThrottleDownload", self.throttle["Download"])

        prefs.put("Network", "Proxy", self.proxy["Proxy"])
        prefs.put("Network", "ProxyAddress", self.proxy["ProxyAddress"])
        prefs.put("Network", "ProxyPort", self.proxy["ProxyPort"])
        prefs.put("Network", "ProxyUser", self.proxy["ProxyUser"])

        prefs.creds.proxy_password = self.proxy["ProxyPassword"]

        prefs.save()

        try:
            self.update_network()
        except ValueError:
            pass

        self.app.prefs_window = None
        Gtk.Window.destroy(self)

    def update_network(self):
        self.app.core_client.networkSettingsChanged(
            api.get_network_settings(
                self.prefs, upload=int(self.throttle["Upload"]),
                download=int(self.throttle["Download"])))

    def toggle_display_notifications(self, w):
        if str(self.display_notif) == "True":
            self.display_notif = "False"
        else:
            self.display_notif = "True"

    def toggle_icons(self, w, type=""):
        self.icon_type = type
        self.app.icon_type = self.icon_type
        self.app.update_menu()

    def toggle_start_at_login(self, w):
        folder_path = os.path.join(os.path.expanduser('~'),
                                   '.config/autostart')
        file_path = os.path.join(folder_path, '{brand}.desktop'.format(brand=BRAND))

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
        else:
            self.selective_sync.present()

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
            self.app.stop_threads()
            meocloud_gui.utils.purge_meta()

            prog = ProgressDialog()
            prog.show_all()

            def end(prog, timeout, new_path, error=False):
                if error:
                    GLib.source_remove(timeout)
                    GLib.idle_add(prog.destroy)

                    error_dialog = Gtk.Dialog(BRAND_PROGRAM_NAME, self, 0,
                                              (Gtk.STOCK_OK,
                                               Gtk.ResponseType.OK))

                    error_dialog.set_default_size(150, 100)

                    label = Gtk.Label(_("An error occurred while moving your "
                                        "{brand_app} folder.").format(brand_app=BRAND_PROGRAM_NAME))

                    box = error_dialog.get_content_area()
                    box.add(label)
                    error_dialog.show_all()
                    error_dialog.run()
                    error_dialog.destroy()
                else:
                    meocloud_gui.utils.clean_bookmark(self.prefs)
                    self.app.restart_core()
                    w.set_label(new_path)
                    self.prefs.put("Advanced", "Folder", new_path)
                    self.prefs.save()
                    meocloud_gui.utils.create_bookmark(self.prefs)
                    GLib.source_remove(timeout)
                    prog.destroy()

            def pulse():
                prog.progress.pulse()
                return True
            timeout = GLib.timeout_add(200, pulse)

            old_path = self.prefs.get("Advanced", "Folder",
                                      CLOUD_HOME_DEFAULT_PATH)
            meocloud_gui.utils.move_folder_async(old_path, new_path,
                                                 lambda p, e:
                                                 end(prog, timeout, p, e))
        else:
            dialog.destroy()

    def toggle_throttle(self, w, throttle):
        if w.get_sensitive():
            self.throttle[throttle] = "0"
            w.set_sensitive(False)
        else:
            try:
                val = int(w.get_text())
            except ValueError:
                val = 128

            self.throttle[throttle] = str(val)
            w.set_sensitive(True)

        self.update_network()

    def throttle_value_changed(self, w, throttle):
        try:
            val = int(w.get_text())
        except ValueError:
            val = 128

        self.throttle[throttle] = str(val)
        self.update_network()

    def proxy_manual_value_changed(self, w, pref_name):
        self.proxy[pref_name] = w.get_text()

    def set_proxy(self, w, proxy):
        if w.get_active():
            self.proxy["Proxy"] = proxy

            if proxy == "None":
                self.proxy_manual_address.hide()
                self.proxy_manual_port.hide()
                self.proxy_manual_user.hide()
                self.proxy_manual_password.hide()
                self.proxy["ProxyAddress"] = ""
                self.proxy["ProxyPort"] = ""
                self.proxy["ProxyUser"] = ""
                self.proxy["ProxyPassword"] = ""
            elif proxy == "Automatic":
                self.proxy_manual_address.hide()
                self.proxy_manual_port.hide()
                self.proxy_manual_user.hide()
                self.proxy_manual_password.hide()
                self.proxy["ProxyAddress"] = ""
                self.proxy["ProxyPort"] = ""
                self.proxy["ProxyUser"] = ""
                self.proxy["ProxyPassword"] = ""
            else:
                self.proxy_manual_address.show()
                self.proxy_manual_port.show()
                self.proxy_manual_user.show()
                self.proxy_manual_password.show()
