jupyter:True
# Henge tutorial

Henge is a Python package that builds backends for generic decomposable recursive unique identifiers (or, *DRUIDs*). It was started as building block for sequence collections (see [`seqcol`](https://github.com/refgenie/seqcol)), but can also be used for other data types that need content-derived identifiers.

## Introduction to DRUIDs

A DRUID builds on the concept of a basic key-value database with value-derived identifiers. A henge is ultimately a database that stores values, allowing them to be looked up.

In the simplest case, say we're interested in storing strings. We define an algorithm to obtain a unique identifier for the string; for example, we may take the md5 digest of the string. We then store the key (md5 digest) and value (string) in a database, and allow retrieving the the string given its identifier.

Henge builds on this basic concept by making the identifiers *decomposable* and *recursive*. In henge, the *value* in the database can represent multiple elements, which may, themselves be independent values stored individually in the database. This enables a recursive lookup of entries that adds power to the basic approach above.

## Henge schemas

Henge defines data types using JSON-schema. Let's say we want to make a henge that stores and retrieves objects of type *Person*. We define a JSON-schema for a *Person*. In our case, a person has 2 attributes: a string `name`, and an integer `age`: 



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

Now we will create a henge that understands this data type by passing the schema along with a name ("person") as a dict to the `schemas` parameter in the `Henge` constructor. You can pass either the schema dict object, or a path to a yaml file.


```python
import henge
person_henge = henge.Henge(database={}, schemas=["../tests/data/person.yaml"])
```


```python
person_henge.item_types
```




    ['person']



To enter data into this henge, we use `insert`, providing the object and its type. The henge will use JSON-schema to make sure the object satisfies the schema.


```python
druid1 = person_henge.insert({"name":"Pat", "age":38}, item_type="person")
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
Attempting to insert item: {'first_name': 'Pat', 'age': 38}
Item type: person

```

```.output
'name' is a required property

Failed validating 'required' in schema:
    {'description': 'Person',
     'properties': {'age': {'description': 'Integer attribute',
                            'type': 'integer'},
                    'name': {'description': 'String attribute',
                             'type': 'string'}},
     'required': ['name'],
     'type': 'object'}

On instance:
    {'age': 38, 'first_name': 'Pat'}

```




    False



Record the version used in this tutorial:


```python
import henge
henge.__version__
```




    '0.0.2'



## A multi-schema example

Here we'll use a more complicated example.


```python
!cat "../tests/data/family_complete.yaml" 
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
    recursive: true
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
recursive:
  - parents
  - children

```


```python
famhenge = henge.Henge(database={}, schemas=["../tests/data/family_complete.yaml"])
```

```.output
adding people
adding people

```


```python
famhenge.item_types
```




    ['family', 'location', 'people', 'person']




```python
druid1 = famhenge.insert({"name":"Pat", "age":38}, item_type="person")
druid2 = famhenge.insert({"name":"Kelly", "age":35}, item_type="person")
```


```python
druid_people = famhenge.insert([druid1, druid2], item_type="people")
```


```python
famhenge.retrieve(druid_people)
```




    [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}]




```python
famhenge.retrieve(druid_people, reclimit=0)
```




    ['685a5a70a3d9450e42346bc36ca4ff11', '4d3433cc9446fcf5038a21b088013762']




```python
family_data = {'parents': [{'name': 'Pat', 'age': 35},
  {'name': 'Kelly', 'age': 38}],
 'children': ''}
```


```python
famhenge.insert(family_data, item_type="family")
```

```.output
Not valid data
Attempting to insert item: {'parents': [{'name': 'Pat', 'age': 35}, {'name': 'Kelly', 'age': 38}], 'children': ''}
Item type: family

```

```.output
[{'name': 'Pat', 'age': 35}, {'name': 'Kelly', 'age': 38}] is not of type 'string'

Failed validating 'type' in schema['properties']['parents']:
    {'type': 'string'}

On instance['parents']:
    [{'age': 35, 'name': 'Pat'}, {'age': 38, 'name': 'Kelly'}]

```




    False



You can't do that; the way henge works, you can only insert one-level items in. You have to write a custom function to load multi-level items in.

Instead, you use the recursive druids to load the hierarchical items, like this


```python
family_data = {'parents': druid_people,
 'children': ''}
```


```python
druid_fam = famhenge.insert(family_data, item_type="family")
```


```python
famhenge.retrieve(druid_fam, reclimit=0)
```




    {'domicile': '', 'parents': '6a9f4378876423f7d032fc86a5eca4d1', 'children': ''}




```python
famhenge.retrieve(druid_fam, reclimit=1)
```




    {'domicile': '',
     'parents': ['685a5a70a3d9450e42346bc36ca4ff11',
      '4d3433cc9446fcf5038a21b088013762'],
     'children': ''}




```python
famhenge.retrieve(druid_fam, reclimit=None)
```




    {'domicile': '',
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': ''}



For our data type we can write a load family function that will handle the piecing together, allowing us to use the full hierarchicical data seamlessly


```python
def load_family(family, h):

    if "parents" in family:
        temp_digest = []
        for person in family["parents"]:
            temp_digest.append(h.insert(person, "person"))
            
        parents_digest = h.insert(temp_digest, "people")
    else:
        parents_digest = ""
        
    if "children" in family:
        temp_digest = []
        for person in family["children"]:
            temp_digest.append(h.insert(person, "person"))
            
        children_digest = h.insert(temp_digest, "people")
    else:
        children_digest = ""
    fam2 = {
        "parents": parents_digest,
        "children": children_digest
    }

    return h.insert(fam2, "family")
```


```python
family_data = {'parents': [{'name': 'Pat', 'age': 38},
  {'name': 'Kelly', 'age': 35}]}
druid_fam2 = load_family(family_data, famhenge)
```


```python
druid_fam2
```




    'f0cb45b0383532c239d48faf457a7448'




```python
druid_fam
```




    'f0cb45b0383532c239d48faf457a7448'




```python
famhenge.retrieve(druid_fam2)
```




    {'domicile': '',
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': ''}




```python
famhenge.show()
```

```.output
685a5a70a3d9450e42346bc36ca4ff11 Pat38
685a5a70a3d9450e42346bc36ca4ff11_item_type person
685a5a70a3d9450e42346bc36ca4ff11_digest_version md5
4d3433cc9446fcf5038a21b088013762 Kelly35
4d3433cc9446fcf5038a21b088013762_item_type person
4d3433cc9446fcf5038a21b088013762_digest_version md5
6a9f4378876423f7d032fc86a5eca4d1 685a5a70a3d9450e42346bc36ca4ff11	4d3433cc9446fcf5038a21b088013762
6a9f4378876423f7d032fc86a5eca4d1_item_type people
6a9f4378876423f7d032fc86a5eca4d1_digest_version md5
f0cb45b0383532c239d48faf457a7448 6a9f4378876423f7d032fc86a5eca4d1
f0cb45b0383532c239d48faf457a7448_item_type family
f0cb45b0383532c239d48faf457a7448_digest_version md5

```


```python
famhenge.retrieve(druid_fam, reclimit=None)
```




    {'domicile': '',
     'parents': [{'name': 'Pat', 'age': '38'}, {'name': 'Kelly', 'age': '35'}],
     'children': ''}



## The old way

We used to do it such that you'd have to insert each item's schema individually. You'd write a regular JSON-Schema document, and then assign it to an item type and provide these to the henge.

The challenge with this way is that the schema designer has to handle all the cognitive burden of piecing together the hierarchy of the data structure. In the new system, the schemas are loaded from one schema by adding the 'henge_class' argument, we specify the top-level objects the schema can store, all at once.

What's missing at this point is an auto-loader.


```python
schemas = {"person": "../tests/data/person.yaml",
           "people": "../tests/data/people.yaml",
           "family": "../tests/data/family.yaml"}

```


```python

```


```python
schemas
```




    {'person': '../tests/data/person.yaml',
     'people': '../tests/data/people.yaml',
     'family': '../tests/data/family.yaml'}




```python
h = henge.Henge(database={}, schemas=schemas)
```


```python
h
```




    Henge object
    Item types: person,people,family
    Schemas: {'person': {'description': 'Person', 'type': 'object', 'henge_class': 'person', 'properties': {'name': {'type': 'string', 'description': 'String attribute'}, 'age': {'type': 'integer', 'description': 'Integer attribute'}}, 'required': ['name']}, 'people': {'description': 'People', 'type': 'array', 'items': {'type': 'object', 'properties': {'name': {'type': 'string', 'description': 'String attribute'}, 'age': {'type': 'integer', 'description': 'Integer attribute'}}, 'required': ['name']}}, 'family': {'description': 'Family', 'type': 'object', 'properties': {'parents': {'type': 'string', 'description': 'array attribute'}, 'children': {'type': 'string'}}, 'required': ['parents'], 'recursive': ['parents', 'children']}}




```python
druid = h.insert({"name":"Pat", "age":35}, item_type="person")
```


```python
druid
```




    '975eee5a7a58f09a8bfa0f9af84e4c0e'




```python
druid2 = h.insert({"name":"Kelly", "age":38}, item_type="person")
```
