import unittest
import datetime
import decimal
import os
from pathlib import Path

import zirconium


class TestConfig(unittest.TestCase):

    def test_one_file(self):
        path = Path(__file__).parent / "example_configs/basic.yaml"
        config = zirconium.ApplicationConfig(True)
        config.register_file(path)
        config.init()
        self.assertTrue("one" in config)
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

    def test_two_files(self):
        path = Path(__file__).parent / "example_configs/basic.yaml"
        path2 = Path(__file__).parent / "example_configs/override.toml"
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "base": "one"
        })
        config.register_file(path)
        config.register_file(path2)
        config.init()
        self.assertEqual(config["base"], "one")
        self.assertTrue("one" in config)
        self.assertEqual(config["one"], "b")
        self.assertEqual(config["two"], 3)
        self.assertEqual(config["three"], "three")
        self.assertEqual(config["four"], " four five ")
        self.assertEqual(config["five"], datetime.date(2020, 1, 1))
        self.assertEqual(config["six"], 6.66)
        self.assertIsInstance(config["seven"], dict)
        self.assertEqual(len(config["seven"]), 2)
        self.assertIsInstance(config["twelve"], list)
        self.assertEqual(config["seventeen"], datetime.datetime(2020, 1, 1, 1, 2, 3))

    def test_environment_replacement(self):
        config = zirconium.ApplicationConfig(True)
        os.environ["VAR_NAME"] = "var"
        os.environ["lower_var"] = "var2"
        os.environ["${INNER}"] = "inner"
        os.environ["}end"] = "end"
        config.load_from_dict({
            "simple_replace": "${VAR_NAME}",
            "no_replace": "$${VAR_NAME}",
            "complex_replace": "$$$$${VAR_NAME}",
            "complex_noreplace": "$$$${VAR_NAME}",
            "default_use": "${VAR_NAME_2=test}",
            "no_end": "${VAR_NAME_NO_END",
            "suffix_replace": "${VAR_NAME} VAR_NAME",
            "prefix_replace": "VAR_NAME  ${VAR_NAME}",
            "middle_replace": "VN ${VAR_NAME} VN",
            "lower_var": "${LOWER_VAR}",
            "upper_var": "${var_name}",
            "complex_inner": r"${${INNER\}}",
            "weird_bracket": r"${\}end}",
            "weird_bracket_default": r"${\}end2=bar}"
        })
        self.assertEqual(config["simple_replace"], "var")
        self.assertEqual(config["default_use"], "test")
        self.assertEqual(config["complex_replace"], "$$var")
        self.assertEqual(config["complex_noreplace"], "$${VAR_NAME}")
        self.assertEqual(config["no_replace"], "${VAR_NAME}")
        self.assertEqual(config["no_end"], "${VAR_NAME_NO_END")
        self.assertEqual(config["lower_var"], "var2")
        self.assertEqual(config["upper_var"], "var")
        self.assertEqual(config["suffix_replace"], "var VAR_NAME")
        self.assertEqual(config["middle_replace"], "VN var VN")
        self.assertEqual(config["prefix_replace"], "VAR_NAME  var")
        self.assertEqual(config["weird_bracket"], "end")
        self.assertEqual(config["complex_inner"], "inner")
        self.assertEqual(config["weird_bracket_default"], "bar")

    def test_list_access(self):
        path = Path(__file__).parent / "example_configs/basic.yaml"
        config = zirconium.ApplicationConfig(True)
        config.register_file(path)
        config.init()
        self.assertEqual(config[("one",)], "a")
        self.assertEqual(config[("seven", "eight", "nine")], "nine")
        self.assertTrue(("seven", "eight") in config)
        self.assertFalse(("seven", "nine") in config)
        self.assertFalse(("test", "two") in config)
        config[("test", "two")] = "test three"
        self.assertTrue(("test", "two") in config)
        self.assertEqual(config[("test", "two")], "test three")
        self.assertEqual(config["test", "two"], "test three")
        self.assertEqual(config.get("test", "two"), "test three")
        del config["test", "two"]
        self.assertFalse(("test", "two") in config)

    def test_integer_index(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            1: "one"
        })
        self.assertTrue(1 in config)
        self.assertFalse(2 in config)
        self.assertEqual(config[1], "one")

    def test_len(self):
        config = zirconium.ApplicationConfig(True)
        self.assertEqual(len(config), 0)
        config.load_from_dict({
            "one": 1,
            "two": 2,
            "three": {
                "four": 4
            }
        })
        self.assertEqual(len(config), 3)

    def test_iter(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "one": 1,
            "two": 2,
            "three": {
                "four": 4
            }
        })
        lst = [x for x in config]
        self.assertTrue("one" in lst)
        self.assertTrue("two" in lst)
        self.assertTrue("three" in lst)
        self.assertFalse("four" in lst)

    def test_deep_update(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "one": 1,
            "two": 2,
            "three": {
                "four": 4
            }
        })
        self.assertTrue("one" in config)
        self.assertTrue("two" in config)
        self.assertTrue("three" in config)
        self.assertTrue(("three", "four") in config)
        self.assertFalse("four" in config)
        config.deep_update({
            "one": 11,
            "three": {
                "four": 44,
                "five": 55,
            },
            "six": 66
        })
        self.assertEqual(config["one"], 11)
        self.assertEqual(config["three"]["four"], 44)
        self.assertEqual(config["three"]["five"], 55)
        self.assertEqual(config["six"], 66)
        self.assertEqual(config["two"], 2)

    def test_update(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "one": 1,
            "two": 2,
            "three": {
                "four": 4,
                "seven": 7,
            }
        })
        config.update({
            "one": 11,
            "three": {
                "four": 44,
                "five": 55,
            },
            "six": 66
        })
        self.assertEqual(config["one"], 11)
        self.assertEqual(config["three"]["four"], 44)
        self.assertEqual(config["three"]["five"], 55)
        self.assertFalse("seven" in config["three"])
        self.assertEqual(config["six"], 66)
        self.assertEqual(config["two"], 2)

    def test_get(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "one": 1
        })
        self.assertEqual(config["one"], 1)
        self.assertRaises(ValueError, config.__getitem__, 'two')
        self.assertIsNone(config.get("two"))
        self.assertEqual(config.get("three", default=3), 3)
        self.assertRaises(ValueError, config.get, "four", raise_error=True)

    def test_dict_load(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "one": {
                "two": "three"
            }
        })
        self.assertTrue("one" in config)
        self.assertTrue(("one" ,"two") in config)
        self.assertEqual(config["one", "two"], "three")

    def test_int_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "str": "1234",
            "int": 12,
            "bad": "modern general",
            "nope": None,
            "blank": "",
        })
        self.assertEqual(config.as_int("str"), 1234)
        self.assertEqual(config.as_int("int"), 12)
        self.assertIsNone(config.as_int("nope"))
        self.assertIsNone(config.as_int("blank"))
        self.assertRaises(ValueError, config.as_int, "bad")

    def test_float_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "int": 123,
            "str_int": "1234",
            "str_float": "12.34",
            "float": 12.34,
            "exp": "1.1e3",
            "decimal": decimal.Decimal("12.34"),
            "bad": "modern general",
            "nope": None,
            "blank": "",
        })
        self.assertEqual(config.as_float("int"), 123.0)
        self.assertEqual(config.as_float("str_int"), 1234.0)
        self.assertEqual(config.as_float("str_float"), 12.34)
        self.assertEqual(config.as_float("float"), 12.34)
        self.assertEqual(config.as_float("exp"), 1100.0)
        self.assertEqual(config.as_float("decimal"), 12.34)
        self.assertIsNone(config.as_float("nope"))
        self.assertIsNone(config.as_float("blank"))
        self.assertRaises(ValueError, config.as_float, "bad")

    def test_decimal_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "int": 123,
            "str_int": "1234",
            "str_float": "12.34",
            "exp": "1.1e3",
            "decimal": decimal.Decimal("12.34"),
            "bad": "modern general",
            "nope": None,
            "blank": "",
        })
        self.assertEqual(config.as_decimal("int"), decimal.Decimal("123.0"))
        self.assertEqual(config.as_decimal("str_int"), decimal.Decimal("1234.0"))
        self.assertEqual(config.as_decimal("str_float"), decimal.Decimal("12.34"))
        self.assertEqual(config.as_decimal("decimal"), decimal.Decimal("12.34"))
        self.assertEqual(config.as_float("exp"), decimal.Decimal("1100"))
        self.assertIsNone(config.as_decimal("nope"))
        self.assertIsNone(config.as_decimal("blank"))
        self.assertRaises(decimal.InvalidOperation, config.as_decimal, "bad")

    def test_bool_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "zero": 0,
            "blank": "",
            "not_blank": "modern general",
            "true": True,
            "false": False,
            "one": 1,
            "positive": 512,
            "negative": -1,
            "nope": None,
            "empty_list": [],
            "empty_tuple": tuple(),
            "empty_set": set(),
            "empty_dict": dict(),
        })
        self.assertFalse(config.as_bool("zero"))
        self.assertFalse(config.as_bool("blank"))
        self.assertFalse(config.as_bool("false"))
        self.assertFalse(config.as_bool("nope"))
        self.assertFalse(config.as_bool("empty_list"))
        self.assertFalse(config.as_bool("empty_tuple"))
        self.assertFalse(config.as_bool("empty_set"))
        self.assertFalse(config.as_bool("empty_dict"))
        self.assertTrue(config.as_bool("not_blank"))
        self.assertTrue(config.as_bool("true"))
        self.assertTrue(config.as_bool("one"))
        self.assertTrue(config.as_bool("not_blank"))
        self.assertTrue(config.as_bool("positive"))
        self.assertTrue(config.as_bool("negative"))

    def test_date_coerce(self):
        config = zirconium.ApplicationConfig(True)
        est = datetime.timezone(-datetime.timedelta(hours=5), "EST")
        config.load_from_dict({
            "blank": "",
            "nope": None,
            "iso_str": "2020-01-01",
            "iso_dt_str": "2020-01-01 01:02:03",
            "date_obj": datetime.date(2020, 1, 1),
            "datetime_obj": datetime.datetime(2020, 1, 1, 0, 0, 0),
            "datetimetz_obj": datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=est)
        })
        self.assertIsNone(config.as_date("blank"))
        self.assertIsNone(config.as_date("nope"))
        self.assertEqual(config.as_date("iso_str"), datetime.date(2020, 1, 1))
        self.assertEqual(config.as_date("iso_dt_str"), datetime.date(2020, 1, 1))
        self.assertEqual(config.as_date("date_obj"), datetime.date(2020, 1, 1))
        self.assertEqual(config.as_date("datetime_obj"), datetime.date(2020, 1, 1))
        self.assertEqual(config.as_date("datetimetz_obj"), datetime.date(2020, 1, 1))

    def test_datetime_coerce(self):
        config = zirconium.ApplicationConfig(True)
        est = datetime.timezone(-datetime.timedelta(hours=5), "EST")
        config.load_from_dict({
            "blank": "",
            "nope": None,
            "iso_str": "2020-01-01",
            "iso_dt_str": "2020-01-01 01:02:03",
            "date_obj": datetime.date(2020, 1, 1),
            "datetime_obj": datetime.datetime(2020, 1, 1, 1, 2, 3),
            "datetimetz_obj": datetime.datetime(2020, 1, 1, 1, 2, 3, tzinfo=est)
        })
        self.assertIsNone(config.as_datetime("blank"))
        self.assertIsNone(config.as_datetime("nope"))
        self.assertEqual(config.as_datetime("iso_str"), datetime.datetime(2020, 1, 1))
        self.assertEqual(
            config.as_datetime("iso_str", tzinfo=est),
            datetime.datetime(2020, 1, 1, tzinfo=est)
        )
        self.assertEqual(config.as_datetime("iso_dt_str"), datetime.datetime(2020, 1, 1, 1, 2, 3))
        self.assertEqual(
            config.as_datetime("iso_dt_str", tzinfo=est),
            datetime.datetime(2020, 1, 1, 1, 2, 3, tzinfo=est)
        )
        self.assertEqual(config.as_datetime("date_obj"), datetime.datetime(2020, 1, 1))
        self.assertEqual(
            config.as_datetime("date_obj", tzinfo=est),
            datetime.datetime(2020, 1, 1, tzinfo=est)
        )
        self.assertEqual(config.as_datetime("datetime_obj"), datetime.datetime(2020, 1, 1, 1, 2, 3))
        self.assertEqual(
            config.as_datetime("datetime_obj", tzinfo=est),
            datetime.datetime(2020, 1, 1, 1, 2, 3, tzinfo=est)
        )
        self.assertEqual(config.as_datetime("datetimetz_obj"), datetime.datetime(2020, 1, 1, 1, 2, 3, tzinfo=est))
