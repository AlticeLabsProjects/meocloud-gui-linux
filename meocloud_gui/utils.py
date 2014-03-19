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
