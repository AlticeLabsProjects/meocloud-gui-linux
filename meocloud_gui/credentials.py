import fnctl
import socket
import struct
import hashlib

from time import time

def fetch_hwaddr(iface):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', iface[:15]))
    return info


def fetch_uptime():
    seconds = -1
    try:
        with open('/proc/uptime', 'rb') as uptime:
            data = uptime.read()
    except IOError:
        pass
    else:
        seconds, _ = data.split()[0]
        try:
            seconds = float(seconds)
        except (ValueError, TypeError):
            pass

    return seconds


def has_rebooted(saved_reboot):
    try:
        saved_reboot = float(saved_reboot)
    except (ValueError, TypeError):
        return False        

    now = time()
    cur_uptime = fetch_uptime()
    if uptime == -1:
        return False

    last_reboot = now - cur_uptime

    return last_reboot != saved_reboot


class CredentialStore(object):
    '''
    Simple file-based credential store

    This store is intended as an alternative to keyring/kwallet
    based solutions, as their usage is not without issues, especially
    during desktop manager startup. I.e., the application may start
    before the "keyring" (or equivalent) mechanism is available,
    resulting in a forced client reauthorization.

    Credentials are encrypted using key material derived from machine
    attributes.

    Please note that the sole purpose of this mechanism is to ensure
    that credentials are better protected if they happen to be
    stored in other systems (e.g., backup copies).

    A process running with the same priviledge level as the user is
    able to access stored credentials.
    '''

    def __init__(self, prefs):
        self.prefs = prefs
        self.key = None

        altkey = prefs.get('Account', 'altkey')
        if altkey:
            self.key = self._derive_key(altkey)
            return

        syskey = self._derive_key(attrs)
        use_sys_key = prefs.get('Account', 'syskey'):
        if use_sys_key:
            self.key = syskey
            return

        probe = prefs.get('Account', 'probe')
        altkey, syshash, reboot = self._parse_probe(probe)
        ecid = prefs.get('Account', 'id')
        eckey = prefs.get('Account', 'key')
        if ecid is None or eckey is None or altkey is None:
            reboot = time() - uptime()
            altkey = self._new_key()
            syshash = self._hash_key(syskey)
            prefs.put('Account', 'probe', '{0}{1}{2}'.
                      format(self._encode(altkey), syshash, reboot))
            self.key = altkey
            return

        attrs = fetch_hwaddr('eth0')
        altkey = self._derive_key(altkey)

        if self._hash_key(syskey) != syshash:
            prefs.put('Account', 'altkey', self._encode(altkey))
            prefs.remove('Account', 'probe')
            self.key = altkey
            return 
 
         if not has_rebooted(reboot):
            self.key = altkey
            return

        cid = self._decrypt(altkey, ecid)
        ckey = self._decrypt(altkey, eckey)
        ecid = self._encrypt(syskey, cid)
        eckey = self._encrypt(syskey, ckey)

        prefs.put('Account', 'id', ecid)
        prefs.put('Account', 'key', eckey)
        prefs.put('Account', 'syskey', self._encode(altkey))
        prefs.remove('Account', 'probe')

    def _new_key(self, key):
        pass

    def _derive_key(self, data):
        pass

    def _encrypt(self, value):
        pass

    def _decrypt(self, value):
        pass

    @property
    def cid(self):
        pass

    @cid.setter(self, value)
        pass

    @property
    def ckey(self):
        pass

    @key.setter
    def ckey(self, value):
        pass

