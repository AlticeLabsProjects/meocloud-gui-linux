from gi.repository import Gtk


class SpinnerBox(Gtk.Box):
    __gtype_name__ = 'SpinnerBox'

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)

        self.pack_start(Gtk.Label(), True, True, 0)
        self.spinner = Gtk.Spinner()
        self.pack_start(self.spinner, False, False, 0)
        self.pack_start(Gtk.Label(), True, True, 0)

    def start(self):
        self.spinner.start()

    def stop(self):
        self.spinner.stop()
