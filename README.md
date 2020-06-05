[![Build Status](https://travis-ci.com/databio/henge.svg?branch=master)](https://travis-ci.com/databio/henge)

# Henge 

Henge is a Python package that builds backends for generic decomposable recursive unique identifiers (or, *DRUIDs*). It is intended to be used as a building block for refget 2.0 on collections (see [`refget-py`](https://github.com/databio/refget-py) package), and also for other data types that need content-derived identifiers.

**Henge provides 2 key advances:**

- decomposing: identifiers in henge will automatically retrieve tuples. These tuples can be tailored with a simple JSON schema document, so that henge can be used as a back-end for arbitrary data.

- recursion: individual elements retrieved by the henge object can be tagged as recursive, which means these attributes contain their own DRUIDs. Henge can recurse through these.

## Install

Install with: `pip install --user .`


## Use
*For full henge package documentation please refer [API documentation page](./docs/api.md)*

`Henge` constructor requires 2 arguments: 

1. a `dict` of schemas to validate inserted object aginst
2. a backend for data storage 

### No data persistence

In the simple case just use a Python `dict` object as `database`:

```python
schemas = {"sequence": yaml.safe_load(seq_schema), "asd": yaml.safe_load(asd),
            "acd": yaml.safe_load(acd)}

h = henge.Henge(database={}, schemas=schemas)

```

### Data persistence

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


### Stick stuff in it

Henge will return the druid (*aka* digest, checksum, unique identifier) for your object, which you can later use to retrieve it

```python
object = ...  # produce the object of the type your henge understands
druid = h.insert(..., item_type=...)
```

You have to tell the henge what type of item you're inserting, which corresponds to one of the schemas you have used when instantiating the henge.

### Retrieve stuff from it

```python
h.retrieve(druid)
```
