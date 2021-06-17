jupyter:True
# Henge tutorial

## Introduction to henge

A henge is a management layer that overlays a database. You can use henge with a variety of back-end types that support key-value pair storage, such as a simple python `dict` object, a redis database, MongoDB, SQLite, etc.

The point of the henge management layer is to automatically mint unique, data-derived identifiers, and make it easy to retrieve the data using these identifiers. When you insert an arbitrary object into the Henge, it will return a unique digest for the object, which we refer to as a DRUID. The DRUID is a cryptographic digest/hash; it behaves like a fingerprint for the item you inserted. DRUIDs are computed deterministically from the item, so they represent globally unique identifiers. If you insert the same item repeatedly, it will produce the same DRUID -- this is even true across henges, as long as they share a data schema (explained more later). You can use DRUIDs as identifiers, and you can also use them to retrieve the original item again from the henge.

To introduce you to the basic idea, let's store simple strings, and make it possible to retrieve them with their digests. You can choose the digest algorithm; we'll use `md5` for now. Henge will store the DRUID (md5 digest) and value (string) in a database, and allow retrieving the the string given its identifier.

Record the version used in this tutorial:


```python
from platform import python_version 
import henge
print("Python version: {}; henge version: {}".format(python_version(), henge.__version__))
```

```.output
Python version: 3.8.5; henge version: 0.1.0-dev

```


```python
# If you want you can turn debug text on with this command:
# logmuse.init_logger("henge", "DEBUG", devmode=True)
```

Henge defines data types using JSON-schema. Let's define a data type called `string` which is just a string, or a sequence of characters:


```python
!cat "../tests/data/string.yaml" 
```

```.output
description: "Simple schema for a string"
type: string
henge_class: mystring

```

Henge schemas are just JSON-schemas with one additional keyword: `henge_class`. For any item type that we want to digest as a separate entity in the henge, we need to cleare a `henge_class`. Here, we called the class of this simple string `mystring`. We construct a henge object that is aware of this data type like this:


```python
h = henge.Henge(database={}, schemas=["../tests/data/string.yaml"])
h
```




    Henge object. Item types: mystring



The database in this case is just an empty python dict `{}`, which is useful for testing. Insert a sequence object which will be stored in the database, which in this case is just a dictionary:


```python
digest = h.insert("TCGA", item_type="mystring")
```

Just for kicks, let's take a look at what the digest actually is:


```python
digest
```




    '45d0ff9f1a9504cf2039f89c1ffb4c32'



That digest is a globally unique identifier for the item, derived from the item itself. You can retrieve the original item using the digest:


```python
h.retrieve(digest)
```




    'TCGA'



Since the digest is deterministic, repeated attempts to insert the same item will yield the same result. This item is already in the database, so it will not take up additional storage:


```python
h.insert("TCGA", item_type="mystring")
```




    '45d0ff9f1a9504cf2039f89c1ffb4c32'



This demonstrates how to use a henge on a basic, primitive data type like a string. All the henge layer is doing is simplifying the interface to: 1) create a unique identifier automatically; 2) insert your item into the database, keyed by the unique identifier; and 3) provide an easy lookup function to get your item back.

Next, what if we have a more complicated data, like an array, or an object with named attributes? The power of henge becomes more apparent when we want to store such more complicated objects. A DRUID builds on basic value-derived identifiers by allowing the objects to be *decomposable* and *recursive*. In other words, the *value* stored in the database can have multiple elements (decomposible); and 2) each element which may, itself, be an independent value stored individually in the database (recursive). This will make more sense as we look at examples of more complicated objects next.

## Decomposing: storing arrays and multi-property objects

To demonstrate, we'll first show an example with a data type that has more than one property. Let's say we want to make a henge that stores and retrieves objects of type *Person*. We define a JSON-schema for a *Person*, which has 2 attributes: a string `name`, and an integer `age`: 



```python
!cat "../tests/data/person.yaml"                                
```

```.output
description: "Person"
type: object
henge_class: person
properties:
  name:
    type: string
    description: "String attribute"
  age:
    type: integer
    description: "Integer attribute"
required:
  - name
  
```

Notice again that we have `henge_class: person` in there. We did *not* define henge classes for the individual property elements of `name` and `age`. This means that the `Person` object will be digested, but the `name` and `age` elements will not be seperately digested -- they will only exist as elements of a Person. 

Now we will create a henge either with the schema dict object, or a path to a yaml file:


```python
import henge
person_henge = henge.Henge(database={}, schemas=["../tests/data/person.yaml"])
```

