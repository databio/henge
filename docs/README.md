[![Build Status](https://travis-ci.com/databio/henge.svg?branch=master)](https://travis-ci.com/databio/henge)

# Henge 

Henge is a Python package for building data storage and retrieval interfaces for arbitrary data. Henge is based on the idea of decomposable recursive unique identifiers (or, *DRUIDs*), which are hash-based unique identifiers for data derived from the data itself. For arbitrary data with any structure, Henge can mint unique DRUIDs to identify data, store the data in a key-value database of your choice, and provide lookup functions to retrieve the data in its original structure using its druid identifier.

Henge was intended as a building block for sequence collections (see [the seqcol python package](https://github.com/refgenie/seqcol)), but has been made generic so that it can be used for data types that needs content-derived identifiers with database lookup capability.

## Install

```
pip install henge
```

## Basic use

Create a Henge object by providing a database and a data schema. The database can be a Python dict or backed by persistent storage. Data schemas are [JSON-schema](https://json-schema.org/) descriptions of data type, and can be hierarchical.

```python
schemas = ["path/to/json_schema.yaml"]
h = henge.Henge(database={}, schemas=schemas)
```

Then you insert items into the henge. Upon insert, henge returns the DRUID (*aka* digest, checksum, or unique identifier) for your object, which you can later use to retrieve it

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

## Decomposible Recursive Unique IDs (DRUIDs)

DRUIDs are simply a special type of unique identifiers that have a few nice properties. A DRUID is ultimately the result of a digest operation (such as `md5` or `sha256`) on some data. What sets DRUIDs apart from a typical digest is that, when backed by a Henge, DRUIDS are *decomposable* and *recursive*:

- decomposing: identifiers in henge will automatically retrieve tuples. These tuples can be tailored with a simple JSON schema document, so that henge can be used as a back-end for arbitrary data.

- recursion: individual elements retrieved by the henge object can be tagged as recursive, which means these attributes contain their own DRUIDs. Henge can recurse through these, which allows us to mint unique identifiers for arbitrary nested data forms.
