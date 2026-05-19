"""
Hermes Coaching API — OpenAI-compatible server.
Routes user messages to Max, Forge, or Myriam via an orchestrator LLM.
Includes conversation persistence and document management.
"""
import os
import json
import time
import uuid
import shutil
from pathlib import Path
from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI

app = FastAPI(title="Hermes Coaching API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

PROMPTS_DIR = Path(__file__).parent / "plugins" / "coaching" / "prompts"
DATA_DIR = Path("/data")

SOUL = (Path(__file__).parent / "SOUL.md").read_text()
MAX_PROMPT = (PROMPTS_DIR / "max.md").read_text()
FORGE_PROMPT = (PROMPTS_DIR / "forge.md").read_text()
MYRIAM_PROMPT = (PROMPTS_DIR / "myriam.md").read_text()

COACHES = {
    "max": {"system": MAX_PROMPT, "description": "business, entrepreneuriat, développement personnel"},
    "forge": {"system": FORGE_PROMPT, "description": "sport, nutrition, performance physique"},
    "myriam": {"system": MYRIAM_PROMPT, "description": "émotions, stress, dépolarisation, bien-être mental"},
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": f"consult_{name}",
            "description": f"Consulte {name.capitalize()}, coach {coach['description']}.",
            "parameters": {
                "type": "object",
                "properties": {"message": {"type": "string", "description": "Le message complet de l'utilisateur"}},
                "required": ["message"],
            },
        },
    }
    for name, coach in COACHES.items()
]


def get_client():
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


MODEL = "anthropic/claude-sonnet-4"


# --- User data helpers ---

def _user_dir(user_id: str) -> Path:
    safe_id = user_id.replace("/", "_").replace("..", "_")
    d = DATA_DIR / safe_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def _convos_dir(user_id: str) -> Path:
    d = _user_dir(user_id) / "conversations"
    d.mkdir(exist_ok=True)
    return d


def _docs_dir(user_id: str) -> Path:
    d = _user_dir(user_id) / "documents"
    d.mkdir(exist_ok=True)
    return d


def _get_user_documents_context(user_id: str) -> str:
    docs_path = _docs_dir(user_id)
    docs = []
    for f in sorted(docs_path.iterdir()):
        if f.suffix in (".txt", ".md"):
            docs.append(f"--- Document: {f.stem} ---\n{f.read_text()}")
        elif f.suffix == ".json" and f.stem.endswith("_meta"):
            continue
        elif f.suffix == ".json":
            docs.append(f"--- Document: {f.stem} ---\n{f.read_text()}")
    if not docs:
        return ""
    return "\n\n# Documents de l'utilisateur\n\n" + "\n\n".join(docs)


# --- Conversations API ---

