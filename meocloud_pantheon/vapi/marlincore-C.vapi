[CCode (cprefix = "", lower_case_cprefix = "", cheader_filename = "config.h")]
namespace Config {
    public const string GETTEXT_PACKAGE;
    public const string PIXMAP_DIR;
    public const string UI_DIR;
    public const string PACKAGE_VERSION;
    public const string VERSION;
    public const string GNOMELOCALEDIR;
    public const string PLUGIN_DIR;
}

[CCode (cprefix = "FM", lower_case_cprefix = "fm_", cheader_filename = "fm-list-model.h")]
namespace FM
{
    public class ListModel : GLib.Object, Gtk.TreeModel, Gtk.TreeDragDest, Gtk.TreeSortable
    {
        public bool load_subdirectory(Gtk.TreePath path, out GOF.Directory.Async dir);
        public void add_file(GOF.File file, GOF.Directory.Async dir);
        public GOF.File file_for_path(Gtk.TreePath path);
    }
}

[CCode (cprefix = "MarlinFileOperations", lower_case_cprefix = "marlin_file_operations_", cheader_filename = "marlin-file-operations.h")]
namespace Marlin.FileOperations {
    static void empty_trash(Gtk.Widget widget);
    static void copy_move (GLib.List<GLib.File> files, void* relative_item_points, GLib.File target_dir, Gdk.DragAction copy_action, Gtk.Widget? parent_view = null, void* done_callback = null, void* done_callback_data = null);
}

[CCode (cprefix = "EelGtk", lower_case_cprefix = "eel_gtk_window_", cheader_filename = "eel-gtk-extensions.h")]
namespace EelGtk.Window {
    public string get_geometry_string (Gtk.Window win);
    public void set_initial_geometry_from_string (Gtk.Window win, string geometry, uint w, uint h, bool ignore_position);
}
[CCode (cprefix = "Eel", lower_case_cprefix = "eel_", cheader_filename = "eel-gtk-extensions.h")]
namespace Eel {
    public void pop_up_context_menu (Gtk.Menu menu, int16 offset_x, int16 offset_y, Gdk.EventButton event);
}

[CCode (cprefix = "Eel", lower_case_cprefix = "eel_", cheader_filename = "eel-fcts.h")]
namespace Eel {
    public string? get_date_as_string (uint64 d, string format);
    public GLib.List? get_user_names ();
    public bool get_user_id_from_user_name (string *user_name, out int uid);
    public bool get_group_id_from_group_name (string *group_name, out int gid);
    public bool get_id_from_digit_string (string digit_str, out int id);
    public string format_size (uint64 size);
}

[CCode (cprefix = "EelPango", lower_case_cprefix = "eel_pango_", cheader_filename = "eel-pango-extensions.h")]
namespace EelPango {
    public unowned Pango.AttrList attr_list_small();
    public unowned Pango.AttrList attr_list_big();
}

[CCode (cprefix = "Marlin", lower_case_cprefix = "marlin_")]
namespace Marlin
{
    [CCode (cheader_filename = "marlin-file-utilities.h")]
    public string get_accel_map_file ();
    [CCode (cheader_filename = "marlin-icon-info.h")]
    public class IconInfo : GLib.Object {
        public static IconInfo lookup(GLib.Icon icon, int size);
        public Gdk.Pixbuf get_pixbuf_nodefault();
        public Gdk.Pixbuf get_pixbuf_at_size(int size);
        public static void clear_caches ();
    }

    [CCode (cheader_filename = "marlin-abstract-sidebar.h")]
    public abstract class AbstractSidebar : Gtk.ScrolledWindow
    {
        public void add_extra_item(string text);
    }

    [CCode (cheader_filename = "marlin-trash-monitor.h")]
    public abstract class TrashMonitor : GLib.Object
    {
        public static TrashMonitor get();
        public static bool is_empty ();

        public signal void trash_state_changed (bool new_state);
    }

    [CCode (cheader_filename = "marlin-undostack-manager.h")]
    public struct UndoMenuData {
        string undo_label;
        string undo_description;
        string redo_label;
        string redo_description;
    }

    [CCode (cheader_filename = "marlin-undostack-manager.h")]
    public delegate void UndoFinishCallback (UndoManager manager, Gtk.Widget? w);
    /*public delegate void UndoFinishCallback (void *data);*/
    /*public delegate void UndoFinishCallback ();*/

    [CCode (cheader_filename = "marlin-undostack-manager.h")]
    public abstract class UndoManager : GLib.Object
    {
        public static UndoManager instance ();

