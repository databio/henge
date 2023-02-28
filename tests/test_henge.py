import pytest
from henge import Henge
from jsonschema import ValidationError

# See conftest.py for fixtures


class TestInserting:
    @pytest.mark.parametrize(
        ["x", "success"],
        [
            ({"string_attr": "12321%@!"}, True),
            ({"string_attr": "string", "integer_attr": 1}, True),
            ({"string_attr": 1}, False),
            ({"string_attr": ["a", "b"]}, False),
            ({"string_attr": {"string_attr": "test"}}, False),
            ({"string_attr": "string", "integer_attr": "1"}, False),
            ({"integer_attr": 1}, False),
        ],
    )
    def test_insert_validation_works(self, schema, x, success):
        """Test whether insertion is performed only for valid objects"""
        type_key = "test_item"
        print(f"here's what I got for schema: {schema}")
        h = Henge(database={}, schemas=["tests/data/schema.yaml"])
        if success:
            assert isinstance(h.insert(x, item_type=type_key), str)
        else:
            with pytest.raises(ValidationError):
                h.insert(x, item_type=type_key)


class TestRetrieval:
    @pytest.mark.parametrize(
        "x",
        [
            ({"string_attr": "12321%@!", "integer_attr": 2}),
            ({"string_attr": "string", "integer_attr": 1}),
            ({"string_attr": "string"}),
        ],
    )
    def test_retrieve_returns_inserted_obj(self, schema, x):
        type_key = "test_item"
        h = Henge(database={}, schemas=["tests/data/schema.yaml"])
        d = h.insert(x, item_type=type_key)
        # returns str versions of inserted data
        assert h.retrieve(d) == {k: v for k, v in x.items()}

    @pytest.mark.parametrize(
        ["seq", "anno"],
        [
            ("ATGCAGTA", {"name": "seq1", "length": 10, "topology": "linear"}),
            ("AAAAAAAA", {"name": "seq2", "length": 11, "topology": "linear"}),
        ],
    )
    def test_retrieve_recurses(self, schema_asd, schema_sequence, seq, anno):
        h = Henge(
            database={},
            schemas=[
                "tests/data/sequence.yaml",
                "tests/data/annotated_sequence_digest.yaml",
            ],
        )
        seq_digest = h.insert(seq, item_type="sequence")
        anno.update({"sequence_digest": seq_digest})
        asd = h.insert(anno, item_type="annotated_sequence_digest")
        res = h.retrieve(asd)
        assert isinstance(res["name"], str)

    def test_inherent_attributes(self, inherent):
        print("test")
