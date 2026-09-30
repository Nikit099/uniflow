from app.api.max_webhook import _open_attachment
from app.core.config import Settings


def test_open_attachment_uses_max_bot_deep_link() -> None:
    settings = Settings(public_base_url="https://uniflow.example", max_bot_username="@uniflow_bot")
    attachments = _open_attachment(
        settings,
        "Open UniFlow",
        "8c8a326e-1df8-4d87-aaf1-d9ad6411ef60",
    )
    button = attachments[0]["payload"]["buttons"][0][0]
    assert button["url"] == (
        "https://max.ru/uniflow_bot?startapp=case_8c8a326e-1df8-4d87-aaf1-d9ad6411ef60"
    )


def test_local_attachment_targets_mini_app_url() -> None:
    settings = Settings(public_base_url="http://localhost:8080/")
    attachments = _open_attachment(settings, "Open UniFlow")
    button = attachments[0]["payload"]["buttons"][0][0]
    assert button["url"] == "http://localhost:8080?startapp"
