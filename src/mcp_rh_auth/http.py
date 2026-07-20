"""Shared httpx client for outbound HTTPS calls (JWKS discovery, etc.)."""

from __future__ import annotations

import logging
import os
import ssl

logger = logging.getLogger(__name__)

import certifi
import httpx

_httpx_async_client: httpx.AsyncClient | None = None  # pylint: disable=invalid-name


def _extra_ca_cert_file() -> str | None:
    """Return an optional extra CA bundle.

    Use EXTRA_CA_CERTS for development (e.g. macOS with a corporate proxy).
    Avoid setting SSL_CERT_FILE via ``set -a`` as OpenSSL applies it process-wide
    and can break third-party HTTPS clients.
    """
    return os.getenv("EXTRA_CA_CERTS") or os.getenv("SSL_CERT_FILE")


def httpx_verify_setting() -> bool | ssl.SSLContext:
    """Return the ``verify`` argument for httpx clients.

    Builds a trust store from certifi (public CAs) plus an optional extra CA
    bundle from EXTRA_CA_CERTS or SSL_CERT_FILE. Set SSL_VERIFY=false to
    disable TLS verification entirely (development only).
    """
    if os.getenv("SSL_VERIFY", "true").strip().lower() in {"0", "false", "no", "off"}:
        logger.warning("TLS verification disabled via SSL_VERIFY — do not use in production")
        return False

    context = ssl.create_default_context(cafile=certifi.where())
    cert_file = _extra_ca_cert_file()
    if cert_file:
        context.load_verify_locations(cafile=cert_file)
    return context


def get_httpx_async_client(*, timeout: float = 10.0) -> httpx.AsyncClient:
    """Shared async httpx client (singleton). Used for JWKS fetches."""
    global _httpx_async_client  # pylint: disable=global-statement
    if _httpx_async_client is None:
        _httpx_async_client = httpx.AsyncClient(
            timeout=timeout,
            verify=httpx_verify_setting(),
        )
    return _httpx_async_client
