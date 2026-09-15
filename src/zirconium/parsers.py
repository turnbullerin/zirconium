import logging
import json
import configparser
import importlib.util
import pathlib
import sys
import typing as t

from zirconium.utils import MutableDeepDict



import abc
class GenericParser(abc.ABC):
    @abc.abstractmethod
    def handles(self, path: pathlib.Path) -> bool:
        raise NotImplementedError

    @abc.abstractmethod
    def read_dict(self, path: pathlib.Path, encoding: str) -> t.Mapping:
        raise NotImplementedError



class YamlConfigParser(GenericParser):

    def __init__(self):
        self.package_installed = importlib.util.find_spec("yaml") is not None

    def handles(self, path: pathlib.Path) -> bool:
        return self.package_installed and path.name.lower().endswith(".yaml")

    def read_dict(self, path: pathlib.Path, encoding: str) -> t.Mapping:
        import yaml
        with open(path, "r", encoding=encoding) as h:
            obj = yaml.safe_load(h)
            if isinstance(obj, dict):
                return obj
            logging.getLogger(__name__).warning("File {} did not contain a valid YAML dictionary".format(path))
            return {}


class TomlConfigParser(GenericParser):

    def __init__(self):
        self.package_lib = None
        if sys.version_info[0] == 3 and sys.version_info[1] >= 11:
            self.package_lib = "core"
        elif importlib.util.find_spec("toml") is not None:
            self.package_lib = "third-party"

    def handles(self, path: pathlib.Path) -> bool:
        return self.package_lib is not None and path.name.lower().endswith(".toml")

    def read_dict(self, path: pathlib.Path, encoding: str) -> t.Mapping:
        if self.package_lib == "core":
            import tomllib
        elif self.package_lib == "third-party":
            import toml as tomllib
        else:
            return {}
        with open(path, "r", encoding=encoding) as h:
            return tomllib.loads(h.read())


class JsonConfigParser(GenericParser):

    def handles(self, path: pathlib.Path) -> bool:
        return path.name.lower().endswith(".json")

    def read_dict(self, path: pathlib.Path, encoding: str) -> t.Mapping:
        with open(path, "r", encoding=encoding) as h:
            data = h.read()
            if data == "":
                logging.getLogger(__name__).warning("File {} did not contain a valid JSON dictionary".format(path))
                return {}
            obj = json.loads(data)
            if isinstance(obj, dict):
                return obj
            logging.getLogger(__name__).warning("File {} did not contain a valid JSON dictionary".format(path))
            return {}


class IniConfigParser(GenericParser):

    def __init__(self, global_section=None):
        self.global_section = global_section if global_section else 'DEFAULT'

    def handles(self, path: pathlib.Path) -> bool:
        return path.name.lower().endswith(".ini")

    def read_dict(self, path: pathlib.Path, encoding: str) -> t.Mapping:
        p = configparser.ConfigParser(default_section=self.global_section)
        with open(path, "r", encoding=encoding) as h:
            p.read_file(h)
            return {s: p[s] for s in p.sections()}


class CfgConfigParser(IniConfigParser):

    def __init__(self):
        super().__init__("global")

    def handles(self, path: pathlib.Path):
        return path.name.lower().endswith(".cfg")


class DbConfigParser:

    def __init__(self):
        self.package_installed = importlib.util.find_spec("sqlalchemy") is not None
        pass

    def handles(self, path):
        if not self.package_installed:
            return False
        if "://" not in path:
            return False
        import sqlalchemy
        import sqlalchemy.exc
        try:
            conn_string, table, key_col, val_col = self._split_path(path)
            u = sqlalchemy.engine.make_url(conn_string)
            return u.get_dialect() is not None
        except TypeError:
            return False
        except ValueError:
            return False
        except sqlalchemy.exc.ArgumentError:
            return False

    def read_dict(self, path, encoding: str):
        import sqlalchemy
        import sqlalchemy.sql
        conn_string, table, key_col, val_col = self._split_path(path)
        engine = sqlalchemy.create_engine(conn_string)
        metadata = sqlalchemy.MetaData()
        metadata.reflect(bind=engine)
        if table not in metadata.tables:
            logging.getLogger(__name__).warning("Table {} does not exist".format(table))
            return {}
        t = metadata.tables[table]
        if not hasattr(t.c, key_col):
            logging.getLogger(__name__).warning("Table {} does not have key column {}".format(table, key_col))
            return {}
        if not hasattr(t.c, val_col):
            logging.getLogger(__name__).warning("Table {} does not have value column {}".format(table, val_col))
            return {}
        k = getattr(t.c, key_col)
        v = getattr(t.c, val_col)
        with engine.connect() as conn:
            q = t.select().with_only_columns(k, v).order_by(sqlalchemy.sql.expression.func.length(k))
            d = MutableDeepDict()
            for row in conn.execute(q).fetchall():
                d[row[0]] = row[1]
            return d

    def _split_path(self, path):
        # mysql+pymysql://scott:tiger@localhost/foo/schema.table/col1/col2
        qs = ""
        if "?" in path:
            qs = path[path.find("?"):]
            path = path[:path.find("?")]
        pieces = path.split("/")
        if len(pieces) < 4:
            raise ValueError("Invalid path")
        return "/".join(pieces[:-3]) + qs, pieces[-3], pieces[-2], pieces[-1]
