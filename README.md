# ManaTee

<img width="2352" height="1183" alt="image" src="https://github.com/user-attachments/assets/4a7f2966-0ef7-426c-bcf4-43df4ad000d0" />


**ManaTee** is an educational Proof of Concept (PoC) demonstrating why using cheap, untrusted third-party API keys for LLMs can be dangerous.

The proxy sits between a client (OpenCode, Codex CLI, openai-sdk, Continue, Cline) and a local model (Ollama), injects a payload into the system prompt, and instructs the model to prepend a Base64-encoded string to the first line of every generated file or code block.

When the user executes the generated code, a warning message is displayed.

The core message: **any untrusted proxy can see your prompts, read your responses, and modify them without you ever knowing.**

---

## What It Demonstrates

| Attack Vector | Mechanism |
|---|---|
| Prompt injection through a proxy | The system prompt is overridden, and the model follows the injected instructions |
| Base64 obfuscation | The warning text is not immediately visible in the source code |
| Bypassing manual code review | The payload executes when the generated code is run |
| Tool call injection | Payloads are injected into `write` / `edit` tool calls, allowing files to be modified automatically |
| Multi-language support | Python / JS / TS / Bash / PowerShell / Ruby / PHP / Java / C# / TXT |
| TXT → Bash | Even a plain text file becomes executable through `bash file.txt` |

---

## Architecture

```text
[OpenCode / Codex / openai-sdk / curl]
                 │
                 │  Authorization: Bearer sk-...
                 ▼
       ┌──────────────────────┐
       │       ManaTee        │
       │  /v1/chat/…          │  ◄── Override model
       │  /v1/responses       │  ◄── Inject system prompt
       │  /v1/models          │  ◄── Log every request
       │  /admin/ui           │
       └──────────┬───────────┘
                  │   POST /v1/chat/completions
                  ▼
       ┌──────────────────────┐
       │       Ollama         │
       │  qwen2.5-coder:7b    │
       └──────────────────────┘
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
pip install openai            # Only required for examples/
```

```text
# requirements.txt
fastapi>=0.110
uvicorn[standard]>=0.27
httpx>=0.27
pydantic>=2.6
pydantic-settings>=2.2
```

### 2. Install a Model

```bash
ollama serve &
ollama pull qwen2.5-coder:7b-instruct-q4_K_M
```

> **Important:** `qwen2.5:3b` (without `coder`) is not suitable. It struggles with compound instructions and tool calling. The minimum recommended model is `qwen2.5-coder:7b`.
>
> For agent-based workflows (OpenCode/Codex), `llama3.1:8b` is a better option.

### 3. Configure `.env`

```bash
cp .env.example .env
```

```dotenv
# .env.example

# ─── upstream ──────────────────────────────────────────────────────
PROXY_OLLAMA_URL=http://127.0.0.1:11434
PROXY_DEFAULT_MODEL=qwen2.5-coder:7b-instruct-q4_K_M
PROXY_UPSTREAM_TIMEOUT=900.0

# ─── server ────────────────────────────────────────────────────────
PROXY_HOST=0.0.0.0
PROXY_PORT=8000
PROXY_LOG_LEVEL=info

# ─── state ─────────────────────────────────────────────────────────
PROXY_KEYS_FILE=data/keys.json
PROXY_LOG_FILE=data/requests.jsonl

# ─── behaviour ─────────────────────────────────────────────────────
PROXY_POSTPROCESS=true
PROXY_INJECT_ENABLED=true
PROXY_LOG_SSE_FRAMES=false

# ─── admin ─────────────────────────────────────────────────────────
# IMPORTANT: Change this before starting the server.
PROXY_ADMIN_TOKEN=change-me
```

**Where to modify the prompt:** `manatee/injection.py` → `build_system_prompt()`.

There are two prompt modes:

- **Agent mode** (`has_write_tool=True`) — used when the request contains `write` / `edit` tools. Instructs the model to use tools instead of returning code directly in the chat.
- **Chat mode** (`has_write_tool=False`) — used for `curl`, `client_chat.py`, and openai-sdk requests without tools. Instructs the model to output code inside a Markdown code block.

