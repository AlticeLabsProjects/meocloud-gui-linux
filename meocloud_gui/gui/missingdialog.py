import os.path
import os
from gi.repository import Gtk
from meocloud_gui.preferences import Preferences
import meocloud_gui.utils


class MissingDialog(Gtk.Dialog):
    __gtype_name__ = 'MissingDialog'

    def __init__(self, app):
        Gtk.Dialog.__init__(self, title=_("MEO Cloud Folder Missing"))

        self.set_resizable(False)

        vbox = Gtk.VBox(False, 8)
        vbox.set_border_width(8)
        self.get_children()[0].add(vbox)

        self.label = Gtk.Label(
            _("We were unable to find your MEO Cloud folder."))
        vbox.add(self.label)

        self.find_folder = Gtk.Button(_("Find Folder"))
        self.find_folder.connect("clicked", self.on_find_folder)
        vbox.add(self.find_folder)

        self.recreate_folder = Gtk.Button(_("Recreate Folder"))
        self.recreate_folder.connect("clicked", lambda w: self.destroy())
        vbox.add(self.recreate_folder)

        self.quit_app = Gtk.Button(_("Quit"))
        self.quit_app.connect("clicked", lambda w: self.on_quit(app))
        vbox.add(self.quit_app)

        vbox.show_all()

    def on_quit(self, app):
        app.missing_quit = True
        self.destroy()

    def on_find_folder(self, w):
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

            if not os.path.exists(os.path.join(new_path, '.cloudcontrol')):
                error_dialog = Gtk.Dialog("MEO Cloud", self, 0,
                                          (Gtk.STOCK_OK,
                                           Gtk.ResponseType.OK))

                error_dialog.set_default_size(150, 100)

                label = Gtk.Label(_("The selected folder is not correct."))

                box = error_dialog.get_content_area()
                box.add(label)
                error_dialog.show_all()
                error_dialog.run()
                error_dialog.destroy()
                return

            meocloud_gui.utils.purge_meta()
            preferences = Preferences()
            preferences.put("Advanced", "Folder", new_path)
            preferences.save()

            self.destroy()
        else:
            dialog.destroy()
