enum PlaceType {
    BUILT_IN,
    MOUNTED_VOLUME,
    BOOKMARK,
    BOOKMARKS_CATEGORY,
    PERSONAL_CATEGORY,
    STORAGE_CATEGORY
}

public class Marlin.Plugins.MEOCloud : Marlin.Plugins.Base {
    private Gtk.UIManager ui_manager;
    private Gtk.Menu menu;

    private string OPEN_BROWSER;
    private string SHARE_FOLDER;
    private string COPY_LINK;
    private string CLOUD_LABEL;
    private string CLOUD_TOOLTIP;
    private string MEOCLOUD_TOOLTIP;

    private Socket socket;
    
    private Gee.HashMap<string, int> status;
    private Gee.HashMap<string, GOF.File> map;
    
    private string buffer = "";
    private string cloud_home;
    
    bool subscribed = false;
    bool disconnected = false;

    public MEOCloud () {  	
        map = new Gee.HashMap<string, GOF.File> ();
        status = new Gee.HashMap<string, int> ();
        
        cloud_home = GLib.Environment.get_home_dir() + "/MEOCloud";

        OPEN_BROWSER = "Open in Browser";
        SHARE_FOLDER = "Share Folder";
        COPY_LINK = "Copy Link";
        CLOUD_LABEL = "Cloud";
        CLOUD_TOOLTIP = "Your cloud locations";
        MEOCLOUD_TOOLTIP = "Your MEO Cloud folder";

        string[] langs = GLib.Intl.get_language_names ();

        if ("pt" in langs[0]) {
            OPEN_BROWSER = "Abrir no browser";
            SHARE_FOLDER = "Partilhar pasta";
            COPY_LINK = "Copiar link";
            CLOUD_LABEL = "Nuvem";
            CLOUD_TOOLTIP = "Nuvem";
            MEOCLOUD_TOOLTIP = "A sua pasta MEO Cloud";
        }

        socket = new Socket (SocketFamily.UNIX, SocketType.STREAM, SocketProtocol.DEFAULT);
        assert (socket != null);

        debug ("connecting\n");
        socket.connect (new UnixSocketAddress (GLib.Environment.get_home_dir() + "/.meocloud/gui/meocloud_shell_proxy.socket"));
        debug ("connected\n");

        this.request_cloud_home();

        var io = new GLib.IOChannel.unix_new(socket.fd);
        io.add_watch(IOCondition.IN|IOCondition.HUP, (source, condition) => {
        	if ((condition & IOCondition.HUP) != 0) {
        		disconnected = true;
        		return false;
        	}
        	
        	uint8 tbuffer[8192];
			ssize_t len;
			len = socket.receive (tbuffer);
			string data = (string) tbuffer;
			
			debug("TESTE2: " + data);
			
			while (data.length > 0) {	
				int data_length = data.length;
				
				for (int i = 0; i < data.length; i++) {
					if (data.data[i] == '\n') {
						process_data(buffer + data[0:i]);
						buffer = "";
						data = data[(i+1):data.length];
						break;
					}
				}
				
				if (data_length == data.length) {
					buffer += data;
					data = "";
					break;
				}
			}

			buffer += data;

        	return true; // continue
        });
    }
    
    private void process_data(string data) {
    	string msg = data;
    	
    	if (msg.has_prefix("\n"))
    		msg = msg[1:msg.length];

    	string command = unescape(msg.split("\t")[0]);
    	string path = unescape(msg.split("\t")[1]);
		string status = msg.split("\t")[2];
		
		debug ("TESTE: " + path);
    	
    	if (command == "home") {
    		this.cloud_home = path;
    		
    		if (!subscribed) {
    			this.subscribe_path("/");
    			subscribed = true;
    		}
    		
    		return;
    	}
    	
    	if (path == "/")
    		path = "";
    	
    	this.status.set (cloud_home + path, int.parse(status));

		if (map.has_key (cloud_home + path)) {
			GOF.File file = map.get (cloud_home + path);

			file.emblems_list.foreach ((emblem) => {
				file.emblems_list.remove (emblem);
			});

			file.add_emblem ("emblem-default");

			file.update_emblem ();
		}
    }
    
    private void subscribe_path(string path) {
        send_message("subscribe", path);
    }

    
    private void request_cloud_home() {
        send_message("home", "/");
    }

    private void request_file_status(string path) {
    	send_message("status", path);
	}

    private void send_message(string cmd, string arg) {
    	if (disconnected)
    		return;
    	
    	string full = cmd + "\t" + this.escape(arg) + "\n";
		socket.send(full.data);
	}

    private string escape(string path) {
    	return path.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n");
    }

    private string unescape(string path) {
    	return path.replace("\\t", "\t").replace("\\n", "\n").replace("\\\\", "\\");
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

        Gtk.Menu submenu = new Gtk.Menu ();

        var open_in_browser = new Gtk.MenuItem.with_label (OPEN_BROWSER);
        open_in_browser.activate.connect ((w) => {
            try {
            	send_message("browser", path.replace(cloud_home, ""));
            } catch (Error e) {
            }
        });
        submenu.add (open_in_browser);

        GLib.File f = File.new_for_path (path);

        if (f.query_file_type (0) == FileType.DIRECTORY) {
            var share_folder = new Gtk.MenuItem.with_label (SHARE_FOLDER);
            share_folder.activate.connect ((w) => {
                try {
                	send_message("folder", path.replace(cloud_home, ""));
                } catch (Error e) {
                }
            });
            submenu.add (share_folder);
        } else {
            var copy_link = new Gtk.MenuItem.with_label (COPY_LINK);
            copy_link.activate.connect ((w) => {
                try {
                	send_message("link", path.replace(cloud_home, ""));
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
        	if (path.has_prefix(cloud_home)) {
				string short_path = path.replace(cloud_home, "");
	
				if (status.has_key(path)) {
					switch(status.get(path)) {
						case 0:
							file.add_emblem ("emblem-default");
							break;
						case 1:
							file.add_emblem ("emblem-synchronizing");
							break;
						case 2:
						case 3:
							file.add_emblem ("emblem-important");
							break;
					}
				} else {
					if (short_path == "")
						short_path = "/";
					
					map.set (path, file);
					this.request_file_status(short_path);
				}
        	}
        }
    }

    public override void directory_loaded (void* user_data) {
        map.clear ();
        status.clear ();
    }

    private void add_menuitem (Gtk.Menu menu, Gtk.MenuItem menu_item) {
        menu.append (menu_item);
        menu_item.show ();
        plugins.menuitem_references.add (menu_item);
    }
}

public Marlin.Plugins.Base module_init () {
    return new Marlin.Plugins.MEOCloud ();
}
