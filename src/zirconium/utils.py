import threading
import pymitter
from autoinject import injector


def _config_decorator(func):
    ee = injector.get(pymitter.EventEmitter)
    ee.once("zirconium.configure", func)
    return func


class MutableDeepDict:

    def __init__(self, base_dict=None):
        self.d = base_dict if base_dict else {}
        self.lock = threading.RLock()

    def _navigate_to_item(self, key, create=False):
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
        with self.lock:
            parent, k = self._navigate_to_item(key, True)
            parent[k] = value

    def __getitem__(self, key):
        return self.get(key, raise_error=True)

    def __delitem__(self, key):
        with self.lock:
            parent, k = self._navigate_to_item(key)
            if parent:
                del parent[k]

    def __contains__(self, key):
        parent, k = self._navigate_to_item(key)
        return parent is not None and k in parent

    def __len__(self):
        return len(self.d)

    def __iter__(self):
        return iter(self.d)

    def deep_update(self, d):
        with self.lock:
            for key in d.keys():
                if key in self.d and MutableDeepDict.is_dict_like(d[key]) and MutableDeepDict.is_dict_like(self.d[key]):
                    mut = MutableDeepDict(self.d[key])
                    mut.deep_update(d[key])
                else:
                    self.d[key] = d[key]

    def update(self, d):
        with self.lock:
            self.d.update(d)

    def _expand_key(self, key):
        expanded = []
        for k in key:
            if isinstance(k, str) or not hasattr(k, "__iter__"):
                expanded.append(k)
            else:
                expanded.extend(k)
        return expanded

    def get(self, *key, default=None, raise_error=False):
        key = self._expand_key(key)
        parent, k = self._navigate_to_item(key)
        if ((parent is None) or (not k in parent)) and raise_error:
            raise ValueError("No such key: {}".format(".".join(key)))
        value = default
        if parent and k in parent:
            value = parent[k]
        return value

    def keys(self):
        return self.d.keys()

    def values(self):
        return self.d.values()

    def pop(self, key, default):
        with self.lock:
            parent, k = self._navigate_to_item(key)
            if parent:
                return parent.pop(key, default)
            return default

    @staticmethod
    def is_dict_like(d):
        if isinstance(d, dict):
            return True
        if isinstance(d, MutableDeepDict):
             return True
        if hasattr(d, "keys"):
            return True
        return False
