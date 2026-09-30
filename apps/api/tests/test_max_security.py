import hashlib
import hmac
import json
from urllib.parse import urlencode

import pytest

from app.core.security import InvalidMaxLaunch, validate_max_init_data


def signed_data(token: str, timestamp: int, start_param: str | None = None) -> str:
    values = {
        "auth_date": str(timestamp),
        "query_id": "demo",
        "user": json.dumps(
            {"id": 42, "first_name": "Test", "language_code": "ru"}, separators=(",", ":")
        ),
    }
    if start_param:
        values["start_param"] = start_param
    check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_valid_max_signature() -> None:
    result = validate_max_init_data(
        signed_data("secret", 2_000_000_000), "secret", 3600, now=2_000_000_010
    )
    assert result.max_user_id == "42"


def test_valid_max_start_parameter() -> None:
    result = validate_max_init_data(
        signed_data("secret", 2_000_000_000, "case_8c8a326e-1df8-4d87-aaf1-d9ad6411ef60"),
        "secret",
        3600,
        now=2_000_000_010,
    )
    assert result.max_user_id == "42"


def test_expired_and_invalid_max_signature() -> None:
    with pytest.raises(InvalidMaxLaunch, match="Expired"):
        validate_max_init_data(signed_data("secret", 100), "secret", 3600, now=10_000)
    with pytest.raises(InvalidMaxLaunch, match="signature"):
        validate_max_init_data(
            signed_data("secret", 2_000_000_000), "wrong", 3600, now=2_000_000_010
        )
