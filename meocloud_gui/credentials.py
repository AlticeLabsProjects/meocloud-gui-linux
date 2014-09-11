import fcntl
import socket
import struct
import hashlib
import base64
import os

from time import time


KEY_SIZE = 16
ENCODED_KEY_SIZE = 26
DERIVE_ROUNDS = 2500


def fetch_hwaddr_fcntl(iface):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927,  struct.pack('256s', iface[:15]))
    except (socket.error, EnvironmentError):
        result = None
    else:
        result = ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]
    return result


def fetch_hwaddr_sysfs(iface):
    try:
        with open('/sys/class/net/' + iface) as ifile:
            result = ifile.read()
    except EnvironmentError:
        result = None
    return result


def fetch_hwaddr(iface):
    addr = fetch_hwaddr_sysfs(iface)
    if addr is not None:
        return addr
    return fetch_hwaddr_fcntl(iface)


def fetch_uptime():
    seconds = -1
    try:
        with open('/proc/uptime', 'rb') as uptime:
            data = uptime.read()
    except IOError:
        pass
    else:
        seconds, _ = data.split()
        try:
            seconds = int(float(seconds))
        except (ValueError, TypeError):
            pass

    return seconds


def has_rebooted(saved_reboot):
    try:
        saved_reboot = saved_reboot
    except (ValueError, TypeError):
        return False        

    now = int(time())
    uptime = fetch_uptime()
    if uptime == -1:
        return False

    min_reboot_secs = 300
    last_reboot = (now - uptime) / min_reboot_secs
    saved_reboot /= min_reboot_secs

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

    def __init__(self, prefs, encrypt, decrypt):
        self.prefs = prefs
        self.__encrypt = encrypt
        self.__decrypt = decrypt
        self.key = None

        altseed = prefs.get('Account', 'altkey')
        if altseed:
            self.key = self._derive_key(altseed)
            return

        attrs = fetch_hwaddr('eth0')
        if attrs:
            try:
                import platform
                dist = platform.dist()[0]
            except ImportError:
                dist = None
            else:
                if dist:
                    attrs += dist
            syskey = self._derive_key(attrs)
        else:
            syskey = None

        use_sys_key = prefs.get('Account', 'syskey')
        if syskey and use_sys_key:
            self.key = syskey
            return

        probe = prefs.get('Account', 'probe')
        altseed, syshash, reboot = self._parse_probe(probe)
        ecid = prefs.get('Account', 'id')
        eckey = prefs.get('Account', 'key')
        if ecid is None or eckey is None or altseed is None:
            reboot = int(time()) - fetch_uptime()
            altseed = self._encode(self._new_key())
            syshash = self._encode(self._hash(syskey))
            prefs.put('Account', 'probe', '{0}{1}{2}'.
                      format(altseed, syshash, reboot))
            prefs.save()
            self.key = self._derive_key(altseed)
            return

        self.key = self._derive_key(altseed)

        if self._encode(self._hash(syskey)) != syshash:
            prefs.put('Account', 'altkey', altseed)
            prefs.remove('Account', 'probe')
            prefs.save()
            return 
 
        if not has_rebooted(reboot):
            return

        cid = self._decrypt(self._decode(ecid))
        ckey = self._decrypt(self._decode(eckey))

        self.key = syskey

        ecid = self._encode(self._encrypt(cid))
        eckey = self._encode(self._encrypt(ckey))

        prefs.put('Account', 'id', ecid)
        prefs.put('Account', 'key', eckey)
        prefs.put('Account', 'syskey', altseed)
        prefs.remove('Account', 'probe')
        prefs.save()

    def _new_key(self):
        return os.urandom(KEY_SIZE)

    def _derive_key(self, data):
        hasher = hashlib.sha256(data)
        for _ in xrange(DERIVE_ROUNDS):
             hasher.update(hasher.digest())
        return hasher.digest()[:KEY_SIZE]

    def _hash(self, data):
        hasher = hashlib.sha256(data)
        return hasher.digest()[:KEY_SIZE]

    def _parse_probe(self, probe):
        invalid_probe = (None, None, None)
        if probe is None:
            return invalid_probe

        try:
            start = 0
            end = ENCODED_KEY_SIZE
            altseed = probe[start:end]
            start += ENCODED_KEY_SIZE
            end += ENCODED_KEY_SIZE
            syshash = probe[start:end]
            start += ENCODED_KEY_SIZE
            reboot = int(probe[start:])
        except IndexError:
            return invalid_probe

        return altseed, syshash, reboot

    def _encrypt(self, value):
        if self.key is None or value is None:
            return None

        return self.__encrypt(value, self.key, encode=None)

    def _decrypt(self, value):
        if self.key is None or value is None:
            return None
        return self.__decrypt(value, self.key, decode=None)

    def _encode(self, data):
        if not data:
            return None
        try:
            result = base64.b32encode(data).strip('=').lower()
        except (ValueError, TypeError):
            result = None
        return result

    def _decode(self, data):
        if not data:
            return None
        data += '=' * (8 - len(data) % 8)
        try:
            result = base64.b32decode(data.upper())
        except (ValueError, TypeError):
            result = None
        return result

    def clear(self):
        if self.prefs:
            for attr in ('id', 'key', 'syskey', 'altkey', 'probe'):
                self.prefs.remove('Account', attr)

    @property
    def cid(self):
        ecid = self.prefs.get('Account', 'id')
        return self._decrypt(self._decode(ecid))

    @cid.setter
    def cid(self, value):
        ecid = self._encode(self._encrypt(value))
        self.prefs.put('Account', 'id', ecid)
        self.prefs.save()

    @property
    def ckey(self):
        eckey = self.prefs.get('Account', 'key')
        return self._decrypt(self._decode(eckey))

    @ckey.setter
    def ckey(self, value):
        eckey = self._encode(self._encrypt(value))
        self.prefs.put('Account', 'key', eckey)
        self.prefs.save()

