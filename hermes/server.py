"""
Hermes Coaching API — OpenAI-compatible server.
Routes user messages to Max, Forge, or Myriam via an orchestrator LLM.
"""
import os
import json
from pathlib import Path
from fastapi import FastAPI, Request
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


async def delegate_to_coach(coach_name: str, message: str) -> str:
    client = get_client()
    response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=2048,
        messages=[
            {"role": "system", "content": COACHES[coach_name]["system"]},
            {"role": "user", "content": message},
        ],
    )
    return response.choices[0].message.content


async def route_and_respond(messages: list):
    """Use the orchestrator to pick a coach, then stream the coach's response."""
    client = get_client()

    # Step 1: Ask orchestrator which coach to use
    router_response = await client.chat.completions.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "system", "content": SOUL}] + messages,
        tools=TOOLS,
        tool_choice="auto",
    )

    choice = router_response.choices[0]

    # If the orchestrator called a tool, delegate to the coach
    if choice.message.tool_calls:
        tool_call = choice.message.tool_calls[0]
        coach_name = tool_call.function.name.replace("consult_", "")
        args = json.loads(tool_call.function.arguments)
        user_message = args.get("message", messages[-1]["content"] if messages else "")

        # Step 2: Stream the coach's response
        coach_system = COACHES.get(coach_name, COACHES["myriam"])["system"]
        stream = await client.chat.completions.create(
            model=MODEL,
            max_tokens=2048,
            stream=True,
            messages=[
                {"role": "system", "content": coach_system},
                {"role": "user", "content": user_message},
            ],
        )
        return stream, coach_name
    else:
        # Fallback: orchestrator responded directly (shouldn't happen)
        return choice.message.content, None


async def stream_openai_response(stream, coach_name: str, request_model: str):
    """Yield SSE chunks in OpenAI-compatible format."""
    import time
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

    # Final chunk
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

    result, coach_name = await route_and_respond(messages)

    if stream_requested and hasattr(result, "__aiter__"):
        return StreamingResponse(
            stream_openai_response(result, coach_name or "myriam", model),
            media_type="text/event-stream",
        )
    elif hasattr(result, "__aiter__"):
        # Collect full response
        full_text = ""
        async for chunk in result:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                full_text += delta.content
        return _make_response(full_text, model)
    else:
        return _make_response(result, model)


def _make_response(text: str, model: str):
    import time
    return {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "model": model,
        "choices": [{"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
    }
