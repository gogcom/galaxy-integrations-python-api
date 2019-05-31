# GOG Galaxy - Community Integration - Python API

This document is still work in progress.

## Basic Usage

Basic implementation:

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

Plugin should be deployed with manifest:
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

## Development

Install required packages:
```bash
pip install -r requirements.txt
```

Run tests:
```bash
pytest
```
## Methods Documentation
TODO

## Legal Notice

By integrating or attempting to integrate any applications or content with or into GOG Galaxy® 2.0. you represent that such application or content is your original creation (other than any software made available by GOG) and/or that you have all necessary rights to grant such applicable rights to the relevant community integration to GOG and to GOG Galaxy 2.0 end users for the purpose of use of such community integration and that such community integration comply with any third party license and other requirements including compliance with applicable laws.