@app.get("/conversations")
async def list_conversations(request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    convos = []
    convos_path = _convos_dir(user_id)
    for f in sorted(convos_path.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        data = json.loads(f.read_text())
        convos.append({
            "id": f.stem,
            "title": data.get("title", "Nouvelle conversation"),
            "updated_at": data.get("updated_at", ""),
            "message_count": len(data.get("messages", [])),
        })
    return convos


@app.get("/conversations/{convo_id}")
async def get_conversation(convo_id: str, request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    f = _convos_dir(user_id) / f"{convo_id}.json"
    if not f.exists():
        return {"error": "not found"}, 404
    return json.loads(f.read_text())


@app.post("/conversations")
async def create_conversation(request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    convo_id = str(uuid.uuid4())[:8]
    data = {
        "id": convo_id,
        "title": "Nouvelle conversation",
        "messages": [],
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    f = _convos_dir(user_id) / f"{convo_id}.json"
    f.write_text(json.dumps(data, ensure_ascii=False))
    return data


@app.put("/conversations/{convo_id}")
async def update_conversation(convo_id: str, request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    f = _convos_dir(user_id) / f"{convo_id}.json"
    body = await request.json()
    if f.exists():
        data = json.loads(f.read_text())
    else:
        data = {"id": convo_id, "messages": [], "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
    data["messages"] = body.get("messages", data["messages"])
    data["title"] = body.get("title", data.get("title", "Nouvelle conversation"))
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")
    f.write_text(json.dumps(data, ensure_ascii=False))
    return data


@app.delete("/conversations/{convo_id}")
async def delete_conversation(convo_id: str, request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    f = _convos_dir(user_id) / f"{convo_id}.json"
    if f.exists():
        f.unlink()
    return {"ok": True}


# --- Documents API ---

@app.get("/documents")
async def list_documents(request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    docs = []
    docs_path = _docs_dir(user_id)
    for f in sorted(docs_path.iterdir()):
        if f.stem.endswith("_meta"):
            continue
        meta_file = docs_path / f"{f.stem}_meta.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        docs.append({
            "id": f.stem,
            "name": meta.get("name", f.name),
            "type": meta.get("type", "document"),
            "size": f.stat().st_size,
            "uploaded_at": meta.get("uploaded_at", ""),
        })
    return docs


@app.post("/documents/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    doc_type: str = Form("document"),
):
    user_id = request.headers.get("x-user-id", "anonymous")
    doc_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix if file.filename else ".txt"

    # Save file
    dest = _docs_dir(user_id) / f"{doc_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    # Save metadata
    meta = {
        "name": file.filename,
        "type": doc_type,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": len(content),
    }
    meta_file = _docs_dir(user_id) / f"{doc_id}_meta.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False))

    return {"id": doc_id, **meta}


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, request: Request):
    user_id = request.headers.get("x-user-id", "anonymous")
    docs_path = _docs_dir(user_id)
    for f in docs_path.glob(f"{doc_id}*"):
        f.unlink()
    return {"ok": True}


# --- Coaching routing ---

async def route_and_respond(messages: list, user_id: str = "anonymous"):
    """Use the orchestrator to pick a coach, then stream the coach's response."""
    client = get_client()
    doc_context = _get_user_documents_context(user_id)

    # Step 1: Ask orchestrator which coach to use
    router_response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "system", "content": SOUL}] + messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    choice = router_response.choices[0]

    if choice.message.tool_calls:
        tool_call = choice.message.tool_calls[0]
        coach_name = tool_call.function.name.replace("consult_", "")
        args = json.loads(tool_call.function.arguments)
        user_message = args.get("message", messages[-1]["content"] if messages else "")

        # Build coach system prompt with user documents
        coach_system = COACHES.get(coach_name, COACHES["myriam"])["system"]
        if doc_context:
            coach_system += doc_context

        # Stream the coach's response with full conversation history
        coach_messages = [{"role": "system", "content": coach_system}]
        for m in messages:
            coach_messages.append({"role": m["role"], "content": m["content"]})

        stream = await client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            stream=True,
            messages=coach_messages,
        )
        return stream, coach_name
    else:
        return choice.message.content, None


async def stream_openai_response(stream, coach_name: str, request_model: str):
    """Yield SSE chunks in OpenAI-compatible format."""
    resp_id = f"chatcmpl-{int(time.time())}"

    async for chunk in stream:
        delta = chunk.choices[0].delta if chunk.choices else None
        if delta and delta.content:
            data = {
                "id": resp_id,
                "object": "chat.completion.chunk",
                "model": request_model,
                "choices": [{"index": 0, "delta": {"content": delta.content}, "finish_reason": None}],
            }
            yield f"data: {json.dumps(data)}\n\n"

    data = {
        "id": resp_id,
        "object": "chat.completion.chunk",
        "model": request_model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    }
    yield f"data: {json.dumps(data)}\n\n"
    yield "data: [DONE]\n\n"


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/v1/models")
async def models():
    return {
        "data": [
            {"id": "hermes-coaching", "object": "model", "owned_by": "team-dereve"},
        ]
    }


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    stream_requested = body.get("stream", False)
    model = body.get("model", "hermes-coaching")
    user_id = request.headers.get("x-user-id", "anonymous")

    result, coach_name = await route_and_respond(messages, user_id)

    if stream_requested and hasattr(result, "__aiter__"):
        return StreamingResponse(
            stream_openai_response(result, coach_name or "myriam", model),
            media_type="text/event-stream",
        )
    elif hasattr(result, "__aiter__"):
        full_text = ""
        async for chunk in result:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
        return _make_response(full_text, model)
    else:
        return _make_response(result, model)


def _make_response(text: str, model: str):
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
    }
