import os
import decimal
import datetime
import threading
import sys
from pathlib import Path
import logging
import typing as t

from autoinject import injector, CacheStrategy
from autoinject.injection import InjectionManager

import zirconium.sproviders as sp
from zirconium.parsers import JsonConfigParser, IniConfigParser, YamlConfigParser, TomlConfigParser, CfgConfigParser, \
    GenericParser
from zirconium.utils import MutableDeepDict, _AppConfigHooks, convert_to_timedelta, convert_to_bytes, parse_for_units


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


VT = t.TypeVar("VT")
RT = t.TypeVar("RT")
DT = t.TypeVar("DT")


class _ConfigRef(t.Generic[VT]):

    def __init__(self, cfg_obj, cb_method, *key, **kwargs):
        self.config = cfg_obj
        self.cb_method = cb_method
        self.key = key
        self.kwargs = kwargs
        self._cached = None
        self._cache_identifier = None

    def _ensure_cache(self) -> VT:
        if self._cache_identifier is None or self._cache_identifier != self.config.cache_identifier:
            self._cache_identifier = self.config.cache_identifier
            self._cached = getattr(self.config, self.cb_method)(*self.key, **self.kwargs)
        return self._cached

    def __eq__(self, other) -> bool:
        if isinstance(other, _ConfigRef):
            return self.raw_value() == other.raw_value()
        else:
            return self.raw_value() == other

    def raw_value(self) -> VT:
        return self._ensure_cache()

    def is_none(self) -> bool:
        return self._ensure_cache() is None

    def __getattr__(self, item):
        c = self._ensure_cache()
        if c:
            return getattr(c, item)
        return None

    def __bool__(self) -> bool:
        return bool(self._ensure_cache())

    def __str__(self) -> str:
        return str(self._ensure_cache())

    def __int__(self) -> int:
        return int(self._ensure_cache())

    def __float__(self) -> float:
        return float(self._ensure_cache())