You can see which types of items your henge can process by looking at the `item_types` property:


```python
person_henge.item_types
```




    ['person']



Use `insert` to add an item to the henge, providing the object and its type. The henge will use JSON-schema to make sure the object satisfies the schema.


```python
druid1 = person_henge.insert({"name":"Pat", "age":38}, item_type="person")
print(druid1)
```

```.output
685a5a70a3d9450e42346bc36ca4ff11

```

When you insert an item into the henge, it returns the unique identifier (or, the *DRUID*) for that item. Then, you can use the unique identifier to retrieve the item from the henge.


```python
person_henge.retrieve(druid1)
```




    {'name': 'Pat', 'age': '38'}



Our schema listed `name` as a required attribute. Here's what happens if we try to insert non-conforming data:


```python
person_henge.insert({"first_name":"Pat", "age":38}, item_type="person")
```

```.output
Not valid data
Attempting to insert item: {'age': 38}
Item type: person

```

```.output
'name' is a required property

Failed validating 'required' in schema:
    {'description': 'Person',
     'henge_class': 'person',
     'properties': {'age': {'description': 'Integer attribute',
                            'type': 'integer'},
                    'name': {'description': 'String attribute',
                             'type': 'string'}},
     'recursive': [],
     'required': ['name'],
     'type': 'object'}

On instance:
    {'age': 38}

```




    False



Next, let's consider an array. Here's a quick example with array data. Once again, we must define a JSON-schema describing the data type that our henge will understand.


```python
!cat "../tests/data/simple_array.yaml"
```

```.output
description: "An array of items."
type: array
henge_class: array
items:
  type: string


```


```python
arrhenge = henge.Henge(database={}, schemas=["../tests/data/simple_array.yaml"])
```


```python
digest = arrhenge.insert(["a", "b", "c"], item_type="array")
print(digest)
```

```.output
655d1ca349985f7c611a59ab8abf74a4

```


```python
arrhenge.retrieve(digest)
```




    ['a', 'b', 'c']



We've just seen how the DRUID concept works for structured data with multiple attributes. One nice thing about this is that henge is handling all the details of the digest algorithm, which can start to get complicated once your data is more than just a single element. For example -- How do you integrate property names? How do you delimit items?  With henge, you're just using a standardized algorithm that is independent of data type.

If I were to create another henge on a different computer using the same JSON-schema, then I'm guarenteed that the same data will produce the same digest, making it possible to share these digests across servers.

Next, we'll expand into the area where henge becomes very powerful: what if the data are hierarchical, with nested objects?

## Recursion: storing structured data

Next, we'll show an example of a data type that contains other complex data types. Let's define a *Family* as an array of parents and an array of children:


```python
!cat "../tests/data/family.yaml" 
```

```.output
description: "Family"
type: object
henge_class: family
properties:
  domicile:
    type: object
    henge_class: location
    properties:
      address:
        type: string
  parents:
    type: array
    henge_class: people
    items:
      type: object
      henge_class: person
      properties:
        name:
          type: string
          description: "String attribute"
        age:
          type: integer
          description: "Integer attribute"
      required:
        - name
  children:
    type: array
    henge_class: people
    items:
      type: object
      henge_class: person
      properties:
        name:
          type: string
          description: "String attribute"
        age:
          type: integer
          description: "Integer attribute"
      required:
        - name
required:
  - parents
```

In our family object, parents are required, which is a *People* object, which is an array with one or more *Person* objects. The *children* attribute is optional, which is also a *People* object with one or more *Person* objects. Our *Family* object also has a *domicile* attribute, which is a *Location* object that has an *address* property.

Notice where we've put `henge_class` keywords in this object. Not only the top-level `family` object has a `henge_class`, but also several other properties, including `people`, `person`, and `domicile`, which are both arrays and objects. We'll see below how this type of schema will automatically create first-class database entries, with their own unique identifiers, for each of these nested data types. Therefore, you can not only retrieve `family` objects using DRUIDS, but you can also retrieve `people`, `person`, or `domicile` objects with their own DRUIDs as well. Check it out:


```python
famhenge = henge.Henge(database={}, schemas=["../tests/data/family.yaml"])
```


```python
famhenge.item_types
```




    ['family', 'location', 'people', 'person']



Now, this henge can accommodate objects that subscribe to this structure data type. Let's build a simple family object and store it in the henge:


```python
myfam = {'domicile': '',
 'parents': [{'name': 'Pat', 'age': 38}, {'name': 'Kelly', 'age': 35}],
 'children': [{'name': 'Oedipus', 'age': 2}]}
```


