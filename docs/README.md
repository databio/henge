[![Build Status](https://travis-ci.com/databio/henge.svg?branch=master)](https://travis-ci.com/databio/henge)

# Henge 

Henge is a Python package that builds backends for generic decomposable recursive unique identifiers (or, *DRUIDs*). It was started as building block for sequence collections (see [`seqcol`](https://github.com/refgenie/seqcol)), but can also be used for other data types that need content-derived identifiers.

Henge provides a way to store arbitrary data, defined with JSON-schema, and uses object-derived unique identifiers to retrieve the data. Henge provides 2 key advances:

- decomposing: identifiers in henge will automatically retrieve tuples. These tuples can be tailored with a simple JSON schema document, so that henge can be used as a back-end for arbitrary data.

- recursion: individual elements retrieved by the henge object can be tagged as recursive, which means these attributes contain their own DRUIDs. Henge can recurse through these.

## Install

```
pip install henge
```

## Basic use

Create a Henge object by providing a database and a data schema. The database can be a Python dict or backed by persistent storage. Data schemas are JSON-schema formatted descriptions of data type, and can be hierarchical.

```python
schemas = ...
h = henge.Henge(database={}, schemas=schemas)
```

Then you insert items into the henge. Upon insert, henge returns the druid (*aka* digest, checksum, unique identifier) for your object, which you can later use to retrieve it

```python
object = ...  # produce the object of the type your henge understands
druid = h.insert(..., item_type=...)
```

You have to tell the henge what type of item you're inserting, which corresponds to one of the schemas you have used when instantiating the henge.

Finally, you can retrieve the original object from the henge using the DRUID identifier:

```python
h.retrieve(druid)
```

For more detailed example, consult the [tutorial](tutorial.md).