@injector.register("zirconium.config.ApplicationConfig", caching_strategy=CacheStrategy.GLOBAL_CACHE)
class ApplicationConfig(MutableDeepDict):

    ach: _AppConfigHooks = None

    @injector.construct
    def __init__(self, manual_init=False):
        super().__init__()
        self.log = logging.getLogger("zirconium")
        self.encoding: str = "utf-8"
        self.parsers: list[GenericParser] = [
            TomlConfigParser(),
            YamlConfigParser(),
            CfgConfigParser(),
            IniConfigParser(),
            JsonConfigParser(),
        ]
        self._secret_providers = {}
        if sp.AZURE_ENABLED:
            self._secret_providers["azure_key_vault"] = sp.azure_key_vault
        self.file_registry: dict[str, list[tuple[str | Path, int, GenericParser | None, str | None]]] = {
            "defaults": [],
            "regulars": [],
            "environment": [],
        }
        self.secrets_env_map = {}
        self.secrets_map = {}
        self.environment_map = {}
        self._default_config = {}
        self._on_load = []
        self.loaded_files = []
        self._init_flag = False
        self.cache_identifier = None
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

    def on_load(self, cb):
        self._on_load.append(cb)

    def get(self,
            *key: t.Union[str, t.Sequence[str]],
            default: DT = None,
            coerce: t.Optional[t.Union[t.Type[RT], t.Callable[[t.Any], RT]]] = None,
            blank_to_none: bool = False,
            raw: bool = False,
            raise_error: bool = False) -> t.Union[DT, RT]:
        value = super().get(*key, default=None, raise_error=raise_error)
        if blank_to_none and value == "":
            value = None
        if (not raw) and isinstance(value, str):
            value = self.resolve_environment_references(value)
        if coerce and value is not None:
            value = coerce(value)
        if value is None:
            return default
        return value

    def get_ref(self,
                *key: str,
                default: DT = None,
                coerce: t.Optional[t.Callable[[t.Any], RT]] = None,
                blank_to_none: bool = False,
                raw: bool = False,
                raise_error: bool = False) -> _ConfigRef[t.Union[DT, RT]]:
        return _ConfigRef[t.Any](self, 'get', *key, default=default, coerce=coerce, blank_to_none=blank_to_none, raw=raw, raise_error=raise_error)

    def resolve_environment_references(self, value: str) -> str:
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
                    resolved += self.parse_env_reference(ref_buffer, "")
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

    def parse_env_reference(self, name: str, default_val: DT = None) -> t.Union[str, DT]:
        if "=" in name:
            default_val = name[name.find("=") + 1:]
            name = name[0:name.find("=")]
        actual_val = self.get_env_var(name)
        return default_val if actual_val is None else actual_val

    def get_env_var(self, env_var_name: str) -> t.Optional[str]:
        if env_var_name in os.environ:
            return os.environ[env_var_name]
        elif env_var_name.lower() in os.environ:
            return os.environ[env_var_name.lower()]
        elif env_var_name.upper() in os.environ:
            return os.environ[env_var_name.upper()]
        elif env_var_name in self.secrets_env_map:
            return self.get_secret(*self.secrets_env_map[env_var_name])
        return None

    def get_secret(self, secret_path, secret_provider):
        if secret_provider not in self._secret_providers:
            self.log.warning(f"Secret provider {secret_provider} not found")
            return None
        return self._secret_providers[secret_provider](secret_path)

    def as_bytes(self,
                 *key: str | t.Sequence[str],
                 default: DT = None,
                 default_units: str = "b",
                 allow_metric: bool = False,
                 raw: bool = False) -> t.Union[float, DT]:
        val = self.get(*key, default=default, blank_to_none=True, raw=raw)
        if val is None:
            return val
        elif isinstance(val, int) or isinstance(val, float):
            return convert_to_bytes(val, default_units, not allow_metric)
        else:
            val, units = parse_for_units(str(val), 3, default_units)
            return convert_to_bytes(val, units, not allow_metric)

    def as_bytes_ref(self,
                     *key: str,
                     default: DT = None,
                     default_units: str = "b",
                     raw: bool = False) -> _ConfigRef[t.Union[float, DT]]:
        return _ConfigRef(self, 'as_bytes', *key, default=default, default_units=default_units, raw=raw)

    def as_timedelta(self,
                     *key: str | t.Sequence[str],
                     default: DT = None,
                     default_units: str = "s",
                     raw: bool = False) -> t.Union[datetime.timedelta, DT]:
        val = self.get(*key, default=default, blank_to_none=True, raw=raw)
        if val is None or isinstance(val, datetime.timedelta):
            return val
        elif isinstance(val, int) or isinstance(val, float):
            return convert_to_timedelta(val, default_units)
        else:
            val, units = parse_for_units(str(val), 2, default_units)
            return convert_to_timedelta(val, units)

    def as_timedelta_ref(self,
                         *key: t.Union[str, t.Sequence[str]],
                         default: DT = None,
                         default_units: str = "s",
                         raw: bool = False) -> _ConfigRef[t.Union[datetime.timedelta, DT]]:
        return _ConfigRef(self, 'as_timedelta', *key, default=default, default_units=default_units, raw=raw)

    def as_date(self,
                *key: t.Union[str, t.Sequence[str]],
                default: DT = None,
                raw: bool = False) -> t.Union[datetime.date, DT]:
        dt = self.get(*key, default=default, blank_to_none=True, raw=raw)
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

    def as_date_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None,
                    raw: bool = False) -> _ConfigRef[t.Union[datetime.date, DT]]:
        return _ConfigRef(self, 'as_date', *key, default=default, raw=raw)

    def as_datetime(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None,
                    tzinfo: t.Optional[datetime.tzinfo] = None,
                    raw: bool = False) -> t.Union[datetime.datetime, DT]:
        dt = self.get(*key, default=default, blank_to_none=True, raw=raw)
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

    def as_datetime_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None,
                    tzinfo: t.Optional[datetime.tzinfo] = None,
                    raw: bool = False) -> _ConfigRef[t.Union[datetime.datetime, DT]]:
        return _ConfigRef(self, 'as_datetime', *key, default=default, tzinfo=tzinfo, raw=raw)

    def as_int(self,
               *key: t.Union[str, t.Sequence[str]],
               default: DT = None,
               raw: bool = False) -> t.Union[int, DT]:
        return self.get(*key, default=default, coerce=int, blank_to_none=True, raw=raw)

    def as_int_ref(self,
                   *key: t.Union[str, t.Sequence[str]],
                   default: DT = None,
                   raw: bool = False) -> _ConfigRef[t.Union[int, DT]]:
        return _ConfigRef(self, 'as_int', *key, default=default, raw=raw)

    def as_float(self,
                 *key: t.Union[str, t.Sequence[str]],
                 default: DT = None,
                 raw: bool = False) -> t.Union[float, DT]:
        return self.get(*key, default=default, coerce=float, blank_to_none=True, raw=raw)

    def as_float_ref(self,
                     *key: t.Union[str, t.Sequence[str]],
                     default: DT = None,
                     raw: bool = False) -> _ConfigRef[t.Union[float, DT]]:
        return _ConfigRef(self, 'as_float', *key, default=default, raw=raw)

    def as_decimal(self,
                   *key: t.Union[str, t.Sequence[str]],
                   default: DT = None,
                   raw: bool = False) -> t.Union[decimal.Decimal, DT]:
        return self.get(*key, default=default, coerce=decimal.Decimal, blank_to_none=True, raw=raw)

    def as_decimal_ref(self,
                       *key: t.Union[str, t.Sequence[str]],
                       default: DT = None,
                       raw: bool = False) -> _ConfigRef[t.Union[decimal.Decimal, DT]]:
        return _ConfigRef(self, 'as_decimal', *key, default=default, raw=raw)

    def as_str(self,
               *key: t.Union[str, t.Sequence[str]],
               default: DT = None,
               raw: bool = False) -> t.Union[str, DT]:
        return self.get(*key, default=default, coerce=str, raw=raw)

    def as_str_ref(self,
                   *key: t.Union[str, t.Sequence[str]],
                   default: DT = None,
                   raw: bool = False) -> _ConfigRef[t.Union[str, DT]]:
        return _ConfigRef(self, 'as_float', *key, default=default, raw=raw)

    def as_bool(self,
                *key: t.Union[str, t.Sequence[str]],
                default: DT = None,
                raw: bool = False) -> t.Union[bool, DT]:
        return self.get(*key, default=default, raw=raw, coerce=bool)

    def as_bool_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None,
                    raw: bool = False) -> _ConfigRef[t.Union[bool, DT]]:
        return _ConfigRef(self, 'as_bool', *key, default=default, raw=raw)

    def as_path(self,
                *key: t.Union[str, t.Sequence[str]],
                default: DT = None,
                raw: bool = False) -> t.Union[Path, DT]:
        return self.get(*key, default=default, coerce=Path, blank_to_none=True, raw=raw)

    def as_path_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None,
                    raw: bool = False) -> _ConfigRef[t.Union[Path, DT]]:
        return _ConfigRef(self, 'as_path', *key, default=default, raw=raw)

    def as_set(self,
               *key: t.Union[str, t.Sequence[str]],
               default: DT = None) -> t.Union[set | DT]:
        return self.get(*key, default=default, coerce=set, blank_to_none=True, raw=True)

    def as_set_ref(self,
                   *key: t.Union[str, t.Sequence[str]],
                   default: DT = None) -> _ConfigRef[t.Union[set, DT]]:
        return _ConfigRef(self, 'as_set', *key, default=default)

    def as_list(self,
                *key: t.Union[str, t.Sequence[str]],
                default: DT = None) -> t.Union[list, DT]:
        return self.get(*key, default=default, coerce=list, blank_to_none=True, raw=True)

    def as_list_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None) -> _ConfigRef[t.Union[list, DT]]:
        return _ConfigRef[list](self, 'as_list', *key, default=default)

    def as_dict(self,
                *key: t.Union[str, t.Sequence[str]],
                default: DT = None) -> t.Union[MutableDeepDict, DT]:
        return self.get(*key, default=default, coerce=MutableDeepDict, blank_to_none=True, raw=True)

    def as_dict_ref(self,
                    *key: t.Union[str, t.Sequence[str]],
                    default: DT = None) -> _ConfigRef[t.Union[MutableDeepDict, DT]]:
        return _ConfigRef(self, 'as_dict', *key, default=default)

    def is_truthy(self,
                  *key: t.Union[str, t.Sequence[str]]) -> bool:
        if not self._init_flag:
            self.init()
        parent, k = self._navigate_to_item(*key)
        return parent is not None and k in parent and bool(parent[k])

    def set_default_encoding(self, enc: str):
        self.encoding = enc

    def register_parser(self, parser):
        self.parsers.append(parser)

    def register_secret_provider(self, name, callback):
        self._secret_providers[name] = callback

    def register_files(self,
                       search_directories: t.Iterable[t.Union[Path, t.AnyStr]],
                       files: t.Optional[t.Iterable[str]] = None,
                       default_files: t.Optional[t.Iterable[str]] = None):
        for sd in search_directories:
            sd = sd if isinstance(sd, Path) else Path(sd)
            for file in files or []:
                self.register_file(sd / file)
            for default_file in default_files or []:
                self.register_default_file(sd / default_file)

    def register_default_file(self,
                              file_path, weight=None, parser=None, encoding=None):
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

    def register_environ_map(self, env_map):
        self.environment_map.update(env_map)

    def reload_config(self):
        # We take all three locks to prevent any weird multi-threaded behaviour from happening. All writes are blocked until we are done the re-load except our own.
        with self.lock:
            with self.registry_lock:
                with self.cache_lock:
                    self._cached_gets = {}
                    self.loaded_files = []
                    self._init_flag = False
                    self.clear()
                    self.init()

    def register_secret_as_environ_var(self, secret_path, secret_provider, env_var_name):
        self.secrets_env_map[env_var_name] = (secret_path, secret_provider)

    def register_secret_config(self, secret_path, secret_provider, *target_config):
        secret_provider = secret_provider.lower()
        self.secrets_map[f"{secret_path}{secret_provider}"] = (secret_path, secret_provider, target_config)

    def init(self):
        with self.registry_lock:
            if not self._init_flag:
                new_conf = MutableDeepDict()
                new_conf.deep_update(self._default_config)
                self.file_registry["defaults"].sort(key=lambda x: x[1])
                for file, weight, parser, enc in self.file_registry["defaults"]:
                    self.load_file(new_conf, file, parser, enc)
                self.file_registry["regulars"].sort(key=lambda x: x[1])
                for file, weight, parser, enc in self.file_registry["regulars"]:
                    self.load_file(new_conf, file, parser, enc)
                self.file_registry["environment"].sort(key=lambda x: x[1])
                for env_name, weight, parser, enc in self.file_registry["environment"]:
                    env_val = self.get_env_var(str(env_name))
                    if env_val:
                        self.load_file(new_conf, env_val, parser, enc)
                for env_name, target_config in self.environment_map.items():
                    env_val = self.get_env_var(env_name)
                    if env_val is not None:
                        self.log.info(f"Setting config from environment variable {env_name}")
                        new_conf[target_config] = env_val
                    else:
                        self.log.debug(f"No environment variable set for {env_name}")
                for key in self.secrets_map:
                    spath, sprovider, target_config = self._secret_providers[key]
                    secret_val = self.get_secret(sprovider, spath)
                    if secret_val is not None:
                        self.log.info(f"Loading secret from {sprovider} {spath}")
                        new_conf[target_config] = secret_val
                self.d = new_conf.d
                self._init_flag = True
                if self.cache_identifier is None:
                    self.cache_identifier = 1
                else:
                    self.cache_identifier += 1
                for cb in self._on_load:
                    cb(self)

    def load_file(self,
                  new_conf: MutableDeepDict,
                  file_path: t.Union[str, Path],
                  parser: t.Optional[GenericParser] = None,
                  encoding: t.Optional[str] = None):
        with self.registry_lock:
            enc = (self.encoding or "utf-8") if encoding is None else encoding
            path_obj = file_path if isinstance(file_path, Path) else Path(file_path)
            path_obj = path_obj.expanduser().absolute()
            if path_obj in self.loaded_files:
                return
            if path_obj.exists():
                if parser is None:
                    for p in self.parsers:
                        if p.handles(path_obj):
                            parser = p
                            break

                if parser:
                    self.log.info(f"Loading config file {path_obj}")
                    new_conf.deep_update(parser.read_dict(path_obj, enc))
                    self.loaded_files.append(path_obj)
                else:
                    self.log.warning(f"No parser found for {path_obj}")
            else:
                self.log.info(f"No config file found at {path_obj}")

    def set_defaults(self, d):
        self._default_config.update(d)

    def load_from_dict(self, d):
        self.deep_update(d)


def test_with_config(config: dict,
                     _injector: InjectionManager | None = None):
    """Create a test fixture for ApplicationConfig (if one doesn't exist) and set a config value for it"""

    def _build_config() -> ApplicationConfig:
        conf = ApplicationConfig(manual_init=True)
        conf.set_defaults(config)
        conf.init()
        return conf

    def _inner(fn):
        im = _injector or injector
        return im.with_fixture(ApplicationConfig, _build_config)(fn)

    return _inner
