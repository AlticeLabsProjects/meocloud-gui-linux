from gi.repository import Nautilus, GObject
import dbus
import dbus.service
import urllib
import os
import gettext
import locale
from dbus.mainloop.glib import DBusGMainLoop


(
    CORE_INITIALIZING,
    CORE_AUTHORIZING,
    CORE_WAITING,
    CORE_SYNCING,
    CORE_READY,
    CORE_PAUSED,
    CORE_ERROR,
    CORE_SELECTIVE_SYNC,
    CORE_RESTARTING,
    CORE_OFFLINE
) = xrange(0, 10)


def init_localization():
    '''prepare l10n'''
    locale.setlocale(locale.LC_ALL, '')
    loc = locale.getlocale()
    filename = "meocloud_mo/%s.mo" % locale.getlocale()[0][0:2]
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), filename)

    try:
        trans = gettext.GNUTranslations(open(path, "rb"))
    except IOError:
        trans = gettext.NullTranslations()

    trans.install()


class DBusService(dbus.service.Object):
    def __init__(self, files):
        bus_name = dbus.service.BusName('pt.meocloud.shell',
                                        bus=dbus.SessionBus())
        dbus.service.Object.__init__(self, bus_name, '/pt/meocloud/shell')
        self.files = files

    @dbus.service.method('pt.meocloud.shell')
    def UpdateFile(self, path):
        if path in self.files:
            item = self.files[path]
            self.files.pop(path, None)
            item.invalidate_extension_info()
            del item


class MEOCloudNautilus(Nautilus.InfoProvider, Nautilus.MenuProvider,
                       GObject.GObject):
    def __init__(self):
        init_localization()
        self.service = None
        self.files = dict()

        DBusGMainLoop(set_as_default=True)
        self.dbus_service = DBusService(self.files)

        self.get_dbus()

    def get_dbus(self):
        if self.service is None:
            bus = dbus.SessionBus()

            try:
                self.service = bus.get_object('pt.meocloud.dbus',
                                              '/pt/meocloud/dbus')

                self.status = self.service.get_dbus_method(
                    'Status', 'pt.meocloud.dbus')
                self.file_in_cloud = self.service.get_dbus_method(
                    'FileInCloud', 'pt.meocloud.dbus')
                self.get_cloud_home = self.service.get_dbus_method(
                    'GetCloudHome', 'pt.meocloud.dbus')
                self.share_link = self.service.get_dbus_method(
                    'ShareLink', 'pt.meocloud.dbus')
                self.share_folder = self.service.get_dbus_method(
                    'ShareFolder', 'pt.meocloud.dbus')
                self.open_in_browser = self.service.get_dbus_method(
                    'OpenInBrowser', 'pt.meocloud.dbus')
            except:
                pass

    def get_local_path(self, path):
        return urllib.unquote(path)[7:]

    def valid_uri(self, uri):
        if not uri.startswith("file://"):
            return False
        else:
            return True

    def changed_cb(self, i):
        del i

    def update_file_info(self, item):
        self.get_dbus()
        uri = item.get_uri()

        if self.valid_uri(uri):
            uri = self.get_local_path(uri)
            if uri in self.files:
                self.files.pop(uri, None)
            self.files[uri] = item
            item.connect("changed", self.changed_cb)

            try:
                if uri == self.get_cloud_home():
                    status = self.status()

                    if (status == CORE_INITIALIZING or
                            status == CORE_AUTHORIZING or
                            status == CORE_WAITING):
                        item.add_emblem("emblem-synchronizing")
                    elif status == CORE_SYNCING:
                        item.add_emblem("emblem-synchronizing")
                    elif status == CORE_READY:
                        item.add_emblem("emblem-default")
                else:
                    in_cloud, syncing = self.file_in_cloud(uri)
                    if in_cloud and syncing:
                        item.add_emblem("emblem-synchronizing")
                    elif in_cloud:
                        item.add_emblem("emblem-default")
            except:
                self.service = None
                pass

        return Nautilus.OperationResult.COMPLETE

    def get_file_items(self, window, files):
        if len(files) != 1:
            return None,

        self.get_dbus()
        item = files[0]
        uri = item.get_uri()

        if self.valid_uri(uri):
            uri = self.get_local_path(uri)

            try:
                in_cloud, syncing = self.file_in_cloud(uri)
                if not in_cloud:
                    return None,
            except:
                self.service = None
                return None,
        else:
            return None,

        top_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::MEOCloud',
                                             'MEO Cloud', '', '')

        submenu = Nautilus.Menu()
        top_menuitem.set_submenu(submenu)

        if os.path.isfile(uri):
            link_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::Copy',
                                                  _('Copy Link'), '', '')
            link_menuitem.connect("activate", lambda w: self.share_link(uri))
            submenu.append_item(link_menuitem)
        else:
            share_menuitem = Nautilus.MenuItem.new(
                'MEOCloudMenuProvider::Share', _('Share Folder'), '', '')
            share_menuitem.connect("activate", lambda w:
                                   self.share_folder(uri))
            submenu.append_item(share_menuitem)

        browser_menuitem = Nautilus.MenuItem.new(
            'MEOCloudMenuProvider::Browser', _('Open in Browser'), '', '')
        browser_menuitem.connect("activate", lambda w:
                                 self.open_in_browser(uri))
        submenu.append_item(browser_menuitem)

        return top_menuitem,

    def get_background_items(self, window, item):
        return None,
