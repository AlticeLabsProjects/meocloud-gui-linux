import fcntl
import socket
import struct
import hashlib
import base64
import os

import keyring

from time import time

from meocloud_gui.constants import (
    CLIENT_ID,
    AUTH_KEY
)

KEY_SIZE = 16
IV_SIZE = 16
ENCODED_KEY_SIZE = 26
ENCODED_IV_SIZE = 26
DERIVE_ROUNDS = 2500


CREDS_MAP = {
    'id': CLIENT_ID,
    'key': AUTH_KEY
}


def fetch_hwaddr_fcntl(iface):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        info = fcntl.ioctl(s.fileno(), 0x8927, struct.pack('256s', iface[:15]))
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


def fetch_plaftorm_info():
    dist = None
    try:
        import platform
        dist = platform.dist()[0]
    except ImportError:
        dist = None
    return dist if dist else None


def fetch_attrs():
    addr = fetch_hwaddr('eth0')
    distro = fetch_plaftorm_info()
    attrs = ''

    if addr:
        attrs += addr
    if distro:
        attrs += distro

    return attrs


class CredentialStore(object):
    def __init__(self, prefs, encrypt, decrypt):
        self.prefs = prefs
        self.__encrypt = encrypt
        self.__decrypt = decrypt
        self.key = None
        self.used_keyring = False
        self.kwallet_enabled = 'kwallet' in str(keyring.get_keyring()).lower()

        altseed = prefs.get('Account', 'altkey')
        if altseed:
            self.key = self._derive_key(altseed)
            return

        attrs = fetch_attrs()
        syskey = self._derive_key(attrs) if attrs else None

        use_sys_key = prefs.get('Account', 'syskey')
        if syskey and use_sys_key:
            self.key = syskey
            return

        probe = prefs.get('Account', 'probe')
        altseed, syshash, reboot = self._parse_probe(probe)
        if altseed is None:
            reboot = int(time()) - fetch_uptime()
            altseed = self._encode(self._new_key())
            syshash = self._encode(self._hash(syskey))
            prefs.put('Account', 'probe', '{0}{1}{2}'.
                      format(altseed, syshash, reboot))
            prefs.save()
            self.key = self._derive_key(altseed)
            return

        self.key = self._derive_key(altseed)

        if not syskey or self._encode(self._hash(syskey)) != syshash:
            prefs.put('Account', 'altkey', altseed)
            prefs.remove('Account', 'probe')
            prefs.save()
            return

        if not has_rebooted(reboot):
            return

        ecid = prefs.get('Account', 'id')
        eckey = prefs.get('Account', 'key')

        cid = self._decrypt(self._decode(ecid))
        ckey = self._decrypt(self._decode(eckey))

        eproxypwd = prefs.get('Network', 'proxypassword')
        if eproxypwd and eproxypwd[0] == '[' and eproxypwd[-1] == ']':
            proxypwd = self._decrypt(self._decode(eproxypwd))
        else:
            proxypwd = None

        self.key = syskey

        ecid = self._encode(self._encrypt(cid))
        eckey = self._encode(self._encrypt(ckey))

        prefs.put('Account', 'id', ecid)
        prefs.put('Account', 'key', eckey)
        prefs.put('Account', 'syskey', altseed)
        prefs.remove('Account', 'probe')

        if proxypwd:
            proxypwd = self._encode(self._encrypt(proxypwd))
            prefs.put('Network', 'proxypassword', proxypwd)

        prefs.save()

    def _get_keyring_password(self, key):
        value = keyring.get_password('meocloud', key)
        if value or self.used_keyring:
            return value

        self.used_keyring = True

        # kwallet is just too much hassle. Give up.
        if self.kwallet_enabled:
            return None

        # First time we are accessing the keyring
        # If the client is registered, try waiting for the keyring to
        # become available
        if self.prefs.get('Account', 'email') is None:
            return None

        for i in xrange(5):
            time.sleep(2 ** i)
            value = keyring.get_password('meocloud', key)
            if value:
                return value

        return None

    def _get_(self, key):
        if not self.kwallet_enabled:
            return self._get_keyring_password(key)

        evalue = self.prefs.get('Account', key)
        value = self._decrypt(self._decode(evalue))
        if value:
            return value

        value = self._get_keyring_password(key)
        if value:
            self._set(key, value)
            key = CREDS_MAP.get(key)
            if key:
                keyring.delete_password('Account', key)
        return value

    def _set(self, key, value):
        if not self.kwallet_enabled:
            key = CREDS_MAP.get(key)
            if key:
                keyring.set_password('meocloud', key, value)
            return

        evalue = self._encode(self._encrypt(value))
        self.prefs.put('Account', key, evalue)
        self.prefs.save()

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

        iv = os.urandom(IV_SIZE)
        key = hashlib.sha256(iv + self.key).digest()
        encrypted = self.__encrypt(value, key, encode=None)

        return iv + encrypted

    def _decrypt(self, value):
        if self.key is None or value is None:
            return None

        if len(value) < IV_SIZE + 1:
            return None

        iv = value[:IV_SIZE]

        key = hashlib.sha256(iv + self.key).digest()
        encrypted = value[IV_SIZE:]

        return self.__decrypt(encrypted, key, decode=None)

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
        return self._get_('id')

    @cid.setter
    def cid(self, value):
        self._set('id', value)

    @property
    def ckey(self):
        return self._get_('key')

    @ckey.setter
    def ckey(self, value):
        self._set('key', value)

    @property
    def proxy_password(self):
        password = self.prefs.get('Network', 'proxypassword')
        if not password:
            return ''

        try:
            password = password[1: -1]
        except IndexError:
            return password

        decrypted = self._decrypt(self._decode(password))
        return decrypted if decrypted is not None else password

    @proxy_password.setter
    def proxy_password(self, value):
        if value:
            password = '[{0}]'.format(self._encode(self._encrypt(value)))
        else:
            password = ''
        self.prefs.put('Network', 'proxypassword', password)
        self.prefs.save()
