import hashlib
import hmac
import json
import secrets
import time
from base64 import urlsafe_b64encode
from dataclasses import dataclass
from urllib.parse import parse_qsl

from app.core.config import Settings


def token_urlsafe() -> str:
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def csrf_token() -> str:
    return urlsafe_b64encode(secrets.token_bytes(24)).decode().rstrip("=")


@dataclass(frozen=True)
class MaxLaunchUser:
    max_user_id: str
    username: str | None
    first_name: str
    last_name: str | None
    language_code: str | None


class InvalidMaxLaunch(ValueError):
    pass


def validate_max_init_data(
    init_data: str, bot_token: str, max_age_seconds: int, now: int | None = None
) -> MaxLaunchUser:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    keys = [key for key, _ in pairs]
    if len(keys) != len(set(keys)):
        raise InvalidMaxLaunch("Duplicate parameter")
    values = dict(pairs)
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise InvalidMaxLaunch("Missing hash")
    auth_date_raw = values.get("auth_date")
    if not auth_date_raw or not auth_date_raw.isdigit():
        raise InvalidMaxLaunch("Invalid auth_date")
    current_time = now or int(time.time())
    if (
        current_time - int(auth_date_raw) > max_age_seconds
        or int(auth_date_raw) > current_time + 30
    ):
        raise InvalidMaxLaunch("Expired auth data")
    check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_hash):
        raise InvalidMaxLaunch("Invalid signature")
    try:
        user = json.loads(values["user"])
        return MaxLaunchUser(
            max_user_id=str(user["id"]),
            username=user.get("username"),
            first_name=user.get("first_name", "MAX user"),
            last_name=user.get("last_name"),
            language_code=user.get("language_code"),
        )
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise InvalidMaxLaunch("Invalid user data") from exc


def verify_origin(origin: str | None, settings: Settings) -> bool:
    return origin is None or origin in settings.origins
