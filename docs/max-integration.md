# MAX integration

The Mini App loads the official MAX Bridge script and submits `window.WebApp.initData` to `/auth/max`. If the Bridge object is unavailable, the signed launch data is read from the `WebAppData` URL fragment. Both paths send the signed string for backend validation; identity is never taken from `initDataUnsafe`. A `case_<uuid>` start parameter opens the case after session restoration; the case API still enforces ownership.

The backend implements the documented `HMAC-SHA256(HMAC-SHA256("WebAppData", bot_token), sorted_init_data)` validation, exact hash occurrence check and maximum auth age. It then creates a hashed opaque session in an HttpOnly/Secure/SameSite cookie. If MAX authentication fails, the app shows a retry state and does not expose demo login inside a MAX launch.

The real bot client uses `https://platform-api2.max.ru`, the `Authorization` header and `POST /messages`. Production uses webhook delivery, validates `X-Max-Bot-Api-Secret`, and does not use long polling. `/start`, `/help`, `/cases` and `/language` are localized commands. The bot returns a MAX deep link in the form `https://max.ru/<bot-username>?startapp=case_<uuid>`; the launch payload contains a random case identifier, not personal data. Local mode uses the Mini App URL and a synthetic payload.

Local delivery uses a clearly labelled fake adapter and does not impersonate MAX.
