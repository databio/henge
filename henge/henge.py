""" An interface to a database back-end for DRUIDs """

import copy
import hashlib
import jsonschema
import logging
import logmuse
import os
import sys
import yacman
import yaml

from ubiquerg import VersionInHelpParser

from . import __version__
from .const import *

_LOGGER = logging.getLogger(__name__)

class NotFoundException(Exception):
    """Raised when a digest is not found"""
    def __init__(self, m):
        self.message = "{} not found in database".format(m)
    def __str__(self):
        return self.message


def md5(seq):
    return hashlib.md5(seq.encode()).hexdigest()


class Henge(object):
    def __init__(self, database, schemas, henges=None, checksum_function=md5):
        """
        A user interface to insert and retrieve decomposable recursive unique
        identifiers (DRUIDs).

        :param dict database: Dict-like lookup database for sequences and
            hashes.
        :param list schemas: One or more jsonschema schemas describing the
            data types stored by this Henge
        :param dict henges: One or more henge objects indexed by object name for
            remote storing of items.
        :param function(str) -> str checksum_function: Default function to
            handle the digest of the serialized items stored in this henge.
        """
        self.database = database
        self.checksum_function = checksum_function
        self.digest_version = "md5"

        if isinstance(schemas, dict):
            _LOGGER.debug("Using old dict schemas")
            populated_schemas = {}
            for schema_key, schema_value in schemas.items():
                if isinstance(schema_value, str):
                    populated_schemas[schema_key] = yacman.load_yaml(schema_value)
            self.schemas = populated_schemas
        else:
            populated_schemas = []
            for schema_value in schemas:
                if isinstance(schema_value, str):
                    if os.path.isfile(schema_value):
                        populated_schemas.append(yacman.load_yaml(schema_value))
                    else:
                        populated_schemas.append(yaml.safe_load(schema_value))
            split_schemas = {}
            for s in populated_schemas:
                split_schemas.update(split_schema(s))

            self.schemas = split_schemas

        # Default array object schema
        self.schemas["array"] = {"type": "array", "items": {"type": "string"}}

        # Identify which henge to use for each item type. Default to self:
        self.henges = {}
        for item_type in self.item_types:
            self.henges[item_type] = self

        # Next add in any remote henges for item types not stored in self:
        if henges:
            for item_type, henge in henges.items():
                if item_type not in self.item_types:
                    self.schemas[item_type] = henge.schemas[item_type]
                    self.henges[item_type] = henge


    def retrieve(self, druid, reclimit=None, raw=False):
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
                return [reconstruct_item(substr, schema["items"], reclimit)
                        for substr in string.split(DELIM_ITEM)]
            elif schema["type"] == "object":
            #else:  # assume it's an object
                attr_array = string.split(DELIM_ATTR)
                item_reconstituted = dict(zip(schema['properties'].keys(),
                                              attr_array))
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
                # if 'recursive' in schema:
                if 'henge_class' in schema:
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

        if not druid + ITEM_TYPE in self.database:
            raise NotFoundException(druid)

        item_type = self.database[druid + ITEM_TYPE]
        henge_to_query = self.henges[item_type]
        # _LOGGER.debug("item_type: {}".format(item_type))
        # _LOGGER.debug("henge_to_query: {}".format(henge_to_query))
        try:
            string = henge_to_query.database[druid]
        except KeyError:
            raise NotFoundException(druid)

        schema = self.schemas[item_type]
        return reconstruct_item(string, schema, reclimit)

    @property
    def item_types(self):
        """
        A list of item types handled by this Henge instance
        """
        return list(self.schemas.keys())

    def select_item_type(self, item):
        """
        Returns a list of all item types handled by this instance that validate
        with the given item.

        :param dict item: The item you wish to validate type of.
        """
        valid_schemas = []
        for name, schema in self.schemas.items():
            _LOGGER.debug("Testing schema: {}".format(name))
            try:
                jsonschema.validate(item, schema)
                valid_schemas.append(name)
            except jsonschema.ValidationError:
                continue
        return valid_schemas

    def insert(self, item, item_type):
        """
        Add structured items of a specified type to the database.

        :param list item: List of items to add.
        :param str item_type: A string specifying the type of item. Must match
            something from Henge.list_item_types. You can use
            Henge.select_item_type to automatically choose this, if only one
            fits.
        """

        
        _LOGGER.debug("Insert item: {} / Type: {}".format(item, item_type))
        
        if item_type not in self.schemas.keys():
            _LOGGER.error("I don't know about items of type '{}'. "
                          "I know of: '{}'".format(item_type,
                                                   list(self.schemas.keys())))
            return False

        schema = self.schemas[item_type]

        if not schema:
            return self.insert(item, item_type)

        flat_item = None
        if schema['type'] == 'object':
            flat_item = {}
            for prop in item:
                if prop in schema["properties"]:
                    _LOGGER.debug("-Prop {}; Schema: {}".format(prop, str(schema["properties"][prop])))
                    if "recursive" in schema and prop in schema["recursive"]:
                        hclass = schema["properties"][prop]["henge_class"]
                        digest = self.insert(item[prop], hclass)
                        flat_item[prop] = digest
                    elif schema["properties"][prop]["type"] in ['array']:
                        digest = self.insert(item[prop], "array")
                        flat_item[prop] = digest
                    else:
                        flat_item[prop] = item[prop]
                    _LOGGER.debug("Prop: {}; Flat item: {}".format(prop, flat_item[prop]))
                else:
                    pass  # Ignore non-schema defined properties
        elif schema['type'] == 'array':
            flat_item = []
            if 'henge_class' in schema['items']:
                digest = []
                hclass = schema['items']["henge_class"]
                for element in item:
                    digest.append(self.insert(element, hclass))
                flat_item = digest
            else:
                flat_item = item
                _LOGGER.debug("Array flat item: {}".format(flat_item))
        else:
            _LOGGER.error("I don't understand this type!")
            _LOGGER.debug(schema)

        return self._insert_flat(flat_item, item_type)


    def _insert_flat(self, item, item_type=None):
        """
        Add flattened items (of a specified type) to the database.

        Flattened items have removed all levels, so it's only attributes and 
        strict values; no nesting allowed. Use the upstream insert function
        to insert full structured objects, which calls this function.

        :param list item: List of items to add.
        :param str item_type: A string specifying the type of item. Must match
            something from Henge.list_item_types. You can use
            Henge.select_item_type to automatically choose this, if only one
            fits.
        """
        if item_type not in self.schemas.keys():
            _LOGGER.error("I don't know about items of type '{}'. "
                          "I know of: '{}'".format(item_type,
                                                   list(self.schemas.keys())))
            return False

        _LOGGER.debug("Insert flat item: {} / Type: {}".format(item, item_type))

        # digest_version should be automatically appended to the item by the
        # henge. if we can put a 'default' into the schema, then the henge
        # should also populate any missing attributes with default values. can
        # jsonschema do this automatically?
        # also item_type ?

        def safestr(item, x):
            try:
                return str(item[x])
            except (ValueError, TypeError, KeyError):
                return ""

        def build_attr_string(item, schema):
            if "type" in schema and schema["type"] == "array":
                return DELIM_ITEM.join([build_attr_string(x, schema['items'])
                                        for x in item])
            elif schema["type"] == "object" and 'properties' in schema:
            #else:  # assume it's an object
                return DELIM_ATTR.join([safestr(item, x) for x in
                                        list(schema['properties'].keys())])
            else: #assume it's a primitive
                return item

        valid_schema = self.schemas[item_type]
        # Add defaults here ?
        try: 
            jsonschema.validate(item, valid_schema)
        except jsonschema.ValidationError as e:
            _LOGGER.error("Not valid data")
            _LOGGER.error("Attempting to insert item: {}".format(item))
            _LOGGER.error("Item type: {}".format(item_type))
            print(e)
            return False
            
        attr_string = build_attr_string(item, valid_schema)
        druid = self.checksum_function(attr_string)
        self._henge_insert(druid, attr_string, item_type)
        _LOGGER.debug("Loaded {}".format(druid))
        return druid

    def _henge_insert(self, druid, string, item_type, digest_version=None):
        """
        Inserts an item into the database, with henge-metadata slots for item
        type and digest version.
        """
        if not digest_version:
            digest_version = self.digest_version

        # Here we could do a few things; should we put this metadata into the
        # interface henge or the henge where the storage actually occurs? it
        # MUST be in the interface henge; should it also be in the storage
        # henge?

        henge_to_query = self.henges[item_type]
        _LOGGER.debug("henge_to_query: {}".format(henge_to_query))
        try:
            henge_to_query.database[druid] = string
            henge_to_query.database[druid + ITEM_TYPE] = item_type
            henge_to_query.database[druid + "_digest_version"] = digest_version

            if henge_to_query != self:
                self.database[druid + ITEM_TYPE] = item_type
                self.database[druid + "_digest_version"] = digest_version
        except Exception as e:
            raise e

    def clean(self):
        """
        Remove all items from this database.
        """
        for k, v in self.database.items():
            try:
                del self.database[k]
                del self.database[k + ITEM_TYPE]
                del self.database[k + "_digest_version"]
            except (KeyError, AttributeError):
                pass

    def show(self):
        """
        Show all items in the database.
        """
        for k, v in self.database.items():
            print(k, v)


    def __repr__(self):
        repr = "Henge object. Item types: " + ",".join(self.item_types) + "\n"
        return repr


