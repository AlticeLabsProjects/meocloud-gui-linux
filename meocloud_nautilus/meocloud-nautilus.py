from gi.repository import Nautilus, GObject
import dbus

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

class MEOCloudNautilus(Nautilus.InfoProvider, Nautilus.MenuProvider,
                       GObject.GObject):
    def __init__(self):
        bus = dbus.SessionBus()
        self.service = None
        self.get_dbus()

    def get_dbus(self):
        if self.service is None:
            bus = dbus.SessionBus()

            try:
                self.service = bus.get_object('pt.meocloud.dbus',
                                              '/pt/meocloud/dbus')

                self.status = self.service.get_dbus_method('status',
                                                      'pt.meocloud.dbus')
                self.file_in_cloud = self.service.get_dbus_method('file_in_cloud',
                                                             'pt.meocloud.dbus')
            except:
                pass

    def get_local_path(self, path):
        return path.replace("file://", "")

    def valid_uri(self, uri):
        if not uri.startswith("file://"): return False
        return True

    def update_file_info(self, item):
        self.get_dbus()
        uri = item.get_uri()

        if self.valid_uri(uri):
            uri = self.get_local_path(uri)
            
            if uri == "/home/ivo/MEOCloud":
                try:
                    status = self.status()
                    
                    if (status == CORE_INITIALIZING or
                        status == CORE_AUTHORIZING or
                        status == CORE_WAITING):
                        item.add_emblem("emblem-synchronizing-symbolic")
                    elif status == CORE_SYNCING:
                        item.add_emblem("emblem-synchronizing-symbolic")
                    elif status == CORE_READY:
                        item.add_emblem("emblem-ok-symbolic")
                except:
                    self.service = None
                    pass

        return Nautilus.OperationResult.COMPLETE

    def get_file_items(self, window, files):
        self.get_dbus()
        for item in files:
            uri = item.get_uri()

            if self.valid_uri(uri):
                uri = self.get_local_path(uri)
                
                try:
                    if not self.file_in_cloud(uri):
                        return None,
                except:
                    self.service = None
                    return None,
            else:
                return None,

        top_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::MEOCloud', 'MEO Cloud', '', '')

        submenu = Nautilus.Menu()
        top_menuitem.set_submenu(submenu)

        sub_menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::Share', 'Share', '', '')
        submenu.append_item(sub_menuitem)

        return top_menuitem,

    def get_background_items(self, window, item):
        self.get_dbus()
        uri = item.get_uri()

        if self.valid_uri(uri):
            uri = self.get_local_path(uri)
            
            try:
                if not self.file_in_cloud(uri):
                    return None,
            except:
                self.service = None
                return None,
        else:
            return None,

        submenu = Nautilus.Menu()
        submenu.append_item(Nautilus.MenuItem.new('MEOCloudMenuProvider::Share', 'Share', '', ''))

        menuitem = Nautilus.MenuItem.new('MEOCloudMenuProvider::MEOCloud', 'MEO Cloud', '', '')
        menuitem.set_submenu(submenu)

        return menuitem,
