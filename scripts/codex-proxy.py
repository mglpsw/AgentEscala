#!/usr/bin/env python3
"""
Proxy adaptador: OpenAI Responses API → Chat Completions API
Permite o codex CLI apontar para o agent-router (que só tem /v1/chat/completions).

Uso:
  python3 scripts/codex-proxy.py            # porta 8099, agent-router local
  python3 scripts/codex-proxy.py --port 8099 --upstream http://192.168.3.155:8010
  python3 scripts/codex-proxy.py --upstream https://api.ks-sm.net:9443

Configure o codex para usar este proxy:
  -c model_providers.aiops.base_url=http://localhost:8099
"""
import argparse
import asyncio
import json
import time
import uuid
import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
import uvicorn

parser = argparse.ArgumentParser(description="Responses API → Chat Completions proxy")
parser.add_argument("--port", type=int, default=8099)
parser.add_argument("--upstream", default="http://192.168.3.155:8010")
parser.add_argument("--upstream-key", default="dummy")
args, _ = parser.parse_known_args()

UPSTREAM = args.upstream.rstrip("/")
UPSTREAM_KEY = args.upstream_key
PORT = args.port

app = FastAPI(title="Codex-AIOps Proxy", version="1.0")


def responses_input_to_messages(data: dict) -> list:
    """Converte input da Responses API para messages da Chat Completions API."""
    messages = []

    # instructions → system
    if data.get("instructions"):
        messages.append({"role": "system", "content": data["instructions"]})

    input_val = data.get("input", [])

    if isinstance(input_val, str):
        messages.append({"role": "user", "content": input_val})
    elif isinstance(input_val, list):
        for item in input_val:
            if isinstance(item, str):
                messages.append({"role": "user", "content": item})
            elif isinstance(item, dict):
                role = item.get("role", "user")
                content = item.get("content", "")
                # content pode ser lista (multimodal) ou string
                if isinstance(content, list):
                    text_parts = [
                        p.get("text", "") for p in content
                        if isinstance(p, dict) and p.get("type") == "text"
                    ]
                    content = " ".join(text_parts)
                messages.append({"role": role, "content": content})

    return messages


def chat_response_to_responses(chat: dict, model: str) -> dict:
    """Converte resposta Chat Completions para Responses API."""
    choice = chat.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "") or ""
    usage = chat.get("usage", {})

    resp_id = f"resp_{uuid.uuid4().hex[:24]}"
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"

    return {
        "id": resp_id,
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "status": "completed",
        "output": [
            {
                "id": msg_id,
                "type": "message",
                "status": "completed",
                "role": "assistant",
                "content": [
                    {
                        "type": "output_text",
                        "text": content,
                        "annotations": [],
                    }
                ],
            }
        ],
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "output_tokens_details": {"reasoning_tokens": 0},
        },
        "text": {"format": {"type": "text"}},
        "truncation": "disabled",
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "metadata": {},
        "temperature": 1.0,
        "top_p": 1.0,
        "max_output_tokens": None,
    }


