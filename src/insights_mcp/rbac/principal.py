"""Infer caller principal type from OAuth token when available."""

from __future__ import annotations

from typing import Any

import jwt


def classify_principal_from_token(access_token: str | None) -> dict[str, Any]:
    """Best-effort principal classification from JWT (no signature verification).

    Returns:
        dict with keys: principal_type, client_id, username_hint, note
    """
    if not access_token:
        return {
            "principal_type": "unknown",
            "client_id": None,
            "username_hint": None,
            "note": "No access token available to classify caller.",
        }

    try:
        payload = jwt.decode(
            access_token,
            options={"verify_signature": False, "verify_exp": False},
            algorithms=["HS256", "RS256"],
        )
    except jwt.PyJWTError:
        return {
            "principal_type": "unknown",
            "client_id": None,
            "username_hint": None,
            "note": "Could not decode access token.",
        }

    client_id = payload.get("clientId") or payload.get("azp")
    identity = payload.get("identity") or payload.get("claims", {}).get("identity")
    username = None
    identity_type = None
    if isinstance(identity, dict):
        identity_type = identity.get("type")
        user = identity.get("user")
        if isinstance(user, dict):
            username = user.get("username")
        elif isinstance(user, str):
            username = user

    if identity_type == "ServiceAccount" or (client_id and str(client_id).startswith("service-account")):
        return {
            "principal_type": "service_account",
            "client_id": client_id,
            "username_hint": username or client_id,
            "note": (
                "Permissions from GET /api/rbac/v1/access/ apply to this service account, "
                "not necessarily the human user in the chat."
            ),
        }

    if identity_type == "User" or username:
        return {
            "principal_type": "user",
            "client_id": client_id,
            "username_hint": username,
            "note": ("Permissions from GET /api/rbac/v1/access/ apply to this user principal."),
        }

    return {
        "principal_type": "unknown",
        "client_id": client_id,
        "username_hint": username,
        "note": "Could not determine if caller is a user or service account.",
    }


def extract_permissions_from_access_response(access_payload: dict[str, Any]) -> list[str]:
    """Extract permission strings from RBAC access API response."""
    data = access_payload.get("data", [])
    if not isinstance(data, list):
        return []
    perms: list[str] = []
    for item in data:
        if isinstance(item, dict) and "permission" in item:
            perm = item["permission"]
            if isinstance(perm, str) and perm not in perms:
                perms.append(perm)
    return perms
