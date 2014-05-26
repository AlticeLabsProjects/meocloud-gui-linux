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
        if (map.has_key (path)) {
            GOF.File file = map.get (path);

            file.emblems_list.foreach ((emblem) => {
                file.emblems_list.remove (emblem);
            });

            file.update_emblem ();
        }
    }
}

enum PlaceType {
    BUILT_IN,
    MOUNTED_VOLUME,
    BOOKMARK,
    BOOKMARKS_CATEGORY,
    PERSONAL_CATEGORY,
    STORAGE_CATEGORY
}

uint8[] buffer;
Gee.HashMap<string, int> status;
Gee.HashMap<string, GOF.File> map;

static Python.Object? emb_buffer (Python.Object? self, Python.Object? args) {
	if (!Python.arg_parse_tuple (args, ":buffer")) {
        return null;
	}
	return Python.build_value ("s#", buffer, buffer.length);
}

static Python.Object? emb_set_buffer (Python.Object? self, Python.Object? args) {
	unowned string s;
	unowned int size;

    if (!Python.arg_parse_tuple (args, "s#", out s, out size)) {
        return null;
	}

    buffer = ((uint8[])s)[0:size];

	return Python.build_value ("");
}

static Python.Object? emb_update_status (Python.Object? self, Python.Object? args) {
	unowned string path;
	unowned int fstatus;

    if (!Python.arg_parse_tuple (args, "si", out path, out fstatus)) {
        return null;
	}

    debug("TESTE: " + path);
    debug("TESTE: %d", fstatus);

    status.set ("/home/ivo/MEOCloud" + path, fstatus);
    
    if (map.has_key ("/home/ivo/MEOCloud" + path)) {
    	debug("TESTE: emb_update_status has key");
    	
		GOF.File file = map.get (path);

		file.emblems_list.foreach ((emblem) => {
			file.emblems_list.remove (emblem);
		});
		
		file.add_emblem ("emblem-default");

		file.update_emblem ();
	}
    
	return Python.build_value ("");
}

const Python.MethodDef[] emb_methods = {
	{ "update_status", emb_update_status, Python.MethodFlags.VARARGS,
	  "Update file status" },
	{ "set_buffer", emb_set_buffer, Python.MethodFlags.VARARGS,
	  "Set the Vala buffer" },
	{ "buffer", emb_buffer, Python.MethodFlags.VARARGS,
	  "Return the current Vala buffer." },
	{ null, null, 0, null }
};

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

    private Socket socket;

    public MEOCloud () {
        map = new Gee.HashMap<string, GOF.File> ();
        status = new Gee.HashMap<string, int> ();

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

        socket = new Socket (SocketFamily.UNIX, SocketType.STREAM, SocketProtocol.DEFAULT);
        assert (socket != null);

        socket.connect (new UnixSocketAddress ("/home/ivo/.meocloud/gui/meocloud_shell_listener.socket"));
        debug ("connected\n");

        this.subscribe_path("/");
        var io = new GLib.IOChannel.unix_new(socket.fd);
        io.add_watch(IOCondition.IN|IOCondition.HUP, (source, condition) => {
        	if (condition == IOCondition.HUP) {
        		return false;
        	}
        	
        	uint8 tbuffer[100];
			ssize_t len;

			len = socket.receive (tbuffer);
			buffer = tbuffer[0:len];
			
			thrift_deserialize();
        	
        	debug ("TESTE: received something!");
        	return true; // continue
        });
    }

    private void thrift_serialize(string object_to_serialize) {
    	Python.initialize ();
		Python.init_module ("emb", emb_methods);
		Python.run_simple_string ("""

import emb
import sys
sys.path.insert(0, '/opt/meocloud/libs/')
sys.path.insert(0, '/opt/meocloud/gui/meocloud_gui/protocol/')

from shell.ttypes import OpenMessage, OpenType, \
	ShareMessage, ShareType, SubscribeMessage, SubscribeType

from shell.ttypes import Message, FileState, MessageType, \
	FileStatusMessage, FileStatusType, FileStatus, FileState

from thrift.protocol import TBinaryProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.transport import TTransport

def serialize(msg):
	msg.validate()
	transport = TTransport.TMemoryBuffer()
	protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
	msg.write(protocol)

	data = transport.getvalue()
	transport.close()
	return data


def serialize_thrift_msg(msg):
	'''
	Try to serialize a 'Message' (msg) into a byte stream
	'Message' is defined in the thrift ShellHelper specification
	'''
	try:
		data = serialize(msg)
	except TProtocolException as tpe:
		raise

	return data

serialized_msg = serialize_thrift_msg(
	""" + object_to_serialize + """)

emb.set_buffer(serialized_msg)

""");
		Python.finalize ();
    }
    
    private void subscribe_path(string path) {
    	this.thrift_serialize("""
Message(type=MessageType.SUBSCRIBE_PATH, subscribe=SubscribeMessage(type=SubscribeType.SUBSCRIBE, path=" """ + path + """ "))
""");
        socket.send(buffer);
    }
    
    private void request_file_status(string path) {
		this.thrift_serialize("""
Message(type=MessageType.FILE_STATUS, fileStatus=FileStatusMessage(type=FileStatusType.REQUEST, status=FileStatus(path=" """ + path + """ ")))
""");
		socket.send(buffer);
	}

    private void thrift_deserialize() {
    	Python.initialize ();
		Python.init_module ("emb", emb_methods);
		Python.run_simple_string ("""

import emb
import sys
sys.path.insert(0, '/opt/meocloud/libs/')
sys.path.insert(0, '/opt/meocloud/gui/meocloud_gui/protocol/')

from shell.ttypes import OpenMessage, OpenType, \
	ShareMessage, ShareType, SubscribeMessage, SubscribeType

from shell.ttypes import Message, FileState, MessageType, \
	FileStatusMessage, FileStatusType, FileStatus, FileState

from thrift.protocol import TBinaryProtocol
from thrift.protocol.TProtocol import TProtocolException
from thrift.transport import TTransport

def deserialize(msg, data):
    transport = TTransport.TMemoryBuffer(data)
    protocol = TBinaryProtocol.TBinaryProtocolAccelerated(transport)
    msg.read(protocol)
    msg.validate()
    remaining = data[transport.cstringio_buf.tell():]
    transport.close()

    return msg, remaining


def deserialize_thrift_msg(data, socket_state=None, msgobj=Message()):
    '''
    Try to deserialize data (or buf + data) into a valid
    "Message" (msgobj), as defined in the thrift ShellHelper specification
    '''
    if socket_state:
        data = ''.join((socket_state, data))
        socket_state = None
    try:
        msg, remaining = deserialize(msgobj, data)
    except (TProtocolException, EOFError, TypeError) as dex:
        if len(data) <= 8192:
            socket_state = data
            msg = None
            remaining = None
        else:
            raise OverflowError('Message does not fit buffer.')

    return msg


des = deserialize_thrift_msg(emb.buffer())

if des is not None and des.fileStatus is not None:
	emb.update_status(des.fileStatus.status.path, des.fileStatus.status.state)

""");
		Python.finalize ();
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
            	if (status.has_key(path)) {
            		map.set (path, file);
            		file.add_emblem ("emblem-synchronizing");
//file.add_emblem ("emblem-important");
//					file.add_emblem ("emblem-default");
            	} else {
            		map.set (path, file);
            		status.set (path, 0);
            		this.request_file_status(path.replace(cloud_home, ""));
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
