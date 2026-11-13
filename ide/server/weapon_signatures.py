"""Signature abilities for every weapon (the 2026-11-13 weapon redesign).

A weapon used to be "+N impact" plus a coin number, so most of them played the same. Each weapon now
adds a *trigger*: a situation in the fight that makes it hit harder or help you. The trigger words
match the Dungeon's own run weapons (first, clean, follow, retry, low HP) plus a few new ones, and the
campaign objective loop reads them through :func:`signature_bonus`.

Nothing here is stored in a save. Saves and cloud checks carry only item ids, so changing what an id
does never makes an older build reject a save.

Each row is ``item id -> (combat style, shape, effect additions)``. ``shape`` is the weapon's real
silhouette (hammer, spear, chakram...). Until a style animation exists for a shape the weapon uses the
closest existing combat ``style``, and the art brief in ``docs/WEAPON_ART_KIT.md`` asks for the real thing.
"""
from __future__ import annotations

from typing import Any, Mapping

# One-line meaning of each trigger, in the words shown to the player.
SIGNATURE_TEXT = {
    "chip_streak": "+{n} impact on your third clean objective in a row",
    "chip_switch": "+{n} impact when the question type changes",
    "chip_chain": "+{n} impact when the question type repeats",
    "chip_heavy": "+{n} impact on objectives worth 4 or more",
    "chip_finish": "+{n} impact once the enemy is at 40% Resolve or less",
    "chip_ramp": "+{n} impact for every two objectives already verified (up to +3)",
    "chip_clean": "+{n} impact on an objective you get right first time",
    "chip_follow": "+{n} impact on a clean follow-up (not the first objective)",
    "chip_low": "+{n} impact while you are at half HP or less",
    "heal_clean": "heal {n} HP on an objective you get right first time",
    "coin_clean": "+{n} coins on an objective you get right first time",
    "break_guard": "one extra free mistake when you break a guard",
}
SIGNATURE_LABEL = {
    "chip_streak": "Combo", "chip_switch": "Variety", "chip_chain": "Chain", "chip_heavy": "Heavy blow",
    "chip_finish": "Reap", "chip_ramp": "Burn", "chip_clean": "Precision", "chip_follow": "Follow-up",
    "chip_low": "Last stand", "heal_clean": "Mend", "coin_clean": "Pay-out", "break_guard": "Guard",
}
SIGNATURE_CAPS = {key: (1 if key == "break_guard" else 3) for key in SIGNATURE_TEXT}
IMPACT_KEYS = ("chip_streak", "chip_switch", "chip_chain", "chip_heavy", "chip_finish", "chip_ramp", "chip_clean", "chip_follow", "chip_low")

