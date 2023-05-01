import threading
from autoinject import injector
import datetime
import typing as t
from urllib.parse import urlparse


BYTE_UNITS = {
    # Bits
    "bit": 0.125,
    # Bytes
    "b": 1,
    # Standard prefixes
    "kib": 1024,
    "mib": 1048576,
    "gib": 1073741824,
    "tib": 1099511627776,
    "pib": 1125899906842624,
    "eib": 1152921504606846976,
    # Short forms translate to standard prefixes
    "k": 1024,
    "m": 1048576,
    "g": 1073741824,
    "t": 1099511627776,
    "p": 1125899906842624,
    "e": 1152921504606846976,
    # Allow for hard drive/metric sizing (but with option to disable)
    "kb": 1000,
    "mb": 1000000,
    "gb": 1000000000,
    "tb": 1000000000000,
    "pb": 1000000000000000,
    "eb": 1000000000000000000,
}


def parse_for_units(val: str, max_unit_len: int, default_units: str) -> t.Tuple[t.Union[int, float], str]:
    val = val.strip()
    if max_unit_len < 0:
        raise ValueError("Unit length must be positive")
    unit_len = -1 * min(max_unit_len, len(val))
    while unit_len < 0 and (val[unit_len].isdigit() or val[unit_len] == "."):
        unit_len += 1
    actual_val = val[:unit_len].strip() if unit_len < 0 else val
    units = val[unit_len:].strip() if unit_len < 0 else default_units
    return (float(actual_val), units) if "." in actual_val else (int(actual_val), units)


def convert_to_bytes(val: t.Union[float, int], units: str, disallow_metric_prefixes: bool = False) -> t.Union[float, int]:
    units = units.lower()
    # Convert metric prefixes to standard representations
    if disallow_metric_prefixes and len(units) == 2:
        units = f"{units[0]}i{units[1]}"
    if units not in BYTE_UNITS:
        raise ValueError(f"Unrecognized units for bytes: {units}")
    return val * BYTE_UNITS[units]


def convert_to_timedelta(val: t.Union[float, int], units: str) -> datetime.timedelta:
    units = units.lower()
    if units == "s":
        return datetime.timedelta(seconds=val)
    elif units == "m":
        return datetime.timedelta(minutes=val)
    elif units == "h":
        return datetime.timedelta(hours=val)
    elif units == "d":
        return datetime.timedelta(days=val)
    elif units == "w":
        return datetime.timedelta(weeks=val)
    elif units == "us":
        return datetime.timedelta(microseconds=val)
    elif units == "ms":
        return datetime.timedelta(milliseconds=val)
    else:
        raise ValueError(f"Unknown units for timedelta: {units}")


@injector.inject
def print_config(obfuscate_keys=None, cfg: "zirconium.config.ApplicationConfig" = None):
    print("----- Loaded Files -----")
    for f in cfg.loaded_files:
        print(f)
    print("----- Configuration Values -----")
    _print_dict(cfg.d, obfuscate_keys=obfuscate_keys)


def _print_dict(d, prefix='  ', level=0, parent_prefix=None, obfuscate_keys=None):
    for key in d:
        full_path = list(parent_prefix) if parent_prefix else []
        full_path.append(key)
        full_path = tuple(full_path)
        val = d[key]
        if obfuscate_keys is not None and full_path in obfuscate_keys:
            print(f"{prefix * level}{key}: {'*' * len(val)}")
            continue
        if isinstance(val, dict):
            print(f"{prefix * level}{key}: ")
            _print_dict(val, prefix, level + 1, full_path, obfuscate_keys)
        elif isinstance(val, set) or isinstance(val, list) or isinstance(val, tuple):
            print(f"{prefix * level}{key}: ")
            for entry in val:
                print(f"{prefix * (level+1)}- {_obfuscate_entry(entry)}")
        else:
            print(f"{prefix * level}{key}: {_obfuscate_entry(val)}")


def _obfuscate_entry(entry):
    if "://" in entry:
        try:
            uri = urlparse(entry)
            if uri.password:
                qs = f"?{uri.query}" if uri.query else ""
                fs = f"#{uri.fragment}" if uri.fragment else ""
                return f"{uri.scheme}://{uri.username}:{'*' * len(uri.password)}@{uri.hostname}{uri.path}{qs}{fs}"
        except ValueError:
            pass
    return entry


