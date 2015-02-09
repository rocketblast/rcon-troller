rcon-troller
============
rcon-troller is a Python library for writing game server modifications.

* **Plugins**: rcon-troller provides a plugin environment to make it easy to write/use/mix plugins from different sources.
* **Extensible**: The aim is to create an environment that sets few restrictions.
* **Scalable**: The code uses threads and is battle tested monitoring well over 100 servers using just one listener with over 10 plugins per server.

Supported games today are Battlefield: Bad Company 2, Battlefield 3, Medal of Honor, Battlefield 4, Battlefield: Hardline.

Examples
--------
There is really no point in running rcon-troller without a plugin, so start with writing a simple plugin.
```python
from rocketblast.rcon import Plugin

class MyPlugin(Plugin):
    def __init__(self, listener):
        Plugin.__init__(self, listener)
    def destroy(self):
        pass
    def connected(self):
        pass
    def disconnected(self):
        pass
    def on_timer(self, data):
        pass
    def on_players(self, data):
        pass
    def on_revive(self, data):
        pass
    def on_pb(self, data):
        pass
    def on_load(self, data):
        pass
    def on_over(self, data):
        pass
    def on_connect(self, data):
        event, name, ea_guid = map(str, data)
        print '{name} connected'.format(name=name)
    def on_join(self, data):
        pass
    def on_part(self, data):
        pass
    def on_team(self, data):
        pass
    def on_squad(self, data):
        pass
    def on_spawn(self, data):
        pass
    def on_kill(self, data):
        pass
    def on_chat(self, data):
        pass
```

This minimal plugin will print new gamers who connect to your server.

```python
from rocketblast.rcon import Listener

Listener('uuid', '192.0.0.1', 47200, 'secret', [
    {'name': 'plugins.myplugin.MyPlugin', 'args': {}},
    ]).start()
```
This example will run your plugin on the specified server in a new thread. Run the code and check the output from your plugin when a new player joins your server.

Installation
------------
The easiest way to get started is to download the source and then run the following command:
```
python setup.py install
```

Contribute
----------
The purpose of this repository is to continue to evolve rcon-troller core, making it easier to use and support more games. If you are interested in helping with that feel free to contribute and give feedback.

### License
rcon-troller is GNU Affero GPL v3. 
