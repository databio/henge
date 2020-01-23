# Henge 

Henge is a python package that builds back-ends for generic decomposable recursive unique identifiers (or, *druids*). It is intended to be used as a building block for refget 2.0 on collections, and also potentially for other data types that need content-derived identifiers.

Henge provides 2 key advances:

- decomposing: identifiers in henge will automatically retrieve tuples. these tuples can be tailored with a simple json schema document, so that henge can be used as a back-end for arbitrary data.

- recursion: individual elements retrieved by the henge object can be tagged as recursive, which means these attributes contain their own druids. Henge can recurse through these.

## Install

Install with: `pip install --user .`


More documentation forthcoming.