async def stream_responses_sse(
    chat_response: dict, model: str, resp_id: str, msg_id: str
):
    """Sintetiza SSE Responses API a partir de uma resposta Chat Completions completa.
    O agent-router não suporta streaming real, então sempre fazemos upstream não-streaming
    e simulamos os eventos SSE que o codex espera.
    """
    content = (
        chat_response.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "") or ""
    )
    usage = chat_response.get("usage", {})

    created_response = {
        "id": resp_id,
        "object": "response",
        "created_at": int(time.time()),
        "model": model,
        "status": "in_progress",
        "output": [],
        "usage": None,
        "error": None,
        "incomplete_details": None,
        "instructions": None,
        "metadata": {},
        "tools": [],
        "tool_choice": "auto",
        "temperature": 1.0,
        "top_p": 1.0,
        "max_output_tokens": None,
        "parallel_tool_calls": True,
        "text": {"format": {"type": "text"}},
        "truncation": "disabled",
    }

    yield f"event: response.created\ndata: {json.dumps({'type': 'response.created', 'response': created_response})}\n\n"
    yield f"event: response.output_item.added\ndata: {json.dumps({'type': 'response.output_item.added', 'output_index': 0, 'item': {'id': msg_id, 'type': 'message', 'status': 'in_progress', 'role': 'assistant', 'content': []}})}\n\n"
    yield f"event: response.content_part.added\ndata: {json.dumps({'type': 'response.content_part.added', 'item_id': msg_id, 'output_index': 0, 'content_index': 0, 'part': {'type': 'output_text', 'text': '', 'annotations': []}})}\n\n"

    # Emitir o conteúdo completo como um único delta
    if content:
        yield f"event: response.output_text.delta\ndata: {json.dumps({'type': 'response.output_text.delta', 'item_id': msg_id, 'output_index': 0, 'content_index': 0, 'delta': content})}\n\n"

    yield f"event: response.output_text.done\ndata: {json.dumps({'type': 'response.output_text.done', 'item_id': msg_id, 'output_index': 0, 'content_index': 0, 'text': content})}\n\n"

    # response.output_item.done
    done_item = {
        "id": msg_id,
        "type": "message",
        "status": "completed",
        "role": "assistant",
        "content": [{"type": "output_text", "text": content, "annotations": []}],
    }
    yield f"event: response.output_item.done\ndata: {json.dumps({'type': 'response.output_item.done', 'output_index': 0, 'item': done_item})}\n\n"

    # response.completed
    final = {**created_response, "status": "completed", "output": [done_item]}
    yield f"event: response.completed\ndata: {json.dumps({'type': 'response.completed', 'response': final})}\n\n"


@app.get("/health")
async def health():
    return {"status": "ok", "proxy": "codex-aiops", "upstream": UPSTREAM}


@app.get("/v1/models")
@app.get("/models")
async def list_models():
    async with httpx.AsyncClient(verify=False) as client:
        r = await client.get(f"{UPSTREAM}/v1/models",
                             headers={"Authorization": f"Bearer {UPSTREAM_KEY}"},
                             timeout=10)
        return Response(content=r.content, media_type="application/json")


async def handle_responses(request: Request):
    """Handler principal para /responses e /v1/responses."""
    body = await request.json()
    model = body.get("model", "chat:codigo")
    stream = body.get("stream", False)
    accept = request.headers.get("accept", "")
    # codex sempre quer streaming via SSE
    do_stream = stream or "text/event-stream" in accept

    messages = responses_input_to_messages(body)
    max_tokens = body.get("max_output_tokens") or body.get("max_tokens") or 4096
    temperature = body.get("temperature", 1.0)

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": do_stream,
    }

    resp_id = f"resp_{uuid.uuid4().hex[:24]}"
    msg_id = f"msg_{uuid.uuid4().hex[:24]}"

    # Sempre faz upstream NÃO-streaming (agent-router não suporta streaming real)
    payload["stream"] = False

    async with httpx.AsyncClient(verify=False, timeout=120) as client:
        r = await client.post(
            f"{UPSTREAM}/v1/chat/completions",
            json=payload,
            headers={
                "Authorization": f"Bearer {UPSTREAM_KEY}",
                "Content-Type": "application/json",
            },
        )
        r.raise_for_status()
        chat = r.json()

    if do_stream:
        # Sintetiza SSE events a partir da resposta completa
        return StreamingResponse(
            stream_responses_sse(chat, model, resp_id, msg_id),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    else:
        return chat_response_to_responses(chat, model)


@app.post("/responses")
@app.post("/v1/responses")
async def responses_endpoint(request: Request):
    return await handle_responses(request)


# WebSocket upgrade (codex tenta WS primeiro, vai cair no HTTP)
@app.websocket("/responses")
@app.websocket("/v1/responses")
async def responses_websocket(websocket):
    await websocket.close(code=1011, reason="Use HTTP SSE instead")


if __name__ == "__main__":
    print(f"Codex-AIOps Proxy")
    print(f"  Porta:    http://localhost:{PORT}")
    print(f"  Upstream: {UPSTREAM}")
    print(f"")
    print(f"  Configure o codex:")
    print(f"    codex -c model_providers.aiops.base_url=http://localhost:{PORT} ...")
    print(f"")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
