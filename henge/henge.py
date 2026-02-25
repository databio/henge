"""An interface to a database back-end for DRUIDs."""

import base64
import copy
import hashlib
import json
import logging
import os
from collections.abc import Callable

import jsonschema
import yacman
import yaml

from .const import ITEM_TYPE, LIBS_BY_BACKEND

_LOGGER = logging.getLogger(__name__)


class NotFoundException(Exception):
    """Raised when a digest is not found."""

    def __init__(self, m: str) -> None:
        self.message = f"{m} not found in database"

    def __str__(self) -> str:
        return self.message


def sha512t24u_digest(seq: str, offset: int = 24) -> str:
    """Compute GA4GH truncated SHA-512 digest.

    Args:
        seq: The sequence to digest.
        offset: Number of bytes to truncate to.

    Returns:
        URL-safe base64-encoded truncated digest.
    """
    digest = hashlib.sha512(seq.encode()).digest()
    tdigest_b64us = base64.urlsafe_b64encode(digest[:offset])
    return tdigest_b64us.decode("ascii")


def md5(seq: str) -> str:
    """Compute MD5 hash of a string."""
    return hashlib.md5(seq.encode()).hexdigest()


def is_url(maybe_url: str) -> bool:
    """Check if a string looks like a URL."""
    from urllib.parse import urlparse

    return " " not in maybe_url and urlparse(maybe_url).scheme != ""


def read_url(url: str) -> dict:
    """Fetch and parse YAML from a URL.

    Args:
        url: URL to fetch.

    Returns:
        Parsed YAML content.
    """
    _LOGGER.info(f"Reading URL: {url}")
    from urllib.error import HTTPError
    from urllib.request import urlopen

    try:
        response = urlopen(url)
    except HTTPError as e:
        raise e
    data = response.read()
    text = data.decode("utf-8")
    return yaml.safe_load(text)


