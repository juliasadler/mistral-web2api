"""会话管理：从 data/session.json 加载 Mistral 登录态，检查有效期。"""
import json
import os
from datetime import datetime, timezone

SESSION_PATH = os.path.normpath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'session.json'))


class SessionExpired(Exception):
    pass


def load_session():
    """返回 (cookie_header, csrf_token)。过期则抛 SessionExpired。"""
    if not os.path.exists(SESSION_PATH):
        raise SessionExpired('data/session.json 不存在，请先运行 cdp/kratos-login.py 登录')
    with open(SESSION_PATH) as f:
        sess = json.load(f)
    meta = sess.get('_meta', {})
    exp = meta.get('expires_at')
    if exp:
        # "2027-01-15T17:29:38.701444554Z" -> 截断到微秒
        exp_clean = exp[:26] + '+00:00' if exp.endswith('Z') else exp
        try:
            exp_dt = datetime.fromisoformat(exp_clean.replace('Z', '+00:00'))
            if exp_dt < datetime.now(timezone.utc):
                raise SessionExpired(f'session 已过期（{exp}），请重跑 cdp/kratos-login.py')
        except SessionExpired:
            raise
        except Exception:
            pass  # 解析失败就不校验
    cookies = sess.get('cookies', {})
    if not cookies:
        raise SessionExpired('session.json 里没有 cookie，请重跑 cdp/kratos-login.py')
    cookie_header = '; '.join(f"{n}={v['value']}" for n, v in cookies.items())
    csrf = cookies.get('csrftoken', {}).get('value', '')
    return cookie_header, csrf
