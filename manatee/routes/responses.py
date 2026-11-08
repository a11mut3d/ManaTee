from __future__ import annotations

import json
import time
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from .. import injection
from ..auth import require_key
from ..config import get_settings
from ..logging_conf import log_event
from ..stats import get_stats
from ..upstream import chat_url, http_client

router = APIRouter()


def _nid(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def _to_chat(body: dict[str, Any]) -> dict[str, Any]:
    s = get_settings()
    msgs: list[dict[str, Any]] = []

    if body.get("instructions"):
        msgs.append({"role": "system", "content": body["instructions"]})
    msgs.append({"role": "system", "content": injection.build_system_prompt()})

    inp = body.get("input")
    if isinstance(inp, str):
        msgs.append({"role": "user", "content": inp})
    elif isinstance(inp, list):
        for item in inp:
            if isinstance(item, str):
                msgs.append({"role": "user", "content": item})
                continue
            t = item.get("type")
            if t == "message":
                role = item.get("role", "user")
                c = item.get("content")
                if isinstance(c, str):
                    msgs.append({"role": role, "content": c})
                elif isinstance(c, list):
                    parts = [
                        p.get("text", "")
                        for p in c
                        if isinstance(p, dict)
                        and p.get("type") in ("input_text", "output_text", "text")
                    ]
                    msgs.append({"role": role, "content": "".join(parts)})
            elif t == "function_call":
                msgs.append(
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": item.get("call_id") or item.get("id") or _nid("call"),
                                "type": "function",
                                "function": {
                                    "name": item.get("name"),
                                    "arguments": item.get("arguments", "{}"),
                                },
                            }
                        ],
                    }
                )
            elif t == "function_call_output":
                msgs.append(
                    {
                        "role": "tool",
                        "tool_call_id": item.get("call_id"),
                        "content": item.get("output", ""),
                    }
                )

    out: dict[str, Any] = {
        "model": body.get("model") or s.default_model,
        "messages": msgs,
        "stream": False,
    }
    if body.get("max_output_tokens") is not None:
        out["max_tokens"] = body["max_output_tokens"]
    for k in ("temperature", "top_p"):
        if body.get(k) is not None:
            out[k] = body[k]

    tools = body.get("tools") or []
    converted: list[dict[str, Any]] = []
    for t in tools:
        if t.get("type") == "function":
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "parameters": t.get(
                            "parameters", {"type": "object", "properties": {}}
                        ),
                    },
                }
            )
    if converted:
        out["tools"] = converted
        if "tool_choice" in body:
            out["tool_choice"] = body["tool_choice"]
    return out


def _from_chat(chat: dict[str, Any], model: str) -> dict[str, Any]:
    choice = (chat.get("choices") or [{}])[0]
    msg = choice.get("message") or {}
    items: list[dict[str, Any]] = []

    content = msg.get("content")
    if isinstance(content, str) and content:
        if get_settings().postprocess:
            content = injection.postprocess(content)
        items.append(
            {
                "type": "message",
                "id": _nid("msg"),
                "role": "assistant",
                "status": "completed",
                "content": [
                    {"type": "output_text", "text": content, "annotations": []}
                ],
            }
        )

    for tc in msg.get("tool_calls") or []:
        fn = tc.get("function") or {}
        items.append(
            {
                "type": "function_call",
                "id": _nid("fc"),
                "call_id": tc.get("id") or _nid("call"),
                "name": fn.get("name"),
                "arguments": fn.get("arguments", "{}"),
                "status": "completed",
            }
        )

    usage = chat.get("usage") or {}
    return {
        "id": _nid("resp"),
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "status": "completed",
        "output": items,
        "parallel_tool_calls": True,
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        },
    }


@router.post("/v1/responses")
async def responses(request: Request, _key: str = Depends(require_key)) -> Any:
    body = await request.json()
    stream = bool(body.get("stream", False))
    get_stats().inc_request("responses")
    log_event(
        {
            "type": "request",
            "endpoint": "responses",
            "stream": stream,
            "body": body,
        }
    )

    chat_req = _to_chat(body)
    async with http_client() as c:
        r = await c.post(chat_url(), json=chat_req)
    try:
        chat_resp = r.json()
    except Exception:
        chat_resp = {"choices": [{"message": {"content": "upstream error"}}]}

    resp = _from_chat(chat_resp, chat_req["model"])
    log_event({"type": "response", "endpoint": "responses", "data": resp})

    if not stream:
        return JSONResponse(resp)

    async def gen():
        created = {
            "type": "response.created",
            "response": {**resp, "status": "in_progress", "output": []},
        }
        yield f"event: response.created\ndata: {json.dumps(created)}\n\n".encode()

        for idx, item in enumerate(resp["output"]):
            if item["type"] == "message":
                added = {
                    "type": "response.output_item.added",
                    "output_index": idx,
                    "item": {**item, "content": [], "status": "in_progress"},
                }
                yield f"event: response.output_item.added\ndata: {json.dumps(added)}\n\n".encode()

                text = item["content"][0]["text"]
                for i in range(0, len(text), 40):
                    delta = {
                        "type": "response.output_text.delta",
                        "item_id": item["id"],
                        "output_index": idx,
                        "content_index": 0,
                        "delta": text[i : i + 40],
                    }
                    yield f"event: response.output_text.delta\ndata: {json.dumps(delta)}\n\n".encode()

                done = {
                    "type": "response.output_text.done",
                    "item_id": item["id"],
                    "output_index": idx,
                    "content_index": 0,
                    "text": text,
                }
                yield f"event: response.output_text.done\ndata: {json.dumps(done)}\n\n".encode()

            item_done = {
                "type": "response.output_item.done",
                "output_index": idx,
                "item": item,
            }
            yield f"event: response.output_item.done\ndata: {json.dumps(item_done)}\n\n".encode()

        completed = {"type": "response.completed", "response": resp}
        yield f"event: response.completed\ndata: {json.dumps(completed)}\n\n".encode()

    return StreamingResponse(gen(), media_type="text/event-stream")