@injector.injectable_global
class _AppConfigHooks:
    """ Global storage of configuration hooks for ApplicationConfig prior to instantiation. """

    def __init__(self):
        self.hooks = []

    def add_hook(self, c):
        self.hooks.append(c)

    def execute_hooks(self, cfg):
        for hook in self.hooks:
            hook(cfg)


@injector.inject
def _config_decorator(func, ach: _AppConfigHooks = None):
    """ Decorate a function with this to add configuration files """
    ach.add_hook(func)
    return func


class MutableDeepDict:
    """ Deep dictionary class that supports tuple-like access to deep properties """

    def __init__(self, base_dict=None):
        """ Constructor """
        self.d = base_dict if base_dict else {}
        self.lock = threading.RLock()

    def _navigate_to_item(self, key, create=False):
        """ Navigate to an item in the tree structure specified by key

            :param key: The key to navigate to
            :type key: str or tuple
            :param create: If set to true, the entry will be created
            :type create: bool
            :returns: A tuple, with the first item being the dictionary structure and the second being the key in that
                structure that represents the tail element of key. Both will be None if a parent key does not exist
            :rtype: tuple(dict, str)
        """
        try:
            if isinstance(key, str):
                return self.d, key
            parent = self.d
            for k in key[:-1]:
                if k in parent and MutableDeepDict.is_dict_like(parent[k]):
                    parent = parent[k]
                elif create:
                    parent[k] = {}
                    parent = parent[k]
                else:
                    return None, None
            return parent, key[-1]
        except TypeError:
            return self.d, key

    def __setitem__(self, key, value):
        """ Thread-safe __setitem__ implementation """
        with self.lock:
            parent, k = self._navigate_to_item(key, True)
            parent[k] = value

    def __getitem__(self, key):
        """ __getitem__ implementation"""
        return self.get(key, raise_error=True)

    def __delitem__(self, key):
        """ Thread-safe __delitem__ implementation"""
        with self.lock:
            parent, k = self._navigate_to_item(key)
            if parent:
                del parent[k]

    def __contains__(self, key):
        """ __contains__ implementation """
        parent, k = self._navigate_to_item(key)
        return parent is not None and k in parent

    def __len__(self):
        """ __len__ implementation """
        return len(self.d)

    def __iter__(self):
        """ __iter__ implementation """
        return iter(self.d)

    def clear(self):
        """Clear the dictionary of all entries."""
        self.d = {}

    def deep_update(self, d):
        """ Similar to update(), but will merge dictionaries at depth. Thread-safe. """
        with self.lock:
            for key in d.keys():
                if key in self.d and MutableDeepDict.is_dict_like(d[key]) and MutableDeepDict.is_dict_like(self.d[key]):
                    mut = MutableDeepDict(self.d[key])
                    mut.deep_update(d[key])
                else:
                    self.d[key] = d[key]

    def update(self, d):
        """ Thread-safe implementation of dict.update() """
        with self.lock:
            self.d.update(d)

    def _expand_key(self, key):
        """ Given a key, expands it to an ordered list to be used with _navigate_to_item() or other methods that
        leverage it """
        expanded = []
        for k in key:
            if isinstance(k, str) or not hasattr(k, "__iter__"):
                expanded.append(k)
            else:
                expanded.extend(k)
        return expanded

    def get(self, *key, default=None, raise_error=False):
        """ Implementation of dict.get(). Added a raise_error parameter which causes ValueError to be raised if the
            key does not exist, otherwise the default is returned. """
        key = self._expand_key(key)
        parent, k = self._navigate_to_item(key)
        if ((parent is None) or (not k in parent)) and raise_error:
            raise ValueError("No such key: {}".format(".".join(key)))
        value = default
        if parent and k in parent:
            value = parent[k]
        return value

    def keys(self):
        """ Implementation of dict.keys() """
        return self.d.keys()

    def values(self):
        """ Implementation of dict.values() """
        return self.d.values()

    def pop(self, key, default):
        """ Thread-safe implementation of dict.pop() that works on deep arrays. """
        with self.lock:
            parent, k = self._navigate_to_item(key)
            if parent:
                return parent.pop(key, default)
            return default

    @staticmethod
    def is_dict_like(d):
        """ Checks if d is dict-like """
        if isinstance(d, dict):
            return True
        if isinstance(d, MutableDeepDict):
             return True
        if hasattr(d, "keys"):
            return True
        return False
