import os
from gi.repository import GObject, Gtk
from gi.repository import GdkPixbuf
from meocloud_gui.constants import VERSION


class AboutDialog (GObject.Object):
    __gtype_name__ = 'AboutDialog'

    def __init__(self, app_path):
        aboutdialog = Gtk.AboutDialog()

        authors = ["SAPO"]
        logo_pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(
            os.path.join(app_path, 'icons/meocloud.svg'), 128, 128)

        aboutdialog.set_logo(logo_pixbuf)
        aboutdialog.set_authors(authors)
        aboutdialog.set_program_name("MEO Cloud")
        aboutdialog.set_version(VERSION)
        aboutdialog.set_authors(authors)
        aboutdialog.set_website("http://www.meocloud.pt")
        aboutdialog.set_website_label("Website")

        aboutdialog.set_title("")

        aboutdialog.show_all()
        aboutdialog.run()
        aboutdialog.destroy()
