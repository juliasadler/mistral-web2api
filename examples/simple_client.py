"""用 OpenAI 官方客户端调用 mistral-web2api 网关的最小示例。

前置：网关已在 127.0.0.1:8082 运行，API Key 见项目根目录 api_key.txt。
"""
import os

from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8082/v1",
    api_key=os.environ.get("MISTRAL_WEB2API_KEY", "your-api-key-here"),
)

# 非流式
resp = client.chat.completions.create(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": "你好"}],
)
print(resp.choices[0].message.content)

# 流式
stream = client.chat.completions.create(
    model="mistral-large-latest",
    messages=[{"role": "user", "content": "讲个笑话"}],
    stream=True,
)
for chunk in stream:
    delta = chunk.choices[0].delta.content
    if delta:
        print(delta, end="", flush=True)
print()
