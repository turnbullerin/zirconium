# Zirconium

Zirconium is a powerful configuration tool for loading and using configuration in your application.

## Use Case

Zirconium abstracts away the process of loading and type-coercing configuration so that it Just Works for your 
application. For example

## Key Features

### Features

* Support for libraries to provide their own default configuration and/or configuration file locations
* Applications specify their own configuration with `@zirconium.configure` decorator
* Automatic replacement of ${ENVIRONMENT_VARIABLES} in strings
* Consistent type coercion for common data types: paths, ints, floats, decimals, bytes, lists, dicts, sets, dates, timedeltas, and datetimes
* Where dictionary-style declarations are not supported, instead use the dot syntax (e.g. "foo.bar") 
* Supports multiple file encodings 
* Extensible to other formats as needed
* Configuration is dict-like for ease-of-use in existing locations (e.g. Flask)
* Multiple files can be specified with different weights to control loading order
* Supports default vs. normal configuration file (defaults always loaded first)
* Supports thread-safe injection of the configuration into your application via autoinject
* Supports specifying default configuration for libraries in entry points `zirconium.config` and for parsers in
  `zirconium.parsers`, as well as using the `@zirconium.configure` decorator.

### Supported configuration methods

* Database tables (with SQLAlchemy installed)
* YAML (with pyyaml installed)
* TOML (with toml installed or Python >= 3.11)
* JSON
* Setuptools-like CFG files
* INI files (following the defaults of the configparser module)
* Environment variables

### Priority Order

Later items in this list will override previous items

1. Files registered with `register_default_file()`, in ascending order by `weight` (or order called)
2. Files registered with `register_file()`, in ascending order by `weight`
3. Files from environment variables registered with `register_file_from_environ()`, in ascending order by `weight`
5. Values from environment variables registered with `register_environ_var()`


## Example Usage

```python
import pathlib
import zirconium
from autoinject import injector


@zirconium.configure
def add_config(config):
  
    # Direct load configuration from dict:
    config.load_from_dict({
        "version": "0.0.1",
        "database": {
            # Load these from environment variables
            "username": "${MYAPP_DATABASE_USERNAME}",
            "password": "${MYAPP_DATABASE_PASSWORD}",
        },
        "escaped_environment_example": "$${NOT_AN_ENVIRONMENT VARIABLE",
        "preceding_dollar_sign": "$$${STOCK_PRICE_ENV_VARIABLE}",
    })
    
    # Default configuration, relative to this file, will override the above dict
    base_file = pathlib.Path(__file__).parent / ".myapp.defaults.toml"
    config.register_default_file(base_file) 
    
    # File in user home directory, overrides the defaults
    config.register_file("~/.myapp.toml")
    
    # File in CWD, will override whatever is in home
    config.register_file("./.myapp.toml")
    
    # Load a file path from environment variable, will override ALL registered files
    config.register_file_from_environ("MYAPP_CONFIG_FILE")
    
    # Load values direct from the environment, will override ALL files including those specific in environment variables
    # sets config["database"]["password"]
    config.register_environ_var("MYAPP_DATABASE_PASSWORD", "database", "password")
    # sets config["database"]["username"]
    config.register_environ_var("MYAPP_DATABASE_USERNAME", "database", "username")
    
  
# Injection example
class NeedsConfiguration:

    config: zirconium.ApplicationConfig = None

    @injector.construct
    def __init__(self):
        # you have self.config available as of here
        pass
    
    
# Method example

@injector.inject 
def with_config(config: zirconium.ApplicationConfig = None):
    print(f"Hello world, my name is {config.as_str('myapp', 'welcome_name')}")
    print(f"Database user: {config.as_str('database', 'username')}")
```

## Type Coercion Examples

