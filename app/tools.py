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

"""RPG tools for dice rolling, item catalog lookup, character tracking, and combat."""

import random
import re
from typing import Any, Dict

# Catalog of fantasy equipment, weapons, potions, and spells
CATALOG: Dict[str, Dict[str, Any]] = {
    "longsword": {
        "name": "Steel Longsword",
        "type": "Martial Melee Weapon",
        "damage": "1d8 slashing (versatile 1d10)",
        "rarity": "Common",
        "cost_gp": 15,
        "description": "A finely forged double-edged blade favored by knights and rangers.",
    },
    "shortbow": {
        "name": "Hunting Shortbow",
        "type": "Ranged Weapon",
        "damage": "1d6 piercing (range 80/320)",
        "rarity": "Common",
        "cost_gp": 25,
        "description": "A light yew wood bow ideal for swift strikes from the shadows.",
    },
    "elixir of healing": {
        "name": "Elixir of Healing",
        "type": "Potion",
        "effect": "Restores 2d4 + 2 Hit Points",
        "rarity": "Common",
        "cost_gp": 50,
        "description": "A glowing red potion that seals flesh and restores vitality upon drinking.",
    },
    "sunfire blade": {
        "name": "Sunfire Blade",
        "type": "Magic Weapon",
        "damage": "1d8 + 2 radiant (sheds bright light in 15ft)",
        "rarity": "Rare",
        "cost_gp": 1200,
        "description": "A gold-hilt rapier blazing with solar radiance. Deals extra damage to undead.",
    },
    "mithral chainmail": {
        "name": "Mithral Chainmail",
        "type": "Heavy Armor",
        "ac": "AC 16",
        "rarity": "Uncommon",
        "cost_gp": 450,
        "description": "Interlocking rings of featherlight elven mithral. Imposes no stealth disadvantage.",
    },
    "scroll of fireball": {
        "name": "Scroll of Fireball",
        "type": "Spell Scroll",
        "damage": "8d6 fire damage (20ft sphere, Dex save DC 15)",
        "rarity": "Rare",
        "cost_gp": 300,
        "description": "A crisp parchment inscribed with draconic runes that burst into a fiery inferno.",
    },
    "potion of invisibility": {
        "name": "Potion of Invisibility",
        "type": "Potion",
        "effect": "Grants invisible condition for 1 hour or until attacking/casting",
        "rarity": "Very Rare",
        "cost_gp": 800,
        "description": "Clear silver liquid that causes the drinker to fade completely from vision.",
    },
}


def roll_dice(dice_notation: str, reason: str = "") -> str:
    """Parses standard tabletop RPG dice notation and returns the roll breakdown.

    Args:
        dice_notation: RPG dice formula like '1d20+4', '2d6+3', '1d100', '3d8-2'.
        reason: Optional description or context for the roll (e.g. 'Attack check', 'Stealth save').

    Returns:
        Formatted string detailing each individual roll and the final total.
    """
    cleaned = dice_notation.strip().replace(" ", "").lower()
    pattern = r"^(\d+)d(\d+)([+-]\d+)?$"
    match = re.match(pattern, cleaned)
    if not match:
        return f"Invalid dice format '{dice_notation}'. Use standard format like '1d20+5' or '2d6'."

    count = int(match.group(1))
    sides = int(match.group(2))
    modifier = int(match.group(3)) if match.group(3) else 0

    if count < 1 or count > 100 or sides < 2 or sides > 1000:
        return "Dice limits exceeded (allowed: 1-100 dice, 2-1000 sides)."

    rolls = [random.randint(1, sides) for _ in range(count)]
    sum_rolls = sum(rolls)
    total = sum_rolls + modifier

    rolls_str = ", ".join(str(r) for r in rolls)
    mod_str = f" {modifier:+d}" if modifier != 0 else ""
    reason_prefix = f"[{reason}] " if reason else ""

    if sides == 20 and count == 1:
        if rolls[0] == 20:
            return f"{reason_prefix}Rolled {dice_notation}: Natural 20! (CRITICAL HIT!) Total = {total}"
        if rolls[0] == 1:
            return f"{reason_prefix}Rolled {dice_notation}: Natural 1! (CRITICAL MISS!) Total = {total}"

    return f"{reason_prefix}Rolled {dice_notation}: [{rolls_str}]{mod_str} = {total}"