        public signal void request_menu_update (UndoMenuData data);

        public void undo (UndoFinishCallback? cb);
        public void redo (UndoFinishCallback? cb);
    }

    [CCode (cheader_filename = "marlin-progress-info.h")]
    public class Progress.Info : GLib.Object {
        public Info ();
        public signal void changed ();
        public signal void started ();
        public signal void finished ();
        public signal void progress_changed ();
        public void cancel ();
        public string get_status ();
        public string get_details ();
        public double get_progress ();
        public double get_current ();
        public double get_total ();
        public bool get_is_finished ();
        public bool get_is_paused ();
        public GLib.Cancellable get_cancellable ();
    }

    [CCode (cheader_filename = "marlin-progress-info-manager.h")]
    public class Progress.InfoManager : GLib.Object {
        public InfoManager ();
        public signal void new_progress_info (Progress.Info info);
        public void add_new_info (Progress.Info info);
        public unowned GLib.List<Progress.Info> get_all_infos ();
    }
}

[CCode (cprefix = "MarlinFile", lower_case_cprefix = "marlin_file_", cheader_filename = "marlin-file-changes-queue.h")]
namespace MarlinFile {
    public void changes_queue_file_added (GLib.File location);
    public void changes_queue_file_changed (GLib.File location);
    public void changes_queue_file_removed (GLib.File location);
    public void changes_queue_file_moved (GLib.File location);
    public void changes_consume_changes (bool consume_all);
}

[CCode (cprefix = "GOF", lower_case_cprefix = "gof_")]
namespace GOF {

    [CCode (cheader_filename = "gof-file.h")]
    public class File : GLib.Object {
        [CCode (cheader_filename = "gof-file.h")]
        public enum ThumbState {
            UNKNOWN,
            NONE,
            READY,
            LOADING
        }
        public signal void changed ();
        public signal void info_available ();
        public signal void icon_changed ();

        public const string GIO_DEFAULT_ATTRIBUTES;

        public File(GLib.File location, GLib.File dir);
        public static File get(GLib.File location);
        public static File cache_lookup (GLib.File file);

        public void remove_from_caches ();
        public bool is_gone;
        public GLib.File location;
        public GLib.File directory; /* parent directory location */
        public GLib.Icon? icon;
        public GLib.FileInfo? info;
        public string basename;
        public string uri;
        public uint64 size;
        public string format_size;
        public int color;
        public string formated_modified;
        public string formated_type;
        public string tagstype;
        public Gdk.Pixbuf pix;
        public int pix_size;
        public GLib.List<string> emblems_list;

        public GLib.FileType file_type;
        public bool is_hidden;
        public bool is_directory;
        public bool is_desktop;
        public bool is_folder();
        public bool is_symlink();
        public bool is_trashed();
        public bool link_known_target;
        public uint flags;

        public unowned string get_display_name ();
        public unowned GLib.File get_target_location ();
        public unowned string get_ftype ();
        public string? get_formated_time (string attr);
        public Gdk.Pixbuf get_icon_pixbuf (int size, bool forced_size, FileIconFlags flags);
        public Marlin.IconInfo get_icon (int size, FileIconFlags flags);

        public bool is_mounted;
        public bool exists;

        public int uid;
        public int gid;
        public string owner;
        public string group;
        public bool has_permissions;
        public uint32 permissions;

        public void update ();
        public void update_type ();
        public void update_icon (int size);
        public void update_desktop_file ();
        public void update_emblem ();
        public void add_emblem (string name);
        public void query_update ();
        public void query_thumbnail_update ();
        public unowned string? get_thumbnail_path();
        public string? get_preview_path();
        public bool can_set_owner ();
        public bool can_set_group ();
        public bool can_set_permissions ();
        public bool can_unmount ();
        public string get_permissions_as_string ();
        public bool launch (Gdk.Screen screen, GLib.AppInfo app);

        public GLib.List? get_settable_group_names ();
        public static int compare_by_display_name (File file1, File file2);

        public bool is_remote_uri_scheme ();
        public bool is_root_network_folder ();
        public bool is_network_uri_scheme ();
        public bool is_smb_uri_scheme ();

        public unowned string get_display_target_uri ();

        public GLib.AppInfo get_default_handler ();
    }

    [CCode (cheader_filename = "gof-file.h")]
    public enum FileIconFlags
    {
        NONE,
        USE_THUMBNAILS
    }

    [CCode (cheader_filename = "gof-abstract-slot.h")]
    public class AbstractSlot : GLib.Object {
        public void add_extra_widget(Gtk.Widget widget);
    }
}
