"""Mistral 网页版 API 客户端：调 /api/chat，解析 tRPC SSE，产出文本流。"""
import json
import random
import string
from datetime import datetime

import httpx

from .session import load_session

CHAT_URL = 'https://chat.mistral.ai/api/chat'
UPSTREAM_MODEL = 'mistral-large-latest'


def _rand_id(n=8):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))


def build_body(prompt_text, model=UPSTREAM_MODEL):
    today = datetime.now().strftime('%Y-%m-%d')
    return {
        'content': [{'type': 'text', 'text': prompt_text}],
        'mode': 'create',
        'productType': 'work',  # "chat" 已下线，必须用 "work"
        'model': model,
        'stableAnonymousIdentifier': _rand_id(6),
        'features': [],
        'incognito': False,
        'files': [],
        'clientPromptData': {
            'currentDate': today,
            'userTimezone': 'T+08:00 (Asia/Shanghai)',
        },
        'disabledFeatures': [],
    }


def messages_to_prompt(messages):
    """OpenAI messages -> 单段 prompt 文本（system 前置，role 标注）。"""
    parts = []
    for m in messages:
        role = m.get('role', 'user')
        content = m.get('content', '')
        if isinstance(content, list):  # 多模态：只取文本
            content = ' '.join(
                p.get('text', '') for p in content if p.get('type') == 'text')
        if role == 'system':
            parts.append(f'[System]\n{content}')
        elif role == 'assistant':
            parts.append(f'Assistant: {content}')
        else:
            parts.append(f'User: {content}')
    return '\n\n'.join(parts)


class RateLimited(Exception):
    def __init__(self, retry_after):
        self.retry_after = retry_after
        super().__init__(f'上游限流，需等待约 {retry_after // 60} 分钟')


def parse_sse_line(line):
    """解析一行 `<n>:<json>`，返回 (text_delta, done)。限流则抛 RateLimited。"""
    line = line.strip()
    if not line or ':' not in line:
        return None, False
    try:
        payload = json.loads(line.split(':', 1)[1])
    except Exception:
        return None, False
    if payload is None:
        # "8:null" 结束标记
        return None, True
    # 限流：6:{"message":"Message rate limit reached",...,"retryAfterSeconds":7905}
    if isinstance(payload, dict) and payload.get('category') == 'rate_limit':
        raise RateLimited(payload.get('retryAfterSeconds', 0))
    data = payload.get('json')
    if data is None:
        return None, False
    if not isinstance(data, dict):
        return None, False
    for p in data.get('patches') or []:
        path = p.get('path', '')
        op = p.get('op', '')
        val = p.get('value')
        # 短回复：replace /contentChunks，value 是 [{"type":"text","text":"..."}]
        if path == '/contentChunks' and isinstance(val, list):
            txt = ''.join(i.get('text', '') for i in val
                          if isinstance(i, dict) and i.get('type') == 'text')
            if txt:
                return ('[FULL]' + txt), False
        if op == 'append' and path.startswith('/contentChunks'):
            if isinstance(val, str):
                return val, False
        if path == '/content' and isinstance(val, str):
            return ('[FULL]' + val), False
    return None, False


async def chat_stream(prompt_text, model=UPSTREAM_MODEL):
    """异步生成器：yield 文本增量。"""
    cookie_header, csrf = load_session()
    headers = {
        'Content-Type': 'application/json',
        'Cookie': cookie_header,
        'Origin': 'https://chat.mistral.ai',
        'Referer': 'https://chat.mistral.ai/chat',
        'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                       'AppleWebKit/537.36 (KHTML, like Gecko) '
                       'Chrome/120.0 Safari/537.36'),
    }
    if csrf:
        headers['X-CSRFTOKEN'] = csrf
    proxy = __import__('os').environ.get('https_proxy') or __import__('os').environ.get('HTTPS_PROXY')
    async with httpx.AsyncClient(proxy=proxy, timeout=120) as client:
        async with client.stream('POST', CHAT_URL,
                                 json=build_body(prompt_text, model),
                                 headers=headers) as resp:
            if resp.status_code == 401:
                raise RuntimeError('上游返回 401，会话可能过期，请重跑 cdp/kratos-login.py')
            resp.raise_for_status()
            buf = ''
            async for chunk in resp.aiter_text():
                buf += chunk
                while '\n' in buf:
                    line, buf = buf.split('\n', 1)
                    delta, done = parse_sse_line(line)
                    if delta:
                        if delta.startswith('[FULL]'):
                            yield ('FULL', delta[6:])
                        else:
                            yield ('DELTA', delta)
                    if done:
                        return
            if buf.strip():
                delta, _ = parse_sse_line(buf)
                if delta:
                    yield ('DELTA', delta[6:] if delta.startswith('[FULL]') else delta)
