"""Tests for the `config` module."""

from dataclasses import fields

from insiders._internal.config import Config


def test_valid_field_names_and_keys() -> None:
    """Test that all field names match their unset name."""
    for field in fields(Config):
        assert field.name == field.default.name
