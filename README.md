# RealmCrafter - Fantasy RPG Character & Quest Companion

**RealmCrafter** is an autonomous, multimodal tabletop RPG assistant and rules sage built with Google ADK (Agent Development Kit) on the Gemini platform. It assists players and Dungeon Masters in managing heroes, looking up live 5e rules and stats, generating concept artwork, searching real-world venues, and calculating combat math in a secure Python sandbox.

## Features & Capabilities

- **Firestore Equipment & Magic Item Catalog**:
  - Direct integration with Google Cloud Firestore (`items` collection) to browse, inspect, and forge custom weapons, armor, and artifacts (`get_item`, `list_items`, `add_item`).
- **Live SRD Rules & Creature Stats**:
  - Queries official 5e spellbook rules, damage, components, and casting times via D&D 5e SRD API (`fetch_srd_spell`).
  - Fetches monster stat blocks (Armor Class, Hit Points, Challenge Rating, traits) via Open5e REST API (`fetch_srd_monster_stats`).
- **Multimodal Concept Art Generation**:
  - Generates item and equipment artwork using `gemini-3.1-flash-lite-image`.
  - Saves images to session artifacts and directly uploads them to Google Cloud Storage with public access.
- **Google Maps Integration**:
  - Locates real-world hobby shops, gaming cafes, and meetup spots using Google Maps Geocoding and Places API (New) (`geocode_address`, `find_nearby_places`).
- **Cloud Sandbox Code Execution**:
  - Leverages Vertex AI Agent Platform code sandboxes (`AgentEngineSandboxCodeExecutor`) to simulate combat rounds, compute complex dice probabilities, and solve algorithmic puzzles in Python.
- **Cross-Session Long-Term Memory**:
  - Connects to Vertex AI Memory Bank (`PreloadMemoryTool` and callback) to remember character backstories, player preferences, and campaign choices across sessions.
- **A2UI Interactive Visual Display**:
  - Formats equipment tables and item cards natively using A2UI.

## Project Structure

```
realmcrafter/
├── app/
│   ├── agent.py               # Core agent definition, instructions, tools, and code executor
│   ├── fast_api_app.py        # FastAPI server with A2A protocol and reasoning engine routes
│   ├── firestore_tools.py     # Firestore item catalog tools
│   ├── image_tools.py         # Gemini multimodal image generation and GCS upload
│   ├── maps_tools.py          # Google Maps Geocoding & Places (New) integration
│   ├── tools.py               # SRD Spells, Open5e Monster stats, dice roller, combat simulator
│   ├── a2ui_utils.py          # A2UI card and layout formatting
│   └── app_utils/             # Process-wide session, artifact, and memory services
├── deployment/                # Deployment configuration and service specs
├── tests/                     # Unit and integration test suites
├── project_brief.md           # Project design brief and tool coverage
├── agents-cli-manifest.yaml   # Project manifest
└── pyproject.toml             # Python dependencies and uv configuration
```

## Quick Start

### 1. Prerequisites
- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Google Cloud SDK (`gcloud`)
- [agents-cli](https://cloud.google.com/vertex-ai/docs)

### 2. Environment Variables
Create a `.env` file in the project root:
```env
GOOGLE_CLOUD_PROJECT=<your-project-id>
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_MAPS_API_KEY=<your-google-maps-api-key>
```

### 3. Installation
Install project dependencies using `uv`:
```bash
uv sync
```

### 4. Running Locally
Run the ADK Web playground with cross-session Memory Bank support:
```bash
uv run adk web . --port 8080 --reload_agents --memory_service_uri=agentengine://<YOUR_AGENT_ENGINE_ID>
```
Open `http://localhost:8080` in your browser.

## Built With
- **Google ADK** (Agent Development Kit)
- **Gemini 2.5 / 3.0 Flash** & **Gemini 3.1 Flash Lite Image**
- **Google Cloud Firestore**
- **Google Cloud Storage**
- **Google Maps Platform** (Geocoding & Places API New)
- **Vertex AI Agent Platform & Memory Bank**
