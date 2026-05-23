"""
Hermes Coaching API — OpenAI-compatible server.
Routes user messages to coaches via an orchestrator LLM.
Agents are dynamically configurable with editable prompts and resources.
"""
import os
import json
import time
import uuid
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
AGENTS_DIR = DATA_DIR / "agents"

SOUL_PATH = Path(__file__).parent / "SOUL.md"

# Default agent definitions (used as fallback)
DEFAULT_AGENTS = {
    "max": {
        "name": "Max",
        "description": "business, entrepreneuriat, développement personnel",
        "color": "#5b9cf6",
        "icon": "briefcase",
    },
    "forge": {
        "name": "Forge",
        "description": "sport, nutrition, performance physique",
        "color": "#f5a623",
        "icon": "dumbbell",
    },
    "myriam": {
        "name": "Myriam",
        "description": "émotions, stress, dépolarisation, bien-être mental",
        "color": "#d46ef5",
        "icon": "heart",
    },
}


def get_client():
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )


MODEL = "anthropic/claude-sonnet-4"


# --- Agent management helpers ---

def _agents_dir() -> Path:
    AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    return AGENTS_DIR


def _agent_dir(agent_id: str) -> Path:
    d = _agents_dir() / agent_id
    d.mkdir(exist_ok=True)
    return d


def _agent_resources_dir(agent_id: str) -> Path:
    d = _agent_dir(agent_id) / "resources"
    d.mkdir(exist_ok=True)
    return d


def _init_agents():
    """Initialize agent configs from defaults if they don't exist yet."""
    for agent_id, defaults in DEFAULT_AGENTS.items():
        config_file = _agent_dir(agent_id) / "config.json"
        prompt_file = _agent_dir(agent_id) / "prompt.md"

        if not config_file.exists():
            config_file.write_text(json.dumps(defaults, ensure_ascii=False, indent=2))

        if not prompt_file.exists():
            # Copy from bundled prompts
            source = PROMPTS_DIR / f"{agent_id}.md"
            if source.exists():
                prompt_file.write_text(source.read_text())
            else:
                prompt_file.write_text(f"Tu es {defaults['name']}.")


def _get_agent_config(agent_id: str) -> dict:
    config_file = _agent_dir(agent_id) / "config.json"
    if config_file.exists():
        return json.loads(config_file.read_text())
    return DEFAULT_AGENTS.get(agent_id, {"name": agent_id, "description": "", "color": "#888", "icon": "bot"})


def _get_agent_prompt(agent_id: str) -> str:
    prompt_file = _agent_dir(agent_id) / "prompt.md"
    if prompt_file.exists():
        return prompt_file.read_text()
    source = PROMPTS_DIR / f"{agent_id}.md"
    if source.exists():
        return source.read_text()
    return ""


def _get_agent_resources_context(agent_id: str) -> str:
    res_dir = _agent_resources_dir(agent_id)
    docs = []
    for f in sorted(res_dir.iterdir()):
        if f.stem.endswith("_meta"):
            continue
        if f.suffix in (".txt", ".md"):
            docs.append(f"--- Ressource: {f.stem} ---\n{f.read_text()}")
        elif f.suffix == ".json":
            docs.append(f"--- Ressource: {f.stem} ---\n{f.read_text()}")
    if not docs:
        return ""
    return "\n\n# Ressources méthodologiques\n\n" + "\n\n".join(docs)


def _get_all_agents() -> dict:
    """Get all agents with their configs."""
    agents = {}
    for d in sorted(_agents_dir().iterdir()):
        if d.is_dir():
            agent_id = d.name
            config = _get_agent_config(agent_id)
            agents[agent_id] = {
                "system": _get_agent_prompt(agent_id),
                "description": config.get("description", ""),
                **config,
            }
    return agents


def _get_soul() -> str:
    """Get the orchestrator system prompt, dynamically built from active agents."""
    soul_data = DATA_DIR / "soul.md"
    if soul_data.exists():
        return soul_data.read_text()
    return SOUL_PATH.read_text()


def _build_tools(agents: dict) -> list:
    return [
        {
            "type": "function",
            "function": {
                "name": f"consult_{name}",
                "description": f"Consulte {agent.get('name', name.capitalize())}, coach {agent['description']}.",
                "parameters": {
                    "type": "object",
                    "properties": {"message": {"type": "string", "description": "Le message complet de l'utilisateur"}},
                    "required": ["message"],
                },
            },
        }
        for name, agent in agents.items()
    ]


# Initialize agents on startup
_init_agents()


# --- Agents API ---

