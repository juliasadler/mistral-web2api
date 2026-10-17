# mistral-web2api

Mistral Le Chat（chat.mistral.ai，现名 Vibe）网页版 → OpenAI 兼容 API 的本地网关。

在本地 `127.0.0.1:8082` 上暴露 OpenAI 兼容的 `/v1/models` 与 `/v1/chat/completions`（支持流式）接口，
底层调用 Le Chat 网页版聊天接口（`POST https://chat.mistral.ai/api/chat`，SSE 流式）。

## 原理

1. 用 Ory Kratos 流程脚本化登录网页版，拿到 `ory_session_*` 会话 cookie（约 3 个月有效）。
2. 网关收到 OpenAI 格式请求后，转调网页版 `/api/chat`（`productType: "work"`），解析 tRPC SSE 增量，转成 OpenAI chunk 格式返回。

## 快速开始

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 登录（密码经 stdin 传入，不落盘；会话存 data/session.json，0600）
.venv/bin/python cdp/kratos-login.py
# 启动
.venv/bin/python -m src.server  # 127.0.0.1:8082
```

API Key 在 `api_key.txt`（首次启动自动生成，0600）。测试：

```bash
KEY=$(cat api_key.txt)
curl http://127.0.0.1:8082/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
  -d '{"model":"mistral-large-latest","messages":[{"role":"user","content":"你好"}],"stream":true}'
```

## 限流说明

Mistral Free 账号网页版限流较严（约每小时几次调用即 429），本网关仅适合低频个人使用。
网关会透传 429（HTTP 429 + `Retry-After`），请勿高频/并发调用。

## 隐私与安全

- 账号会话只存本地 `0600` 权限文件（`data/session.json`），**绝不提交到本仓库**。
- `.gitignore` 已排除所有凭证类文件。

## 免责

本项目仅供学习研究网页 API 逆向技术。使用网页版接口可能违反 Mistral 服务条款，
请使用小号并控制调用频率，风险自负。
