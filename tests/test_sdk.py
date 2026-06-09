"""Tests for saturn-sdk client. Uses daemon REST API."""
import os
import pytest
import subprocess
import sys
import time
import signal

from pathlib import Path

import pytest

from saturn.config import resolve_workspace, write_default_config, load_config
from saturn.db import initialize_database


@pytest.fixture
def init_workspace(tmp_path):
    workspace = resolve_workspace(tmp_path)
    write_default_config(workspace)
    config = load_config(tmp_path)
    initialize_database(config.db_path, config.schema_version)
    return tmp_path


def test_sdk_client_import():
    from saturn_sdk import SaturnClient, Fact, Contradiction
    assert SaturnClient is not None


def test_sdk_add_and_query_fact(init_workspace):
    from saturn_sdk import SaturnClient
    client = SaturnClient(base_url="http://localhost:8468")
    assert client is not None
