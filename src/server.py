"""mistral-web2api：Mistral Le Chat 网页版 -> OpenAI 兼容 API。监听 127.0.0.1:8082。"""
import json
import os
import secrets
import time
import uuid

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import upstream
from .session import SessionExpired
from .upstream import RateLimited

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_KEY_PATH = os.path.join(BASE_DIR, 'api_key.txt')
MODEL_ID = 'mistral-large-latest'

app = FastAPI(title='mistral-web2api')


def get_api_key():
    if not os.path.exists(API_KEY_PATH):
        key = 'sk-' + secrets.token_hex(16)
        with open(API_KEY_PATH, 'w') as f:
            f.write(key)
        os.chmod(API_KEY_PATH, 0o600)
        return key
    with open(API_KEY_PATH) as f:
        return f.read().strip()


API_KEY = get_api_key()


def check_auth(authorization: str = ''):
    if not authorization.startswith('Bearer '):
        raise HTTPException(401, 'Missing Bearer token')
    if authorization[7:] != API_KEY:
        raise HTTPException(401, 'Invalid API key')


@app.get('/health')
def health():
    return {'ok': True}


@app.get('/v1/models')
def list_models(authorization: str = Header('')):
    check_auth(authorization)
    return {
        'object': 'list',
        'data': [{
            'id': MODEL_ID,
            'object': 'model',
            'created': int(time.time()),
            'owned_by': 'mistral-web2api',
        }],
    }


def _openai_chunk(cid, model, delta=None, finish=None):
    d = {'id': cid, 'object': 'chat.completion.chunk',
         'created': int(time.time()), 'model': model, 'choices': [{}]}
    if delta is not None:
        d['choices'][0]['delta'] = delta
    if finish is not None:
        d['choices'][0]['finish_reason'] = finish
    return 'data: ' + json.dumps(d, ensure_ascii=False) + '\n\n'


@app.post('/v1/chat/completions')
async def chat_completions(request: Request, authorization: str = Header('')):
    check_auth(authorization)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, 'Invalid JSON')
    messages = body.get('messages', [])
    if not messages:
        raise HTTPException(400, 'messages 为空')
    stream = bool(body.get('stream', False))
    model = body.get('model', MODEL_ID)
    prompt = upstream.messages_to_prompt(messages)
    cid = 'chatcmpl-' + uuid.uuid4().hex[:12]

    if not stream:
        full_text = ''
        try:
            async for kind, text in upstream.chat_stream(prompt):
                if kind == 'FULL':
                    full_text = text
                    break
                full_text += text
        except SessionExpired as e:
            raise HTTPException(401, str(e))
        except RateLimited as e:
            raise HTTPException(429, str(e),
                                headers={'Retry-After': str(e.retry_after)})
        except Exception as e:
            raise HTTPException(502, f'上游调用失败: {e}')
        return {
            'id': cid, 'object': 'chat.completion',
            'created': int(time.time()), 'model': model,
            'choices': [{
                'index': 0,
                'message': {'role': 'assistant', 'content': full_text},
                'finish_reason': 'stop',
            }],
            'usage': {'prompt_tokens': 0, 'completion_tokens': 0, 'total_tokens': 0},
        }

    async def gen():
        yield _openai_chunk(cid, model, delta={'role': 'assistant'})
        yielded_any = False
        try:
            async for kind, text in upstream.chat_stream(prompt):
                if kind == 'FULL':
                    if yielded_any:
                        break  # 已有增量，全文跳过防重复
                    for piece in text.replace('\n\n', '\n').split('\n'):
                        if piece:
                            yield _openai_chunk(cid, model, delta={'content': piece + '\n'})
                            yielded_any = True
                    break
                yield _openai_chunk(cid, model, delta={'content': text})
                yielded_any = True
        except SessionExpired as e:
            yield _openai_chunk(cid, model, delta={'content': f'\n[会话过期: {e}]'})
        except RateLimited as e:
            yield _openai_chunk(cid, model, delta={'content': f'\n[上游限流: {e}]'})
        except Exception as e:
            yield _openai_chunk(cid, model, delta={'content': f'\n[上游错误: {e}]'})
        yield _openai_chunk(cid, model, finish='stop')
        yield 'data: [DONE]\n\n'

    return StreamingResponse(gen(), media_type='text/event-stream')


def main():
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8082, log_level='info')


if __name__ == '__main__':
    main()