def inspect_item(item_name: str) -> dict:
    """Look up an item, weapon, potion, or spell in the fantasy catalog.

    Args:
        item_name: Name of the item to inspect (e.g. 'longsword', 'elixir of healing').

    Returns:
        Dictionary containing item details, stats, rarity, cost, and description.
    """
    key = item_name.strip().lower()
    if key in CATALOG:
        return {"status": "found", "item": CATALOG[key]}

    for catalog_key, data in CATALOG.items():
        if key in catalog_key or key in data["name"].lower():
            return {"status": "found", "item": data}

    available = [data["name"] for data in CATALOG.values()]
    return {
        "status": "not_found",
        "message": f"Item '{item_name}' was not found in the shop catalog.",
        "available_items": available,
    }


def update_character_sheet(
    name: str,
    char_class: str,
    race: str,
    level: int = 1,
    current_hp: int = 10,
    max_hp: int = 10,
    xp: int = 0,
    add_items: str = "",
    remove_items: str = "",
) -> dict:
    """Calculates and updates character status, health, leveling, and inventory.

    Args:
        name: Name of the adventurer.
        char_class: Character class (e.g. 'Ranger', 'Wizard', 'Paladin').
        race: Character race (e.g. 'Wood Elf', 'Dwarf', 'Human').
        level: Current character level (1-20).
        current_hp: Current hit points.
        max_hp: Maximum hit points.
        xp: Current experience points.
        add_items: Comma-separated list of items to add to inventory.
        remove_items: Comma-separated list of items to remove from inventory.

    Returns:
        Dictionary with updated stats, level status, and inventory changes.
    """
    next_level_xp = level * 1000
    leveled_up = xp >= next_level_xp
    new_level = level + 1 if leveled_up else level

    added = [i.strip() for i in add_items.split(",") if i.strip()]
    removed = [i.strip() for i in remove_items.split(",") if i.strip()]

    return {
        "character": {
            "name": name,
            "race": race,
            "class": char_class,
            "level": new_level,
            "hp": f"{max(0, current_hp)}/{max_hp}",
            "xp": xp,
            "next_level_xp": new_level * 1000,
            "leveled_up": leveled_up,
        },
        "inventory_updates": {
            "items_added": added,
            "items_removed": removed,
        },
    }


def simulate_combat_round(
    attacker_bonus: int,
    damage_dice: str,
    defender_ac: int,
    defender_hp: int,
) -> dict:
    """Simulates a combat attack check and damage resolution against a defender.

    Args:
        attacker_bonus: Attack roll modifier (e.g. +5).
        damage_dice: Damage formula (e.g. '1d8+3').
        defender_ac: Armor class of target.
        defender_hp: Current HP of defender.

    Returns:
        Dictionary with attack roll, hit/miss outcome, damage dealt, and remaining HP.
    """
    d20 = random.randint(1, 20)
    attack_total = d20 + attacker_bonus
    is_crit = d20 == 20
    is_fumble = d20 == 1
    hit = (attack_total >= defender_ac or is_crit) and not is_fumble

    damage_dealt = 0
    if hit:
        cleaned = damage_dice.strip().replace(" ", "").lower()
        match = re.match(r"^(\d+)d(\d+)([+-]\d+)?$", cleaned)
        if match:
            cnt = int(match.group(1)) * (2 if is_crit else 1)
            sides = int(match.group(2))
            mod = int(match.group(3)) if match.group(3) else 0
            rolls = [random.randint(1, sides) for _ in range(cnt)]
            damage_dealt = max(1, sum(rolls) + mod)
        else:
            damage_dealt = random.randint(4, 10)

    remaining_hp = max(0, defender_hp - damage_dealt)

    return {
        "attack_roll": {
            "natural_d20": d20,
            "total": attack_total,
            "target_ac": defender_ac,
            "critical_hit": is_crit,
            "hit": hit,
        },
        "damage": {
            "dealt": damage_dealt,
            "defender_initial_hp": defender_hp,
            "defender_remaining_hp": remaining_hp,
            "defender_defeated": remaining_hp == 0,
        },
    }


