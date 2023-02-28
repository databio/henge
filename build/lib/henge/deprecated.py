
    def retrieveOld(self, druid, reclimit=None, raw=False):

        try:
            item_type = self.database[druid + ITEM_TYPE]
        except:
            _LOGGER.debug(f"Item type not saved in database for {druid}")
            raise NotFoundException(druid)
            
        # _LOGGER.debug("item_type: {}".format(item_type))
        # _LOGGER.debug("henge_to_query: {}".format(henge_to_query))

        schema = self.schemas[item_type] #"type" in schema and 
        # string = druid
        _LOGGER.debug("Got druid to retrieve: {} / item_type: {} / schema: {}".format(
            druid, item_type, schema))

        if schema["type"] == "array":
            string = self.lookup(druid, item_type)
            _LOGGER.debug("Lookup/array/Recursive: {}; Schema: {}".format(string, schema))
            splitstr = string.split(DELIM_ITEM)
            # if self.flexible_digests:
            #     pass
            #     item_name = splitstr.pop(0)
            if isinstance(reclimit, int) and reclimit == 0:  
                return splitstr
            if 'henge_class' in schema['items']:
                _LOGGER.debug("Henge classed array: {}; Schema: {}".format(string, schema))
                if isinstance(reclimit, int):
                    reclimit = reclimit - 1                
                return [self.retrieve(substr, reclimit) for substr in splitstr]
            else:
                return splitstr
        elif schema["type"] == "object":
            string = self.lookup(druid, item_type)
            attr_array = string.split(DELIM_ATTR)
            if self.flexible_digests:
                keys = attr_array[::2]  # evens
                vals = attr_array[1::2]  # odds
                item_reconstituted = dict(zip(keys,vals))    
            else:
                item_reconstituted = dict(zip(schema['properties'].keys(),
                                          attr_array))
            # I think this part needs to be removed... it's based on the
            # previous 'recursive' for arrays, which went away...
            # but actually these may be added in by me, so nevermind.
            if 'recursive' in schema:
                if isinstance(reclimit, int) and reclimit == 0:
                    _LOGGER.debug("Lookup/obj/Recursive: {}; Schema: {}".format(string, schema))
                    return item_reconstituted
                else:
                    if isinstance(reclimit, int):
                        reclimit = reclimit - 1
                    for recursive_attr in schema['recursive']:                    
                        if recursive_attr in item_reconstituted \
                                and item_reconstituted[recursive_attr] != "":
                            item_reconstituted[recursive_attr] = self.retrieve(
                                item_reconstituted[recursive_attr],
                                reclimit,
                                raw)                
            return item_reconstituted
        else: # It must be a primitive type
            # but it could be a primitive (string) that represents something to lookup,
            # or something not-to-lookup (or already looked up)
            _LOGGER.debug("Lookup/prim: {}; Schema: {}".format(druid, schema))
            # return string
            if 'henge_class' in schema and self.schemas[schema['henge_class']]['type'] in ['object', 'array']:
                if isinstance(reclimit, int) and reclimit == 0:
                    _LOGGER.debug("Lookup/prim/Recursive-skip: {}; Schema: {}".format(string, schema))
                    string = self.lookup(druid, item_type)
                    return string
                else:
                    if isinstance(reclimit, int):
                        reclimit = reclimit - 1
                    _LOGGER.debug("Lookup/prim/Recursive: {}; Schema: {}".format(druid, schema))
                    return self.retrieve(druid, reclimit, raw)
            else:
                string = self.lookup(druid, item_type)
                _LOGGER.debug("Lookup/prim/Non-recursive: {}; Schema: {}".format(string, schema))
                return string #self.retrieve(string, reclimit, raw)      

        # try:
        #     string = henge_to_query.database[druid]
        # except KeyError:
        #     raise NotFoundException(druid)

        # return reconstruct_item(string, schema, reclimit)

   def retrieve2(self, druid, reclimit=None, raw=False):
        """
        Retrieve an item given a digest

        :param str druid: The Decomposable recursive unique identifier (DRUID), or
            digest that uniquely identifies that item to retrieve.
        :param int reclimit: Recursion limit. Set to None for no limit (default).
        :param bool raw: Return the value as a raw, henge-delimited string, instead
            of processing into a mapping. Default: False.
        """
        def reconstruct_item(string, schema, reclimit):
            if "type" in schema and schema["type"] == "array":
                _LOGGER.debug("Lookup/array/Recursive: {}; Schema: {}".format(string, schema))
                splitstr = string.split(DELIM_ITEM)
                # if self.flexible_digests:
                #     pass
                #     item_name = splitstr.pop(0)
                if 'henge_class' in schema['items'] and schema['items']['type'] not in ["object", "array"]:
                    _LOGGER.debug("Henge classed array: {}; Schema: {}".format(string, schema))
                    return "ASDF"
                    return [reconstruct_item(self.henges[item_type].database[substr], schema["items"], reclimit)
                        for substr in splitstr]
                else:
                    return [reconstruct_item(substr, schema["items"], reclimit)
                        for substr in splitstr]
            elif schema["type"] == "object":
                attr_array = string.split(DELIM_ATTR)
                if self.flexible_digests:
                    keys = attr_array[::2]  # evens
                    vals = attr_array[1::2]  # odds
                    item_reconstituted = dict(zip(keys,vals))    
                else:
                    item_reconstituted = dict(zip(schema['properties'].keys(),
                                              attr_array))
                # I think this part needs to be removed... it's based on the
                # previous 'recursive' for arrays, which went away...
                # but actually these may be added in by me, so nevermind.
                if 'recursive' in schema:
                    if isinstance(reclimit, int) and reclimit == 0:
                        _LOGGER.debug("Lookup/obj/Recursive: {}; Schema: {}".format(string, schema))
                        return item_reconstituted
                    else:
                        if isinstance(reclimit, int):
                            reclimit = reclimit - 1
                        for recursive_attr in schema['recursive']:                    
                            if item_reconstituted[recursive_attr] \
                                    and item_reconstituted[recursive_attr] != "":
                                item_reconstituted[recursive_attr] = self.retrieve(
                                    item_reconstituted[recursive_attr],
                                    reclimit,
                                    raw)                
                return item_reconstituted
            else: # it must be a primitive
                # but it could be a primitive (string) that represents something to lookup,
                # or something not-to-lookup (or already looked up)
                _LOGGER.debug("Lookup/prim: {}; Schema: {}".format(string, schema))
                # return string
                if 'henge_class' in schema and self.schemas[schema['henge_class']]['type'] in ['object', 'array']:
                    if isinstance(reclimit, int) and reclimit == 0:
                        _LOGGER.debug("Lookup/prim/Recursive-skip: {}; Schema: {}".format(string, schema))
                        return string
                    else:
                        if isinstance(reclimit, int):
                            reclimit = reclimit - 1
                        _LOGGER.debug("Lookup/prim/Recursive: {}; Schema: {}".format(string, schema))
                        return self.retrieve(string, reclimit, raw)
                else:
                    _LOGGER.debug("Lookup/prim/Non-recursive: {}; Schema: {}".format(string, schema))
                    return string

        # This requires the database to have __iter__ defined...and it scrolls through
        # not a great way, take it out! 2021-01 NS
        # I'll instead do a try block
        # if not druid + ITEM_TYPE in self.database:
            # raise NotFoundException(druid)

        try:
            item_type = self.database[druid + ITEM_TYPE]
        except:
            _LOGGER.debug(f"Item type not saved in database for {druid}")
            raise NotFoundException(druid)
            
        try:
            henge_to_query = self.henges[item_type]
        except:
            _LOGGER.debug("No henges available for this item type")
            raise NotFoundException(druid)
        # _LOGGER.debug("item_type: {}".format(item_type))
        # _LOGGER.debug("henge_to_query: {}".format(henge_to_query))
        try:
            string = henge_to_query.database[druid]
        except KeyError:
            raise NotFoundException(druid)

        schema = self.schemas[item_type]
        _LOGGER.debug("Got druid to retrieve: {} / item_type: {} / schema: {}".format(
            druid, item_type, schema))
        return reconstruct_item(string, schema, reclimit)



Part of: _insert_flat

        def safestr(item, x):
            try:
                return str(item[x])
            except (ValueError, TypeError, KeyError):
                return ""



        def build_attr_string(item, schema, item_name=None):
            if "type" in schema and schema["type"] == "array":
                if self.flexible_digests:
                    return DELIM_ITEM.join([build_attr_string(x, schema['items'])
                                        for x in item])
                else:
                    return DELIM_ITEM.join([build_attr_string(x, schema['items'])
                                        for x in item])
            elif schema["type"] == "object" and 'properties' in schema:
                if self.flexible_digests:
                    # flexible schema
                    keys_to_include = sorted([x for x in item.keys() if x in list(schema['properties'].keys())])
                    return DELIM_ATTR.join([DELIM_ATTR.join([k, safestr(item, k)]) for k in keys_to_include])

                else:
                    # fixed schema
                    return DELIM_ATTR.join([safestr(item, x) for x in
                                        list(schema['properties'].keys())])
            else: #assume it's a primitive
                if self.flexible_digests:
                    return item
                    attr_string = DELIM_ATTR.join([item_name, item])
                    return attr_string
                else:
                    return item