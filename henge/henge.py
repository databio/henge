""" An interface to a database back-end for DRUIDs """

import copy
import hashlib
import jsonschema
import logging
import logmuse
import sys
import yacman

from ubiquerg import VersionInHelpParser

from . import __version__
from .const import *

_LOGGER = logging.getLogger(__name__)


def md5(seq):
    return hashlib.md5(seq.encode()).hexdigest()


class Henge(object):
    def __init__(self, database, schemas, henges=None, checksum_function=md5):
        """
        A user interface to insert and retrieve decomposable recursive unique
        identifiers (DRUIDs).

        :param dict database: Dict-like lookup database for sequences and
            hashes.
        :param dict schemas: One or more jsonschema schemas describing the
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
                    populated_schemas.append(yacman.load_yaml(schema_value))
            split_schemas = {}
            for s in populated_schemas:
                split_schemas.update(split_schema(s))

            self.schemas = split_schemas

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
                return [reconstruct_item(substr, schema["items"], reclimit)
                        for substr in string.split(DELIM_ITEM)]
            elif schema["type"] == "object":
            #else:  # assume it's an object
                attr_array = string.split(DELIM_ATTR)
                item_reconstituted = dict(zip(schema['properties'].keys(),
                                              attr_array))
                _LOGGER.debug(schema)
                if 'recursive' in schema:
                    if isinstance(reclimit, int) and reclimit == 0:
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
                if 'recursive' in schema:
                    if isinstance(reclimit, int) and reclimit == 0:
                        return string
                    else:
                        if isinstance(reclimit, int):
                            reclimit = reclimit - 1
                            print(string)
                        return self.retrieve(string, reclimit, raw)
                else:
                    print("not recursive")
                    print(schema)
                    return string


        item_type = self.database[druid + ITEM_TYPE]
        _LOGGER.debug("item_type: {}".format(item_type))
        henge_to_query = self.henges[item_type]
        _LOGGER.debug("henge_to_query: {}".format(henge_to_query))
        try:
            string = henge_to_query.database[druid]
        except KeyError:
            return "Not found"

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

    def insert(self, item, item_type=None):
        """
        Add items (of a specified type) the the database.

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
        repr = "Henge object\n" + \
        "Item types: " + ",".join(self.item_types) + "\n" + \
        "Schemas: " + str(self.schemas)
        return repr



def split_schema(schema, name=None):
    """
    Splits a complete schema into components suitable for a Henge
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
    else:
        if schema['type'] == 'object':
            if 'henge_class' in schema:
                schema_copy = copy.deepcopy(schema)
                _LOGGER.debug("adding " + str(schema_copy['henge_class']))
                henge_class = schema_copy['henge_class']
                del schema_copy['henge_class']
                for p in schema_copy['properties']:
                    if schema_copy['properties'][p]['type'] in ['object', 'array']:
                        schema_copy['properties'][p] = {'type': "string"}
                # del schema_copy['properties']
                slist[henge_class] = schema_copy

            for p in schema['properties']:
                schema_sub = schema['properties'][p]
                _LOGGER.debug("checking property:" + p)
                slist.update(split_schema(schema['properties'][p]))

        if schema['type'] == 'array':
            _LOGGER.debug("found array")
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
            _LOGGER.debug("Checking item")
            slist.update(split_schema(schema_sub))
    return slist




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
