# GOG Galaxy Integrations Python API

This Python library allows to easily build community integrations for various gaming platforms with GOG Galaxy 2.0.

- refer to our <a href='https://galaxy-integrations-python-api.readthedocs.io'>documentation</a>

## Features

Each integration in GOG Galaxy 2.0 comes as a separate Python script, and is launched as a separate process, that which needs to communicate with main instance of GOG Galaxy 2.0.

The provided features are:

- multistep authorisation using a browser built into GOG Galaxy 2.0
- support for GOG Galaxy 2.0 features:
    - importing owned and detecting installed games
    - installing and launching games
    - importing achievements and game time
    - importing friends lists and statuses
    - importing friends recomendations list
    - receiving and sending chat messages
- cache storage

## Basic usage

Eeach integration should inherit from the :class:`~galaxy.api.plugin.Plugin` class. Supported methods like :meth:`~galaxy.api.plugin.Plugin.get_owned_games` should be overwritten - they are called from the GOG Galaxy client in the appropriate times.
Each of those method can raise exceptions inherited from the :exc:`~galaxy.api.jsonrpc.ApplicationError`.
Communication between an integration and the client is also possible with the use of notifications, for example: :meth:`~galaxy.api.plugin.Plugin.update_local_game_status`.

```python
import sys
from galaxy.api.plugin import Plugin, create_and_run_plugin
from galaxy.api.consts import Platform

class PluginExample(Plugin):
    def __init__(self, reader, writer, token):
        super().__init__(
            Platform.Generic, # Choose platform from available list
            "0.1", # Version
            reader,
            writer,
            token
        )

    # implement methods
    async def authenticate(self, stored_credentials=None):
        pass

def main():
    create_and_run_plugin(PluginExample, sys.argv)

# run plugin event loop
if __name__ == "__main__":
    main()
```

## Deployment

The client has a built-in Python 3.7 interpreter, so the integrations are delivered as python modules.
In order to be found by GOG Galaxy 2.0 an integration folder should be placed in [lookup directory](#deploy-location). Beside all the python files, the integration folder has to contain [manifest.json](#deploy-manifest) and all third-party dependencies. See an [examplary structure](#deploy-structure-example).

### <a name="deploy-location"></a> Lookup directory:
- Windows:

    `%localappdata%\GOG.com\Galaxy\plugins\installed`

- macOS:

    `~/Library/Application Support/GOG.com/Galaxy/plugins/installed`

### <a name="deploy-manifest"></a> Manifest
Obligatory JSON file to be placed in a integration folder.

```json
{
    "name": "Example plugin",
    "platform": "generic",
    "guid": "UNIQUE-GUID",
    "version": "0.1",
    "description": "Example plugin",
    "author": "Name",
    "email": "author@email.com",
    "url": "https://github.com/user/galaxy-plugin-example",
    "script": "plugin.py"
}
```
| property      | description |
|---------------|---|
| `guid`        |   |
| `description` |   |
| `url`         |   |
| `script`      | path of the entry point module, relative to the integration folder |

### Dependencies
All third-party packages (packages not included in Python 3.7 standard library) should be deployed along with plugin files. Use the folowing command structure:

```pip install DEP --target DIR --implementation cp --python-version 37```

For example plugin that uses *requests* has structure as follows:

<a name="deploy-structure-example"></a>
```bash
installed
└── my_integration
    ├── galaxy
    │   └── api
    ├── requests
    │   └── ...
    ├── plugin.py
    └── manifest.json
```

## Legal Notice

By integrating or attempting to integrate any applications or content with or into GOG Galaxy 2.0 you represent that such application or content is your original creation (other than any software made available by GOG) and/or that you have all necessary rights to grant such applicable rights to the relevant community integration to GOG and to GOG Galaxy 2.0 end users for the purpose of use of such community integration and that such community integration comply with any third party license and other requirements including compliance with applicable laws.
