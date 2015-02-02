import os
import socket
from gi.repository import Gtk
from meocloud_gui.gui.pages import Pages
from meocloud_gui.gui.prefswindow import PrefsWindow
from meocloud_gui.gui.spinnerbox import SpinnerBox
from meocloud_gui.constants import LOGGER_NAME, CLOUD_HOME_DEFAULT_PATH, BRAND_PROGRAM_NAME

# Logging
import logging

log = logging.getLogger(LOGGER_NAME)


class SetupWindow(Gtk.Window):
    __gtype_name__ = 'SetupWindow'

    def __init__(self, app):
        Gtk.Window.__init__(self)
        self.set_title(_("Setup"))
        self.set_position(Gtk.WindowPosition.CENTER)

        log.info('SetupWindow: initializing setup')

        self.app = app
        self.pages = Pages()

        try:
            if not app.use_headerbar:
                assert False

            self.headerbar = Gtk.HeaderBar()
            self.headerbar.set_title(_("Welcome to {brand_app}").format(brand_app=BRAND_PROGRAM_NAME))
            self.headerbar.set_show_close_button(True)
            self.set_titlebar(self.headerbar)
            self.add(self.pages)
        except (AttributeError, AssertionError):
            self.headerbar = None
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            welcome_label = Gtk.Label(
                "<b>" + _("Welcome to {brand_app}").format(brand_app=BRAND_PROGRAM_NAME) + "</b>")
            welcome_label.set_use_markup(True)
            box.pack_start(welcome_label, False, False, 10)
            box.pack_start(self.pages, True, True, 0)
            self.add(box)

        # First page

        first_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        first_page_box.pack_start(Gtk.Label(), True, True, 0)

        self.setup_easy = Gtk.RadioButton.new_with_label(None, "Easy")
        self.setup_advanced = Gtk.RadioButton.new_with_label_from_widget(
            self.setup_easy, _("Advanced"))

        first_page_mode_vertical = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL)
        first_page_mode_vertical.pack_start(self.setup_easy, False, True, 10)
        first_page_mode_vertical.pack_start(self.setup_advanced,
                                            False, True, 10)
        first_page_mode_horizontal = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        first_page_mode_horizontal.pack_start(Gtk.Label(), True, True, 0)
        first_page_mode_horizontal.pack_start(first_page_mode_vertical,
                                              False, False, 0)
        first_page_mode_horizontal.pack_start(Gtk.Label(), True, True, 0)
        first_page_box.pack_start(first_page_mode_horizontal, False, False, 0)

        first_page_next_button = Gtk.Button(_("Next"))
        first_page_next_button.connect("clicked", self.on_second_page)
        first_page_box_horizontal = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        first_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        first_page_box_horizontal.pack_start(first_page_next_button, False,
                                             False, 0)
        first_page_box.pack_start(Gtk.Label(), True, True, 0)
        first_page_box.pack_end(first_page_box_horizontal, False, False, 10)

        self.pages.append_page(first_page_box, Gtk.Label())

        # Second page (device info)

        second_page_box_outv = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL)
        second_page_box_outh = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        second_page_box_outv.pack_start(second_page_box_outh, True, True, 0)
        second_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        second_page_box_outh.pack_start(Gtk.Label(), True, True, 0)
        second_page_box_outh.pack_start(second_page_box, False, False, 0)
        second_page_box_outh.pack_start(Gtk.Label(), True, True, 0)
        second_page_box.pack_start(Gtk.Label(), True, True, 0)
        self.pages.append_page(second_page_box_outv, Gtk.Label())
        device_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.device_entry = Gtk.Entry()
        self.device_entry.set_text(socket.gethostname())
        device_box.pack_start(Gtk.Label(_("Device name: ")), False, False, 0)
        device_box.pack_start(self.device_entry, True, True, 0)
        second_page_box.pack_start(device_box, False, False, 10)

        self.cloud_home_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.cloud_home_box.pack_start(
            Gtk.Label(_("Folder: ")), False, False, 0)
        self.cloud_home_select = Gtk.Button(CLOUD_HOME_DEFAULT_PATH)
        self.cloud_home_select.connect("clicked", self.on_cloud_home_select)
        self.cloud_home_box.pack_start(self.cloud_home_select, True, True, 0)
        second_page_box.pack_start(self.cloud_home_box, False, False, 10)

        second_page_back_button = Gtk.Button(_("Back"))
        second_page_back_button.connect("clicked", self.on_first_page)
        self.login_button = Gtk.Button(_("Authorize"))
        second_page_box_horizontal = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        second_page_box_horizontal.pack_start(second_page_back_button, False,
                                              False, 0)
        second_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        second_page_box_horizontal.pack_start(self.login_button, False,
                                              False, 0)
        second_page_box.pack_start(Gtk.Label(), True, True, 0)
        second_page_box_outv.pack_end(
            second_page_box_horizontal, False, False, 10)

        # Spinner page

        self.spinner = SpinnerBox()
        self.pages.append_page(self.spinner, Gtk.Label())

        # Advanced setup page

        advanced_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        app.prefs_window = PrefsWindow(app, True)
        self.prefs_window = app.prefs_window
        app.prefs_window.remove(app.prefs_window.box)
        advanced_page_box.pack_start(app.prefs_window.box, False,
                                     False, 0)

        advanced_page_finish_button = Gtk.Button(_("Finish"))
        advanced_page_finish_button.connect("clicked",
                                            self.finish_advanced_setup)
        advanced_page_box_horizontal = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        advanced_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        advanced_page_box_horizontal.pack_start(advanced_page_finish_button,
                                                False, False, 0)
        advanced_page_box.pack_end(advanced_page_box_horizontal, False,
                                   False, 10)

        self.pages.append_page(advanced_page_box, Gtk.Label())

        # Success page

        success_page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        success_page_box.pack_start(Gtk.Label(), True, True, 0)

        success_label = Gtk.Label(
            _("Your computer has been successfully linked."))
        success_page_box.pack_start(success_label, False, False, 10)

        success_page_finish_button = Gtk.Button(_("Finish"))
        success_page_finish_button.connect("clicked", lambda w: self.destroy())
        success_page_box_horizontal = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL)
        success_page_box_horizontal.pack_start(Gtk.Label(""), True, True, 0)
        success_page_box_horizontal.pack_start(success_page_finish_button,
                                               False, False, 0)
        success_page_box.pack_start(Gtk.Label(), True, True, 0)
        success_page_box.pack_end(success_page_box_horizontal, False,
                                  False, 10)

        self.pages.append_page(success_page_box, Gtk.Label())

        self.set_size_request(400, 300)

    def on_first_page(self, widget):
        log.info('SetupWindow.on_first_page: changing to first page')
        self.pages.first_page()

    def on_second_page(self, widget):
        log.info('SetupWindow.on_second_page: changing to second page')

        if self.setup_easy.get_active():
            self.cloud_home_box.hide()
        else:
            self.cloud_home_select.set_label(CLOUD_HOME_DEFAULT_PATH)
            self.cloud_home_box.show_all()

        self.pages.next_page()

    def start_waiting(self):
        log.info('SetupWindow.start_waiting: waiting for core')
        self.pages.next_page()
        self.spinner.start()

        if self.headerbar is not None:
            self.headerbar.set_show_close_button(False)

    def stop_waiting(self):
        log.info('SetupWindow.stop_waiting: no longer waiting')
        self.pages.next_page()
        self.spinner.stop()

    def finish_advanced_setup(self, widget):
        log.info('SetupWindow.finish_advanced_setup: completing setup')
        self.app.enable_sync = True
        self.app.update_menu()
        self.prefs_window.destroy()
        self.destroy()

    def on_cloud_home_select(self, w):
        dialog = Gtk.FileChooserDialog(
            _("Please choose a folder"), self,
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                _("Select"), Gtk.ResponseType.OK))
        dialog.set_default_size(800, 400)
        response = dialog.run()

        if response == Gtk.ResponseType.OK:
            cloud_home = os.path.join(dialog.get_filename())
            dialog.destroy()
            self.cloud_home_select.set_label(cloud_home)
        else:
            dialog.destroy()
            return

    def destroy(self):
        log.info('SetupWindow.destroy: closing setup')
        self.prefs_window.destroy()
        Gtk.Window.destroy(self)
