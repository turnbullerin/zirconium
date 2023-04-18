import unittest
import datetime
import logging
from pathlib import Path

import zirconium

TEST_PATHS = {
    "ascii_path": r"C:\my\ascii.txt",
    "cyrillic_path": r"C:\my\fileЧ.txt",
    "arabic_path": r"C:\my\fileص.txt",
    "latin_path": r"C:\my\fileÉ.txt",
    "greek_path": r"C:\my\fileΨ.txt",
    "traditional_chinese_path": r"C:\my\file碼.txt",
    "simplified_chinese_path": r"C:\my\file响.txt",
    "korean_path": r"C:\my\file탇.txt",
    "japanese_path": r"C:\my\file語.txt",
}


class TestYamlFiles(unittest.TestCase):

    def test_basic_file(self):
        path = Path(__file__).parent / "example_configs/basic.yaml"
        handler = zirconium.YamlConfigParser()
        self.assertTrue(handler.handles(path.name))
        config = handler.read_dict(path, "ascii")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["one"], "a")
        self.assertEqual(config["two"], 2)
        self.assertEqual(config["three"], "three")
        self.assertEqual(config["four"], " four five ")
        self.assertEqual(config["five"], datetime.date(2020, 1, 1))
        self.assertEqual(config["six"], 6.66)
        self.assertIsInstance(config["seven"], dict)
        self.assertEqual(len(config["seven"]), 2)
        self.assertIsInstance(config["twelve"], list)
        self.assertEqual(config["seventeen"], datetime.datetime(2020, 1, 1, 1, 2, 3))
        self.assertEqual(config["blank"], "")
        self.assertIsNone(config["none"])

    def test_blank_file(self):
        path = Path(__file__).parent / "example_configs/blank.yaml"
        handler = zirconium.YamlConfigParser()
        # suppress error output
        lvl = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        config = handler.read_dict(path, "ascii")
        logging.getLogger().setLevel(lvl)
        self.assertIsInstance(config, dict)
        self.assertEqual(len(config), 0)
        self.assertLogs("zirconium.parsers")

    def test_utf8(self):
        path = Path(__file__).parent / "example_configs/utf-8.yaml"
        handler = zirconium.YamlConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        config = handler.read_dict(path, "utf-8")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])

    def test_utf16be(self):
        path = Path(__file__).parent / "example_configs/utf-16-be.yaml"
        handler = zirconium.YamlConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "utf-8")
        config = handler.read_dict(path, "utf-16-be")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])


class TestTomlFiles(unittest.TestCase):

    def test_basic_file(self):
        path = Path(__file__).parent / "example_configs/basic.toml"
        handler = zirconium.TomlConfigParser()
        self.assertTrue(handler.handles(path.name))
        config = handler.read_dict(path, "ascii")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["one"], "a")
        self.assertEqual(config["two"], 2)
        self.assertEqual(config["three"], "three")
        self.assertEqual(config["four"], " four five ")
        self.assertEqual(config["five"], datetime.date(2020, 1, 1))
        self.assertEqual(config["six"], 6.66)
        self.assertIsInstance(config["seven"], dict)
        self.assertEqual(len(config["seven"]), 2)
        self.assertIsInstance(config["twelve"], list)
        self.assertEqual(config["seventeen"], datetime.datetime(2020, 1, 1, 1, 2, 3))
        self.assertEqual(config["blank"], "")

    def test_utf8(self):
        path = Path(__file__).parent / "example_configs/utf-8.toml"
        handler = zirconium.TomlConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        config = handler.read_dict(path, "utf-8")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])

    def test_utf16be(self):
        path = Path(__file__).parent / "example_configs/utf-16-be.toml"
        handler = zirconium.TomlConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "utf-8")
        config = handler.read_dict(path, "utf-16-be")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])

    def test_blank_file(self):
        path = Path(__file__).parent / "example_configs/blank.toml"
        handler = zirconium.TomlConfigParser()
        # suppress error output
        lvl = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        config = handler.read_dict(path, "ascii")
        logging.getLogger().setLevel(lvl)
        self.assertIsInstance(config, dict)
        self.assertEqual(len(config), 0)
        self.assertLogs("zirconium.parsers")


