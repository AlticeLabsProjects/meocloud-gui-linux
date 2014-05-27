enum PlaceType {
    BUILT_IN,
    MOUNTED_VOLUME,
    BOOKMARK,
    BOOKMARKS_CATEGORY,
    PERSONAL_CATEGORY,
    STORAGE_CATEGORY
}

uint8[] socket_state;
uint8[] buffer;
string file_path;
int file_status;

static Python.Object? emb_state (Python.Object? self, Python.Object? args) {
	if (!Python.arg_parse_tuple (args, ":socket_state")) {
        return null;
	}
	return Python.build_value ("s#", socket_state, buffer.length);
}

static Python.Object? emb_set_state(Python.Object? self, Python.Object? args) {
	unowned string s;
	unowned int size;

    if (!Python.arg_parse_tuple (args, "s#", out s, out size)) {
        return null;
	}

    socket_state = ((uint8[])s)[0:size];

	return Python.build_value ("");
}

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
    
    file_path = path.strip();
    file_status = fstatus;
    
	return Python.build_value ("");
}

const Python.MethodDef[] emb_methods = {
	{ "update_status", emb_update_status, Python.MethodFlags.VARARGS,
	  "Update file status" },
	{ "set_buffer", emb_set_buffer, Python.MethodFlags.VARARGS,
	  "Set the Vala buffer" },
	{ "buffer", emb_buffer, Python.MethodFlags.VARARGS,
	  "Return the current Vala buffer." },
	{ "set_state", emb_set_state, Python.MethodFlags.VARARGS,
	  "Set the Vala socket_state" },
	{ "state", emb_state, Python.MethodFlags.VARARGS,
	  "Return the current Vala socket_state." },
	{ null, null, 0, null }
};

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

    public MEOCloud () {
    	Python.initialize ();
		Python.init_module ("emb", emb_methods);
    	
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
			
			debug("TESTE2: " + file_path + " - " + file_status.to_string());
			
			status.set ("/home/ivo/MEOCloud" + file_path, file_status);
			    
			if (map.has_key ("/home/ivo/MEOCloud" + file_path)) {
				debug("TESTE: emb_update_status has key");
				
				GOF.File file = map.get ("/home/ivo/MEOCloud" + file_path);

				file.emblems_list.foreach ((emblem) => {
					file.emblems_list.remove (emblem);
				});
				
				file.add_emblem ("emblem-default");

				file.update_emblem ();
			}
        	
        	return true; // continue
        });
    }

    private void thrift_serialize(string object_to_serialize) {
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


def deserialize_thrift_msg(data, socket_state, msgobj=Message()):
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

    return msg, remaining, socket_state


state = emb.state()
data = emb.buffer()

if state is not None and len(state) < 1:
	state = None

while data:
	des, remaining, state = deserialize_thrift_msg(
		data, state)

	if not des:
		break

	if des is not None and des.fileStatus is not None and des.fileStatus.status is not None:
		emb.update_status(des.fileStatus.status.path, des.fileStatus.status.state)

	data = remaining

if state is not None:
	emb.set_state(state)
else:
	emb.set_state('')

""");
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
                debug("open in browser");
            } catch (Error e) {
            }
        });
        submenu.add (open_in_browser);

        GLib.File f = File.new_for_path (path);

        if (f.query_file_type (0) == FileType.DIRECTORY) {
            var share_folder = new Gtk.MenuItem.with_label (SHARE_FOLDER);
            share_folder.activate.connect ((w) => {
                try {
                	debug("share folder");
                } catch (Error e) {
                }
            });
            submenu.add (share_folder);
        } else {
            var copy_link = new Gtk.MenuItem.with_label (COPY_LINK);
            copy_link.activate.connect ((w) => {
                try {
                	debug("copy link");
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
            string cloud_home = "/home/ivo/MEOCloud";

            if (path == cloud_home) {
                int status = 4;

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
            } else if (path.has_prefix(cloud_home)) {
            	if (status.has_key(path)) {
            		file.add_emblem ("emblem-synchronizing");
//file.add_emblem ("emblem-important");
//					file.add_emblem ("emblem-default");
            	} else {
            		map.set (path, file);
            		//status.set (path, 2);
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
