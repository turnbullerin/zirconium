import os
import decimal
import datetime
import threading
import sys
from pathlib import Path

from autoinject import injector, CacheStrategy
from .parsers import JsonConfigParser, IniConfigParser, YamlConfigParser, TomlConfigParser, CfgConfigParser
from .utils import MutableDeepDict, _AppConfigHooks

# Metadata entrypoint support depends on Python version
import importlib.util
if importlib.util.find_spec("importlib.metadata"):
    # Python 3.10 supports entry_points(group=?)
    if sys.version_info.minor >= 10:
        from importlib.metadata import entry_points
    # Python 3.8 and 3.9 have metadata, but don't support the keyword argument
    else:
        from importlib.metadata import entry_points as _entry_points

        def entry_points(group=None):
            eps = _entry_points()
            if group is None:
                return eps
            elif group in eps:
                return eps[group]
            else:
                return []

# Backwards support for Python 3.7
else:
    from importlib_metadata import entry_points


@injector.register("zirconium.config.ApplicationConfig", caching_strategy=CacheStrategy.GLOBAL_CACHE)
class ApplicationConfig(MutableDeepDict):

    ach: _AppConfigHooks = None

    @injector.construct
    def __init__(self, manual_init=False):
        super().__init__()
        self.encoding = "utf-8"
        self.parsers = [
            TomlConfigParser(),
            YamlConfigParser(),
            CfgConfigParser(),
            IniConfigParser(),
            JsonConfigParser(),
        ]
        self.file_registry = {
            "defaults": [],
            "regulars": [],
            "environment": [],
        }
        self.environment_map = {}
        self.loaded_files = []
        self._init_flag = False
        self._cached_gets = {}
        self.registry_lock = threading.RLock()
        self.cache_lock = threading.RLock()
        if not manual_init:
            auto_register = entry_points(group="zirconium.parsers")
            for ep in auto_register:
                self.parsers.append(ep.load()(self))
            auto_register = entry_points(group="zirconium.config")
            for ep in auto_register:
                registrar_func = ep.load()
                registrar_func(self)
            self.ach.execute_hooks(self)
            self.init()

    def get(self, *key, default=None, coerce=None, blank_to_none=False, raw=False, raise_error=False):
        key = self._expand_key(key)
        full_key = ".".join([str(x) for x in key])
        if full_key in self._cached_gets:
            return self._cached_gets[full_key]
        with self.cache_lock:
            if full_key not in self._cached_gets:
                value = super().get(*key, default=default, raise_error=raise_error)
                if blank_to_none and value == "":
                    value = None
                if (not raw) and isinstance(value, str):
                    value = ApplicationConfig.resolve_environment_references(value)
                if coerce and value is not None:
                    value = coerce(value)
                self._cached_gets[full_key] = value
            return self._cached_gets[full_key]

    @staticmethod
    def resolve_environment_references(value: str) -> str:
        pos = 0
        # Escape rule for $ is dollar signs that precede a bracket
        # ${var}
        # $${not_a_var}, equivalent to string ${not_a_var}
        # $$${var}, equivalent to "${}".format(os.environ["var"])
        # $$$${not_a var}, equivalent to string $${not_a_var}
        #
        # ${{\}} equivalent to os.environ["{}"]
        # ${{\\\}} equivalent to os.environ["{\}"]
        state = "buffering"
        ref_buffer = ""
        resolved = ""
        for i in range(0, len(value)):
            c = value[i]
            if c == "$":
                if state == "buffering":
                    state = "opening_ref"
                    continue
                elif state == "opening_ref":
                    resolved += "$"
                    state = "buffering"
                    continue
            elif c == "{":
                if state == "opening_ref":
                    state = "in_ref"
                    continue
            elif c == "\\":
                if state == "in_ref":
                    state = "escaping_in_ref"
                    continue
                elif state == "escaping_in_ref":
                    ref_buffer += "\\"
                    state = "in_ref"
                    continue
            elif c == "}":
                if state == "escaping_in_ref":
                    ref_buffer += "}"
                    state = "in_ref"
                    continue
                elif state == "in_ref":
                    resolved += ApplicationConfig.parse_env_reference(ref_buffer)
                    ref_buffer = ""
                    state = "buffering"
                    continue
            if state == "buffering":
                resolved += c
            elif state == "in_ref":
                ref_buffer += c
            elif state == "escaping_in_ref":
                ref_buffer += "\\" + c
                state = "in_ref"
        if ref_buffer:
            resolved += "${" + ref_buffer
        return resolved

    @staticmethod
    def parse_env_reference(name):
        val = ""
        if "=" in name:
            val = name[name.find("=") + 1:]
            name = name[0:name.find("=")]
        # first check however we wrote it
        if name in os.environ:
            val = os.environ[name]
            # local variables first in UNIX
        elif name.lower() in os.environ:
            val = os.environ[name]
            # global variables next
        elif name.upper() in os.environ:
            val = os.environ[name]
        return val

    def as_date(self, key, default=None, raw=False):
        dt = self.get(key, default=default, blank_to_none=True, raw=raw)
        if isinstance(dt, datetime.datetime):
            return datetime.date(dt.year, dt.month, dt.day)
        elif dt is None or isinstance(dt, datetime.date):
            return dt
        else:
            try:
                return datetime.date.fromisoformat(dt)
            except ValueError:
                dt = datetime.datetime.fromisoformat(dt)
                return datetime.date(dt.year, dt.month, dt.day)

    def as_datetime(self, key, default=None, tzinfo=None, raw=False):
        dt = self.get(key, default=default, blank_to_none=True, raw=raw)
        if dt is None:
            return None
        if isinstance(dt, datetime.datetime):
            if dt.tzinfo is None and tzinfo is not None:
                return datetime.datetime(
                    dt.year,
                    dt.month,
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second,
                    dt.microsecond,
                    tzinfo
                )
            return dt
        elif isinstance(dt, datetime.date):
            return datetime.datetime(dt.year, dt.month, dt.day, 0, 0, 0, tzinfo=tzinfo)
        else:
            dt = datetime.datetime.fromisoformat(dt)
            if dt.tzinfo is None and tzinfo is not None:
                return datetime.datetime(
                    dt.year,
                    dt.month,
                    dt.day,
                    dt.hour,
                    dt.minute,
                    dt.second,
                    dt.microsecond,
                    tzinfo
                )
            return dt

    def as_int(self, key, default=None, raw=False):
        return self.get(key, default=default, coerce=int, blank_to_none=True, raw=raw)

    def as_float(self, key, default=None, raw=False):
        return self.get(key, default=default, coerce=float, blank_to_none=True, raw=raw)

    def as_decimal(self, key, default=None, raw=False):
        return self.get(key, default=default, coerce=decimal.Decimal, blank_to_none=True, raw=raw)

    def as_str(self, key, default=None, raw=False):
        return self.get(key, default=default, coerce=str, raw=raw)

    def as_bool(self, key, default=None, raw=False):
        return bool(self.get(key, default=default, raw=raw))

    def as_path(self, key, default=None, raw=False):
        return self.get(key, default=default, coerce=Path, blank_to_none=True, raw=raw)

    def as_dict(self, key, default=None):
        return self.get(key, default=default, coerce=MutableDeepDict, blank_to_none=True, raw=True)

    def set_default_encoding(self, enc):
        self.encoding = enc

    def is_truthy(self, key):
        parent, k = self._navigate_to_item(key)
        return parent is not None and k in parent and bool(parent[k])

    def register_parser(self, parser):
        self.parsers.append(parser)

    def register_default_file(self, file_path, weight=None, parser=None, encoding=None):
        with self.registry_lock:
            if weight is None:
                weight = self._next_weight("defaults")
            self.file_registry["defaults"].append((file_path, weight, parser, encoding))

    def register_file(self, file_path, weight=None, parser=None, encoding=None):
        with self.registry_lock:
            if weight is None:
                weight = self._next_weight("regulars")
            self.file_registry["regulars"].append((file_path, weight, parser, encoding))

    def register_file_from_environ(self, env_var_name, weight, parser=None, encoding=None):
        with self.registry_lock:
            if weight is None:
                weight = self._next_weight("environment")
            self.file_registry["environment"].append((env_var_name, weight, parser, encoding))

    def _next_weight(self, key):
        if self.file_registry[key]:
            return max(x[1] for x in self.file_registry[key]) + 1
        return 0

    def register_environ_var(self, env_var_name, *target_config):
        self.environment_map[env_var_name] = target_config

    def init(self):
        with self.registry_lock:
            if not self._init_flag:
                self.file_registry["defaults"].sort(key=lambda x: x[1])
                for file, weight, parser, enc in self.file_registry["defaults"]:
                    self.load_file(file, parser, enc)
                self.file_registry["regulars"].sort(key=lambda x: x[1])
                for file, weight, parser, enc in self.file_registry["regulars"]:
                    self.load_file(file, parser, enc)
                self.file_registry["environment"].sort(key=lambda x: x[1])
                for env_name, weight, parser, enc in self.file_registry["environment"]:
                    if env_name in os.environ:
                        self.load_file(os.environ.get(env_name), parser, enc)
                for env_name, target_config in self.environment_map:
                    if env_name in os.environ:
                        self.config[target_config] = os.environ.get(env_name)
                self._init_flag = True

    def load_file(self, file_path, parser=None, encoding=None):
        with self.registry_lock:
            if encoding is None:
                encoding = self.encoding
            file_path = Path(file_path).expanduser().absolute()
            if file_path.exists() and file_path not in self.loaded_files:
                if parser:
                    self.load_from_dict(parser.read_dict(file_path, encoding))
                    self.loaded_files.append(file_path)
                else:
                    for parser in self.parsers:
                        if parser.handles(file_path.name):
                            self.load_from_dict(parser.read_dict(file_path, encoding))
                            self.loaded_files.append(file_path)
                            break

    def load_from_dict(self, d):
        self.deep_update(d)