class TestJsonFiles(unittest.TestCase):

    def test_basic_file(self):
        path = Path(__file__).parent / "example_configs/basic.json"
        handler = zirconium.JsonConfigParser()
        self.assertTrue(handler.handles(path.name))
        config = handler.read_dict(path, "ascii")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["one"], "a")
        self.assertEqual(config["two"], 2)
        self.assertEqual(config["three"], "three")
        self.assertEqual(config["four"], " four five ")
        self.assertEqual(config["five"], "2020-01-01")
        self.assertEqual(config["six"], 6.66)
        self.assertIsInstance(config["seven"], dict)
        self.assertEqual(len(config["seven"]), 2)
        self.assertIsInstance(config["twelve"], list)
        self.assertEqual(config["seventeen"], "2020-01-01T01:02:03Z")

    def test_utf8(self):
        path = Path(__file__).parent / "example_configs/utf-8.json"
        handler = zirconium.JsonConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        config = handler.read_dict(path, "utf-8")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])

    def test_utf16be(self):
        path = Path(__file__).parent / "example_configs/utf-16-be.json"
        handler = zirconium.JsonConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "utf-8")
        config = handler.read_dict(path, "utf-16-be")
        self.assertEqual(len(config), 9)
        for key in TEST_PATHS:
            self.assertEqual(config[key], TEST_PATHS[key])

    def test_blank_file(self):
        path = Path(__file__).parent / "example_configs/blank.json"
        handler = zirconium.JsonConfigParser()
        # suppress error output
        lvl = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        config = handler.read_dict(path, "ascii")
        logging.getLogger().setLevel(lvl)
        self.assertIsInstance(config, dict)
        self.assertEqual(len(config), 0)
        self.assertLogs("zirconium.parsers")

    def test_invalid_file(self):
        path = Path(__file__).parent / "example_configs/invalid.json"
        handler = zirconium.JsonConfigParser()
        # suppress error output
        lvl = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        config = handler.read_dict(path, "ascii")
        logging.getLogger().setLevel(lvl)
        self.assertIsInstance(config, dict)
        self.assertEqual(len(config), 0)
        self.assertLogs("zirconium.parsers")


class TestConfigFiles(unittest.TestCase):

    def test_basic_file(self):
        path = Path(__file__).parent / "example_configs/basic.cfg"
        handler = zirconium.CfgConfigParser()
        self.assertTrue(handler.handles(path.name))
        config = handler.read_dict(path, "ascii")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["test"]["one"], "a")
        self.assertEqual(config["test"]["two"], '2')
        self.assertEqual(config["test"]["three"], "three")
        self.assertEqual(config["test"]["four"], "four five")
        self.assertEqual(config["test"]["five"], "2020-01-01")
        self.assertEqual(config["test"]["six"], '6.66')
        self.assertEqual(config["test"]["twelve"], "[13,14,15,16]")
        self.assertEqual(config["test"]["seventeen"], "2020-01-01T01:02:03Z")
        self.assertEqual(config["test"]["twenty"], "20")

    def test_blank_file(self):
        path = Path(__file__).parent / "example_configs/blank.cfg"
        handler = zirconium.CfgConfigParser()
        # suppress error output
        lvl = logging.getLogger().level
        logging.getLogger().setLevel(logging.ERROR)
        config = handler.read_dict(path, "ascii")
        logging.getLogger().setLevel(lvl)
        self.assertIsInstance(config, dict)
        self.assertEqual(len(config), 0)
        self.assertLogs("zirconium.parsers")


class TestIniFiles(unittest.TestCase):

    def test_basic_file(self):
        path = Path(__file__).parent / "example_configs/basic.ini"
        handler = zirconium.IniConfigParser()
        self.assertTrue(handler.handles(path.name))
        config = handler.read_dict(path, "ascii")
        self.assertIsInstance(config, dict)
        self.assertEqual(config["test"]["one"], "a")
        self.assertEqual(config["test"]["two"], '2')
        self.assertEqual(config["test"]["three"], "three")
        self.assertEqual(config["test"]["four"], "four five")
        self.assertEqual(config["test"]["five"], "2020-01-01")
        self.assertEqual(config["test"]["six"], '6.66')
        self.assertEqual(config["test"]["twelve"], "[13,14,15,16]")
        self.assertEqual(config["test"]["seventeen"], "2020-01-01T01:02:03Z")
        self.assertEqual(config["test"]["twenty"], "20")

    def test_utf8(self):
        path = Path(__file__).parent / "example_configs/utf-8.ini"
        handler = zirconium.IniConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        config = handler.read_dict(path, "utf-8")
        self.assertEqual(len(config["section"]), 9)
        for key in TEST_PATHS:
            self.assertEqual(config["section"][key], TEST_PATHS[key])

    def test_utf16be(self):
        path = Path(__file__).parent / "example_configs/utf-16-be.ini"
        handler = zirconium.IniConfigParser()
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "ascii")
        self.assertRaises(UnicodeDecodeError, handler.read_dict, path, "utf-8")
        config = handler.read_dict(path, "utf-16-be")
        self.assertEqual(len(config["section"]), 9)
        for key in TEST_PATHS:
            self.assertEqual(config["section"][key], TEST_PATHS[key])


class TestDBConfig(unittest.TestCase):

    def test_basic_db(self):
        p = Path(__file__).parent / "example_configs/basic.db"
        path = "sqlite:///{}/config/key/value".format(str(p.absolute()).replace("\\", "\\\\"))
        handler = zirconium.DbConfigParser()
        self.assertTrue(handler.handles(path))
        d = handler.read_dict(path, "ascii")
        self.assertTrue(len(d), 2)
        self.assertTrue("one" in d)
        self.assertEqual(d["one"], '1')
        #self.assertTrue(("two", "three") in d)
        #self.assertEqual(d["two", "three"], "3")

    def test_bad_table(self):
        p = Path(__file__).parent / "example_configs/basic.db"
