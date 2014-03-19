import sys
import os


def create_startup_file():
    folder_path = os.path.join(os.path.expanduser('~'),
                               '.config/autostart')
    file_path = os.path.join(folder_path, 'meocloud.desktop')

    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

    desktop_file = open(file_path, 'w')
    desktop_file.write("[Desktop Entry]\n")
    desktop_file.write("Type=Application\n")
    desktop_file.write("Name=MEO Cloud\n")
    desktop_file.write("Exec=" + os.path.join(os.getcwd(),
                       "meocloud-gui") + "\n")
    desktop_file.close()


def test_already_running(pid_path, proc_name):
    try:
        with open(pid_path) as f:
            pid = int(f.read())
        with open('/proc/{0}/cmdline'.format(pid)) as f:
            if proc_name in f.read():
                assert pid != 0
                return pid
    except Exception:
        # Either the application is not running or we have no way
        # to find it, so assume it is not running.
        pass
    return False


def get_own_dir(own_filename):
    if getattr(sys, "frozen", False):
        own_path = sys.executable
    else:
        own_path = os.path.join(os.getcwd(), own_filename)
    return os.path.dirname(own_path)
    

def get_proxy(ui_config):
    return None
    
def get_ratelimits(ui_config):
    return 0, 0
