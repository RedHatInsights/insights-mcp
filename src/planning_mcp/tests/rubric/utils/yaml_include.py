"""Custom YAML loader with !include support for rubric files.

This module provides a YAML loader that supports the !include directive,
allowing YAML files to reference common definitions from other YAML files.

The include path is relative to the file containing the !include directive.
"""

import os
from typing import Any

import yaml
from rubric_kit.validator import load_rubric


class IncludeLoader(yaml.SafeLoader):
    """YAML loader that supports !include directive for file inclusion."""

    _base_dir: str

    def __init__(self, stream: Any, base_dir: str | None = None):
        """Initialize the loader with a base directory for resolving includes.

        Args:
            stream: YAML content stream
            base_dir: Base directory for resolving relative include paths
        """
        self._base_dir = base_dir or os.getcwd()
        super().__init__(stream)


def _include_constructor(loader: IncludeLoader, node: yaml.ScalarNode) -> Any:
    """Handle !include directive by loading and parsing the referenced file.

    Args:
        loader: The YAML loader instance
        node: The YAML node containing the include path

    Returns:
        The parsed content from the included file
    """
    include_path = str(loader.construct_scalar(node))

    # Resolve relative path from the base directory
    if not os.path.isabs(include_path):
        include_path = os.path.join(loader._base_dir, include_path)

    # Load and parse the included file
    with open(include_path, encoding="utf-8") as f:
        return yaml.load(f, Loader=yaml.SafeLoader)


# Register the !include constructor
IncludeLoader.add_constructor("!include", _include_constructor)


def load_yaml_with_includes(file_path: str) -> dict:
    """Load a YAML file with !include directive support.

    Args:
        file_path: Path to the YAML file to load

    Returns:
        Parsed YAML content with all includes resolved
    """
    base_dir = os.path.dirname(os.path.abspath(file_path))

    with open(file_path, encoding="utf-8") as f:
        # Use IncludeLoader directly with base_dir set via class attribute workaround
        loader = IncludeLoader(f, base_dir=base_dir)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()


def load_rubric_with_includes(file_path: str):
    """Load a rubric file with !include support, then pass to rubric-kit.

    This function preprocesses the YAML file to resolve !include directives,
    then loads it through rubric-kit's standard validation.

    Args:
        file_path: Path to the rubric YAML file

    Returns:
        A validated Rubric object from rubric-kit
    """
    import tempfile

    # Load YAML with includes resolved
    rubric_data = load_yaml_with_includes(file_path)

    # Write resolved content to a temporary file for rubric-kit
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8") as tmp:
        yaml.dump(rubric_data, tmp, default_flow_style=False, allow_unicode=True)
        tmp_path = tmp.name

    try:
        return load_rubric(tmp_path)
    finally:
        os.unlink(tmp_path)