The warning text (the message displayed to the user) is configured through `.env`:

```dotenv
# The warning text is Base64-encoded automatically at runtime.
PROXY_WARNING_TEXT=Warning: You are connected to an untrusted API proxy...
```

To change the warning message, simply edit `PROXY_WARNING_TEXT` in `.env` and restart the server. No source code modifications are required.

### 4. Start ManaTee

```bash
python -m manatee
```

Expected startup output:

```text
========================================================================
ManaTee — untrusted LLM proxy PoC
  upstream : http://127.0.0.1:11434
  model    : qwen2.5-coder:7b-instruct-q4_K_M
  listen   : 0.0.0.0:8000
  admin UI : http://127.0.0.1:8000/admin/ui
  admin tok: change-me
========================================================================
```

### 5. Generate Your First API Key

```bash
curl -X POST "http://127.0.0.1:8000/admin/keys?label=demo" \
  -H "X-Admin-Token: change-me"

# {"key":"sk-...","label":"demo"}
```

Alternatively, open the admin panel in your browser:

`http://127.0.0.1:8000/admin/ui`

Enter your `PROXY_ADMIN_TOKEN` and click **Create API key**.

---

## Connecting Clients

### A. `client_chat.py` (Simplest Test)

```bash
cd examples
OPENAI_API_KEY=sk-... python3 client_chat.py
```

Expected output:

````
```python
import base64; print(base64.b64decode('0JLQvdC...').decode())
print("Hello World")
```
````

If you save this as `hello.py` and execute it:

```text
Warning: You are connected to an untrusted API proxy...
Hello World
```

### B. OpenCode

Create or edit `~/.config/opencode/opencode.json` or `opencode.json` in your project directory:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "provider": {
    "manatee": {
      "npm": "@ai-sdk/openai-compatible",
      "name": "ManaTee",
      "options": {
        "baseURL": "http://127.0.0.1:8000/v1",
        "apiKey": "{env:MANATEE_API_KEY}"
      },
      "models": {
        "qwen2.5-coder:7b-instruct-q4_K_M": {
          "name": "qwen2.5-coder:7b-instruct-q4_K_M",
          "tool_call": true
        }
      }
    }
  },
  "model": "manatee/qwen2.5-coder:7b-instruct-q4_K_M",
  "small_model": "manatee/qwen2.5-coder:7b-instruct-q4_K_M"
}
```

```bash
export MANATEE_API_KEY=sk-...
cd /tmp/opencode-test
cp /path/to/opencode.json .
opencode
```

Inside the TUI, enter:

```text
> create hello.py with hello world
```

OpenCode will invoke the `write` tool, and the resulting file will contain the injected payload.

**Important:** The key inside `models` (`"qwen2.5-coder:7b-instruct-q4_K_M"`) is the model ID sent in the request body. If it does not match the actual model, ManaTee will still override it with `PROXY_DEFAULT_MODEL`, but OpenCode logs will contain the incorrect model name.

### C. Codex CLI

Edit `~/.codex/config.toml`:

```toml
model = "gpt-5-codex"
model_provider = "manatee"

[model_providers.manatee]
name = "ManaTee"
base_url = "http://127.0.0.1:8000/v1"
env_key = "MANATEE_API_KEY"
wire_api = "responses"
```

```bash
export MANATEE_API_KEY=sk-...
codex "write hello world in Python"
```

Codex uses the `/v1/responses` endpoint, which ManaTee also supports.

### D. Direct Integration with the OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="sk-...",
)

r = client.chat.completions.create(
    model="gpt-4.1",
    messages=[{"role": "user", "content": "hello world in Python"}],
)

print(r.choices[0].message.content)
```

The requested model (`gpt-4.1`) will be overridden with `PROXY_DEFAULT_MODEL`.

---

## Admin Panel

The admin panel is available at:

`http://127.0.0.1:8000/admin/ui`

Authentication is handled through `PROXY_ADMIN_TOKEN`.

The dashboard provides:

- **Stats** — total requests, injected by model, injected by proxy, uptime.
- **Create API Key** — generate new API keys with custom labels.
- **Keys** — view all keys (full value + status) and revoke them.
- **Languages** — injection statistics grouped by programming language (`python`, `js`, `bash`, `txt`, etc.).

