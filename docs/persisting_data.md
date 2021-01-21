# How to persist data

In the simple case just use a Python `dict` object as `database`:

```python
seq_schema = "tests/data/sequence.yaml"
asd = "tests/data/annotated_sequence_digest.yaml"
acd = "tests/data/annotated_collection_digest.yaml"

schemas = {"sequence": yaml.safe_load(seq_schema), "asd": yaml.safe_load(asd),
            "acd": yaml.safe_load(acd)}

h = henge.Henge(database={}, schemas=schemas)

```

This keeps all database objects in memory. In case you want data persist across python sessions, you'll need to back that Dict with persistent storage. You can do this in many ways, here are two examples, using SQLite or MongoDB:

## SQLite backend

You can use an SQLite database like this

```
from sqlitedict import SqliteDict
mydict = SqliteDict('./my_db.sqlite', autocommit=True)
h = henge.Henge(mydict, schemas=schemas)
```

## MongoDB backend

If you want the data to persist, you need to connect `Henge` object to a running database instance, for example [MongoDB](https://www.mongodb.com/). Here are the example steps to do it:


1. **Start a MongoDB with docker**

```
docker run --network="host" ... mongo
```

For persistent storage, mount a folder to `/data/db`, and if that's a remote filesystem, make sure to map the user/group so the container has permissions to read/write the filesystem. Here's an example command: 

```
docker run -it --network="host" --user=854360:25014 -v /ext/qumulo/database/mongo:/data/db mongo
```

In production you can use `-p 27017:27017` instead of `network="host"`, but on a dev server, the network command is more secure because it obeys firewall rules, while the `-p` potentially opens a port despite the firewall settings.

2. **Point `Henge` to your MongoDB backend**

Naturally, you need to have relevant packages installed.  In this case (for MongoDB backend): `pymongo` and `mongodict`.

```python
import henge
schemas = {"sequence": yaml.safe_load(seq_schema), "asd": yaml.safe_load(asd),
            "acd": yaml.safe_load(acd)}

h = henge.Henge(henge.connect_mongo(), schemas=schemas)
```


