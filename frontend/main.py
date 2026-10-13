"""Minimal FastAPI proxy for a deployed A2A agent (Agent Runtime, agents-cli 1.1.0+).

The browser talks ONLY to this proxy (same origin, no CORS, no GCP creds in the
browser). The proxy authenticates with Application Default Credentials and
forwards chat to the deployed agent over the A2A protocol, returning replies as
structured parts the chat UI knows how to show:

  * {"kind": "text", "text": ...}  -> a normal chat bubble
  * {"kind": "a2ui", "data": ...}  -> one A2UI message (beginRendering /
    surfaceUpdate); static/index.html renders these as a card.

Why A2A: agents-cli 1.1.0 (GA) deploys ADK agents to Agent Runtime as A2A agents
and no longer registers the reasoning-engine operation schema the old
`agent_engines.get(...).stream_query()` path relied on (operation_schemas() comes
back empty). The container serves the A2A protocol over the Agent Engine HTTP
passthrough, so this proxy fetches the agent's card and sends messages with the
a2a-sdk client (the same path `agents-cli run --mode a2a` uses). This works for
both A2A and plain ADK 1.1.0 deployments (the container serves A2A either way).

Run:
  pip install -r requirements.txt
  export AGENT_ENGINE_RESOURCE_NAME="projects/.../locations/.../reasoningEngines/..."
  export AGENT_DIRECTORY="app"   # your agent's app directory (agents-cli-manifest.yaml)
  python main.py                 # -> http://localhost:8080
"""

import inspect
import json
import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import A2ACardResolver, ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
)

try:
    from a2a.types import FilePart, TextPart, TransportProtocol
except ImportError:
    try:
        from a2a.compat.v0_3.types import FilePart, TextPart
    except ImportError:
        FilePart = None
        TextPart = None
    try:
        from a2a.client.client_factory import TransportProtocol
    except ImportError:
        TransportProtocol = None

try:
    from a2a.types import SendMessageRequest
except ImportError:
    SendMessageRequest = None

from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message as ProtoMessage

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/701107460665/locations/us-central1/reasoningEngines/7269029975779442688",
)
# The agent's app directory (matches agent_directory in agents-cli-manifest.yaml).
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
# Location is embedded in the resource name: projects/<p>/locations/<loc>/reasoningEngines/<id>.
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

# A2A endpoint for an Agent Runtime deployment, via the Agent Engine HTTP
# passthrough. The card lives at the well-known path under this base.
A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

# The agent tags its A2UI data parts with this mime type.
_A2UI_MIME = "application/json+a2ui"

# One set of ADC credentials, refreshed per request (access tokens expire ~1h).
_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    # Always return JSON so the browser never receives a plain-text 500 page
    # (which shows up in the chat as "Unexpected token 'I', "Internal S"... is
    # not valid JSON"). Any server-side failure now surfaces as a readable
    # message in the chat bubble instead.
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


# Reuse ONE A2A context per user so the agent remembers the conversation.
_contexts: dict[str, str] = {}
# Cache the agent card after the first fetch.
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        try:
            resolver = A2ACardResolver(client, A2A_BASE)
            _card = await resolver.get_agent_card()
        except Exception:
            resp = await client.get(A2A_CARD_URL)
            resp.raise_for_status()
            card = AgentCard(**resp.json())
            # Agent Runtime does not serve a public card URL, so point the client at
            # the passthrough base for message sends.
            card.url = A2A_BASE
            _card = card
    return _card