```python
myfam_druid = famhenge.insert(myfam, "family")
myfam_druid
```




    '516719e59dc46c9aa06c718d0436c6a6'



As before, we can retrieve the complete structured data using the digest:


```python
famhenge.retrieve(myfam_druid)
```




    {'domicile': {'address': ''},
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': [{'name': 'Oedipus', 'age': '2'}]}



Already we see that this is something useful: as before, henge is handling the algorithmic details to create your unique identifier, and it even works with these more complicated data types! You will give you the same DRUID wherever you have this particular family, for any henge that uses the same schema.

And it gets better: one of the powerful features of Henge is that, under the hood, henge is actually storing objects as separate elements, each with its own identifiers, and you can retrieve them individually. This becomes more apparent when we use the `reclimit` argument to limit the number of recursive steps when we retrieve data. If we allow no recursion, we'll pull out the digests for the *People* objects:


```python
famhenge.retrieve(myfam_druid, reclimit=0)
```




    {'domicile': 'd41d8cd98f00b204e9800998ecf8427e',
     'parents': '6a9f4378876423f7d032fc86a5eca4d1',
     'children': '98646a8b05f9e0de892e98e256097d40'}



Notice here that each of these elements has its own digest. That means we could actually retrieve just a *part* of our object using the digest from that part. For example, here's a retrieval of just the parents of this family object: 


```python
parent_digest = famhenge.retrieve(myfam_druid, reclimit=0)['parents']
print(parent_digest)
famhenge.retrieve(parent_digest)
```

```.output
6a9f4378876423f7d032fc86a5eca4d1

```




    [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}]



If there were another family with the same set of parents, it would share the data (it would not be duplicated). Back to the `reclimit` parameter, we can recurse one step further to get digests for the *Person* objects:


```python
famhenge.retrieve(myfam_druid, reclimit=1)
```




    {'domicile': {'address': ''},
     'parents': ['685a5a70a3d9450e42346bc36ca4ff11',
      '4d3433cc9446fcf5038a21b088013762'],
     'children': ['20393736960360496a40f29877ec1634']}



These identifiers can be used individually to pull individual items from the database:


```python
digest = famhenge.retrieve(myfam_druid, reclimit=1)['parents'][1]
print(digest)
famhenge.retrieve(digest)
```

```.output
4d3433cc9446fcf5038a21b088013762

```




    {'name': 'Kelly', 'age': '35'}



You can also insert the sub-components (like *People* or *Person*) directly into the database:


```python
druid1 = famhenge.insert({"name":"Pat", "age":38}, item_type="person")
druid2 = famhenge.insert({"name":"Kelly", "age":35}, item_type="person")
```


```python
famhenge.retrieve(druid1)
```




    {'name': 'Pat', 'age': '38'}



Notice here that we re-inserted an object that was already in the database; this will not duplicate anything in the database, and the same identifier is returned here as the one used when this Person was part of the Family object.


```python
print(druid2)
druid2 == digest

```

```.output
4d3433cc9446fcf5038a21b088013762

```




    True



# Advanced example

Now, we'll modify our family to introduce 2 other features: 


```python
!cat "../tests/data/family_with_pets.yaml" 
```

```.output
description: "Family"
type: object
henge_class: family
properties:
  name:
    type: string
    description: "Name of the family."
  coordinates:
    type: string
    henge_class: "recprim"
    description: "A recursive primitive"
  pets:
    type: array
    henge_class: array
    items:
      type: string
  domicile:
    type: object
    henge_class: location
    properties:
      address:
        type: string
      state:
        type: string
      city:
        type: string
  parents:
    type: array
    henge_class: people
    items:
      type: object
      henge_class: person
      properties:
        name:
          type: string
          description: "String attribute"
        age:
          type: integer
          description: "Integer attribute"
      required:
        - name
  children:
    type: array
    henge_class: people
    items:
      type: object
      henge_class: person
      properties:
        name:
          type: string
          description: "String attribute"
        age:
          type: integer
          description: "Integer attribute"
      required:
        - name
required:
  - parents
```

What's different here? First, we added an object property called `pets` that is in array. This will demonstrate that henge handles nesting of arrays and properties.

Second, we added object properties that are simple primitive `string`, either with or without `henge_class` defined: `name` is a new property without a `henge_class`, which means this will *not* be stored as a first-class object in the database with it's own identifier. The `coordinates` property, like `name` is just a simple `string` property, but the difference is that it *is* listed with a `henge_class`. Therefore, it will get a unique identifier as it's own object type in the henge. We'll see below how this shows up in our object types.