def fetch_srd_monster_stats(monster_name: str) -> Dict[str, Any]:
    """Fetch official 5e SRD stat block for a creature from the Open5e API.

    Args:
        monster_name: Name of the creature to look up (e.g. 'Goblin', 'Owlbear', 'Adult Red Dragon').

    Returns:
        A dictionary containing Armor Class, Hit Points, Challenge Rating, speed, and attacks.
    """
    import requests

    try:
        resp = requests.get(
            "https://api.open5e.com/v1/monsters/",
            params={"search": monster_name.strip()},
            timeout=8,
        )
        if resp.status_code != 200:
            return {"status": "error", "message": f"API returned status {resp.status_code}"}

        results = resp.json().get("results", [])
        if not results:
            return {"status": "not_found", "message": f"No SRD stats found for '{monster_name}'."}

        target = monster_name.strip().lower()
        selected = next((m for m in results if m.get("name", "").lower() == target), results[0])

        actions = [
            {"name": a.get("name"), "desc": a.get("desc")}
            for a in selected.get("actions", [])[:3]
        ]

        return {
            "status": "found",
            "name": selected.get("name"),
            "size_type": f"{selected.get('size', '')} {selected.get('type', '')}".strip(),
            "armor_class": selected.get("armor_class"),
            "hit_points": selected.get("hit_points"),
            "challenge_rating": selected.get("challenge_rating"),
            "speed": selected.get("speed"),
            "actions": actions,
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch monster stats: {str(e)}"}


def fetch_srd_spell(spell_name: str) -> Dict[str, Any]:
    """Look up official 5e SRD spell rules, components, range, and damage from the D&D 5e API.

    Args:
        spell_name: Name of the spell to look up (e.g. 'Fireball', 'Cure Wounds', 'Magic Missile', 'Haste').

    Returns:
        A dictionary containing spell level, school, casting time, range, duration, components, and description.
    """
    import os
    import re
    import requests

    base_url = os.getenv("DND5E_API_BASE_URL", "https://www.dnd5eapi.co/api/2014")
    slug = re.sub(r"[^a-z0-9]+", "-", spell_name.strip().lower()).strip("-")

    try:
        resp = requests.get(f"{base_url}/spells/{slug}", timeout=8)
        if resp.status_code == 200:
            data = resp.json()
        else:
            search_resp = requests.get(f"{base_url}/spells", params={"name": spell_name.strip()}, timeout=8)
            if search_resp.status_code != 200 or not search_resp.json().get("results"):
                return {"status": "not_found", "message": f"Spell '{spell_name}' not found in the 5e SRD spellbook."}
            match_url = search_resp.json()["results"][0]["url"]
            detail_resp = requests.get(f"https://www.dnd5eapi.co{match_url}", timeout=8)
            if detail_resp.status_code != 200:
                return {"status": "not_found", "message": f"Could not retrieve details for '{spell_name}'."}
            data = detail_resp.json()

        return {
            "status": "found",
            "name": data.get("name"),
            "level": data.get("level"),
            "school": (data.get("school") or {}).get("name"),
            "casting_time": data.get("casting_time"),
            "range": data.get("range"),
            "components": ", ".join(data.get("components", [])),
            "material": data.get("material", "None"),
            "duration": data.get("duration"),
            "concentration": data.get("concentration", False),
            "ritual": data.get("ritual", False),
            "description": "\n".join(data.get("desc", [])),
            "higher_level": "\n".join(data.get("higher_level", [])),
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fetch spell from D&D 5e API: {str(e)}"}
