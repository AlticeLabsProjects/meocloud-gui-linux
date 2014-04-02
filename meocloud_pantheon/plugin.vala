[DBus (name = "pt.meocloud.dbus")]
interface Core : Object {
    public abstract int status () throws GLib.Error;
    public abstract bool file_in_cloud (string path) throws GLib.Error;
    public abstract bool file_syncing (string path) throws GLib.Error;
    public abstract string get_cloud_home () throws GLib.Error;
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

public class Marlin.Plugins.MEOCloud : Marlin.Plugins.Base {
    private Gtk.UIManager ui_manager;
    private Gtk.Menu menu;
    private GOF.File current_directory = null;
    private Core? core = null;

    private string OPEN_BROWSER;
    private string SHARE_FOLDER;
    private string COPY_LINK;

    public Gee.HashMap<string, GOF.File> map;

    public MEOCloud () {
        this.map = new Gee.HashMap<string, GOF.File> ();

        OPEN_BROWSER = "Open in Browser";
        SHARE_FOLDER = "Share Folder";
        COPY_LINK = "Copy Link";

        string[] langs = GLib.Intl.get_language_names ();

        if ("pt" in langs[0]) {
            OPEN_BROWSER = "Abrir no navegador web";
            SHARE_FOLDER = "Partilhar pasta";
            COPY_LINK = "Copiar hiperligação";
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
            this.core.open_in_browser (path);
        });
        submenu.add (open_in_browser);

        GLib.File f = File.new_for_path (path);

        if (f.query_file_type (0) == FileType.DIRECTORY) {
            var share_folder = new Gtk.MenuItem.with_label (SHARE_FOLDER);
            share_folder.activate.connect ((w) => {
                this.core.share_folder (path);
            });
            submenu.add (share_folder);
        } else {
            var copy_link = new Gtk.MenuItem.with_label (COPY_LINK);
            copy_link.activate.connect ((w) => {
                this.core.share_link (path);
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
                    default:
                        file.add_emblem ("emblem-default");
                        break;
                }
            } else {
                try {
                    if (this.core.file_in_cloud (path)) {
                        if (this.core.file_syncing (path))
                            file.add_emblem ("emblem-synchronizing");
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

    private static File[] get_file_array (List<GOF.File> files) {
        File[] file_array = new File[0];

        foreach (var file in files) {
            if (file.location != null)
                file_array += file.location;
        }

        return file_array;
    }

    public override void update_sidebar (Gtk.Widget sidebar)
    {
    }
}

public Marlin.Plugins.Base module_init () {
    return new Marlin.Plugins.MEOCloud ();
}
