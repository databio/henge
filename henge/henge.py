""" An interface to a database back-end for DRUIDs """

import argparse
import logmuse
import os
import hashlib
import jsonschema
import pymongo
import logging
import logmuse
import mongodict
import yacman
import yaml


from . import __version__
from collections import OrderedDict
from ubiquerg import is_url


pymongo.Connection = lambda host, port, **kwargs: pymongo.MongoClient(host=host, port=port)
_LOGGER = logging.getLogger(__name__)

def md5(seq):
    return hashlib.md5(seq.encode()).hexdigest()



DELIM_ATTR = "\x1e" # chr(30); separating attributes in an item
DELIM_ITEM = "\t" #  separating items in a collection
ITEM_TYPE = "_item_type"


class MongoDict(mongodict.MongoDict):
    """ Just a passthrough to export MongoDict directly here """
    pass

class Henge(object):
    def __init__(self, database, schemas, checksum_function=md5):
        """
        A user interface to insert and retrieve decomposable recursive unique
        identifiers (DRUIDs).

        :param dict database: Dict-like lookup database with sequences and hashes.
        :param dict schemas: One or more jsonschema schemas describing the
            data types stored by this Henge
        :param function(str) -> str checksum_function: Default function to handle the digest of the
            serialized items stored in this henge.
        """
        self.database = database
        self.schemas = schemas
        self.checksum_function = checksum_function
        self.digest_version = "md5"

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
                return [reconstruct_item(substr, schema["items"], reclimit) for substr in string.split(DELIM_ITEM)]
            # if schema["type"] == "object":
            else:  # assume it's an object
                attr_array = string.split(DELIM_ATTR)
                item_reconstituted = dict(zip(schema['properties'].keys(), attr_array))
                _LOGGER.debug(schema)
                if 'recursive' in schema:
                    if isinstance(reclimit, int) and reclimit == 0:
                        return item_reconstituted
                    else:
                        if isinstance(reclimit, int):
                            reclimit = reclimit - 1
                        for recursive_attr in schema['recursive']:                    
                            if item_reconstituted[recursive_attr] and item_reconstituted[recursive_attr] != "":
                                item_reconstituted[recursive_attr] = self.retrieve(
                                    item_reconstituted[recursive_attr],
                                    reclimit,
                                    raw)                
                return item_reconstituted

        try:
            string = self.database[druid]
        except KeyError:
            return "Not found"

        item_type = self.database[druid + ITEM_TYPE]
        _LOGGER.debug("item_type: {}".format(item_type))
        schema = self.schemas[item_type]


        return reconstruct_item(string, schema, reclimit)



    def list_item_types(self):
        """
        Prints and returns a list of item types handled by this Henge instance.
        """
        for k, v in self.schemas.items():
            print("{}: {}".format(k, v["description"]))
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
            except:
                continue
        return valid_schemas

    def insert(self, item, item_type=None):
        """
        Add items (of a specified type) the the database.

        :param list items: List of items to add.
        :param str item_type: A string specifying the type of item. Must match
            something from Henge.list_item_types. You can use
            Henge.select_item_type to automatically choose this, if only one
            fits.
        """


        if not item_type in self.schemas.keys():
            _LOGGER.error("I don't know about items of type '{}'. I know of: '{}'".format(
                item_type, list(self.schemas.keys())))
            return False

        # digest_version should be automatically appended to the item by the
        # henge. if we can put a 'default' into the schema, then the henge
        # should also populate any missing attributes with default values. can
        # jsonschema do this automatically?
        # also item_type ?


        def safestr(item, x):
            try:
                return str(item[x])
            except:
                return ""

        def build_attr_string(item, schema):

            if "type" in schema and schema["type"] == "array":
                return DELIM_ITEM.join([build_attr_string(x, schema['items']) for x in item])
            # if schema["type"] == "object":
            else:  # assume it's an object
                return DELIM_ATTR.join([safestr(item, x) for x in list(schema['properties'].keys())])

        attr_strings = []
        valid_schema = self.schemas[item_type]
        # Add defaults here ?
        try: 
            jsonschema.validate(item, valid_schema)
        except Exception as e:
            _LOGGER.error("Not valid data")
            _LOGGER.error("Attempting to insert item: {}".format(item))
            _LOGGER.error("Item type: {}".format(item_type))
            print(e)
            return False
            
        attr_string = build_attr_string(item, valid_schema)
        druid = self.checksum_function(attr_string)
        # self.database[druid] = attr_string
        self._henge_insert(druid, attr_string, item_type)
        _LOGGER.info("Loaded {}".format(druid))
        return druid
        

    def _henge_insert(self, druid, string, item_type, digest_version=None):
        """
        Inserts an item into the database, with henge-metadata slots for item
        type and digest version.
        """
        if not digest_version:
            digest_version = self.digest_version
        self.database[druid] = string
        self.database[druid + ITEM_TYPE] = item_type
        self.database[druid + "_digest_version"] = digest_version


    def clean(self):
        """
        Remove all items from the database.
        """
        for k,v in self.database.items():
            try:
                del self.database[k]
                del self.database[k + ITEM_TYPE]
                del self.database[k + "_digest_version"]
            except:
                pass

    def show(self):
        """
        Show all items in the database.
        """
        for k,v in self.database.items():
            print(k, v)   


def load_yaml(filepath):
    """ Load a yaml file into a python dict """

    if is_url(filepath):
        _LOGGER.info("Got URL: {}".format(filepath))
        try: #python3
            from urllib.request import urlopen
            from urllib.error import HTTPError
        except: #python2
            from urllib2 import urlopen       
            from urllib2 import URLError as HTTPError
        try:
            response = urlopen(filepath)
        except HTTPError as e:
            raise e
        data = response.read()      # a `bytes` object
        text = data.decode('utf-8')
        manifest_lines = yacman.YacAttMap(yamldata=text)
    else:
        manifest_lines = yacman.YacAttMap(filepath=filepath) 
        # yaml.safe_load(f)

    return manifest_lines

class _VersionInHelpParser(argparse.ArgumentParser):
    def format_help(self):
        """ Add version information to help text. """
        return "version: {}\n".format(__version__) + \
               super(_VersionInHelpParser, self).format_help()


def build_argparser():
    """
    Builds argument parser.

    :return argparse.ArgumentParser
    """

    banner = "%(prog)s - "
    additional_description = "\n..."

    parser = _VersionInHelpParser(
            description=banner,
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