class Henge:
    """Interface for storing and retrieving decomposable recursive unique identifiers (DRUIDs)."""

    def __init__(
        self,
        database: dict,
        schemas: list[str] | dict,
        schemas_str: list[str] | None = None,
        henges: dict | None = None,
        checksum_function: Callable[[str], str] = md5,
    ) -> None:
        """Initialize a Henge instance.

        Args:
            database: Dict-like lookup database for sequences and hashes.
            schemas: List of file paths or URLs to YAML jsonschema schemas,
                or a dict mapping schema names to schema definitions.
            schemas_str: List of YAML schema strings (parsed directly).
            henges: Henge objects indexed by item type for remote storage.
            checksum_function: Function to compute digest of serialized items.
        """
        self.database = database
        self.checksum_function = checksum_function
        self.digest_version = "md5"
        self.flexible_digests = True
        self.supports_inherent_attrs = True

        # TODO: Right now you can pass a file, or a URL, or some yaml directly
        # into the schemas param. I want to split that out so that at least the
        # yaml direct is its own arg

        if isinstance(schemas, dict):
            _LOGGER.debug("Using old dict schemas")
            populated_schemas = {}
            for schema_key, schema_value in schemas.items():
                if isinstance(schema_value, str):
                    populated_schemas[schema_key] = yacman.load_yaml(schema_value)
            self.schemas = populated_schemas
        else:
            populated_schemas = []
            if isinstance(schemas, str):
                _LOGGER.error(
                    "The schemas should be a list. Please pass a list of schemas"
                )
                schemas = [schemas]
            for schema_value in schemas:
                if isinstance(schema_value, str):
                    if os.path.isfile(schema_value):
                        populated_schemas.append(yacman.load_yaml(schema_value))
                    elif is_url(schema_value):
                        populated_schemas.append(read_url(schema_value))
                    else:
                        _LOGGER.error(
                            f"Schema file not found: {schema_value}. Use schemas_str if you meant to specify a direct schema"
                        )
                        # populated_schemas.append(yaml.safe_load(schema_value))

            for schema_value in schemas_str or []:
                populated_schemas.append(yaml.safe_load(schema_value))

            split_schemas = {}
            for s in populated_schemas:
                split_schemas.update(split_schema(s))

            self.schemas = split_schemas

        # Default array object schema
        # I once wanted the array type to be built in, but now I don't.
        # self.schemas["array"] = {"type": "array", "items": {"type": "string"}}

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

    def retrieve(
        self, druid: str, reclimit: int | None = None, raw: bool = False
    ) -> dict | list:
        """Retrieve an item by its digest.

        Args:
            druid: Decomposable recursive unique identifier (DRUID) to retrieve.
            reclimit: Recursion limit. None for no limit.
            raw: Return raw henge-delimited string instead of parsed mapping.

        Returns:
            The retrieved item as a dict or list.

        Raises:
            NotFoundException: If the druid is not found.
        """
        try:
            item_type = self.database[druid + ITEM_TYPE]
        except KeyError:
            raise NotFoundException(druid)

        digested_string = self.lookup(druid, item_type)
        reconstructed_item = json.loads(digested_string)

        external_string = self.database[druid + "_external_string"]
        if external_string != "null":
            external_values = json.loads(external_string)
            reconstructed_item.update(external_values)

        schema = self.schemas[item_type]

        if schema["type"] == "array":
            if isinstance(reclimit, int) and reclimit == 0:
                return reconstructed_item
            if "henge_class" in schema["items"]:
                _LOGGER.debug(
                    "Henge classed array: {}; Schema: {}".format(
                        digested_string, schema
                    )
                )
                if isinstance(reclimit, int):
                    reclimit = reclimit - 1
                return [self.retrieve(item, reclimit) for item in reconstructed_item]
        elif schema["type"] == "object":
            if "recursive" in schema:
                if isinstance(reclimit, int) and reclimit == 0:
                    _LOGGER.debug(
                        "Lookup/obj/Recursive: {}; Schema: {}".format(
                            digested_string, schema
                        )
                    )
                    return reconstructed_item
                else:
                    if isinstance(reclimit, int):
                        reclimit = reclimit - 1
                    for recursive_attr in schema["recursive"]:
                        if (
                            recursive_attr in reconstructed_item
                            and reconstructed_item[recursive_attr] != ""
                        ):
                            reconstructed_item[recursive_attr] = self.retrieve(
                                reconstructed_item[recursive_attr], reclimit, raw
                            )
        return reconstructed_item

    def lookup(self, druid: str, item_type: str) -> str:
        try:
            henge_to_query = self.henges[item_type]
        except KeyError:
            _LOGGER.debug("No henges available for this item type")
            raise NotFoundException(druid)
        try:
            string = henge_to_query.database[druid]
        except KeyError:
            raise NotFoundException(druid)

        return string

    @property
    def item_types(self) -> list[str]:
        """List of item types handled by this Henge instance."""
        return list(self.schemas.keys())

    def select_item_type(self, item: dict) -> list[str]:
        """Find all item types that validate against the given item.

        Args:
            item: The item to validate.

        Returns:
            List of matching item type names.
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

    def insert(
        self, item: dict | list, item_type: str, reclimit: int | None = None
    ) -> str | bool:
        """Add a structured item to the database.

        Args:
            item: The item to add.
            item_type: Item type name (must match a schema in item_types).
            reclimit: Recursion limit for nested items.

        Returns:
            The digest (DRUID) of the inserted item, or False on failure.
        """

        _LOGGER.debug("Insert type: {} / Item: {}".format(item_type, item))

        if item_type not in self.schemas.keys():
            _LOGGER.error(
                "I don't know about items of type '{}'. I know of: '{}'".format(
                    item_type, list(self.schemas.keys())
                )
            )
            return False

        schema = self.schemas[item_type]

        flat_item = item
        if schema["type"] == "object":
            flat_item = {}
            if isinstance(reclimit, int) and reclimit == 0:
                return self._insert_flat(item, item_type)
            else:
                if isinstance(reclimit, int):
                    reclimit = reclimit - 1
                for prop in item:
                    if prop in schema["properties"]:
                        _LOGGER.debug(
                            "-Prop {}; Schema: {}".format(
                                prop, str(schema["properties"][prop])
                            )
                        )
                        if "recursive" in schema and prop in schema["recursive"]:
                            hclass = schema["properties"][prop]["henge_class"]
                            digest = self.insert(item[prop], hclass, reclimit)
                            flat_item[prop] = digest
                        elif schema["properties"][prop]["type"] in ["array"]:
                            digest = self.insert(item[prop], "array", reclimit)
                            flat_item[prop] = digest
                        else:
                            flat_item[prop] = item[prop]
                        _LOGGER.debug(
                            "Prop: {}; Flat item: {}".format(prop, flat_item[prop])
                        )
                    else:
                        _LOGGER.debug(f"Prop: {prop}. Ignoring due to not in schema")
                        pass  # Ignore non-schema defined properties

                # if len(flat_item) == 0:
                #     flat_item = item
        elif schema["type"] == "array":
            flat_item = []
            if "henge_class" in schema["items"]:
                digest = []
                hclass = schema["items"]["henge_class"]
                if isinstance(reclimit, int) and reclimit == 0:
                    return self._insert_flat(item, item_type)
                else:
                    if isinstance(reclimit, int):
                        reclimit = reclimit - 1
                    _LOGGER.debug(
                        "Item: {}. Pyclass: {}. hclass: {}".format(
                            item, type(item), hclass
                        )
                    )
                    for element in item:
                        digest.append(self.insert(element, hclass, reclimit))
                    flat_item = digest
            else:
                flat_item = item
                _LOGGER.debug("Array flat item: {}".format(flat_item))
        else:  # A primitive type with a henge class
            _LOGGER.debug("Nice! You're using a henge-classed primitive type!")
            hclass = schema["henge_class"]
            # digest = self.insert(item, hclass)
            flat_item = item

        return self._insert_flat(flat_item, item_type)

    def _insert_flat(
        self,
        item: dict | list,
        item_type: str | None = None,
        item_name: str | None = None,
    ) -> str | bool:
        """Add a flattened item to the database.

        Flattened items have no nesting - only attributes and primitive values.
        Use insert() for structured objects; it calls this internally.

        Args:
            item: The flattened item to add.
            item_type: Item type name (must match a schema).
            item_name: Optional item name.

        Returns:
            The digest (DRUID) of the inserted item, or False on failure.
        """
        if item_type not in self.schemas.keys():
            _LOGGER.error(
                "I don't know about items of type '{}'. I know of: '{}'".format(
                    item_type, list(self.schemas.keys())
                )
            )
            return False

        # digest_version should be automatically appended to the item by the
        # henge. if we can put a 'default' into the schema, then the henge
        # should also populate any missing attributes with default values. can
        # jsonschema do this automatically?
        # also item_type ?

        valid_schema = self.schemas[item_type]
        # Add defaults here ?
        try:
            jsonschema.validate(item, valid_schema)
        except jsonschema.ValidationError as e:
            _LOGGER.error(
                "Not valid data. Item type: {}. Attempting to insert item: {}".format(
                    item_type, item
                )
            )
            _LOGGER.error(e)

            if isinstance(item, str):
                henge_to_query = self.henges[item_type]
                try:
                    _ = henge_to_query.database[item + ITEM_TYPE]
                except KeyError:
                    _LOGGER.error(
                        "If you're trying to insert an item with druids, "
                        "the sub-items must exist in the database."
                    )
                try:
                    _ = henge_to_query.database[item]
                except KeyError:
                    _LOGGER.error("That item wasn't in the database.")

                return item

            raise e

        _LOGGER.debug(f"item to insert: {item}")
        item_inherent_split = select_inherent_properties(item, valid_schema)
        attr_string = canonical_str(item_inherent_split["inherent"])
        external_string = canonical_str(item_inherent_split["external"])

        _LOGGER.debug(f"String to digest: {attr_string}")
        _LOGGER.debug(f"External string: {external_string}")
        druid = self.checksum_function(attr_string)
        self._henge_insert(druid, attr_string, item_type, external_string)

        _LOGGER.debug(
            "Inserted flat item. Digest: {} / Type: {} / Item: {}".format(
                druid, item_type, item
            )
        )
        return druid

    def _henge_insert(
        self,
        druid: str,
        string: str,
        item_type: str,
        external_string: str,
        digest_version: str | None = None,
    ) -> None:
        """Insert an item with henge metadata (item type, digest version)."""
        if not digest_version:
            digest_version = self.digest_version

        # Here we could do a few things; should we put this metadata into the
        # interface henge or the henge where the storage actually occurs? it
        # MUST be in the interface henge; should it also be in the storage
        # henge?

        # The storage henge may also be a read-only API...for some items...

        henge_to_query = self.henges[item_type]
        # _LOGGER.debug("henge_to_query: {}".format(henge_to_query))
        henge_to_query.database[druid] = string
        henge_to_query.database[druid + ITEM_TYPE] = item_type
        henge_to_query.database[druid + "_digest_version"] = digest_version
        henge_to_query.database[druid + "_external_string"] = external_string

        if henge_to_query != self:
            self.database[druid + ITEM_TYPE] = item_type
            self.database[druid + "_digest_version"] = digest_version

    def clean(self) -> None:
        """Remove all items from this database."""
        try:
            for k, v in self.database.items():
                try:
                    del self.database[k]
                    del self.database[k + ITEM_TYPE]
                    del self.database[k + "_digest_version"]
                except (KeyError, AttributeError):
                    pass
        except AttributeError as e:
            _LOGGER.warn(f"Error trying to iterate over database items: {e}")

    def show(self) -> None:
        """Log all items in the database."""
        for k, v in self.database.items():
            _LOGGER.info(f"{k} {v}")

    def __len__(self) -> int:
        return len(self.database)

    def list(self, limit: int = 1000, offset: int = 0) -> dict:
        """List items in the database with pagination."""
        return {
            "count": len(self.database),
            "limit": limit,
            "offset": offset,
            "items": list(self.database.keys())[offset : (offset + limit)],
        }

    def __repr__(self):
        repr = "Henge object. Item types: " + ",".join(self.item_types)
        return repr


def split_schema(schema: dict, name: str | None = None) -> dict:
    """Split a hierarchical schema into flat components for a Henge."""
    slist = {}
    # base case
    if schema["type"] not in ["object", "array"]:
        _LOGGER.debug(schema)
        if name:
            slist[name] = schema
        elif "henge_class" in schema:
            slist[schema["henge_class"]] = schema
        _LOGGER.debug("Returning slist: {}".format(str(slist)))
        return slist
    elif schema["type"] == "object":
        recursive_properties = []
        if "henge_class" in schema:
            schema_copy = copy.deepcopy(schema)
            _LOGGER.debug("adding " + str(schema_copy["henge_class"]))
            henge_class = schema_copy["henge_class"]
            # del schema_copy['henge_class']
            for p in schema_copy["properties"]:
                hclass = None
                if "henge_class" in schema_copy["properties"][p]:
                    hclass = schema_copy["properties"][p]["henge_class"]
                    recursive_properties.append(p)
                if schema_copy["properties"][p]["type"] in ["object"]:
                    # recursive_properties.append(p)
                    schema_copy["properties"][p] = {"type": "string"}
                    if hclass:
                        schema_copy["properties"][p]["henge_class"] = hclass
                if schema_copy["properties"][p]["type"] in ["array"]:
                    # recursive_properties.append(p)
                    if schema_copy["properties"][p]["items"]["type"] == "integer":
                        schema_copy["properties"][p] = {"type": "string"}
                    else:
                        schema_copy["properties"][p] = {"type": "string"}
                    if hclass:
                        schema_copy["properties"][p]["henge_class"] = hclass
                    else:
                        schema_copy["properties"][p]["henge_class"] = "strarray"
                    # schema_copy['properties'][p]['type'] = "string"
            # del schema_copy['properties']
            _LOGGER.debug(
                "Adding recursive properties: {}".format(recursive_properties)
            )
            schema_copy["recursive"] = recursive_properties
            slist[henge_class] = schema_copy

        for p in schema["properties"]:
            # if schema['properties'][p]['type'] in ['object', 'array']:
            #     recursive_properties.append(p)
            schema_sub = schema["properties"][p]
            _LOGGER.debug("checking property:" + p)
            slist.update(split_schema(schema["properties"][p]))
    elif schema["type"] == "array":
        _LOGGER.debug("found array")
        _LOGGER.debug(schema)
        if "henge_class" in schema:
            schema_copy = copy.deepcopy(schema)
            _LOGGER.debug("adding " + str(schema["henge_class"]))
            henge_class = schema_copy["henge_class"]
            # del schema_copy['henge_class']
            if schema_copy["items"]["type"] != "integer":
                schema_copy["items"] = {"type": "string"}
            if "recursive" in schema_copy and schema_copy["recursive"]:
                schema_copy["items"]["recursive"] = True
            if "henge_class" in schema["items"]:
                schema_copy["items"]["henge_class"] = schema["items"]["henge_class"]
            # schema_copy['items']['type'] = "string"
            # if 'properties' in schema_copy['items']:
            #     del schema_copy['items']['properties']
            slist[henge_class] = schema_copy
            schema_sub = schema["items"]
            slist.update(split_schema(schema_sub))
        else:
            _LOGGER.debug("Classless array")
            _LOGGER.debug(schema)
            slist.update(schema)

        _LOGGER.debug("Checking item")
    return slist


def canonical_str(item: dict) -> str:
    """Convert a dict into a canonical string representation"""
    return json.dumps(
        item, separators=(",", ":"), ensure_ascii=False, allow_nan=False, sort_keys=True
    )


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


def is_schema_recursive(schema: dict) -> bool:
    """Check if a schema has elements that require recursion."""
    if schema["type"] == "object":
        for prop in schema["properties"]:
            if schema["properties"]["prop"]["type"] in ["object", "array"]:
                return True
    if schema["type"] == "array":
        if schema["items"]["type"] in ["object", "array"]:
            return True
    return False


def connect_mongo(
    host: str = "0.0.0.0",
    port: int = 27017,
    database: str = "henge_dict",
    collection: str = "store",
):
    """Connect to MongoDB and return a dict-like backend.

    Args:
        host: Database address.
        port: Database port.
        database: Database name.
        collection: Collection name.

    Returns:
        MongoDict instance for use as a Henge backend.
    """
    from importlib import import_module
    from inspect import stack

    for lib in LIBS_BY_BACKEND["mongo"]:
        try:
            globals()[lib] = import_module(lib)
        except ImportError:
            raise ImportError(
                "Requirements not met. Package '{}' is required to setup "
                "MongoDB connection. Install the package and call '{}' again.".format(
                    lib, stack()[0][3]
                )
            )
    pymongo.Connection = lambda host, port, **kwargs: pymongo.MongoClient(  # noqa: F821
        host=host, port=port
    )
    return mongodict.MongoDict(  # noqa: F821
        host=host, port=port, database=database, collection=collection
    )
