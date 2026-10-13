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

"""Seed script to populate Firestore with initial RPG items."""

from google.cloud import firestore

# Hardcoded project ID as string to prevent project number resolution issues on Agent Platform
PROJECT_ID = "qwiklabs-gcp-04-e94f2d8b9281"
COLLECTION_NAME = "items"

SEEDED_ITEMS = [
    {
        "id": "longsword",
        "name": "Steel Longsword",
        "category": "Weapon",
        "rarity": "Common",
        "cost_gp": 15,
        "description": "A finely forged double-edged blade favored by knights and rangers.",
        "stats": "1d8 slashing (versatile 1d10)",
    },
    {
        "id": "shortbow",
        "name": "Hunting Shortbow",
        "category": "Weapon",
        "rarity": "Common",
        "cost_gp": 25,
        "description": "A light yew wood bow ideal for swift strikes from the shadows.",
        "stats": "1d6 piercing (range 80/320)",
    },
    {
        "id": "elixir_of_healing",
        "name": "Elixir of Healing",
        "category": "Potion",
        "rarity": "Common",
        "cost_gp": 50,
        "description": "A glowing ruby potion that seals wounds and restores vigor.",
        "stats": "Restores 2d4 + 2 Hit Points",
    },
    {
        "id": "sunfire_blade",
        "name": "Sunfire Blade",
        "category": "Weapon",
        "rarity": "Rare",
        "cost_gp": 1200,
        "description": "A gold-hilted rapier blazing with solar radiance. Deals extra damage to undead.",
        "stats": "1d8 + 2 radiant (sheds bright light 15ft)",
    },
    {
        "id": "mithral_chainmail",
        "name": "Mithral Chainmail",
        "category": "Armor",
        "rarity": "Uncommon",
        "cost_gp": 450,
        "description": "Interlocking rings of featherlight elven mithral. Imposes no stealth disadvantage.",
        "stats": "Armor Class 16",
    },
    {
        "id": "scroll_of_fireball",
        "name": "Scroll of Fireball",
        "category": "Scroll",
        "rarity": "Rare",
        "cost_gp": 300,
        "description": "A crisp parchment inscribed with draconic runes that burst into a blazing inferno.",
        "stats": "8d6 fire damage (20ft sphere, Dex save DC 15)",
    },
    {
        "id": "potion_of_invisibility",
        "name": "Potion of Invisibility",
        "category": "Potion",
        "rarity": "Very Rare",
        "cost_gp": 800,
        "description": "Clear silver liquid that causes the imbiber to vanish completely from sight.",
        "stats": "Invisible condition for up to 1 hour",
    },
    {
        "id": "cloak_of_elvenkind",
        "name": "Cloak of Elvenkind",
        "category": "Wondrous Item",
        "rarity": "Uncommon",
        "cost_gp": 500,
        "description": "A leaf-patterned cloak that shifts color to camouflage the wearer with their surroundings.",
        "stats": "Advantage on Dexterity (Stealth) checks",
    },
]


def seed():
    print(f"Connecting to Firestore in project '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    col_ref = db.collection(COLLECTION_NAME)

    for item in SEEDED_ITEMS:
        doc_id = item["id"]
        data = {k: v for k, v in item.items() if k != "id"}
        col_ref.document(doc_id).set(data)
        print(f"  ✓ Seeded item: {item['name']} ({doc_id})")

    print(f"\nSuccessfully seeded {len(SEEDED_ITEMS)} items into '{COLLECTION_NAME}' collection.")


if __name__ == "__main__":
    seed()
