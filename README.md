# Henge

[![Build Status](https://travis-ci.com/databio/henge.svg?branch=master)](https://travis-ci.com/databio/henge)

Henge is a Python package for building data storage and retrieval interfaces for arbitrary data. Henge is based on the idea of **decomposable recursive unique identifiers (DRUIDs)**, which are hash-based unique identifiers for data derived from the data itself. For arbitrary data with any structure, Henge can mint unique DRUIDs to identify data, store the data in a key-value database of your choice, and provide lookup functions to retrieve the data in its original structure using its DRUID identifier.

Henge was intended as a building block for [sequence collections](https://github.com/refgenie/seqcol), but is generic enough to use for any data type that needs content-derived identifiers with database lookup capability.

## Install

```
pip install henge
```

## Quick Start

Create a Henge object by providing a database and a data schema. The database can be a Python dict or backed by persistent storage. Data schemas are [JSON-schema](https://json-schema.org/) descriptions of data types, and can be hierarchical.

```python
import henge

schemas = ["path/to/json_schema.yaml"]
h = henge.Henge(database={}, schemas=schemas)
```

Insert items into the henge. Upon insert, henge returns the DRUID (digest/checksum/unique identifier) for your object:

```python
druid = h.insert({"name": "Pat", "age": 38}, item_type="person")
```

Retrieve the original object using the DRUID:

```python
h.retrieve(druid)
# {'age': '38', 'name': 'Pat'}
```

## Tutorial

For a comprehensive walkthrough covering basic types, arrays, nested objects, and advanced features, see the [tutorial notebook](docs/tutorial.ipynb).

## What are DRUIDs?

DRUIDs are a special type of unique identifiers with two powerful properties:

- **Decomposable**: Identifiers in henge automatically retrieve structured data (tuples, arrays, objects). The structure is defined by a JSON schema, so henge can be used as a back-end for arbitrary data types.

- **Recursive**: Individual elements retrieved by henge can be tagged as recursive, meaning these attributes contain their own DRUIDs. Henge can recurse through these, allowing you to mint unique identifiers for arbitrary nested data structures.

A DRUID is ultimately the result of a digest operation (such as `md5` or `sha256`) on some data. Because DRUIDs are computed deterministically from the item, they represent globally unique identifiers. If you insert the same item repeatedly, it will produce the same DRUID -- this is true across henges as long as they share a data schema.

## Persisting Data

### In-memory (default)

Use a Python `dict` as the database for testing or ephemeral use:

```python
h = henge.Henge(database={}, schemas=schemas)
```

### SQLite backend

For persistent storage with SQLite:

```python
from sqlitedict import SqliteDict

mydict = SqliteDict('./my_db.sqlite', autocommit=True)
h = henge.Henge(mydict, schemas=schemas)
```

Requires: `pip install sqlitedict`

### MongoDB backend

For production use with MongoDB:

1. **Start MongoDB with Docker:**

```bash
docker run --network="host" mongo
```

For persistent storage, mount a volume to `/data/db`:

```bash
docker run -it --network="host" -v /path/to/data:/data/db mongo
```

2. **Connect henge to MongoDB:**

```python
import henge

h = henge.Henge(henge.connect_mongo(), schemas=schemas)
```

Requires: `pip install pymongo mongodict`
