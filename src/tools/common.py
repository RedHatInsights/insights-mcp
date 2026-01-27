"""Shared functions for Insights MCP tools."""


def normalise_int(name: str, value: int | str | None) -> int | None:
    """Normalise value to an int (or None) - tolerate string input from MCP clients.

    Args:
        name: The name of the parameter being validated.
        value: The value to normalise.

    Returns:
        The normalised integer value, or None if the input was None or an
        empty/whitespace string.
    """
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, bool):  # Boolean is subclass of int
        raise ValueError(f"Parameter '{name}' must be an integer; got '{value}' of type '{type(value).__name__}'.")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Strip and convert; surface a clean error if it is not an integer string.
        value_str = value.strip()
        try:
            return int(value_str)
        except ValueError as exc:
            raise ValueError(
                f"Parameter '{name}' must be convertible to integer; got '{value}' of type '{type(value).__name__}'."
            ) from exc

    # Raise exception in case of any other type provided
    raise ValueError(f"Parameter '{name}' must be an integer; got '{value}' of type '{type(value).__name__}'.")


def normalise_bool(name: str, value: bool | str | None) -> bool | None:
    """Normalise value to an boolean (or None) - tolerate string input from MCP clients."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        # Strip whitechars and convert to lowercase
        value_str = value.strip().casefold()

        if value_str == "true":
            return True
        if value_str == "false":
            return False
        raise ValueError(
            f"Parameter '{name}' must be convertible to boolean ('true'/'false'); "
            f"got '{value}' of type '{type(value).__name__}'."
        )

    # Raise exception in case of any other type provided
    raise ValueError(f"Parameter '{name}' must be a boolean; got '{value}' of type '{type(value).__name__}'.")
