# Item redesign plan — 2026-11-13

Lazi's note: weapons, armour, trinkets, food, tonics, aids and relics feel like copies of each
other. Same passive, same look, and only one piece of art per item that rarely appears in combat.
This is the audit that backs that up, and a plan to fix it.

## Audit (193 items in the armory catalog)

| Slot | Items | Distinct exact effects | What the effects are made of |
|---|---|---|---|
| Weapon | 46 | 24 | 27 are plain "+N impact on every/one objective". 11 add Guard-Break coins. Only 7 do anything else. |
| Armour | 33 | 11 | 29 are only "N% less damage from misses". 4 add "first miss free". |
| Trinket | 64 | 17 | Mostly one number each: start guard (15), heal per objective (12), block first miss (11), +impact (10), coin bonus (9), loot luck (7). |
| Food | 22 | 9 | A heal amount, or a next-battle buff. |
| Tonic | 17 | 11 | Same palette as food. |
| Relic | 4 | 3 | XP or coin bonus. |
| Aid | 7 | 6 | Free Asks or wards. |

Every effect is a number from a closed list (`ARMORY_EFFECT_CAPS` in `ide/server/state.py`).
Nothing is a *mechanic*, so two items at the same tier feel identical whatever they are called.

**Art**
- `lanternItemArt.js` gives a dedicated icon to 17 of 46 weapons, 3 of 33 armours, 8 of 64
  trinkets, and none of the 22 foods, 17 tonics or 7 aids. The rest fall back to shared generic art.
- Where an icon is mapped, many reuse one stock merchant image (scroll x3, blue coat x3,
  key x2, gemstone x2, flame charm x2, brigandine x2, breastplate x2, greatsword x2).
- Only 37 item icon files exist in total.

**Combat scene**
- Weapons: 7 combat styles (sword, staff, whip, greatsword, hand magic, scythe, oil). 20 of 46
  weapons have no style, and every weapon of a style uses the same sprite sheet.
- Armour: 12 looks (`hunterEquipment.js` regex-matches the name; the rest become "steel", "ember"
  or "arcane" palette swaps). 33 armours share these 12 looks.
- Trinkets: 3 can be seen on the hunter. Food, tonics, aids and relics: none appear in combat.

## Direction

1. **Abilities become mechanics, not numbers.** Each gear item gets a `trigger` and an `action`
   (battle start, objective verified, wrong answer, Guard Break, streak of N, low HP, boss phase,
   each use...). One engine evaluates them for the Dungeon, campaign and duel paths.
   Signature mechanic per weapon family, so choosing a weapon changes how you play:
   - sword: streak combos; staff: charged spell from Ask PYR; whip: chain reach across objectives;
   - greatsword: slow heavy hit that needs a clean answer; hand magic: element on the strike;
   - scythe: execute on low-HP enemies; oil: hazard that ticks.
   Armour gets one passive plus one reaction (thorns, regen, a bonus when you fall). Trinkets get
   exactly one gimmick. Consumables get a visible status effect.
2. **Every item gets its own art.** A weapon is its own sprite (blade shape, hilt, colour, a
   distinct hit effect), not a style plus a number. Armour keeps the culture-led sets. Trinkets,
   foods, tonics, aids and relics each get their own icon and, where it reads, a visible prop
   or a use effect in combat.
3. **Combat shows what you wear and use.** Weapon, armour, trinket and consumable use all render
   in the Godot scene and the Home hunter.
4. **Fairness.** Online duels and cloud checks accept only known ability ids. Old saves keep
   their items, and each old item maps onto a new ability so nothing in a player's pack breaks.

## Order of work

0. Design table for all 193 items: name, region and culture, the one ability, art brief. (Claude.)
1. Ability engine plus tests, behind the existing numeric effects so old items still work. (Claude.)
2. Weapons first (46): abilities, then art briefs for Argon and Codex, slicing and wiring.
3. Armour (33): reactions plus the remaining distinct looks.
4. Trinkets (64): one gimmick each, icons, three to five visible props.
5. Food, tonics, aids and relics: status effects, icons and use effects in combat.

Each phase ends with a playable build to check on the test save (`tools/questlab-test.sh`).

## Open questions for Lazi

- Which family first? Recommendation: weapons.
- Duels: should the new abilities also apply in online duels, or only in the campaign and Dungeon
  first? Recommendation: campaign and Dungeon first, then duels once balance holds.
