"""Constants for henge."""

LIBS_BY_BACKEND: dict[str, list[str]] = {"mongo": ["pymongo", "mongodict"]}
DELIM_ATTR: str = ","  # Separating attributes in an item
DELIM_ITEM: str = ","  # Separating items in a collection
ITEM_TYPE: str = "_item_type"
