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

"""Firestore backend tools for RealmCrafter RPG items and equipment catalog."""

import re
from typing import Any, Dict, List, Optional
from google.cloud import firestore

# Hardcoded project ID as string for Firestore client
PROJECT_ID = "qwiklabs-gcp-04-e94f2d8b9281"
COLLECTION_NAME = "items"

_db_client: Optional[firestore.Client] = None


def _get_db() -> firestore.Client:
    """Returns a singleton Firestore client instance."""
    global _db_client
    if _db_client is None:
        _db_client = firestore.Client(project=PROJECT_ID)
    return _db_client


def get_item(item_name: str) -> Dict[str, Any]:
    """Look up a fantasy weapon, armor, potion, or magic item from the Firestore catalog.

    Args:
        item_name: The name or identifier of the item to search for (e.g., 'Elixir of Healing', 'longsword', 'Sunfire Blade').

    Returns:
        A dictionary containing item details (name, category, rarity, cost_gp, stats, description)
        or a message if not found.
    """
    db = _get_db()
    col = db.collection(COLLECTION_NAME)

    # 1. Try direct document ID lookup
    doc_id = re.sub(r"[^a-z0-9_]+", "_", item_name.strip().lower()).strip("_")
    doc = col.document(doc_id).get()
    if doc.exists:
        data = doc.to_dict() or {}
        data["id"] = doc.id
        return {"status": "found", "item": data}

    # 2. Try querying by matching name
    normalized_query = item_name.strip().lower()
    docs = col.stream()
    matched_items = []
    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        name = str(item.get("name", "")).lower()
        if normalized_query == name or normalized_query in name or name in normalized_query:
            matched_items.append(item)

    if matched_items:
        return {"status": "found", "item": matched_items[0], "total_matches": len(matched_items)}

    return {
        "status": "not_found",
        "message": f"Item '{item_name}' was not found in the realm's Firestore item catalog.",
    }


def list_items(category: str = "") -> Dict[str, Any]:
    """List items available in the realm's shop and equipment catalog from Firestore.

    Args:
        category: Optional category filter such as 'Weapon', 'Armor', 'Potion', 'Scroll', or 'Wondrous Item'.
                  Leave empty to view all items.

    Returns:
        A dictionary containing the list of matching items and total count.
    """
    db = _get_db()
    col = db.collection(COLLECTION_NAME)

    docs = col.stream()
    items: List[Dict[str, Any]] = []
    target_category = category.strip().lower()

    for d in docs:
        item = d.to_dict()
        item["id"] = d.id
        if not target_category or target_category in str(item.get("category", "")).lower():
            items.append(item)

    # Sort items by cost
    items.sort(key=lambda x: x.get("cost_gp", 0))

    return {
        "status": "success",
        "category_filter": category or "All",
        "count": len(items),
        "items": items,
    }


def add_item(
    name: str,
    category: str,
    rarity: str,
    cost_gp: int,
    description: str,
    stats: str = "",
) -> Dict[str, Any]:
    """Add a new custom weapon, armor, potion, or magical artifact to the realm's Firestore database.

    Args:
        name: The display name of the item (e.g. 'Dagger of Venom', 'Dragon Scale Shield').
        category: The category (e.g. 'Weapon', 'Armor', 'Potion', 'Scroll', 'Wondrous Item').
        rarity: The rarity tier ('Common', 'Uncommon', 'Rare', 'Very Rare', 'Legendary').
        cost_gp: Value in gold pieces (gp).
        description: A vivid fantasy description of the item and its origins.
        stats: Game mechanics, damage dice, armor class, or magical effects (e.g. '1d4 piercing + 2d10 poison').

    Returns:
        A dictionary confirming the item creation and its stored attributes.
    """
    db = _get_db()
    doc_id = re.sub(r"[^a-z0-9_]+", "_", name.strip().lower()).strip("_")
    item_data = {
        "name": name.strip(),
        "category": category.strip(),
        "rarity": rarity.strip(),
        "cost_gp": int(cost_gp),
        "description": description.strip(),
        "stats": stats.strip(),
    }

    db.collection(COLLECTION_NAME).document(doc_id).set(item_data)
    item_data["id"] = doc_id

    return {
        "status": "created",
        "message": f"Successfully registered '{name}' in Firestore collection '{COLLECTION_NAME}'.",
        "item": item_data,
    }