```python
import henge 
import logmuse 
pethenge = henge.Henge(database={}, schemas=["../tests/data/family_with_pets.yaml"])

myfam = {'name': "Jones",
         'domicile': { 'state': "VA", 'address':"123 Sesame St", 'city': "Charlottesville"},
         'pets': ["Sparky", "Pluto", "Max"],
         'coordinates': '30W300x-40E400x',
         'parents': [{'name': 'Pat', 'age': 38}, {'name': 'Kelly', 'age': 35}],
         'children': [{'name': 'Oedipus', 'age': 2}] }
```

Even for this complicted object with nested objects and arrays, the interface works in exactly the same way. As long as your data validates against your provided schema, just insert your object to get a globally-useful DRUID:


```python
digest = pethenge.insert(myfam, item_type="family")
print(digest)
```

```.output
a504bd32114bff42275444225dabc49d

```

And, as expected, retrieve the object in its original structure from the DRUID:


```python
pethenge.retrieve(digest)
```




    {'name': 'Jones',
     'coordinates': '30W300x-40E400x',
     'pets': ['Sparky', 'Pluto', 'Max'],
     'domicile': {'address': '123 Sesame St',
      'state': 'VA',
      'city': 'Charlottesville'},
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': [{'name': 'Oedipus', 'age': '2'}]}



Now, let's explore how the different sub-object types behave by looking at what happens when we recurse to different levels:


```python
pethenge.retrieve(digest, reclimit=0)
```




    {'name': 'Jones',
     'coordinates': '1a74f8f147bb18aff8ab572184acc191',
     'pets': 'aebd9b30e807de123c6416de045570a8',
     'domicile': '500c1ea172748123bd4e8daae0c2ff97',
     'parents': '6a9f4378876423f7d032fc86a5eca4d1',
     'children': '98646a8b05f9e0de892e98e256097d40'}



Notice here the difference between `name` and `coordinates` -- the `name` did not have a `henge_class`, so it's going to be stored in the database directly under the parent `family` digest. There's no separate digest to retrieve it as it's own entity. In contrast, `coordinates` got its own digest and can therefore be retrieved individually, re-used across data, etc:


```python
coord_digest = pethenge.retrieve(digest, reclimit=0)['coordinates']
pethenge.retrieve(coord_digest)
```




    '30W300x-40E400x'



You can see how the other elements behave with multiple layers of recursion by adjusting `reclimit`:


```python
pethenge.retrieve(digest, reclimit=1)
```




    {'name': 'Jones',
     'coordinates': '30W300x-40E400x',
     'pets': ['Sparky', 'Pluto', 'Max'],
     'domicile': {'address': '123 Sesame St',
      'state': 'VA',
      'city': 'Charlottesville'},
     'parents': ['685a5a70a3d9450e42346bc36ca4ff11',
      '4d3433cc9446fcf5038a21b088013762'],
     'children': ['20393736960360496a40f29877ec1634']}




```python
pethenge.retrieve(digest, reclimit=2)
```




    {'name': 'Jones',
     'coordinates': '30W300x-40E400x',
     'pets': ['Sparky', 'Pluto', 'Max'],
     'domicile': {'address': '123 Sesame St',
      'state': 'VA',
      'city': 'Charlottesville'},
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': [{'name': 'Oedipus', 'age': '2'}]}




```python
pethenge.retrieve(digest, reclimit=3)
```




    {'name': 'Jones',
     'coordinates': '30W300x-40E400x',
     'pets': ['Sparky', 'Pluto', 'Max'],
     'domicile': {'address': '123 Sesame St',
      'state': 'VA',
      'city': 'Charlottesville'},
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': [{'name': 'Oedipus', 'age': '2'}]}



By the time we get to `reclimit=3`, we're done recursing and we've populated the whole object from its components. Each of these henge_class objects at any level in the hierarchy can be used just as if they were top-level objects in the henge:


```python
children_digest=pethenge.retrieve(digest, reclimit=0)["children"]
print(children_digest)
pethenge.retrieve(children_digest)
```

```.output
98646a8b05f9e0de892e98e256097d40

```




    [{'name': 'Oedipus', 'age': '2'}]



## So what?

What's great about this is that you save storage space in your database for duplicate items, you can retrieve structured data of arbitrary complexity. Admittedly, the family example is a bit contrived, but imagine if your data objects have components that are repeated as elements of other objects. Instead of storing each individually, and not having knowledge about the identity relationships there, henge stores each item exactly once. You can also just grab the checksums so you know what items are present if that's what you need.


```python

```
