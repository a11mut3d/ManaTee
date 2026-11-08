import os

from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://ip:8000/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "token"),
)

resp = client.chat.completions.create(
    model="qwen2.5-coder:3b",
    messages=[{"role": "user", "content": "Напиши hello world на Python"}],
)
print(resp.choices[0].message.content)