def _is_a2ui_payload(data, mime=None) -> bool:
    if mime == _A2UI_MIME:
        return True
    if isinstance(data, dict):
        return any(k in data for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface"))
    return False


def _extract_parts(parts: list) -> list[dict]:
    """Turn A2A response parts into structured parts for the chat UI.

    Text parts pass through as {"kind": "text"}. A2UI data parts (tagged
    application/json+a2ui) become {"kind": "a2ui", "data": <message>} so the UI
    renders the card; each data part is one A2UI message (beginRendering or
    surfaceUpdate).
    """
    out: list[dict] = []
    for p in parts:
        if isinstance(p, ProtoMessage):
            d = MessageToDict(p, preserving_proto_field_name=True)
            if d.get("text"):
                out.append({"kind": "text", "text": d["text"]})
            elif d.get("data") is not None:
                data = d["data"]
                mime = None
                if isinstance(data, dict) and data.get("kind") == "data" and "data" in data:
                    mime = (data.get("metadata") or {}).get("mimeType")
                    data = data["data"]
                if _is_a2ui_payload(data, mime):
                    out.append({"kind": "a2ui", "data": data})
            elif d.get("url"):
                out.append({"kind": "text", "text": d["url"]})
            continue

        root = getattr(p, "root", p)
        if TextPart and isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            data = root.data
            meta = getattr(root, "metadata", None) or {}
            mime = meta.get("mimeType") if isinstance(meta, dict) else None
            if isinstance(data, dict) and data.get("kind") == "data" and "data" in data:
                inner_meta = data.get("metadata") or {}
                if isinstance(inner_meta, dict):
                    mime = inner_meta.get("mimeType", mime)
                data = data["data"]
            if _is_a2ui_payload(data, mime):
                out.append({"kind": "a2ui", "data": data})
        elif FilePart and isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        cfg_kwargs = {"httpx_client": client}
        if "supported_transports" in inspect.signature(ClientConfig.__init__).parameters:
            cfg_kwargs["supported_transports"] = [
                getattr(TransportProtocol, "jsonrpc", "JSONRPC"),
                getattr(TransportProtocol, "http_json", "HTTP_JSON"),
            ]
        elif "supported_protocol_bindings" in inspect.signature(ClientConfig.__init__).parameters:
            cfg_kwargs["supported_protocol_bindings"] = ["JSONRPC", "HTTP+JSON"]

        factory = ClientFactory(ClientConfig(**cfg_kwargs))
        a2a_client = factory.create(card)

        user_role = getattr(Role, "ROLE_USER", getattr(Role, "user", 1))
        try:
            part_obj = Part(text=message)
        except Exception:
            part_obj = Part(root=TextPart(text=message))

        context_id = _contexts.get(user_id)
        msg_kwargs = {
            "message_id": str(uuid.uuid4()),
            "role": user_role,
            "parts": [part_obj],
        }
        if context_id:
            msg_kwargs["context_id"] = context_id

        msg = Message(**msg_kwargs)

        last_task = None
        got_artifact_update = False
        try:
            stream = a2a_client.send_message(msg)
        except (TypeError, Exception):
            if SendMessageRequest:
                try:
                    stream = a2a_client.send_message(SendMessageRequest(message=msg))
                except Exception:
                    stream = a2a_client.send_message(msg)
            else:
                stream = a2a_client.send_message(msg)

        async for event in stream:
            if isinstance(event, tuple):
                task, update = event
                if task is not None:
                    last_task = task
                    if getattr(task, "context_id", None):
                        _contexts[user_id] = task.context_id
                if isinstance(update, TaskArtifactUpdateEvent):
                    got_artifact_update = True
                    parts.extend(_extract_parts(update.artifact.parts))
            else:
                if hasattr(event, "status_update") and event.HasField("status_update"):
                    if event.status_update.context_id:
                        _contexts[user_id] = event.status_update.context_id
                if hasattr(event, "artifact_update") and event.HasField("artifact_update"):
                    got_artifact_update = True
                    parts.extend(_extract_parts(event.artifact_update.artifact.parts))
                if hasattr(event, "message") and event.HasField("message"):
                    parts.extend(_extract_parts(event.message.parts))

        # Non-streaming fallback: pull parts from the final task's artifacts.
        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        # The turn produced no text or UI (e.g. the agent only ran tools, or a
        # tool stalled). Be honest rather than silent.
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


# Serve the chat UI (keep this mount last so /chat wins).
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
