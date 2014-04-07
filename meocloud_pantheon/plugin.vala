[DBus (name = "pt.meocloud.dbus")]
interface Core : Object {
    public abstract int status () throws GLib.Error;
    public abstract bool file_in_cloud (string path) throws GLib.Error;
    public abstract bool file_syncing (string path) throws GLib.Error;
    public abstract bool file_ignored (string path) throws GLib.Error;
    public abstract string get_cloud_home () throws GLib.Error;
    public abstract string get_app_path () throws GLib.Error;
    public abstract void share_link (string path) throws GLib.Error;
    public abstract void share_folder (string path) throws GLib.Error;
    public abstract void open_in_browser (string path) throws GLib.Error;
}

[DBus (name = "pt.meocloud.shell")]
public class ShellServer : Object {
    private Marlin.Plugins.MEOCloud parent;

    public ShellServer (Marlin.Plugins.MEOCloud parent) {
        this.parent = parent;
    }

    public void UpdateFile (string path) {
        if (this.parent.map.has_key (path)) {
            GOF.File file = this.parent.map.get (path);

            file.emblems_list.foreach ((emblem) => {
                file.emblems_list.remove (emblem);
            });

            file.update_emblem ();
        }
    }
}

enum SidebarPlaces {
    COLUMN_ROW_TYPE,
    COLUMN_URI,
    COLUMN_DRIVE,
    COLUMN_VOLUME,
    COLUMN_MOUNT,
    COLUMN_NAME,
    COLUMN_ICON,
    COLUMN_INDEX,
    COLUMN_EJECT,
    COLUMN_NO_EJECT,
    COLUMN_BOOKMARK,
    COLUMN_TOOLTIP,
    COLUMN_EJECT_ICON,
    COLUMN_FREE_SPACE,
    COLUMN_DISK_SIZE,

    COLUMN_COUNT
}

public class Marlin.Plugins.MEOCloud : Marlin.Plugins.Base {
    private Gtk.UIManager ui_manager;
    private Gtk.Menu menu;
    private Core? core = null;

    private string OPEN_BROWSER;
    private string SHARE_FOLDER;
    private string COPY_LINK;
    private string CLOUD_LABEL;
    private string CLOUD_TOOLTIP;
    private string MEOCLOUD_TOOLTIP;

    public Gee.HashMap<string, GOF.File> map;

    public MEOCloud () {
        this.map = new Gee.HashMap<string, GOF.File> ();

        OPEN_BROWSER = "Open in Browser";
        SHARE_FOLDER = "Share Folder";
        COPY_LINK = "Copy Link";
        CLOUD_LABEL = "Cloud";
        CLOUD_TOOLTIP = "Your cloud locations";
        MEOCLOUD_TOOLTIP = "Your MEO Cloud folder";

        string[] langs = GLib.Intl.get_language_names ();

        if ("pt" in langs[0]) {
            OPEN_BROWSER = "Abrir no navegador web";
            SHARE_FOLDER = "Partilhar pasta";
            COPY_LINK = "Copiar hiperligação";
            CLOUD_LABEL = "Nuvem";
            CLOUD_TOOLTIP = "Nuvem";
            MEOCLOUD_TOOLTIP = "A sua pasta MEO Cloud";
        }

        Bus.own_name (BusType.SESSION, "pt.meocloud.shell",
                      BusNameOwnerFlags.ALLOW_REPLACEMENT +
                      BusNameOwnerFlags.REPLACE,
                      (conn) => {
                          try {
                              conn.register_object ("/pt/meocloud/shell",
                                                    new ShellServer (this));
                          } catch (IOError e) {
                              stderr.printf ("Could not register service\n");
                          }
                      },
                      () => {},
                      () => stderr.printf ("Could not aquire name\n"));

        this.get_dbus ();
    }

    public void get_dbus () {
        if (this.core == null) {
            try {
                this.core = Bus.get_proxy_sync (BusType.SESSION,
                                                "pt.meocloud.dbus",
                                                "/pt/meocloud/dbus");
            } catch (Error e) {
                this.core = null;
            }
        }
    }

    public override void context_menu (Gtk.Widget? widget,
                                       List<GOF.File> gof_files) {
        menu = widget as Gtk.Menu;
        return_if_fail (menu != null);

        if (gof_files.length() != 1)
            return;

        GOF.File file = gof_files.nth_data (0);
        string path = GLib.Uri.unescape_string (file.uri.replace ("file://",
                                                                  ""));

        try {
            this.get_dbus ();
            var file_in_cloud = this.core.file_in_cloud (path);
            if (!file_in_cloud)
                return;
        } catch (Error e) {
            return;
        }

        Gtk.Menu submenu = new Gtk.Menu ();

        var open_in_browser = new Gtk.MenuItem.with_label (OPEN_BROWSER);
        open_in_browser.activate.connect ((w) => {
            try {
                this.core.open_in_browser (path);
            } catch (Error e) {
            }
        });
        submenu.add (open_in_browser);

        GLib.File f = File.new_for_path (path);

        if (f.query_file_type (0) == FileType.DIRECTORY) {
            var share_folder = new Gtk.MenuItem.with_label (SHARE_FOLDER);
            share_folder.activate.connect ((w) => {
                try {
                    this.core.share_folder (path);
                } catch (Error e) {
                }
            });
            submenu.add (share_folder);
        } else {
            var copy_link = new Gtk.MenuItem.with_label (COPY_LINK);
            copy_link.activate.connect ((w) => {
                try {
                    this.core.share_link (path);
                } catch (Error e) {
                }
            });
            submenu.add (copy_link);
        }

        submenu.show_all ();

        Gtk.MenuItem menu_item = new Gtk.MenuItem.with_label ("MEO Cloud");
        menu_item.set_submenu (submenu);
        add_menuitem (menu, menu_item);
    }

