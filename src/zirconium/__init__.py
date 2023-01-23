from .config import ApplicationConfig
from .parsers import JsonConfigParser, IniConfigParser, YamlConfigParser, TomlConfigParser, CfgConfigParser, DbConfigParser
from .utils import _config_decorator as configure

__version__ = "1.0.0"