```python 
import zirconium

@zirconium.configure 
def add_config(config):
    config.load_from_dict({
        "bytes_example": "5K",
        "timedelta_example": "5m",
        "date_example": "2023-05-05",
        "datetime_example": "2023-05-05T17:05:05",
        "int_example": "5",
        "float_example": "5.55",
        "decimal_example": "5.55",
        "str_example": "5.55",
        "bool_false_example": 0,
        "bool_true_example": 1,
        "path_example": "~/user/file",
        "set_example": ["one", "one", "two"],
        "list_example": ["one", "one", "two"],
        "dict_example": {
          "one": 1,
          "two": 2,
        }
    })
    

@injector.inject 
def show_examples(config: zirconium.ApplicationConfig = None):
    config.as_bytes("bytes_example")                # 5120 (int)
    config.as_timedelta("timedelta_example)         # datetime.timedelta(minutes=5)
    config.as_date("date_example")                  # datetime.date(2023, 5, 5)
    config.as_datetime("datetime_example")          # datetime.datetime(2023, 5, 5, 17, 5, 5)
    config.as_int("int_example")                    # 5 (int)
    config.as_float("float_example")                # 5.55 (float)
    config.as_decimal("decimal_example")            # decimal.Decimal("5.55")
    config.as_str("str_example")                    # "5.55"
    config.as_bool("bool_false_example")            # False (bool)
    config.as_bool("bool_true_example")             # True (bool)
    config.as_path("path_example")                  # pathlib.Path("~/user/file")
    config.as_set("set_example")                    # {"one", "two"}
    config.as_list("list_example")                  # ["one", "one", "two"]
    config.as_dict("dict_example")                  # {"one": 1, "two": 2}
    
    # Raw dicts can still be used as sub-keys, for example
    config.as_int(("dict_example", "one"))          # 1 (int)  
 
```

## Config References

In certain cases, your application might want to let the configuration be reloaded. This is possible via the 
`reload_config()` method which will reset your configuration to its base and reload all the values from the original
files. However, where a value has already been used in your program, that value will need to be updated. This leads
us to the ConfigRef() pattern which lets applications obtain a value and keep it current with the latest value loaded.
If you do not plan on reloading your configuration on-the-fly, you can skip this section.

When using the methods that end in `_ref()`, you will obtain an instance of `_ConfigRef()`. This object has a few
special properties but will mostly behave as the underlying configuration value with a few exceptions:

- `isinstance` will not work with it
- `is None` will not return True even if the configuration value is actually None (use `.is_none()` instead)

To get a raw value to work with, use `raw_value()`.

The value is cached within the `_ConfigRef()` object but this cache is invalidated whenever `reload_config()` is called.
This should reduce the work you have to do when reloading your configuration (though you may still need to call certain
methods when the configuration is reloaded).

To call a method on reload, you can add it via `config.on_load(callable)`. If `callable` needs to interact with a 
different thread or process than the one where `reload_config()` is called, it is your responsibility to manage this
communication (e.g. use `threading.Event` to notify the thread that the configuration needs to be reloaded).


## Change Log

### Version 1.2.0
- Added `as_bytes()` which will accept values like `2M` and return the value converted into bytes (e.g. `2097152`. If 
  you really want to use metric prefixes (e.g. `2MB=2000000`), you must pass `allow_metric=True` and then specify your 
  units as `2MB`. Prefixes up to exbibyte (`EiB`) are handled at the moment. You can also specify `B` for bytes or `bit` 
  for a number of bits. If no unit is specified, it uses the  `default_units` parameter, which is `B` by default. All 
  units are case-insensitive.
- Added `as_timedelta()` which will accept values like `30m` and return `datetime.timedelta(minutes=30)`. Valid units 
  are `s`, `m`, `h`, `d`, `w`, `us`, and `ms`. If no units are specified, it defaults to the `default_units` parameter
  which is `s` by default. All units are case-insensitive.
- Added a new series of methods `as_*_ref()` (and `get_ref()`) which mirror the behaviour of their counterparts not ending in `_ref()`
  except these return a `_ConfigRef()` instance instead of an actual value.
- Added a method `print_config()` which will print out the configuration to the command line.

### Version 1.1.0
- Added `as_list()` and `as_set()` which return as expected
- Type-hinting added to the `as_X()` methods to help with usage in your IDE
- Added support for `register_files()` which takes a set of directories to use and registers a set of files and default files in each.

### Version 1.0.0

- Stable release after extensive testing on my own
- Python 3.11's tomllib now supported for parsing TOML files
- Using `pymitter` to manage configuration registration was proving problematic when called from
  a different thread than where the application config object was instatiated. Replaced it with a more robust solution.
- Fixed a bug for registering default files
- Added `as_dict()` to the configuration object which returns an instance of `MutableDeepDict`.
