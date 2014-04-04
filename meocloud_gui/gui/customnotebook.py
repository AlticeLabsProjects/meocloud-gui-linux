from gi.repository import Gtk
from meocloud_gui.constants import LOGGER_NAME

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)

try:
    base_class = Gtk.Stack
except:
    base_class = Gtk.Notebook


class CustomNotebook (base_class):
    __gtype_name__ = 'CustomNotebook'

    def __init__(self):
        base_class.__init__(self)
        self.max_stack = 0
        self.current_stack = 0

    def append_page(self, widget, label):
        if base_class is Gtk.Notebook:
            Gtk.Notebook.append_page(self, widget, label)
        else:
            self.add_titled(widget, label.get_text(), label.get_text())
            self.max_stack = self.max_stack + 1

    def set_current_page(self, number):
        if base_class is Gtk.Notebook:
            Gtk.Notebook.set_current_page(self, number)
        else:
            self.set_visible_child_name(str(number))
            self.current_stack = number

    def next_page(self):
        if base_class is Gtk.Notebook:
            Gtk.Notebook.next_page(self)
        else:
            self.current_stack = self.current_stack + 1
            self.set_current_page(self.current_stack)

    def first_page(self):
        if self.get_n_pages() > 0:
            self.set_current_page(0)

    def last_page(self):
        if self.get_n_pages() > 0:
            if self.stack is None:
                self.set_current_page(self.get_n_pages() - 1)
            else:
                self.set_current_page(self.max_stack - 1)
