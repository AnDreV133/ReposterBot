==========================
Python JSON Config Manager
==========================

Usage
=====

config.json
-----------
.. code-block:: json

    {
        "database": {
            "password": "pass123", 
            "user": "root", 
            "name": "myDB", 
            "tables": {
                "comments": "nan", 
                "likes": "fuck it", 
                "users": "empty"
            }
            "keys": [
                "name",
                "id",
                "hash"
            ],
        }, 
        "server": {
            "port": 4444, 
            "host": "127.0.0.1"
        }
    }


test.py
-------

.. code-block:: python

    from Jconfig.config import Jconfig

    conf = Jconfig('./config.json', separator='.')

    PORT = conf.get('server.port')
    print(PORT) # 4444

    conf.set('database.tables.likes', 'hi bitch')

    conf.set('database.keys', ['md5', 'password', 'another'])

    conf.set('database.keys.2', 'hoho')
