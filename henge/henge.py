""" Computing configuration representation """

import argparse
import logmuse
import os
from . import __version__
from collections import OrderedDict
import hashlib
import jsonschema
import pymongo
pymongo.Connection = lambda host, port, **kwargs: pymongo.MongoClient(host=host, port=port)
import logging
import mongodict
import yaml
import logmuse


_LOGGER = logging.getLogger(__name__)

def md5(seq):
    return hashlib.md5(seq.encode()).hexdigest()



DELIM_ATTR = "\x1e" # chr(30); separating attributes in an item
DELIM_ITEM = "\t" #  separating items in a collection

class MongoDict(mongodict.MongoDict):
    pass

class Henge(object):
    def __init__(self, database, schemas, checksum_function=md5):
        """
        A holding spot for DRUIDs.

        :@param database: Dict-like lookup database with sequences and hashes.
        """
        self.database = database
        self.schemas = schemas
        self.checksum_function = checksum_function
        self.checksum_function_version = "md5"
        self.digest_version = "md5"

    def retrieve(self, druid, reclimit=None, raw=False):
        try:
            string = self.database[druid]
        except KeyError:
            return "Not found"


        def process_item(string, reclimit):
            if not DELIM_ATTR in string: 
                if raw:
                    return string
                item_reconstituted = {self.database[druid + "_item_type"]: string}
            else:
                attr_array = string.split(DELIM_ATTR)
                item_type = self.database[druid + "_item_type"]
                _LOGGER.info("item_type: {}".format(item_type))
                schema = self.schemas[item_type]
                item_reconstituted = dict(zip(schema['properties'].keys(), attr_array))
                if (isinstance(reclimit, int) and reclimit == 0):
                    return item_reconstituted
                else:
                    if 'recursive' in schema:
                        for recursive_attr in schema['recursive']:                    
                            item_reconstituted[recursive_attr] = self.retrieve(
                                item_reconstituted[recursive_attr],
                                reclimit,
                                raw)
            return item_reconstituted

        if not DELIM_ITEM in string:
            return process_item(string, reclimit)
        else:  # Recursive case
            if isinstance(reclimit, int):
                reclimit = reclimit - 1
            return [process_item(item, reclimit) for item in string.split(DELIM_ITEM)]


    def list_item_types(self):
        return self.schemas.keys()


    def select_item_type(self, item):
        valid_schemas = []
        for name, schema in self.schemas.items():
            _LOGGER.debug("Testing schema: {}".format(name))
            try:
                jsonschema.validate(item, schema)
                valid_schemas.append(name)
            except:
                continue
        return valid_schemas

    def insert(self, items, item_type=None):


        if not item_type in self.schemas.keys():
            _LOGGER.error("I don't know about items of type '{}'. I know of: '{}'".format(
                item_type, self.schemas.keys()))
            return False

        # digest_version should be automatically appended to the item by the
        # henge. if we can put a 'default' into the schema, then the henge
        # should also populate any missing attributes with default values. can
        # jsonschema do this automatically?
        # also item_type ?


        def build_attr_string(item, schema):
            return DELIM_ATTR.join([str(item[x]) for x in list(schema['properties'].keys())])

        attr_strings = []
        for item in items:
            valid_schema = self.schemas[item_type]
            # Add defaults here ?
            try: 
                jsonschema.validate(item, valid_schema)
            except Exception as e:
                _LOGGER.error("Not valid data")
                print(e)
                return False
            

            attr_strings.append(build_attr_string(item, valid_schema))

        attr_string = DELIM_ITEM.join(attr_strings)
        druid = self.checksum_function(attr_string)
        # self.database[druid] = attr_string
        self.henge_insert(druid, attr_string, item_type)
        _LOGGER.info("Loaded {}".format(druid))
        return druid
        

    def henge_insert(self, druid, string, item_type, digest_version=None):
        if not digest_version:
            digest_version = self.digest_version
        self.database[druid] = string
        self.database[druid + "_item_type"] = item_type
        self.database[druid + "_digest_version"] = digest_version


    def clean(self):
        for k,v in self.database.items():
            try:
                del self.database[k]
                del self.database[k + "_item_type"]
                del self.database[k + "_digest_version"]
            except:
                pass

    def show(self):
        for k,v in self.database.items():
            print(k, v)   


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

    banner = "%(prog)s - randomize BED files"
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