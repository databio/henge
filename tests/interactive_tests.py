import henge

from platform import python_version 

print("Python version: {}; henge version: {}".format(python_version(), henge.__version__))

!cat "tests/data/string.yaml" 

h = henge.Henge(database={}, schemas=["tests/data/string.yaml"])
h
digest = h.insert("TCGA", item_type="mystring")
digest
h.retrieve(digest)
h.retrieve2(digest)
h.retrieve3(digest)

person_henge = henge.Henge(database={}, schemas=["tests/data/person.yaml"])

druid1 = person_henge.insert({"name":"Pat", "age":38}, item_type="person")
print(druid1)


person_henge.retrieve(druid1)
person_henge.retrieve2(druid1)
person_henge.retrieve3(druid1)


arrhenge = henge.Henge(database={}, schemas=["tests/data/simple_array.yaml"])

digest = arrhenge.insert(["a", "b", "c"], item_type="array")
print(digest)

arrhenge.retrieve(digest)
arrhenge.retrieve2(digest)
arrhenge.retrieve3(digest)


import henge
famhenge = henge.Henge(database={}, schemas=["tests/data/family.yaml"])
myfam = {'domicile': '',
 'parents': [{'name': 'Pat', 'age': 38}, {'name': 'Kelly', 'age': 35}],
 'children': [{'name': 'Oedipus', 'age': 2}]}


myfam_druid = famhenge.insert(myfam, "family")
myfam_druid

famhenge.retrieve(myfam_druid)
famhenge.retrieve2(myfam_druid)
famhenge.retrieve3(myfam_druid)

famhenge.retrieve3(myfam_druid, reclimit=3)


from henge import Henge
import logmuse
logmuse.init_logger("henge", "DEBUG", devmode=True)

x = {"string_attr": "12321%@!", "integer_attr": 2}
type_key = "test_item"
h = Henge(database={}, schemas=["tests/data/schema.yaml"])
d = h.insert(x, item_type=type_key)
d
h.retrieve(d)
x

hi = Henge(database={}, schemas=["tests/data/inherent.yaml"])
d = hi.insert(x, item_type=type_key)
d
hi.retrieve(d)
x

schema = hi.schemas[type_key]

import henge
henge.select_inherent_properties(x, hi.schemas[type_key])

henge.select_inherent_properties(x, h.schemas[type_key])


select_inherent_properties(x, h.schemas[type_key])
schema = h.schemas[type_key]





def select_inherent_properties(item: dict, schema: dict) -> dict:
    if schema["type"] == "object":
        item_inherent = {}
        if "inherent" in schema and schema["inherent"]:
            for k in schema["inherent"]:
                item_inherent[k] = item[k]
                del item[k]
            return {"inherent": item_inherent, "external": item}
        else:
        	return {"inherent": item, "external": None}
    else:
        return {"inherent": item, "external": None}
