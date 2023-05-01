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
        config.set_defaults({
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

    def test_get_ref(self):
        config = zirconium.ApplicationConfig(True)
        config.set_defaults({
            1: "one"
        })
        config.init()
        r = config.get_ref(1)
        self.assertIsInstance(r, zirconium.config._ConfigRef)
        self.assertEqual(r.raw_value(), "one")
        self.assertEqual(r.raw_value(), "one")
        config.load_from_dict({
            1: "two"
        })
        self.assertEqual(r.raw_value(), "one")
        config.reload_config()
        config.load_from_dict({
            1: "two"
        })
        self.assertEqual(r.raw_value(), "two")

    def test_clear(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            1: "one",
            2: "two"
        })
        self.assertTrue(1 in config)
        self.assertTrue(2 in config)
        self.assertEqual(config[1], "one")
        self.assertEqual(config[2], "two")
        config.reload_config()
        self.assertFalse(1 in config)
        self.assertFalse(2 in config)
        config.load_from_dict({
            1: "new_one"
        })
        self.assertTrue(1 in config)
        self.assertFalse(2 in config)
        self.assertEqual(config[1], "new_one")

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

    def test_bytes_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "raw": 512,
            "raw_str": "512",
            "for_def": 512,
            "bits": "512bit",
            "bytes": "512b",
            "kib": "2kib",
            "mib": "2mib",
            "gib": "2gib",
            "tib": "2tib",
            "pib": "2pib",
            "eib": "2eib",
            "k": "2K",
            "m": "2M",
            "g": "2G",
            "t": "2T",
            "p": "2P",
            "e": "2E",
            "kb": "2KB",
            "mb": "2MB",
            "gb": "2GB",
            "tb": "2TB",
            "pb": "2PB",
            "eb": "2EB",
            "no": "2WB",
            "very_no": "Foobar"
        })
        self.assertEqual(config.as_bytes("raw"), 512)
        self.assertEqual(config.as_bytes("for_def", default_units="kib"), 512 * 1024)
        self.assertEqual(config.as_bytes("raw_str"), 512)
        self.assertEqual(config.as_bytes("bits"), 64.0)
        self.assertEqual(config.as_bytes("bytes"), 512)
        self.assertEqual(config.as_bytes("kib"), 1024 * 2)
        self.assertEqual(config.as_bytes("mib"), 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("gib"), 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("tib"), 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("pib"), 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("eib"), 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("k"), 1024 * 2)
        self.assertEqual(config.as_bytes("m"), 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("g"), 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("t"), 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("p"), 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("e"), 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("kb"), 1024 * 2)
        self.assertEqual(config.as_bytes("mb"), 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("gb"), 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("tb"), 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("pb"), 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("eb"), 1024 * 1024 * 1024 * 1024 * 1024 * 1024 * 2)
        self.assertEqual(config.as_bytes("kb", allow_metric=True), 1000 * 2)
        self.assertEqual(config.as_bytes("mb", allow_metric=True), 1000 * 1000 * 2)
        self.assertEqual(config.as_bytes("gb", allow_metric=True), 1000 * 1000 * 1000 * 2)
        self.assertEqual(config.as_bytes("tb", allow_metric=True), 1000 * 1000 * 1000 * 1000 * 2)
        self.assertEqual(config.as_bytes("pb", allow_metric=True), 1000 * 1000 * 1000 * 1000 * 1000 * 2)
        self.assertEqual(config.as_bytes("eb", allow_metric=True), 1000 * 1000 * 1000 * 1000 * 1000 * 1000 * 2)

    def test_timedelta_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "def": 234,
            "def_min": 234,
            "test_s": "23s",
            "test_m": "23m",
            "test_h": "23h",
            "test_d": "23d",
            "test_w": "23w",
            "test_w1s": "23 w",
            "test_w3s": "   23     w  ",
            "test_us": "23us",
            "test_ms": "23ms",
            "test_str_no": "23",
            "test_err": "23n",
            "test_big_err": "foobar"
        })
        self.assertEqual(config.as_timedelta("def"), datetime.timedelta(seconds=234))
        self.assertEqual(config.as_timedelta("def_min", default_units="m"), datetime.timedelta(minutes=234))
        self.assertEqual(config.as_timedelta("test_s"), datetime.timedelta(seconds=23))
        self.assertEqual(config.as_timedelta("test_m"), datetime.timedelta(minutes=23))
        self.assertEqual(config.as_timedelta("test_h"), datetime.timedelta(hours=23))
        self.assertEqual(config.as_timedelta("test_d"), datetime.timedelta(days=23))
        self.assertEqual(config.as_timedelta("test_w"), datetime.timedelta(weeks=23))
        self.assertEqual(config.as_timedelta("test_w1s"), datetime.timedelta(weeks=23))
        self.assertEqual(config.as_timedelta("test_w3s"), datetime.timedelta(weeks=23))
        self.assertEqual(config.as_timedelta("test_us"), datetime.timedelta(microseconds=23))
        self.assertEqual(config.as_timedelta("test_ms"), datetime.timedelta(milliseconds=23))
        self.assertEqual(config.as_timedelta("test_str_no"), datetime.timedelta(seconds=23))
        self.assertRaises(ValueError, config.as_timedelta, "test_err")
        self.assertRaises(ValueError, config.as_timedelta, "test_big_err")


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

    def test_int_ref_coerce(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "str": "1234",
            "str_int": 1234,
            "int": 12,
            "falsy": 0,
            "bad": "modern general",
            "nope": None,
            "blank": "",
        })
        self.assertEqual(config.as_int_ref("str"), config.as_int_ref("str_int"))
        self.assertNotEqual(config.as_int_ref("str"), config.as_int_ref("int"))
        self.assertEqual(config.as_int_ref("str"), 1234)
        self.assertEqual(config.as_int_ref("int"), 12)
        self.assertIsNone(config.as_int_ref("nope").raw_value())
        self.assertIsNone(config.as_int_ref("blank").raw_value())
        self.assertTrue(config.as_int_ref("nope").is_none())
        self.assertTrue(config.as_int_ref("blank").is_none())
        self.assertFalse(config.as_int_ref("str").is_none())
        self.assertRaises(ValueError, config.as_int_ref("bad").raw_value)
        self.assertTrue(config.as_int_ref("int"))
        self.assertFalse(config.as_int_ref("falsy"))

    def test_cache_by_type(self):
        config = zirconium.ApplicationConfig(True)
        config.load_from_dict({
            "int": 12,
        })
        self.assertEqual(config.as_str("int"), "12")
        self.assertEqual(config.as_int("int"), 12)

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
