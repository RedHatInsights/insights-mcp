"""Shared helpers for Insights MCP dashboard UI resources."""

from importlib import resources
from pathlib import Path

CSS_PLACEHOLDER = "<!-- INSIGHTS_DASHBOARD_CSS -->"


def load_package_text(package: str, *parts: str) -> str:
    """Load a UTF-8 text file from an installed package.

    Args:
        package: Importable package name (e.g. ``insights_mcp``).
        parts: Path components within the package.

    Returns:
        File contents as a string.

    Raises:
        FileNotFoundError: If the asset is not present in the package.
    """
    return resources.files(package).joinpath(*parts).read_text(encoding="utf-8")


def load_package_text_with_fallback(
    package: str,
    parts: tuple[str, ...],
    fallback_dir: Path,
) -> str:
    """Load package text with a filesystem fallback for editable installs.

    Args:
        package: Importable package name.
        parts: Path components within the package.
        fallback_dir: Directory used when the package resource is unavailable.

    Returns:
        File contents as a string.
    """
    try:
        return load_package_text(package, *parts)
    except (FileNotFoundError, ModuleNotFoundError, AttributeError, TypeError):
        return fallback_dir.joinpath(*parts).read_text(encoding="utf-8")


def compose_dashboard_html(
    html: str,
    *,
    base_css_package: str = "insights_mcp",
    base_css_name: str = "assets/dashboard_base.css",
    extra_css: str | None = None,
) -> str:
    """Inject shared and optional dashboard-specific CSS into HTML.

    Args:
        html: Dashboard HTML containing ``CSS_PLACEHOLDER``.
        base_css_package: Package that holds the shared base stylesheet.
        base_css_name: Path to the shared base stylesheet within the package.
        extra_css: Optional dashboard-specific CSS injected after the base styles.

    Returns:
        HTML with ``<style>`` blocks substituted for the placeholder.

    Raises:
        ValueError: If ``html`` does not contain ``CSS_PLACEHOLDER``.
    """
    if CSS_PLACEHOLDER not in html:
        raise ValueError(f"dashboard HTML missing CSS placeholder: {CSS_PLACEHOLDER!r}")

    base_css = load_package_text(base_css_package, base_css_name)
    style_blocks = [f"<style>\n{base_css}\n</style>"]
    if extra_css:
        style_blocks.append(f"<style>\n{extra_css}\n</style>")

    return html.replace(CSS_PLACEHOLDER, "\n".join(style_blocks), 1)


def load_dashboard_html(
    package: str,
    html_filename: str,
    extra_css_filename: str,
    fallback_dir: Path,
) -> str:
    """Load a dashboard HTML template and compose it with shared CSS.

    Args:
        package: Toolset package name (e.g. ``inventory_mcp``).
        html_filename: Dashboard HTML filename within the package.
        extra_css_filename: Dashboard-specific CSS filename within the package.
        fallback_dir: Directory used when package resources are unavailable.

    Returns:
        Composed dashboard HTML ready to serve as an MCP App resource.
    """
    html = load_package_text_with_fallback(package, (html_filename,), fallback_dir)
    extra_css = load_package_text_with_fallback(package, (extra_css_filename,), fallback_dir)
    return compose_dashboard_html(html, extra_css=extra_css)
