"""Test suite shared objects and setup"""

import os
import pytest
import oyaml as yaml


@pytest.fixture
def data_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def load_yaml_for_test(n, data_path):
    with open(os.path.join(data_path, n), "r") as f:
        return yaml.safe_load(f)


@pytest.fixture
def schema(data_path):
    return load_yaml_for_test("schema.yaml", data_path)


@pytest.fixture
def schema_sequence(data_path):
    return load_yaml_for_test("sequence.yaml", data_path)


@pytest.fixture
def schema_asd(data_path):
    return load_yaml_for_test("annotated_sequence_digest.yaml", data_path)


@pytest.fixture
def schema_acd(data_path):
    return load_yaml_for_test("annotated_collection_digest.yaml", data_path)


@pytest.fixture
def inherent(data_path):
    return load_yaml_for_test("inherent.yaml", data_path)