def split_schema(schema, name=None):
    """
    Splits a hierarchical schema into flat components suitable for a Henge
    """
    slist = {}
    # base case
    if schema['type'] not in ['object', 'array']:
        _LOGGER.debug(schema)
        if name:
            slist[name] = schema
        elif 'henge_class' in schema:
            slist[schema['henge_class']] = schema
        _LOGGER.debug("Returning slist: {}".format(str(slist)))
        return slist
    elif schema['type'] == 'object':
        recursive_properties = []
        if 'henge_class' in schema:
            schema_copy = copy.deepcopy(schema)
            _LOGGER.debug("adding " + str(schema_copy['henge_class']))
            henge_class = schema_copy['henge_class']
            # del schema_copy['henge_class']
            for p in schema_copy['properties']:
                hclass = None
                if 'henge_class' in schema_copy['properties'][p]:
                    hclass = schema_copy['properties'][p]['henge_class']
                if schema_copy['properties'][p]['type'] in ['object']:
                    recursive_properties.append(p)
                    schema_copy['properties'][p] = {'type': "string"}
                    if hclass:
                        schema_copy['properties'][p]['henge_class'] = hclass
                if schema_copy['properties'][p]['type'] in ["array"]:
                    recursive_properties.append(p)
                    schema_copy['properties'][p] = {'type': "string"}
                    if hclass:
                        schema_copy['properties'][p]['henge_class'] = hclass
                    else:
                        schema_copy['properties'][p]['henge_class'] = "array"
                    # schema_copy['properties'][p]['type'] = "string"
            # del schema_copy['properties']
            _LOGGER.debug("Adding recursive properties: {}".format(recursive_properties))
            schema_copy['recursive'] = recursive_properties
            slist[henge_class] = schema_copy

        for p in schema['properties']:
            # if schema['properties'][p]['type'] in ['object', 'array']:
            #     recursive_properties.append(p)            
            schema_sub = schema['properties'][p]
            _LOGGER.debug("checking property:" + p)
            slist.update(split_schema(schema['properties'][p]))
    elif schema['type'] == 'array':
        _LOGGER.debug("found array")
        _LOGGER.debug(schema)
        if 'henge_class' in schema:
            schema_copy = copy.deepcopy(schema)
            _LOGGER.debug("adding " + str(schema['henge_class']))
            henge_class = schema_copy['henge_class']
            # del schema_copy['henge_class']
            schema_copy['items'] = {'type': "string"}
            if 'recursive' in schema_copy and schema_copy['recursive']:
                schema_copy['items']['recursive'] = True
            if 'henge_class' in schema['items']:
                schema_copy['items']['henge_class'] = schema['items']['henge_class']
            # schema_copy['items']['type'] = "string"
            # if 'properties' in schema_copy['items']:
            #     del schema_copy['items']['properties']
            slist[henge_class] = schema_copy
            schema_sub = schema['items']
            slist.update(split_schema(schema_sub))
        else:
            _LOGGER.debug("Classless array")
            _LOGGER.debug(schema)
            slist.update(schema)

        _LOGGER.debug("Checking item")
    return slist


