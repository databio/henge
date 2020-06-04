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


class TestRetrieval:
    @pytest.mark.parametrize("x", [
        ({"string_attr": "12321%@!", "integer_attr": 2}),
        ({"string_attr": "string", "integer_attr": 1}),
        ({"string_attr": "string"})
    ])
    def test_retrieve_returns_inserted_obj(self, schema, x):
        type_key = "schema"
        h = Henge(database={}, schemas={type_key: schema})
        d = h.insert(x, item_type=type_key)
        # returns str versions of inserted data
        if len(x) > 1:
            assert h.retrieve(d) == {k: str(v) for k, v in x.items()}
        else:
            assert not h.retrieve(d) == {k: str(v) for k, v in x.items()}



