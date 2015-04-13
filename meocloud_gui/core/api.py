import urlparse
import urllib
import threading

# GLib and Gdk
from gi.repository import GLib, Gdk

from meocloud_gui.protocol.daemon_core.ttypes import NetworkSettings, Account
from meocloud_gui.utils import get_ratelimits


def get_account_dict(ui_config):
    account_dict = dict()

    class AccountCallback:
        def __init__(self):
            self.event = threading.Event()
            self.result = None

        def __call__(self):
            Gdk.threads_enter()
            try:
                account_dict['clientID'] = ui_config.creds.cid
                account_dict['authKey'] = ui_config.creds.ckey
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

    # Fetch settings in the main thread
    account_callback = AccountCallback()
    account_callback.event.clear()
    GLib.idle_add(account_callback)
    account_callback.event.wait()

    return account_dict


def unlink(core_client, ui_config):
    account_dict = get_account_dict(ui_config)
    if account_dict['clientID'] and account_dict['authKey']:
        account = Account(**account_dict)
        ui_config.creds.clear()
        for attr in ('email', 'name', 'deviceName'):
            ui_config.remove('Account', attr)
        ui_config.save()
        core_client.unlink(account)
        return True

    return False


def auto_configure_proxy(settings):
    proxies = urllib.getproxies()
    if 'http' not in proxies:
        return

    proxy = urlparse.urlparse(proxies['http'])

    settings.proxyType = 'http'
    settings.proxyAddress = proxy.hostname
    settings.proxyPort = proxy.port
    if settings.proxyPort is None:
        settings.proxyPort = 3128

    user = proxy.username
    passwd = proxy.password

    settings.proxyUser = user if user is not None else ''
    settings.proxyPassword = passwd if passwd is not None else ''


def get_network_settings(ui_config, download=None, upload=None):
    network_settings = NetworkSettings()

    download_limit, upload_limit = get_ratelimits(ui_config)
    network_settings.downloadBandwidth = download_limit * 1024  # KB/s to B/s
    network_settings.uploadBandwidth = upload_limit * 1024  # KB/s to B/s

    if download is not None:
        network_settings.downloadBandwidth = download * 1024
    if upload is not None:
        network_settings.uploadBandwidth = upload * 1024

    use_proxy = ui_config.get('Network', 'Proxy')

    if use_proxy == 'Manual':
        address = ui_config.get('Network', 'ProxyAddress', '')
        port = ui_config.get('Network', 'ProxyPort', '')
        user = ui_config.get('Network', 'ProxyUser', '')
        password = ui_config.get('Network', 'ProxyPassword', '')

        if address:
            network_settings.proxyAddress = address
            network_settings.proxyType = 'http'

            try:
                network_settings.proxyPort = int(port)
            except (TypeError, ValueError):
                network_settings.proxyPort = 3128

            network_settings.proxyUser = user
            network_settings.proxyPassword = password
    elif use_proxy == 'Automatic' or use_proxy is None:
        auto_configure_proxy(network_settings)

    return network_settings
