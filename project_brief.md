# My agent: RealmCrafter - Fantasy RPG Character & Quest Companion
One-liner: A conversational agent that helps tabletop and RPG adventurers craft heroes, track quest progress, and manage gear with a catalog of fantasy weapons, spells, and monsters.

Tool coverage:
- Memory: Character profile (name, race, class, level, ability scores, max/current HP), current inventory & gold, and completed quest history across sessions.
- Tools: Roll dice (`roll_dice`), equip/unequip inventory items (`manage_gear`), update HP and award XP (`update_character_status`), and lookup monster/item stats (`inspect_item`).
- Catalog/UI: Magic item shop catalog, spellbook cards, and quest board tables rendered via A2UI.
- Image gen: Generates character portraits, artifact illustrations, and encounter scene visuals with Imagen.
- Sandbox: Computes battle outcomes, calculates critical hit probabilities, and tracks stat progression in Python.

Recommended for every project: memory, storage, tools, image generation, A2UI
Agent-specific / stretch (pick what fits): code sandbox for dice simulations & combat calculations, Cloud Trace for tracing tool interactions