def is_schema_recursive(schema):
    """
    Determine if a given schema has elements that need to recurse
    """
    # return 'recursive' in schema # old way
    is_recursive = False
    if schema['type'] is "object":
        for prop in schema['properties']:
            if schema['properties']['prop']['type'] in ['object', 'array']:
                return True
    if schema['type'] is "array":        
        if schema['items']['type'] in ['object', 'array']:
            return True
    return False


def connect_mongo(host='0.0.0.0', port=27017, database='henge_dict',
                  collection='store'):
    """
    Connect to MongoDB and return the MongoDB-backed dict object

    Firstly, the required libraries are imported.

    :param str host: DB address
    :param int port: port DB is listening on
    :param str database: DB name
    :param str collection: collection key
    :return mongodict.MongoDict: a dict backed by MongoDB, ready to use as a
        Henge backend
    """
    from importlib import import_module
    from inspect import stack
    for lib in LIBS_BY_BACKEND["mongo"]:
        try:
            globals()[lib] = import_module(lib)
        except ImportError:
            raise ImportError(
                "Requirements not met. Package '{}' is required to setup "
                "MongoDB connection. Install the package and call '{}' again.".
                    format(lib, stack()[0][3]))
    pymongo.Connection = lambda host, port, **kwargs: \
        pymongo.MongoClient(host=host, port=port)
    return mongodict.MongoDict(host=host, port=port, database=database,
                               collection=collection)


def build_argparser():
    # TODO: add cli hooks for ^
    """
    Builds argument parser.

    :return argparse.ArgumentParser
    """
    banner = "%(prog)s - Keeper of druids: " \
             "a python interface to Decomposable Recursive UIDs"
    additional_description = "\n..."
    parser = VersionInHelpParser(version=__version__, description=banner,
                                 epilog=additional_description)

    parser.add_argument(
            "-V", "--version",
            action="version",
            version="%(prog)s {v}".format(v=__version__))

    parser.add_argument(
            "-i", "--input", required=True,
            help="File path to input file.")

    parser.add_argument(
            "-p", "--parameter", type=int, default=0,
            help="Some parameter.")

    return parser


def main():
    """ Primary workflow """

    parser = logmuse.add_logging_options(build_argparser())
    args = parser.parse_args()
    global _LOGGER
    _LOGGER = logmuse.logger_via_cli(args, make_root=True)

    msg = "Input: {input}; Parameter: {parameter}"
    _LOGGER.info(msg.format(input=args.input, parameter=args.parameter))


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.error("Program canceled by user!")
        sys.exit(1)