    public override void ui (Gtk.UIManager? widget) {
        ui_manager = widget;
        menu = (Gtk.Menu) ui_manager.get_widget ("/selection");
    }

    public override void update_file_info (GOF.File file) {
        if (file.is_trashed() || !file.exists ||
            file.is_remote_uri_scheme () ||
            file.is_network_uri_scheme () ||
            file.is_smb_uri_scheme ())
            return;

        string path = file.get_target_location ().get_path ();

        if (file.emblems_list.length() == 0) {
            string cloud_home;

            try {
                cloud_home = this.core.get_cloud_home ();
            } catch (Error e) {
                return;
            }

            if (path == cloud_home) {
                int status;

                try {
                    status = this.core.status ();
                } catch (Error e) {
                    return;
                }

                switch (status) {
                    case 0:
                    case 1:
                    case 2:
                    case 3:
                        file.add_emblem ("emblem-synchronizing");
                        break;
                    case 6:
                    case 9:
                        file.add_emblem ("emblem-important");
                        break;
                    default:
                        file.add_emblem ("emblem-default");
                        break;
                }
            } else {
                try {
                    if (this.core.file_in_cloud (path)) {
                        if (this.core.file_syncing (path))
                            file.add_emblem ("emblem-synchronizing");
                        else if (this.core.file_ignored (path))
                            file.add_emblem ("emblem-important");
                        else
                            file.add_emblem ("emblem-default");
                    }
                } catch (Error e) {
                    return;
                }
            }
        }

        this.map.set (path, file);
    }

    public override void directory_loaded (void* user_data) {
        this.map.clear ();
    }

    private void add_menuitem (Gtk.Menu menu, Gtk.MenuItem menu_item) {
        menu.append (menu_item);
        menu_item.show ();
        plugins.menuitem_references.add (menu_item);
    }

    public override void update_sidebar (Gtk.Widget sidebar) {
        string cloud_home, app_path;

        try {
            cloud_home = this.core.get_cloud_home();
            app_path = this.core.get_app_path();
        } catch (Error e) {
            return;
        }

        AbstractSidebar _sidebar = (AbstractSidebar) sidebar;
        Gtk.TreeStore store = _sidebar.store;

        Gdk.Pixbuf icon = new Gdk.Pixbuf.from_file_at_size (app_path + "/icons/meocloud.svg", 18, 18);

        Gtk.TreeIter cloud_category;
        store.append (out cloud_category, null);
        store.set (cloud_category, SidebarPlaces.COLUMN_ICON, null,
                   SidebarPlaces.COLUMN_NAME, CLOUD_LABEL,
                   SidebarPlaces.COLUMN_URI, null,
                   SidebarPlaces.COLUMN_DRIVE, null,
                   SidebarPlaces.COLUMN_VOLUME, null,
                   SidebarPlaces.COLUMN_MOUNT, null,
                   SidebarPlaces.COLUMN_ROW_TYPE, 3,
                   SidebarPlaces.COLUMN_INDEX, 0,
                   SidebarPlaces.COLUMN_EJECT, false,
                   SidebarPlaces.COLUMN_NO_EJECT, true,
                   SidebarPlaces.COLUMN_BOOKMARK, false,
                   SidebarPlaces.COLUMN_TOOLTIP, CLOUD_TOOLTIP,
                   SidebarPlaces.COLUMN_EJECT_ICON, null,
                   SidebarPlaces.COLUMN_FREE_SPACE, 0,
                   SidebarPlaces.COLUMN_DISK_SIZE, 0,
                    -1, -1);

        Gtk.TreeIter meocloud_iter;
        store.append (out meocloud_iter, cloud_category);
        store.set (meocloud_iter, SidebarPlaces.COLUMN_ICON, icon,
                   SidebarPlaces.COLUMN_NAME, "MEO Cloud",
                   SidebarPlaces.COLUMN_URI, "file://" + cloud_home.replace(" ", "%20"),
                   SidebarPlaces.COLUMN_DRIVE, null,
                   SidebarPlaces.COLUMN_VOLUME, null,
                   SidebarPlaces.COLUMN_MOUNT, null,
                   SidebarPlaces.COLUMN_ROW_TYPE, 2,
                   SidebarPlaces.COLUMN_INDEX, 0,
                   SidebarPlaces.COLUMN_EJECT, false,
                   SidebarPlaces.COLUMN_NO_EJECT, true,
                   SidebarPlaces.COLUMN_BOOKMARK, 0,
                   SidebarPlaces.COLUMN_TOOLTIP, MEOCLOUD_TOOLTIP,
                   SidebarPlaces.COLUMN_EJECT_ICON, null,
                   SidebarPlaces.COLUMN_FREE_SPACE, 0,
                   SidebarPlaces.COLUMN_DISK_SIZE, 0,
                    -1, -1);
    }
}

public Marlin.Plugins.Base module_init () {
    return new Marlin.Plugins.MEOCloud ();
}