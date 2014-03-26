[DBus (name = "pt.meocloud.dbus")]
interface Core : Object {
    public abstract int status () throws GLib.Error;
    public abstract bool file_in_cloud (string path) throws GLib.Error;
    public abstract string get_cloud_home () throws GLib.Error;
    public abstract void share_link (string path) throws GLib.Error;
    public abstract void share_folder (string path) throws GLib.Error;
    public abstract void open_in_browser (string path) throws GLib.Error;
}

public class Marlin.Plugins.MEOCloud : Marlin.Plugins.Base {
    private Gtk.UIManager ui_manager;
    private Gtk.Menu menu;
    private GOF.File current_directory = null;
    private Core? core = null;

    public MEOCloud () {
        this.get_dbus();
        stdout.printf("MEO Cloud\n");
    }

    public void get_dbus() {
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

    public override void context_menu (Gtk.Widget? widget, List<GOF.File> gof_files) {
        menu = widget as Gtk.Menu;
        return_if_fail (menu != null);

        if (gof_files.length() != 1)
            return;

        GOF.File file = gof_files.nth_data(0);
        string path = GLib.Uri.unescape_string (file.uri.replace("file://", ""));

        try {
            this.get_dbus();
            var file_in_cloud = this.core.file_in_cloud(path);
            if (!file_in_cloud)
                return;
        } catch (Error e) {
            return;
        }

        Gtk.Menu submenu = new Gtk.Menu();

        Gtk.MenuItem open_in_browser = new Gtk.MenuItem.with_label ("Open in Browser");
        open_in_browser.activate.connect((w) => { this.core.open_in_browser(path); });
        submenu.add(open_in_browser);

        GLib.File f = File.new_for_path (path);

        if (f.query_file_type (0) == FileType.DIRECTORY) {
            Gtk.MenuItem share_folder = new Gtk.MenuItem.with_label ("Share Folder");
            share_folder.activate.connect((w) => { this.core.share_folder(path); });
            submenu.add(share_folder);
        } else {
            Gtk.MenuItem copy_link = new Gtk.MenuItem.with_label ("Copy Link");
            copy_link.activate.connect((w) => { this.core.share_link(path); });
            submenu.add(copy_link);
        }

        submenu.show_all();

        Gtk.MenuItem menu_item = new Gtk.MenuItem.with_label ("MEO Cloud");
        menu_item.set_submenu(submenu);
        add_menuitem (menu, menu_item);
    }

    public override void ui (Gtk.UIManager? widget) {
        ui_manager = widget;
        menu = (Gtk.Menu) ui_manager.get_widget ("/selection");
        stdout.printf("\n\nMEO Cloud UI\n\n");
    }

    public override void directory_loaded (void* user_data) {
        current_directory = ((Object[]) user_data)[2] as GOF.File;
        //var window = ((Object[]) user_data)[0] as Gtk.Window;
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

    public override void update_sidebar(Gtk.Widget sidebar)
    {
        AbstractSidebar _sidebar = (AbstractSidebar) sidebar;
        _sidebar.add_extra_item("MEOCloud");
        //Gtk.TreeStore store = _sidebar.store;
        //sb.add_place("HERP DERP");
        /*
        //appends nothing to the tree so the iter is moved to the end of the sidebar
        gtk_tree_store_append (MARLIN_ABSTRACT_SIDEBAR(sidebar)->store, &iter, NULL);
        //inserts an item to the end of the sidebar
        gtk_tree_store_set (MARLIN_ABSTRACT_SIDEBAR(sidebar)->store, &iter,
                            PLACES_SIDEBAR_COLUMN_ICON, NULL,
                            PLACES_SIDEBAR_COLUMN_NAME, _("Online"),
                            PLACES_SIDEBAR_COLUMN_ROW_TYPE, PLACES_STORAGE_CATEGORY,
                            PLACES_SIDEBAR_COLUMN_EJECT, FALSE,
                            PLACES_SIDEBAR_COLUMN_NO_EJECT, TRUE,
                            PLACES_SIDEBAR_COLUMN_BOOKMARK, FALSE,
                            PLACES_SIDEBAR_COLUMN_TOOLTIP, _("Your online storage services"),
                            -1);
        */
    }
}

public Marlin.Plugins.Base module_init () {
    return new Marlin.Plugins.MEOCloud ();
}