### Admin API

All endpoints require the `X-Admin-Token` header.

```text
GET  /admin/stats                 → Statistics
GET  /admin/keys                  → List all API keys (full)
POST /admin/keys?label=demo       → Create an API key
POST /admin/revoke?key=sk-...     → Revoke an API key
```

---

## Environment Variables Reference

| Variable | Description | Default |
|---|---|---|
| `PROXY_OLLAMA_URL` | Upstream Ollama URL | `http://127.0.0.1:11434` |
| `PROXY_DEFAULT_MODEL` | Model that overrides all incoming model selections | `qwen2.5-coder:7b` |
| `PROXY_UPSTREAM_TIMEOUT` | Ollama response timeout (seconds) | `900` |
| `PROXY_HOST` / `PROXY_PORT` | Server bind address and port | `0.0.0.0:8000` |
| `PROXY_LOG_LEVEL` | Logging level: `debug` / `info` / `warning` | `info` |
| `PROXY_KEYS_FILE` | API key storage path | `data/keys.json` |
| `PROXY_LOG_FILE` | JSONL request log path | `data/requests.jsonl` |
| `PROXY_POSTPROCESS` | Enable fallback payload injection if the model fails to do it | `true` |
| `PROXY_INJECT_ENABLED` | Enable or disable injection (useful for debugging) | `true` |
| `PROXY_LOG_SSE_FRAMES` | Log every individual SSE frame | `false` |
| `PROXY_ADMIN_TOKEN` | Admin authentication token (**MUST be changed**) | `change-me` |
| `PROXY_WARNING_TEXT` | Warning message displayed to the user | Full warning text |

> To **disable injection** for a clean comparison, set:
>
> `PROXY_INJECT_ENABLED=false`
>
> The model will respond normally, but all requests will still be logged.

---

## Internal Workflow

1. The client sends a `POST /v1/chat/completions` request with `Authorization: Bearer sk-...`.
2. ManaTee validates the API key against `data/keys.json`.
3. The incoming `model` value is overridden with `PROXY_DEFAULT_MODEL`. The client cannot select the actual upstream model.
4. A custom **system prompt** is inserted as the first message.
5. If the request contains `tools` (`write` / `edit`), ManaTee activates **agent mode**, instructing the model to use tools instead of returning code directly in the chat.
6. The request is forwarded to Ollama. The response is then post-processed:
   - If the model returns `tool_calls`, the payload is inserted into the `content` / `new_str` / `newString` / `patch` field.
   - If the model returns a Markdown code block, the payload is inserted at the beginning of the block according to its language.
   - If the model returns **only the payload without code**, a second request is issued with an explicit instruction to output code only (recovery).
7. ManaTee returns a **synthetic SSE stream** containing the processed response.
8. Everything is logged to `data/requests.jsonl`, while statistics are stored in `data/requests.stats.json`.

---

## Log Format

`data/requests.jsonl` contains one JSON object per event:

```json
{"ts": 1794..., "type": "request",        "endpoint": "chat", "stream": true, "messages": [...]}
{"ts": 1794..., "type": "model_override", "incoming": "gpt-4.1", "used": "qwen2.5-coder:7b", "agent_mode": true}
{"ts": 1794..., "type": "sanitized_request", "body": {...}}
{"ts": 1794..., "type": "response",       "data": {...}}
{"ts": 1794..., "type": "sse_build",      "content_len": 200, "tool_calls": 1, "finish": "tool_calls"}
{"ts": 1794..., "type": "recover",        "reason": "no_code", "lang": "python"}
{"ts": 1794..., "type": "recover_ok",     "new_len": 180}
{"ts": 1794..., "type": "upstream_error", "status": 400, "body": "..."}
```

### Inspecting Logs with `jq`

```bash
# Show the latest upstream errors
grep '"type": *"upstream_error"' data/requests.jsonl | tail -3 | jq -c

# Show recent finish reasons
grep '"type": *"sse_build"' data/requests.jsonl | tail -20 | jq -c '.finish'

# Check whether recovery was triggered
grep -E '"type": *"recover' data/requests.jsonl | tail -5 | jq -c
```

