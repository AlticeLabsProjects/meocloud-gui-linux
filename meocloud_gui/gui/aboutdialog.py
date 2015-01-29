import os
from gi.repository import GObject, Gtk
from gi.repository import GdkPixbuf
from meocloud_gui.constants import VERSION, BRAND, BRAND_PROGRAM_NAME, BRAND_WEBSITE


class AboutDialog (GObject.Object):
    __gtype_name__ = 'AboutDialog'

    def __init__(self, app_path):
        aboutdialog = Gtk.AboutDialog()
        aboutdialog.set_position(Gtk.WindowPosition.CENTER)

        authors = ["SAPO"]
        logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(app_path, 'icons/{0}/meocloud.svg'.format(BRAND)), 128, 128)

        aboutdialog.set_logo(logo_pixbuf)
        aboutdialog.set_authors(authors)
        aboutdialog.set_program_name(BRAND_PROGRAM_NAME)
        aboutdialog.set_version(VERSION)
        aboutdialog.set_authors(authors)
        aboutdialog.set_website(BRAND_WEBSITE)
        aboutdialog.set_website_label("Website")

        aboutdialog.set_title("")

        aboutdialog.show_all()
        aboutdialog.run()
        aboutdialog.destroy()
