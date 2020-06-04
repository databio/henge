import pytest
from henge import Henge


class TestInserting:
    @pytest.mark.parametrize(["x", "success"], [
        ({"string_attr": "12321%@!"}, True),
        ({"string_attr": "string", "integer_attr": 1}, True),
        ({"string_attr": 1}, False),
        ({"string_attr": ["a", "b"]}, False),
        ({"string_attr": {"string_attr": "test"}}, False),
        ({"string_attr": "string", "integer_attr": "1"}, False),
        ({"integer_attr": 1}, False),
    ])
    def test_insert_validation_works(self, schema, x, success):
        """ Test whether insertion is performed only for valid objects """
        type_key = "schema"
        h = Henge(database={}, schemas={type_key: schema})
        if success:
            assert isinstance(h.insert(x, item_type=type_key), str)
        else:
            assert isinstance(h.insert(x, item_type=type_key), bool)
            assert not h.insert(x, item_type=type_key)