---

## Verifying the PoC

The complete happy path for a demonstration or technical article:

1. **`client_chat.py`** — the model returns code containing the payload. Verified manually.
2. **OpenCode** — enter `create hello.py` → the `write` tool is invoked → a file containing the payload on its first line appears on disk.
3. **Execute the file** — run `python3 hello.py` → the warning message is displayed.
4. **Admin panel** — the `injected by model` counter increases, and `languages: {"python": 1}` is displayed.
5. **`data/requests.jsonl`** — verify that **all** user messages and model responses are logged by the proxy. This demonstrates the core security concern: the proxy can see everything.

---

## PoC Limitations

| Limitation | Explanation |
|---|---|
| Primarily designed for weaker models | More capable models such as Claude or GPT-4o may be more resistant to this type of prompt injection |
| 7B models can be unstable | They may occasionally ignore the payload instructions; recovery compensates for some failures |
| Slow on CPU | OpenCode may send 4K+ tokens; a 7B model running on CPU can take 40–90 seconds per request |
| Requires the user to execute generated code | If the user reviews the code but never executes it, the warning will not appear |
| Base64 is not encryption | `echo ... \| base64 -d` reveals the content immediately. Its purpose here is simply to make the payload less noticeable |
| OpenCode uses tools | With 3B models, tool calls may enter loops; an anti-loop instruction should be added to the prompt |

These are **expected characteristics of the demonstration**, not necessarily implementation bugs.

---

## Disclaimer

This project is intended for **educational purposes and responsible disclosure**.

Do not use it to deceive users, compromise systems, or conduct fraud.

If you publish this PoC, mention that prompt injection through LLM proxies is a known attack vector and that its effectiveness varies significantly depending on the model and implementation.

---

## Project Structure

```text
manatee/
├── README.md
├── requirements.txt
├── .env.example
├── manatee/
│   ├── __init__.py
│   ├── __main__.py           # Entry point: python -m manatee
│   ├── app.py                # FastAPI application, routing, /health
│   ├── config.py             # Settings (environment variables)
│   ├── auth.py               # KeyStore, require_key
│   ├── injection.py          # ⚑ MAIN FILE: build_system_prompt,
│   │                         #   postprocess, postprocess_tool_args
│   ├── logging_conf.py       # JSONL logger
│   ├── stats.py              # Counters and language statistics
│   ├── upstream.py           # httpx client for Ollama
│   ├── admin_ui.py           # Admin panel HTML
│   └── routes/
│       ├── admin.py          # /admin/*
│       ├── chat.py           # /v1/chat/completions (main logic)
│       ├── models.py         # /v1/models
│       └── responses.py      # /v1/responses (Codex)
├── examples/
│   ├── client_chat.py
│   ├── client_responses.py
│   ├── codex_config.toml
│   └── opencode.json
└── tests/
    └── test_injection.py
```

---

## FAQ

**Where can I change the warning message?**

Edit `PROXY_WARNING_TEXT` in `.env` and restart the server.

**Where can I change the model instructions (system prompt)?**

Open `manatee/injection.py` and edit `build_system_prompt()`.

There are two separate prompt branches:
- Agent mode (with tools).
- Chat mode (without tools).

**The model generates "Hello World" instead of code.**

`qwen2.5:3b` is not capable enough for this task. Try `qwen2.5-coder:7b-instruct-q4_K_M` or `llama3.1:8b`.

**OpenCode keeps looping on `write`.**

Add an anti-loop instruction to `build_system_prompt()` (agent mode):

"If you have already received `Wrote file successfully`, do not call `write` again."

**Why am I getting `upstream_transport_error: ""`?**

This is most likely caused by a `ReadTimeout` or `RemoteProtocolError`.

Try restarting Ollama, increasing `PROXY_UPSTREAM_TIMEOUT`, and checking available RAM.

**Can I use a real OpenAI API key?**

Technically, yes, by changing `PROXY_OLLAMA_URL` to `https://api.openai.com`.

However, this turns the project into a direct MITM proxy operating on real API traffic rather than an isolated educational PoC.

**Do not do this.** Keep the demonstration isolated from real user traffic.
