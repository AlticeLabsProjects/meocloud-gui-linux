from gi.repository import Gtk


class ProgressDialog(Gtk.Dialog):
    __gtype_name__ = 'ProgressDialog'

    def __init__(self):
        Gtk.Dialog.__init__(self, title="Moving")

        self.set_resizable(False)

        vbox = Gtk.VBox(False, 8)
        vbox.set_border_width(8)
        self.get_children()[0].add(vbox)

        self.progress = Gtk.ProgressBar()
        vbox.add(self.progress)

        vbox.show_all()
