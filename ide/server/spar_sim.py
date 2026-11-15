"""The Sparring Ring's fight rules, so gear does something when you try it on.

A spar is five questions against a simulated foe. It reuses the real campaign rules for what gear does
(`LocalStateService._gear_effects` resolves the loadout, `weapon_signatures.signature_bonus` fires the
weapon triggers) on a small fixed fight:

* the hunter has 20 hit points and every wrong answer is a 4 point counterattack;
* the foe has 12 Resolve and the five questions are worth 2, 2, 2, 2 and 4 (the last is the heavy one);
* damage reduction, free mistakes, guards, revive, healing and impact work as they do in a hunt, and a
  hit that would finish the foe early breaks its guard instead (the "iron rule": the last question ends it).

Coins, XP and loot do not exist in a simulation, so those effects are reported as not applied.
Nothing here reads or writes a save.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from ide.server.weapon_signatures import signature_bonus, signature_text

SPAR_ROUNDS = 5
SPAR_HP = 20
SPAR_RAW_DAMAGE = 4
SPAR_ROUND_IMPACT = (2, 2, 2, 2, 4)
SPAR_RESOLVE = sum(SPAR_ROUND_IMPACT)
SPAR_GUARD_CAP = 3
SPAR_IMPACT_CAP = 11  # the campaign's MAX_IMPACT (8) plus the impact effect cap (3)
# The three ways a spar question is answered, in the campaign's question-type words.
SPAR_QUESTION_TYPES = {"choice": "prediction", "text": "explanation", "code": "code_checkpoint"}
# Effects that only matter for rewards, which a simulation does not give.
UNAPPLIED_EFFECTS = (
    ("coin_bonus", "+{n}% coins"), ("xp_bonus", "+{n}% XP"), ("loot_luck", "+{n}% loot luck"),
)
SPAR_QUESTION_TYPES_WORDS = {"code_checkpoint": "code", "prediction": "prediction", "explanation": "explanation", "bug_diagnosis": "bug-hunt"}
UNAPPLIED_WEAPON_EFFECTS = (("break_coins", "+{n} coins on a Guard Break"), ("coin_clean", "+{n} coins on a clean objective"))


def _matches(on: Any, qtype: str) -> bool:
    """Whether an effect that applies `on` a kind of question applies to this one. A spar's code question can be
    a code checkpoint or a bug hunt, so a bug-hunt effect counts for it too."""
    return on == "any" or on == qtype or (qtype == "code_checkpoint" and on == "bug_diagnosis")


def _int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def simulate(effects: Mapping[str, Any], rounds: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Replay the answered rounds with this gear. Each round is {"correct": bool, "kind": choice|text|code}."""
    weapon = effects.get("weapon") or None
    triggers = effects.get("triggers") or None  # the weapon's and the trinket's triggers, summed
    set_bonus = effects.get("set_bonus") or {}
    reduction = min(80, _int(effects.get("reduction")))
    hp, resolve = SPAR_HP, SPAR_RESOLVE
    start_guards = min(SPAR_GUARD_CAP, _int(effects.get("start_guards")))
    guards = start_guards
    completed = streak = 0
    last_type: str | None = None
    first_miss_used = revive_used = False
    out: list[dict[str, Any]] = []
    for index, entry in enumerate(rounds[:SPAR_ROUNDS]):
        qtype = SPAR_QUESTION_TYPES.get(str(entry.get("kind")), "prediction")
        base = SPAR_ROUND_IMPACT[index]
        remaining = sum(SPAR_ROUND_IMPACT[index + 1:])
        fired: list[str] = []
        damage = healed = impact = 0
        guard_broken = False
        if entry.get("correct"):
            before = resolve
            impact = base
            if weapon and _matches(weapon.get("on"), qtype) and _int(weapon.get("impact")):
                impact += _int(weapon.get("impact"))
                fired.append(f"Weapon +{_int(weapon.get('impact'))}")
            if triggers and completed == 0 and _int(triggers.get("opening_impact")):
                impact += _int(triggers.get("opening_impact"))
                fired.append(f"Opening +{_int(triggers.get('opening_impact'))}")
            streak += 1
            low_hp = hp * 2 <= SPAR_HP
            bonus, labels = signature_bonus(
                triggers, first=completed == 0, clean=True, streak=streak, low_hp=low_hp, heavy=base >= 4,
                last_type=last_type if completed else None, this_type=qtype,
                enemy_low=before * 5 <= SPAR_RESOLVE * 2, verified=completed,
            )
            impact += bonus
            fired += labels
            if _matches(effects.get("trinket_on"), qtype) and _int(effects.get("trinket_impact")):
                impact += _int(effects.get("trinket_impact"))
                fired.append(f"Trinket +{_int(effects.get('trinket_impact'))}")
            if _matches(effects.get("armor_on"), qtype) and _int(effects.get("armor_impact")):
                impact += _int(effects.get("armor_impact"))
                fired.append(f"{effects.get('armor_name') or 'Armour'} +{_int(effects.get('armor_impact'))}")
            if _matches(set_bonus.get("on"), qtype) and _int(set_bonus.get("impact")):
                impact += _int(set_bonus.get("impact"))
                fired.append(f"Set +{_int(set_bonus.get('impact'))}")
            impact = min(SPAR_IMPACT_CAP, impact)
            resolve = max(0, before - impact)
            if resolve == 0 and remaining > 0:
                extra = _int(triggers.get("break_guard")) if triggers else 0
                guards = min(SPAR_GUARD_CAP, guards + 1 + extra)
                resolve = max(1, remaining)
                guard_broken = True
                fired.append("Guard break")
            heal = _int(effects.get("heal_on_objective"))
            if triggers:
                heal += _int(triggers.get("heal_clean"))
                if guard_broken:
                    heal += _int(triggers.get("heal_on_break"))
            if heal:
                healed = min(heal, SPAR_HP - hp)
                hp += healed
                if healed:
                    fired.append(f"Heal +{healed}")
            completed += 1
            last_type = qtype
        else:
            streak = 0
            damage = max(1, (SPAR_RAW_DAMAGE * (100 - reduction) + 99) // 100)
            if guards > 0:
                guards -= 1
                damage = 0
                fired.append("Guard held")
            elif (effects.get("first_miss_free") or effects.get("block_first_miss")) and not first_miss_used:
                first_miss_used = True
                damage = 0
                fired.append(f"{effects.get('first_miss_source') or 'Free mistake'}: no damage")
            elif reduction and damage < SPAR_RAW_DAMAGE:
                fired.append(f"Armour −{SPAR_RAW_DAMAGE - damage}")
            hp = max(0, hp - damage)
            if hp == 0 and effects.get("revive") and not revive_used:
                revive_used = True
                hp = 1
                fired.append("Revive")
        out.append({
            "correct": bool(entry.get("correct")), "hp": hp, "resolve": resolve, "damage": damage, "impact": impact,
            "base_impact": base, "healed": healed, "guards": guards, "guard_broken": guard_broken, "fired": fired,
        })
    return {
        "max_hp": SPAR_HP, "max_resolve": SPAR_RESOLVE, "start": {"hp": SPAR_HP, "resolve": SPAR_RESOLVE, "guards": start_guards},
        "rounds": out,
    }


def effect_lines(effects: Mapping[str, Any]) -> dict[str, list[str]]:
    """What the loadout does in the ring, and what it does only for rewards (so nothing here)."""
    weapon = effects.get("weapon") or {}
    triggers = effects.get("triggers") or {}
    applied: list[str] = []
    if _int(effects.get("reduction")):
        applied.append(f"{_int(effects.get('reduction'))}% less damage from wrong answers")
    if effects.get("first_miss_free") or effects.get("block_first_miss"):
        applied.append(f"Your first wrong answer costs nothing ({effects.get('first_miss_source') or 'gear'})")
    if _int(effects.get("start_guards")):
        applied.append(f"Starts with {_int(effects.get('start_guards'))} free mistake")
    if effects.get("revive"):
        applied.append(f"Survives one knockout ({effects.get('revive_source') or 'gear'})")
    if _int(effects.get("heal_on_objective")):
        applied.append(f"Heal {_int(effects.get('heal_on_objective'))} HP on every right answer")
    if _int(weapon.get("impact")):
        on = weapon.get("on", "any")
        applied.append(f"+{_int(weapon.get('impact'))} impact" + ("" if on == "any" else f" on {SPAR_QUESTION_TYPES_WORDS.get(str(on), str(on))} questions"))
    if _int(triggers.get("opening_impact")):
        applied.append(f"+{_int(triggers.get('opening_impact'))} impact on the first right answer")
    if _int(triggers.get("heal_on_break")):
        applied.append(f"Heal {_int(triggers.get('heal_on_break'))} HP when you break a guard")
    if _int(effects.get("trinket_impact")):
        applied.append(f"+{_int(effects.get('trinket_impact'))} impact from your trinket")
    if _int(effects.get("armor_impact")):
        on = effects.get("armor_on", "any")
        applied.append(f"+{_int(effects.get('armor_impact'))} impact from your armour" + ("" if on == "any" else f" on {SPAR_QUESTION_TYPES_WORDS.get(str(on), str(on))} questions"))
    applied += signature_text({key: value for key, value in triggers.items() if key not in {"coin_clean"}})
    ignored = [text.format(n=_int(effects.get(key))) for key, text in UNAPPLIED_EFFECTS if _int(effects.get(key))]
    ignored += [text.format(n=_int(triggers.get(key))) for key, text in UNAPPLIED_WEAPON_EFFECTS if _int(triggers.get(key))]
    return {"applied": applied, "ignored": ignored}