@app.get("/agents")
async def list_agents():
    agents = []
    for d in sorted(_agents_dir().iterdir()):
        if d.is_dir():
            agent_id = d.name
            config = _get_agent_config(agent_id)
            prompt = _get_agent_prompt(agent_id)
            res_dir = _agent_resources_dir(agent_id)
            resource_count = sum(1 for f in res_dir.iterdir() if not f.stem.endswith("_meta"))
            agents.append({
                "id": agent_id,
                "prompt_length": len(prompt),
                "resource_count": resource_count,
                **config,
            })
    return agents


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str):
    config = _get_agent_config(agent_id)
    prompt = _get_agent_prompt(agent_id)
    return {"id": agent_id, "prompt": prompt, **config}


@app.put("/agents/{agent_id}")
async def update_agent(agent_id: str, request: Request):
    body = await request.json()
    config = _get_agent_config(agent_id)

    # Update config fields
    for key in ("name", "description", "color", "icon"):
        if key in body:
            config[key] = body[key]

    config_file = _agent_dir(agent_id) / "config.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    # Update prompt if provided
    if "prompt" in body:
        prompt_file = _agent_dir(agent_id) / "prompt.md"
        prompt_file.write_text(body["prompt"])

    return {"id": agent_id, **config}


@app.post("/agents")
async def create_agent(request: Request):
    body = await request.json()
    agent_id = body.get("id", str(uuid.uuid4())[:8])
    agent_id = agent_id.lower().replace(" ", "-")

    config = {
        "name": body.get("name", agent_id.capitalize()),
        "description": body.get("description", ""),
        "color": body.get("color", "#888"),
        "icon": body.get("icon", "bot"),
    }

    _agent_dir(agent_id)
    config_file = _agent_dir(agent_id) / "config.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    prompt_file = _agent_dir(agent_id) / "prompt.md"
    prompt_file.write_text(body.get("prompt", f"Tu es {config['name']}."))

    # Update the orchestrator SOUL to include new agent
    _rebuild_soul()

    return {"id": agent_id, **config}


@app.delete("/agents/{agent_id}")
async def delete_agent(agent_id: str):
    import shutil
    agent_path = _agent_dir(agent_id)
    if agent_path.exists():
        shutil.rmtree(agent_path)
    _rebuild_soul()
    return {"ok": True}


def _rebuild_soul():
    """Rebuild the orchestrator SOUL.md based on active agents."""
    agents = []
    for d in sorted(_agents_dir().iterdir()):
        if d.is_dir():
            config = _get_agent_config(d.name)
            agents.append(f"- **{config.get('name', d.name)}** : {config.get('description', '')}")

    agent_list = "\n".join(agents)
    soul = f"""# Rôle
Tu es l'entrypoint d'une plateforme de coaching IA. Ton rôle unique est
d'analyser chaque message et de le déléguer au bon coach spécialisé.

# Coaches disponibles
{agent_list}

# Instructions
1. Analyse l'intention du message
2. Appelle IMMÉDIATEMENT le tool correspondant sans reformuler ni commenter
3. Transmets la réponse du coach telle quelle à l'utilisateur
4. Si ambiguïté, privilégie le domaine émotionnel pour la détresse,
   sportif pour le corps, business pour le reste

# Ce que tu ne fais PAS
- Tu ne réponds jamais directement aux questions de coaching
- Tu ne choisis pas l'agent selon des mots-clés mais selon l'intention profonde
"""
    soul_data = DATA_DIR / "soul.md"
    soul_data.write_text(soul)


# --- Agent resources API ---

@app.get("/agents/{agent_id}/resources")
async def list_agent_resources(agent_id: str):
    res_dir = _agent_resources_dir(agent_id)
    resources = []
    for f in sorted(res_dir.iterdir()):
        if f.stem.endswith("_meta"):
            continue
        meta_file = res_dir / f"{f.stem}_meta.json"
        meta = json.loads(meta_file.read_text()) if meta_file.exists() else {}
        resources.append({
            "id": f.stem,
            "name": meta.get("name", f.name),
            "size": f.stat().st_size,
            "uploaded_at": meta.get("uploaded_at", ""),
        })
    return resources


@app.post("/agents/{agent_id}/resources/upload")
async def upload_agent_resource(agent_id: str, file: UploadFile = File(...)):
    res_id = str(uuid.uuid4())[:8]
    ext = Path(file.filename).suffix if file.filename else ".txt"

    dest = _agent_resources_dir(agent_id) / f"{res_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    meta = {
        "name": file.filename,
        "uploaded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "size": len(content),
    }
    meta_file = _agent_resources_dir(agent_id) / f"{res_id}_meta.json"
    meta_file.write_text(json.dumps(meta, ensure_ascii=False))

    return {"id": res_id, **meta}


@app.delete("/agents/{agent_id}/resources/{res_id}")
async def delete_agent_resource(agent_id: str, res_id: str):
    res_dir = _agent_resources_dir(agent_id)
    for f in res_dir.glob(f"{res_id}*"):
        f.unlink()
    return {"ok": True}