# item id -> (combat style, shape, additions to the existing effect)
WEAPON_SIGNATURES: dict[str, tuple[str, str, dict[str, int]]] = {
    # Lantern Vale
    "lv-01": ("sword", "sword", {"chip_streak": 1}),
    "lv-02": ("sword", "sword", {"heal_clean": 1}),
    "lv-03": ("greatsword", "hammer", {"chip_heavy": 1}),
    "lv-04": ("staff", "spear", {"chip_follow": 1}),
    "lv-05": ("sword", "sword", {"chip_streak": 2, "break_guard": 1}),
    # Blackjack
    "bj-card-edge-dagger": ("sword", "dagger", {"chip_follow": 1}),
    "bj-croupier-s-rake": ("whip", "rake", {"chip_chain": 1, "coin_clean": 1}),
    "bj-ace-of-spades-blade": ("sword", "sword", {"chip_streak": 1, "coin_clean": 1}),
    "bj-the-shoe-splitter": ("greatsword", "cleaver", {"chip_heavy": 2}),
    "bj-the-house-cutter": ("sword", "cutlass", {"coin_clean": 2, "chip_clean": 1}),
    # Casino Slots
    "cas-coin-roll-club": ("greatsword", "club", {"coin_clean": 1, "chip_heavy": 1}),
    "cas-lever-arm-mace": ("greatsword", "mace", {"opening_impact": 1, "chip_heavy": 1}),
    "cas-reel-spinner-chakram": ("handmagic", "chakram", {"chip_switch": 1, "coin_clean": 1}),
    "cas-jackpot-hammer": ("greatsword", "hammer", {"chip_heavy": 2, "coin_clean": 1}),
    "cas-lady-luck-s-sceptre": ("handmagic", "sceptre", {"coin_clean": 2, "heal_clean": 1}),
    "cas-oil-of-doom": ("oil", "oil", {"chip_ramp": 1}),
    # Dungeon Crawler
    "dc-miner-s-pickaxe": ("scythe", "pickaxe", {"chip_finish": 1, "chip_heavy": 1}),
    "dc-lantern-lit-shortsword": ("sword", "shortsword", {"chip_follow": 1, "heal_clean": 1}),
    "dc-deepvein-warhammer": ("greatsword", "warhammer", {"chip_heavy": 2, "chip_low": 1}),
    "dc-cartographer-s-spear": ("staff", "spear", {"chip_switch": 2}),
    "dc-the-core-breaker": ("greatsword", "greatsword", {"chip_heavy": 2, "break_guard": 1}),
    # Hunter's kit and the Merchant
    "hunter-sparring-staff": ("staff", "staff", {"chip_switch": 1}),
    "hunter-sparring-whip": ("whip", "whip", {"chip_chain": 1}),
    "hunter-sparring-greatsword": ("greatsword", "greatsword", {"chip_heavy": 1}),
    "hunter-sparring-scythe": ("scythe", "scythe", {"chip_finish": 1}),
    "hunter-sparring-focus": ("handmagic", "focus", {"heal_clean": 1}),
    "merchant-vigil-sabre": ("sword", "sabre", {"chip_clean": 1}),
    "merchant-moonlit-staff": ("staff", "staff", {"chip_switch": 1}),
    "merchant-nightfall-greatsword": ("greatsword", "greatsword", {"chip_heavy": 1}),
    "hunter-gravebound-greatblade": ("greatsword", "greatsword", {"chip_heavy": 1, "chip_low": 1}),
    "hunter-jack-scythe": ("scythe", "scythe", {"chip_finish": 1, "opening_impact": 1, "coin_clean": 1}),
    # Legacy Journal echoes of the Dungeon's weapons (each keeps the feel of its run original)
    "campaign-dungeon-syntax-sabre": ("sword", "sabre", {"chip_clean": 1}),
    "campaign-dungeon-loopblade": ("sword", "sword", {"chip_chain": 1}),
    "campaign-dungeon-aether-staff": ("staff", "staff", {"break_guard": 1}),
    "campaign-dungeon-pathfinder-whip": ("whip", "whip", {"opening_impact": 1, "chip_chain": 1}),
    "campaign-dungeon-iron-greatsword": ("greatsword", "greatsword", {"retry_impact": 2, "chip_heavy": 1}),
    "campaign-dungeon-grave-scythe": ("scythe", "scythe", {"heal_on_break": 3, "chip_finish": 1, "chip_low": 1}),
    "campaign-dungeon-runic-casting": ("handmagic", "focus", {"heal_clean": 1, "chip_follow": 1}),
    "campaign-dungeon-dawn-lantern": ("staff", "lantern", {"chip_switch": 1, "heal_on_break": 2}),
    "campaign-dungeon-undertow-scythe": ("scythe", "scythe", {"chip_finish": 2, "break_guard": 1}),
    "campaign-dungeon-warden-chain": ("whip", "chain", {"chip_follow": 2, "chip_chain": 1}),
    "campaign-dungeon-last-page": ("handmagic", "tome", {"heal_clean": 1}),
    "campaign-dungeon-minotaur-edge": ("greatsword", "greatsword", {"chip_low": 2, "chip_heavy": 1}),
    "campaign-dungeon-clockwork-greatblade": ("greatsword", "greatsword", {"retry_impact": 3, "chip_heavy": 1}),
    "campaign-dungeon-oracle-staff": ("staff", "staff", {"chip_clean": 2}),
    "campaign-dungeon-hollow-fang": ("sword", "fang", {"heal_on_break": 4, "chip_streak": 1}),
}


def apply_signatures(catalog: dict[str, dict[str, Any]]) -> None:
    """Merge each weapon's signature into the catalog entry (in place, once per build)."""
    for item_id, (style, shape, extra) in WEAPON_SIGNATURES.items():
        item = catalog.get(item_id)
        if item is None or item.get("slot") != "weapon":
            continue
        catalog[item_id] = {**item, "effect": {**item.get("effect", {}), **extra}, "combat_style": style, "shape": shape}


def signature_text(effect: Mapping[str, Any]) -> list[str]:
    """Plain-words lines for the signature keys in an effect, in a stable order."""
    return [SIGNATURE_TEXT[key].format(n=int(effect[key])) for key in SIGNATURE_TEXT if effect.get(key)]


def signature_bonus(effect: Mapping[str, Any] | None, *, first: bool, clean: bool, streak: int, low_hp: bool,
                    heavy: bool, last_type: str | None, this_type: str, enemy_low: bool, verified: int) -> tuple[int, list[str]]:
    """Extra impact earned by one verified objective, with the names of the triggers that fired."""
    if not effect:
        return 0, []
    def cap(key: str) -> int:
        return max(0, min(SIGNATURE_CAPS[key], int(effect.get(key) or 0)))
    fired: list[tuple[str, int]] = []
    if clean and streak >= 3:
        fired.append(("chip_streak", cap("chip_streak")))
    if last_type is not None and last_type != this_type:
        fired.append(("chip_switch", cap("chip_switch")))
    if last_type is not None and last_type == this_type:
        fired.append(("chip_chain", cap("chip_chain")))
    if heavy:
        fired.append(("chip_heavy", cap("chip_heavy")))
    if enemy_low:
        fired.append(("chip_finish", cap("chip_finish")))
    if verified >= 2:
        fired.append(("chip_ramp", min(3, (verified // 2) * cap("chip_ramp")) if cap("chip_ramp") else 0))
    if clean:
        fired.append(("chip_clean", cap("chip_clean")))
    if clean and not first:
        fired.append(("chip_follow", cap("chip_follow")))
    if low_hp:
        fired.append(("chip_low", cap("chip_low")))
    fired = [(key, amount) for key, amount in fired if amount]
    return sum(amount for _, amount in fired), [f"{SIGNATURE_LABEL[key]} +{amount}" for key, amount in fired]
