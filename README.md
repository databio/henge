# Henge 

Henge is a python package that builds back-ends for generic decomposable recursive unique identifiers (or, *druids*). It is intended to be used as a building block for refget 2.0 on collections, and also for other data types that need content-derived identifiers.

Henge provides 2 key advances:

- decomposing: identifiers in henge will automatically retrieve tuples. These tuples can be tailored with a simple json schema document, so that henge can be used as a back-end for arbitrary data.

- recursion: individual elements retrieved by the henge object can be tagged as recursive, which means these attributes contain their own druids. Henge can recurse through these.

## Install

Install with: `pip install --user .`


More documentation forthcoming.


## Use

### Start a MongoDB with docker

```
docker run --network="host" ... mongo
```

For persistent storage, mount a folder to `/data/db`, and if that's a remote filesystem, make sure to map the user/group so the container has permissions to read/write the filesystem. Here's an example command: 

```
docker run -it --network="host" --user=854360:25014 -v /ext/qumulo/database/mongo:/data/db mongo
```

In production you can use `-p 27017:27017` instead of `network="host"`, but on a dev server, the network command is more secure because it obeys firewall rules, while the `-p` potentially opens a port despite the firewall settings.

### Build a henge interface to your MongoDB back-end


```
import henge
backend = henge.MongoDict(host='localhost', port=27017, database='my_dict',
                        collection='store')

schemas = {"sequence": yaml.safe_load(seq_schema), "asd": yaml.safe_load(asd),
            "acd": yaml.safe_load(acd)}

h = henge.Henge(backend, schemas=schemas)
```


### Stick stuff in it

Henge will return the druid (*aka* digest, checksum, unique identifier) for your object, which you can later use to retrieve it

```
object = ...  # produce the object of the type your henge understands
druid = h.insert(..., item_type=...)
```

You have to tell the henge what type of item you're inserting, which corresponds to one of the schemas you have used when instantiating the henge.

### Retrieve stuff from it

```
h.retrieve(druid)
```
