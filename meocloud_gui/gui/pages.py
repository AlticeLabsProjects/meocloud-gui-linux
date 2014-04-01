from gi.repository import Gtk


class Pages (Gtk.Notebook):
    __gtype_name__ = 'Pages'

    def __init__(self):
        Gtk.Notebook.__init__(self)
        self.set_show_tabs(False)
        self.set_scrollable(False)
        self.set_margin_left(10)
        self.set_margin_right(10)

    def first_page(self):
        if self.get_n_pages() > 0:
            self.set_current_page(0)

    def last_page(self):
        if self.get_n_pages() > 0:
            self.set_current_page(self.get_n_pages() - 1)
