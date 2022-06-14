# Zirconium

Zirconium is a powerful configuration tool for loading and using configuration in your application.

## Key Features

### Features

* Support for libraries to provide their own default configuration and/or configuration file locations
* Applications specify their own configuration with `@zirconium.configure` decorator
* Automatic replacement of ${ENVIRONMENT_VARIABLES} in strings
* Consistent type coercion for common data types: paths, ints, floats, decimals, dates, and datetimes
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
* TOML (with toml installed)
* JSON
* Setuptools-like CFG files
* INI files (following the defaults of the configparser module)
* Environment variables
* The keyring module

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
    
    # Load value from keyring, equivalent to config["database"]["password"] = keyring.get_password("db_service", "db_user")
    config.register_keyring_var("db_service", "db_user", "database", "password")
    
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

```
