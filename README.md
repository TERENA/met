met [![Code Health](https://landscape.io/github/biancini/met/master/landscape.svg?style=flat)](https://landscape.io/github/biancini/met/master)
===

Metadata Explorer Tool is a fast way to find federations, entities and his relations through entity/federation metadata file information.

* You can find information about a entity or federation
* You can find how many and which services belong to a federation
* You can find to which federations do an entity belong
* You can find which federations or entities are part of interfederations
* You can find most federated entities.

To install this software please refer to [this documentation page](doc/source/install.rst).

To test the software you have to install selenium and use the command
```
python manage.py test tests --liveserver=localhost:9000-9300
```
