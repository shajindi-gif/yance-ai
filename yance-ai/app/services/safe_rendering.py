"""Security boundaries shared by server-side HTML document renderers."""

from html import escape
from typing import NoReturn


def escape_html(value: object | None) -> str:
    """Convert an untrusted scalar to escaped HTML text."""
    return escape("" if value is None else str(value), quote=True)


def deny_external_url_fetcher(url: str, *args: object, **kwargs: object) -> NoReturn:
    """Deny every renderer-initiated URL/file fetch.

    Generated documents currently contain inline CSS and no external assets, so
    any fetch attempt is unexpected and must fail closed.
    """
    raise ValueError("External resource loading is disabled for document rendering")
