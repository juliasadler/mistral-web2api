# mistral-web2api

[![stars](https://img.shields.io/github/stars/juliasadler/mistral-web2api)](https://github.com/juliasadler/mistral-web2api/stargazers)
[![license](https://img.shields.io/github/license/juliasadler/mistral-web2api)](./LICENSE)
[![last-commit](https://img.shields.io/github/last-commit/juliasadler/mistral-web2api)](https://github.com/juliasadler/mistral-web2api/commits/main)

> 把 Mistral Le Chat（现名 Vibe）网页版转成 OpenAI 兼容 API，本地跑、自己用——免费账号的网页额度也能走标准接口调用。

## ✨ 功能特性

- **OpenAI 兼容** — `/v1/chat/completions` 与 `/v1/models`，支持 `stream` 流式
- **API Key 鉴权** — `Authorization: Bearer`，适合本地调用
- **脚本化登录** — Ory Kratos 流程全自动拿会话，无需浏览器抓包（`login.py`）
- **会话长效** — 登录一次，会话约 3 个月有效
- **限流透传** — 上游 429 时返回标准 429 + `Retry-After`，不吞错误

## 🚀 安装使用

### 前置条件

- Python 3.10+
- 能访问 `chat.mistral.ai` 的网络
- 一个 Mistral 账号（免费即可，建议用小号）

### 安装

```bash
git clone https://github.com/juliasadler/mistral-web2api.git
cd mistral-web2api
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```

## 快速开始

```bash
# 1. 登录拿会话（密码经 stdin 传入，不落盘；会话存 data/session.json，0600）
MISTRAL_EMAIL=you@example.com .venv/bin/python login.py

# 2. 启动网关（127.0.0.1:8082）
.venv/bin/python -m src.server

# 3. 调用（API Key 在 api_key.txt，首次启动自动生成）
curl http://127.0.0.1:8082/v1/chat/completions \
  -H "Authorization: Bearer $(cat api_key.txt)" \
  -H "Content-Type: application/json" \
  -d '{"model":"mistral-large-latest","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

## ⚠️ 限流说明

Mistral Free 账号网页版限流较严（实测约每小时几次调用即 429，需等约 2 小时）。
本网关仅适合低频个人使用，请勿高频/并发调用。

## 原理简介

1. `login.py` 走 Ory Kratos 密码登录流程，拿到 `ory_session_*` 会话 cookie。
2. 网关收到 OpenAI 格式请求后，转调网页版 `POST /api/chat`（`productType: "work"`），解析 tRPC SSE 增量，转成 OpenAI chunk 格式返回。

## 🤝 参与贡献

欢迎提 Issue / PR。请勿在 Issue/PR 中粘贴个人账号、cookie、密码等隐私信息。

## 👤 作者

liyu — [GitHub](https://github.com/juliasadler)

## 📄 许可证

[MIT](./LICENSE)

---

**免责**：本项目仅供学习研究网页 API 逆向技术。使用网页版接口可能违反 Mistral 服务条款，请使用小号并控制调用频率，风险自负。
