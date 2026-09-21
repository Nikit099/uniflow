# MAX integration

The Mini App reads `window.WebApp.initData`, platform/version/language and `start_param`. It uses the Bridge for closing confirmation and official link opening when available. Identity is never taken from `initDataUnsafe`.

The backend implements the documented `HMAC-SHA256(HMAC-SHA256("WebAppData", bot_token), sorted_init_data)` validation, exact hash occurrence check and maximum auth age. It then creates a hashed opaque session in an HttpOnly/Secure/SameSite cookie.

The real bot client uses `https://platform-api2.max.ru`, `Authorization` header and `POST /messages`. Production uses webhook delivery, validates `X-Max-Bot-Api-Secret`, and does not use long polling. `/start`, `/help`, `/cases` and `/language` are localized commands. Payloads contain opaque case references, never personal data.

Local delivery uses a clearly labelled fake adapter and does not impersonate MAX.
