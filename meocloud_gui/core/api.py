import urlparse
import threading
import keyring

# GLib and Gdk
from gi.repository import GLib, Gdk

from meocloud_gui.protocol.daemon_core.ttypes import NetworkSettings, Account
from meocloud_gui.utils import get_proxy, get_ratelimits
from meocloud_gui.preferences import Preferences


def get_account_dict(ui_config):
    account_dict = dict()

    class AccountCallback:
        def __init__(self):
            self.event = threading.Event()
            self.result = None

        def __call__(self):
            Gdk.threads_enter()
            try:
                account_dict['clientID'] = keyring.get_password('meocloud',
                                                                'clientID')
                account_dict['authKey'] = keyring.get_password('meocloud',
                                                               'authKey')
                account_dict['email'] = ui_config.get('Account', 'email',
                                                           None)
                account_dict['name'] = ui_config.get('Account', 'name',
                                                          None)
                account_dict['deviceName'] = ui_config.get('Account',
                                                                'deviceName',
                                                                None)
            finally:
                Gdk.flush()
                Gdk.threads_leave()
                self.event.set()
            return False

    # Keyring must run in the main thread,
    # otherwise we segfault.
    account_callback = AccountCallback()
    account_callback.event.clear()
    GLib.idle_add(account_callback)
    account_callback.event.wait()

    return account_dict


def unlink(core_client, ui_config):
    account_dict = get_account_dict(ui_config)
    if account_dict['clientID'] and account_dict['authKey']:
        account = Account(**account_dict)
        GLib.idle_add(lambda: keyring.delete_password('meocloud', 'clientID'))
        GLib.idle_add(lambda: keyring.delete_password('meocloud', 'authKey'))
        ui_config.put('Account', 'email', '')
        ui_config.put('Account', 'name', '')
        ui_config.put('Account', 'deviceName', '')
        core_client.unlink(account)
        return True
    return False


def get_network_settings(ui_config, download=None, upload=None):
    network_settings = NetworkSettings()

    download_limit, upload_limit = get_ratelimits(ui_config)
    network_settings.downloadBandwidth = download_limit * 1024  # KB/s to B/s
    network_settings.uploadBandwidth = upload_limit * 1024  # KB/s to B/s

    if download is not None:
        network_settings.downloadBandwidth = download * 1024
    if upload is not None:
        network_settings.uploadBandwidth = upload * 1024

    proxy_url = get_proxy(ui_config)
    if proxy_url:
        try:
            parsed = urlparse.urlparse(proxy_url)
        except Exception:
            # Something went wrong while trying to parse proxy_url
            # Ignore and just don't use any proxy
            pass
        else:
            if parsed.hostname:
                network_settings.proxyAddress = parsed.hostname
                network_settings.proxyType = 'http'
                network_settings.proxyPort = parsed.port or 3128
                network_settings.proxyUser = \
                    parsed.user if hasattr(parsed, 'user') else ''
                network_settings.proxyPassword = \
                    parsed.password if hasattr(parsed, 'password') else ''
    else:
        prefs = Preferences()

        use_proxy = prefs.get('Network', 'Proxy', 'None')

        if use_proxy == 'Manual':
            address = prefs.get('Network', 'ProxyAddress', '')
            port = prefs.get('Network', 'ProxyPort', '')
            user = prefs.get('Network', 'ProxyUser', '')
            password = prefs.get('Network', 'ProxyPassword', '')

            if len(address) > 0 and len(port) > 0:
                network_settings.proxyAddress = address
                network_settings.proxyType = 'http'

                try:
                    network_settings.proxyPort = int(port)
                except ValueError:
                    network_settings.proxyPort = 3128

                network_settings.proxyUser = user
                network_settings.proxyPassword = password

    return network_settings
