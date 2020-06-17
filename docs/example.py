
def load_family(family):



    if "parents" in family:
        parent_digests = []
        for parent in family["parents"]:
            parent_digest = parent_digest.append(h.insert(parent, "person"))
        parents_digest = h.insert(family["parents"], "people")
    else:
        parents_digest = ""

    if "children" in family:
        children_digest = h.insert(family["children"], "people")
    else:
        children_digest = ""

    fam2 = {
        "parents": parents_digest,
        "children": children_digest
    }


    return h.insert(fam2, "family")




if fs['type'] == 'object':
    for p in fs['properties']:?
    print


import copy
def split_schema(schema, name=None):
    slist = {}
    # base case
    if schema['type'] not in ['object', 'array']:
        print(schema)
        if name:
            slist[name] = schema
        elif 'henge_class' in schema:
            slist[schema['henge_class']] = schema
        print("returning slist: ", slist)
        return slist
    else:
        if schema['type'] == 'object':
            if 'henge_class' in schema:
                schema_copy = copy.deepcopy(schema)
                print("adding", schema_copy['henge_class'])
                henge_class = schema_copy['henge_class']
                del schema_copy['henge_class']
                for p in schema_copy['properties']:
                    if schema_copy['properties'][p]['type'] in ['object', 'array']:
                        schema_copy['properties'][p] = {'type': "string"}
                # del schema_copy['properties']
                slist[henge_class] = schema_copy

            for p in schema['properties']:
                schema_sub = schema['properties'][p]
                print("checking property:", p)
                slist.update(split_schema(schema['properties'][p]))

        if schema['type'] == 'array':
            print("found array")
            if 'henge_class' in schema:
                schema_copy = copy.deepcopy(schema)
                print("adding", schema_copy['henge_class'])
                henge_class = schema_copy['henge_class']
                del schema_copy['henge_class']
                schema_copy['items'] = {'type': "string"}
                if 'recursive' in schema_copy:
                    schema_copy['items']['recursive'] = True
                # schema_copy['items']['type'] = "string"
                # if 'properties' in schema_copy['items']:
                #     del schema_copy['items']['properties']
                slist[henge_class] = schema_copy

            schema_sub = schema['items']
            print("checking item.")
            slist.update(split_schema(schema_sub))
    return slist


druid = h2.insert({"name":"Joe", "age":35}, item_type="person")
druid_people = h2.insert([{'digest':druid}, {'digest':druid2}], item_type="people")