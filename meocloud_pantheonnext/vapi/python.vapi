[CCode (cheader_filename = "python2.7/Python.h")]
namespace Python {

	[CCode (cname = "Py_Initialize")]
	public static void initialize ();
	[CCode (cname = "Py_Finalize")]
	public static void finalize ();
	[CCode (cname = "Py_InitModule")]
	public static void init_module (string name, [CCode (array_length = false, array_null_terminated = true)] MethodDef[] methods);
	[CCode (cname = "Py_BuildValue")]
	public static Python.Object build_value (string format, ...);
	[CCode (cname = "PyRun_SimpleString")]
	public static void run_simple_string (string code);
	[CCode (cname = "PyArg_ParseTuple")]
	public static bool arg_parse_tuple (Python.Object arg, string format, ...);

	[SimpleType]
	[CCode (cname = "PyMethodDef")]
	public struct MethodDef {
		[CCode (cname = "ml_name")]
		public string name;
		[CCode (cname = "ml_meth")]
		public CFunction meth;
		[CCode (cname = "ml_flags")]
		public int flags;
		[CCode (cname = "ml_doc")]
		public string doc;
	}

	[CCode (cname = "PyCFunction", has_target = false)]
	public delegate Python.Object? CFunction (Python.Object? self, Python.Object? args);

	[Flags]
	[CCode (cprefix = "METH_", cname = "int")]
	public enum MethodFlags {
		OLDARGS,
		VARARGS,
		KEYWORDS,
		NOARGS,
		O,
		CLASS,
		STATIC,
		COEXIST
	}

	[Compact]
	[CCode (cname = "PyObject")]
	public class Object {
		// TODO
	}
}
