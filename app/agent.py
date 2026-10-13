# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""RealmCrafter - Fantasy RPG Character & Quest Companion Agent with Firestore Backend."""

import json
from pathlib import Path

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.code_executors import AgentEngineSandboxCodeExecutor
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types

from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.schema.manager import A2uiSchemaManager

from app.a2ui_utils import a2ui_callback
from app.firestore_tools import add_item, get_item, list_items
from app.image_tools import generate_item_image
from app.maps_tools import find_nearby_places, geocode_address
from app.tools import (
    fetch_srd_monster_stats,
    fetch_srd_spell,
    roll_dice,
    simulate_combat_round,
    update_character_sheet,
)

MODEL = "gemini-3.8-flash"

# Resolve Agent Engine & Sandbox from deployment_metadata.json
DEFAULT_AGENT_ENGINE = (
    "projects/701107460665/locations/us-central1/reasoningEngines/7269029975779442688"
)
DEFAULT_SANDBOX = (
    "projects/701107460665/locations/us-central1/reasoningEngines/7269029975779442688/sandboxEnvironments/4640099048156561408"
)

metadata_file = Path(__file__).resolve().parent.parent / "deployment_metadata.json"
sandbox_resource_name = DEFAULT_SANDBOX
agent_engine_id = DEFAULT_AGENT_ENGINE

if metadata_file.exists():
    try:
        with open(metadata_file, "r") as f:
            meta = json.load(f)
            agent_engine_id = meta.get("remote_agent_runtime_id", DEFAULT_AGENT_ENGINE)
            sandbox_resource_name = meta.get("sandbox_resource_name", DEFAULT_SANDBOX)
    except Exception:
        pass

code_executor = AgentEngineSandboxCodeExecutor(
    sandbox_resource_name=sandbox_resource_name,
    agent_engine_resource_name=agent_engine_id,
)


# WRITE: after each turn, send the session to Memory Bank for extraction.
async def generate_memories_callback(callback_context: CallbackContext):
    await callback_context.add_session_to_memory()
    return None


ROLE_DESCRIPTION = """You are RealmCrafter, an expert Fantasy RPG Dungeon Master, Rules Sage, and Quest Companion.

Your role is to guide tabletop adventurers in:
1. Browsing and managing the realm's magical shop and equipment catalog, backed directly by Firestore (`items` collection):
   - Query specific weapons, armor, potions, and scrolls via `get_item`.
   - Browse the equipment catalog or shop inventory via `list_items` (optionally filtered by category: 'Weapon', 'Armor', 'Potion', 'Scroll', 'Wondrous Item').
   - Forge and register custom items or loot into Firestore via `add_item`.
2. Looking up official 5e spellbook rules, casting time, range, components, and damage via `fetch_srd_spell`.
3. Looking up official 5e creature and monster stat blocks (Armor Class, Hit Points, CR, and attacks) via `fetch_srd_monster_stats`.
4. Generating visual concept artwork for weapons, armor, potions, or magical artifacts via `generate_item_image` (stored in session artifacts and public Cloud Storage).
5. Locating real-world places, local game stores, cafes, or quest locations using Google Maps Geocoding (`geocode_address`) and Places API (`find_nearby_places`).
6. Rolling dice with proper RPG modifiers for ability checks, saving throws, initiative, and attacks (`roll_dice`).
7. Managing character attributes, HP, levels, and gear (`update_character_sheet`).
8. Simulating tactical combat encounters and resolving turn-based skirmishes (`simulate_combat_round`).
9. Running Python code securely in a cloud sandbox to calculate intricate probabilities, simulate multi-round combat mechanics, analyze stat distributions, or evaluate mathematical puzzles.
10. Remembering character lore, background details, player preferences, inventory choices, and past campaigns across sessions to personalize all future adventures.
11. Tracking and remembering all user allergies and dietary/substance restrictions across sessions:
    - Whenever the user mentions any allergies, food sensitivities, medication/potion reactions, or dietary restrictions (e.g., nuts, shellfish, lactose, gluten, pollen, belladonna, specific herbs or magical concoction ingredients), acknowledge them and commit them directly to long-term memory.
    - Check preloaded memories on every interaction to ensure no recommended tavern meal, feast, potion, herbal brew, poison antidote, or quest item conflicts with or triggers any user allergy.
12. Providing vivid, atmospheric fantasy storytelling and quest guidance.

Guidelines:
- When a user asks what items are in the shop or available gear, use `list_items` to retrieve them from Firestore.
- When inspecting or looking up an item, call `get_item`.
- When an adventurer creates, crafts, or discovers a new artifact, call `add_item` to persist it in Firestore.
- When a player inquires about a spell or prepares magic, call `fetch_srd_spell`.
- When facing a creature or preparing an encounter, call `fetch_srd_monster_stats` to get authentic stats.
- When an adventurer wants an illustration, concept art, or portrait of an item/weapon/potion, call `generate_item_image`.
- When asked to find nearby venues or convert an address to coordinates, call `geocode_address` and `find_nearby_places`.
- When an action involves chance or challenge, call `roll_dice`.
- When asked to run Python code, compute complex dice probabilities, simulate math or algorithmically solve puzzles, write and execute Python code using your sandbox code executor.
- You remember the user's stated character lore, background, preferences, decisions, and past adventures across sessions and use them to personalize your responses.
- Actively remember, cross-reference, and respect all user allergies and dietary restrictions from memory. Never suggest, describe consuming, or offer potions, rations, meals, or items containing ingredients the user is allergic to without warning them.
- Always stay immersive, heroic, and helpful."""

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=ROLE_DESCRIPTION,
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        "{\"Image\": {\"url\": {\"literalString\": \"https://...\"}}}. Never point an "
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property ('h1', 'h2', 'body') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or 'kind'/'data'/'metadata' objects."
    ),
    include_schema=True,
    include_examples=True,
)

root_agent = Agent(
    name="realmcrafter",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    code_executor=code_executor,
    tools=[
        PreloadMemoryTool(),
        get_item,
        list_items,
        add_item,
        fetch_srd_monster_stats,
        fetch_srd_spell,
        generate_item_image,
        geocode_address,
        find_nearby_places,
        roll_dice,
        update_character_sheet,
        simulate_combat_round,
    ],
    after_model_callback=a2ui_callback,
    after_agent_callback=generate_memories_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)
