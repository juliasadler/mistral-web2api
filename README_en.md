# mistral-web2api

[![stars](https://img.shields.io/github/stars/juliasadler/mistral-web2api)](https://github.com/juliasadler/mistral-web2api/stargazers)
[![license](https://img.shields.io/github/license/juliasadler/mistral-web2api)](./LICENSE)
[![last-commit](https://img.shields.io/github/last-commit/juliasadler/mistral-web2api)](https://github.com/juliasadler/mistral-web2api/commits/main)
[![CI](https://github.com/juliasadler/mistral-web2api/actions/workflows/ci.yml/badge.svg)](https://github.com/juliasadler/mistral-web2api/actions/workflows/ci.yml)

> Turn Mistral Le Chat (now "Vibe") web into an OpenAI-compatible API. Run locally, for personal use — your free account's web quota becomes callable through a standard interface.

> ⭐ If this project helped you, please consider giving it a star!

[中文](./README.md) | English

## ✨ Features

- **OpenAI compatible** — `/v1/chat/completions` and `/v1/models`, with `stream` support
- **API key auth** — `Authorization: Bearer`, suitable for local use
- **Scripted login** — fully automated Ory Kratos flow to obtain a session, no browser DevTools needed (`login.py`)
- **Long-lived session** — log in once, session lasts ~3 months
- **Rate-limit passthrough** — upstream 429 returns standard 429 + `Retry-After`, never swallowed

## 🚀 Installation

### Prerequisites

- Python 3.10+
- Network access to `chat.mistral.ai`
- A Mistral account (free tier works; a throwaway account is recommended)

### Install

```bash
git clone https://github.com/juliasadler/mistral-web2api.git
cd mistral-web2api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## Quick Start

```bash
# 1. Log in and get a session (password via stdin, never written to disk; session saved to data/session.json with 0600)
MISTRAL_EMAIL=you@example.com .venv/bin/python login.py

# 2. Start the gateway (127.0.0.1:8082)
.venv/bin/python -m src.server

# 3. Call it (API key in api_key.txt, auto-generated on first start)
curl http://127.0.0.1:8082/v1/chat/completions \
  -H "Authorization: Bearer $(cat api_key.txt)" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral-large-latest","messages":[{"role":"user","content":"Hello"}],"stream":true}'
```

See [`examples/simple_client.py`](./examples/simple_client.py) for a Python example using the official OpenAI client.

## ⚠️ Rate Limits

Mistral free accounts are strictly rate-limited on the web side (~a handful of calls per hour triggers 429, then ~2h cooldown).
This gateway is for low-frequency personal use only. Do not use it for high-frequency or concurrent workloads.

## How It Works

1. `login.py` walks the Ory Kratos password-login flow and obtains an `ory_session_*` session cookie.
2. The gateway translates OpenAI-format requests into web `POST /api/chat` calls (`productType: "work"`), parses the tRPC SSE deltas, and returns OpenAI-format chunks.

## 🤝 Contributing

Issues and PRs are welcome. Please do not paste personal accounts, cookies, passwords, or other private info in issues/PRs.

## 👤 Author

liyu — [GitHub](https://github.com/juliasadler)

## 📄 License

[MIT](./LICENSE)

---

**Disclaimer**: For learning and researching web API reverse engineering only. Not an official project, not affiliated with Mistral AI. Using the web interface may violate Mistral's Terms of Service; accounts risk restriction or ban — use a throwaway account and keep call frequency low. Mistral may change its web API at any time, breaking this project; availability and stability are not guaranteed. Use at your own risk.
