from gi.repository import Gtk
from meocloud_gui.constants import LOGGER_NAME

# Logging
import logging
log = logging.getLogger(LOGGER_NAME)


class Pages (Gtk.Notebook):
    __gtype_name__ = 'Pages'

    def __init__(self):
        Gtk.Notebook.__init__(self)
        self.set_show_tabs(False)
        self.set_scrollable(False)
        self.set_margin_left(10)
        self.set_margin_right(10)

        try:
            self.stack = Gtk.Stack()
            self.stack.set_transition_type(
                Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
            self.max_stack = 0
            self.current_stack = 0
        except AttributeError:
            log.warning('Pages: Gtk older than 3.8, falling back')
            self.stack = None

        if self.stack is not None:
            Gtk.Notebook.append_page(self, self.stack, Gtk.Label("Stack"))

    def append_page(self, widget, label):
        if self.stack is None:
            Gtk.Notebook.append_page(self, widget, label)
        else:
            self.stack.add_named(widget, str(self.max_stack))
            self.max_stack += 1

    def set_current_page(self, number):
        if self.stack is None:
            Gtk.Notebook.set_current_page(self, number)
        else:
            self.stack.set_visible_child_name(str(number))
            self.current_stack = number

    def next_page(self):
        if self.stack is None:
            Gtk.Notebook.next_page(self)
        else:
            self.current_stack += 1
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
