"""Unit tests for common functions of Planning MCP tool."""

import re

import pytest

from tools.common import normalise_bool, normalise_int


@pytest.mark.parametrize(("original", "output"), (("6", 6), (7, 7), (None, None), ("  ", None), ("  0  ", 0)))
def test_normalise_int(original, output):
    """Basic scenarios."""
    assert output == normalise_int(name="test", value=original)


def test_normalise_int_exception_bad_string():
    """String which cannot be converted into int."""
    with pytest.raises(ValueError, match="Parameter 'test' must be convertible to integer; got 'foo' of type 'str'."):
        normalise_int(name="test", value="foo")


def test_normalise_int_exception_bad_type():
    """Boolean, which is a subclass of int - shouldn't be converted.

    But since it's subclass, it could be converted:
        >>> isinstance(True, int)
        True
        >>> int(True)
        1
    """
    with pytest.raises(ValueError, match="Parameter 'test' must be an integer; got 'True' of type 'bool'."):
        normalise_int(name="test", value=True)


def test_normalise_int_exception_bad_type2():
    """Type which is unexpected."""
    with pytest.raises(
        ValueError, match=re.escape("Parameter 'test' must be an integer; got '('value', 'value2')' of type 'tuple'.")
    ):
        normalise_int(name="test", value=("value", "value2"))


@pytest.mark.parametrize(
    ("original", "output"), (("TrUe", True), ("   fAlSe", False), (None, None), (False, False), ("  ", None))
)
def test_normalise_bool(original, output):
    """Basic scenarios."""
    assert output == normalise_bool(name="test", value=original)


def test_normalise_bool_exception_bad_string():
    """String which cannot be converted into boolean."""
    with pytest.raises(
        ValueError,
        match=re.escape("Parameter 'test' must be convertible to boolean ('true'/'false'); got 'value' of type 'str'."),
    ):
        normalise_bool(name="test", value="value")


def test_normalise_bool_exception_bad_type():
    """Type which is unexpected."""
    with pytest.raises(ValueError, match="Parameter 'test' must be a boolean; got '1' of type 'int'."):
        normalise_bool(name="test", value=1)