# --- Voice cloning API (ElevenLabs) ---

@app.post("/agents/{agent_id}/voice/clone")
async def clone_voice_for_agent(agent_id: str, file: UploadFile = File(...)):
    """Upload an audio sample and clone the voice via ElevenLabs for this agent."""
    import httpx

    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        return {"error": "ELEVENLABS_API_KEY not configured"}

    config = _get_agent_config(agent_id)
    agent_name = config.get("name", agent_id.capitalize())
    voice_name = f"Coach {agent_name}"

    audio_content = await file.read()

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.elevenlabs.io/v1/voices/add",
            headers={"xi-api-key": elevenlabs_key},
            data={"name": voice_name, "description": f"Voix clonée pour {agent_name}"},
            files={"files": (file.filename or "sample.mp3", audio_content, file.content_type or "audio/mpeg")},
        )

    if resp.status_code != 200:
        return {"error": f"ElevenLabs error: {resp.text}"}

    result = resp.json()
    voice_id = result.get("voice_id", "")

    # Save voice_id in agent config
    config["voice_id"] = voice_id
    config["voice_name"] = voice_name
    config_file = _agent_dir(agent_id) / "config.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    return {"voice_id": voice_id, "voice_name": voice_name}


@app.delete("/agents/{agent_id}/voice")
async def remove_voice_for_agent(agent_id: str):
    """Remove the cloned voice from agent config and optionally from ElevenLabs."""
    import httpx

    config = _get_agent_config(agent_id)
    voice_id = config.pop("voice_id", None)
    config.pop("voice_name", None)
    config_file = _agent_dir(agent_id) / "config.json"
    config_file.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    # Delete from ElevenLabs too
    if voice_id:
        elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
        if elevenlabs_key:
            async with httpx.AsyncClient(timeout=30) as client:
                await client.delete(
                    f"https://api.elevenlabs.io/v1/voices/{voice_id}",
                    headers={"xi-api-key": elevenlabs_key},
                )

    return {"ok": True}


@app.get("/voices")
async def list_voices():
    """List available ElevenLabs voices."""
    import httpx

    elevenlabs_key = os.environ.get("ELEVENLABS_API_KEY", "")
    if not elevenlabs_key:
        return []

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": elevenlabs_key},
        )

    if resp.status_code != 200:
        return []

    voices = resp.json().get("voices", [])
    return [{"id": v["voice_id"], "name": v["name"], "category": v.get("category", "")} for v in voices]


# --- User data helpers ---

def _user_dir(user_id: str) -> Path:
    safe_id = user_id.replace("/", "_").replace("..", "_")
    d = DATA_DIR / "users" / safe_id
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

    dest = _docs_dir(user_id) / f"{doc_id}{ext}"
    content = await file.read()
    dest.write_bytes(content)

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


# --- Proxy to real Hermes Agent ---

HERMES_AGENT_URL = os.environ.get("HERMES_AGENT_URL", "http://host.docker.internal:8080")
HERMES_AGENT_KEY = os.environ.get("HERMES_AGENT_KEY", "hermes-coaching-2026")


@app.get("/health")
async def health():
    return {"status": "ok", "mode": "management-api + hermes-agent-proxy"}


@app.get("/v1/models")
async def models():
    import httpx
    # Proxy to real Hermes Agent and merge with agent list
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(
                f"{HERMES_AGENT_URL}/v1/models",
                headers={"Authorization": f"Bearer {HERMES_AGENT_KEY}"},
            )
            hermes_models = resp.json().get("data", [])
        except Exception:
            hermes_models = [{"id": "hermes-coaching", "object": "model", "owned_by": "hermes"}]

    return {"data": hermes_models}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    """Proxy chat to real Hermes Agent runtime with session persistence."""
    import httpx
    body = await request.json()
    stream_requested = body.get("stream", False)
    user_id = request.headers.get("x-user-id", "anonymous")

    # Build a stable session ID so Hermes Agent maintains memory across conversations
    session_id = f"user-{user_id.replace('@', '_').replace('.', '_')}"

    proxy_headers = {
        "Authorization": f"Bearer {HERMES_AGENT_KEY}",
        "Content-Type": "application/json",
        "X-Hermes-Session-Id": session_id,
    }

    if stream_requested:
        async def proxy_stream():
            async with httpx.AsyncClient(timeout=120) as client:
                async with client.stream(
                    "POST",
                    f"{HERMES_AGENT_URL}/v1/chat/completions",
                    headers=proxy_headers,
                    content=json.dumps(body),
                ) as resp:
                    async for chunk in resp.aiter_bytes():
                        yield chunk

        return StreamingResponse(proxy_stream(), media_type="text/event-stream")
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{HERMES_AGENT_URL}/v1/chat/completions",
                headers=proxy_headers,
                content=json.dumps(body),
            )
            return resp.json()
