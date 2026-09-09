# Rasa Custom Channel Connector — WhatsApp

A Rasa Open Source custom channel built on your own
[whatsloon](https://github.com/maharanasarkar/whatsloon) SDK
(`whatsloon>=3.0.0`, modern v3 client) for the WhatsApp Cloud API.
Chat with your Rasa assistant directly from WhatsApp.

## Features

- **Two-way messaging** via the WhatsApp Cloud API (`graph.facebook.com`).
- **Text** with automatic chunking to Meta's 4096-character limit.
- **Interactive reply buttons** (up to 3 per message; extras fall back to a
  numbered list; titles truncated to Meta's 20-character limit).
- **Media**: images, video, audio, documents by URL, with optional captions.
- **Templates and locations** via `send_custom_json` (see below).
- **Inbound**: text, button/list replies (payload routed as user text), media
  captions, locations. Delivery statuses and unknown events are ignored.
- **Webhook security**: `hub.verify_token` handshake plus optional
  `X-Hub-Signature-256` HMAC verification via `app_secret` (fail-closed).

## Prerequisites

- Python 3.9+
- A Rasa Open Source project (uses the `rasa.core.channels` custom-channel API).
- A WhatsApp Business Account with a Meta app: **access token**,
  **phone number ID**, and a **verify token** you choose for the webhook.
- A public HTTPS URL for the webhook during development (e.g. via ngrok).

## Installation

1. Clone this repository (or copy `whatsapp.py` into your Rasa project so it
   is importable, e.g. the project root):
   ```
   git clone https://github.com/maharanasarkar/rasa-whatsapp_connector.git
   ```
2. Install the SDK:
   ```
   pip install -r requirements.txt
   ```
3. Add the channel to your Rasa `credentials.yml` (copy from
   `credentials.yml.example`):
   ```
   whatsapp.WhatsAppInput:
     access_token: "<WHATSAPP_ACCESS_TOKEN>"
     phone_number_id: "<PHONE_NUMBER_ID>"
     verify_token: "<VERIFY_TOKEN>"
     app_secret: ""
     graph_api_version: "latest"
   ```
   If `whatsapp.py` lives in a package, prefix the module path accordingly
   (e.g. `channels.whatsapp.WhatsAppInput`).

### Configuration reference

| Key | Required | Description |
|---|---|---|
| `access_token` | yes | Meta WhatsApp access token (`auth_token` accepted as alias). |
| `phone_number_id` | yes | Sender phone number ID from the Meta app dashboard. |
| `verify_token` | yes | Token Meta must echo during webhook subscription. |
| `app_secret` | no | Meta app secret; enables HMAC signature checks on webhooks. |
| `graph_api_version` | no | Pinned version or `"latest"` (default). |
| `debug_mode` | no | Re-raise handler errors instead of logging them (default `true`). |

4. In the Meta app dashboard, subscribe the webhook to callback URL
   `https://<your-host>/webhooks/whatsapp/webhook` using your verify token,
   and subscribe to the `messages` field.
5. Run Rasa and talk to the bot on WhatsApp:
   ```
   rasa run
   ```

## Sending rich messages from Rasa

Buttons work out of the box with standard Rasa responses. For templates or
locations, use a custom JSON payload:

```
- custom:
    template:
      name: "hello_world"
      language: "en_US"
```

```
- custom:
    location:
      latitude: 28.6139
      longitude: 77.2090
      name: "New Delhi"
```

Inbound messages carry `metadata` with `message_id`, `message_type`, and
`timestamp` for use in custom actions or trackers.

## Testing

```
python -m pytest -q
```

The suite covers inbound text extraction (text, button/list replies, media
captions, locations), chunking limits, handshake rejection, and webhook
envelope parsing. Rasa and Sanic are stubbed in tests (runtime-only
dependencies); run a live `rasa run` + webhook test before release.

## Migrating from heyoo

This connector previously used the `heyoo` package. It now uses `whatsloon`
exclusively — remove `heyoo` from your environment. `auth_token` in existing
`credentials.yml` files keeps working as an alias for `access_token`.

## Contributing

- Fork, create a feature branch, add/extend tests in `tests/`.
- Run `python -m pytest -q` and `python -m ruff check whatsapp.py tests/ --select I,BLE`.
- Open a pull request describing behavior change, verification, and risks.

## License

MIT — see [LICENSE](LICENSE).
