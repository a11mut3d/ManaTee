import os

from openai import OpenAI

client = OpenAI(
    base_url=os.getenv("OPENAI_BASE_URL", "http://ip:8000/v1"),
    api_key=os.getenv("OPENAI_API_KEY", "token"),
)

resp = client.responses.create(
    model="gpt-5-codex",
    input="Сделай README.txt с описанием проекта",
)
for item in resp.output:
    if item.type == "message":
        for c in item.content:
            if c.type == "output_text":
                print(c.text)
