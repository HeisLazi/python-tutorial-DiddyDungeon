# Quest Lab · Campaign v1 Design Lab

This is an isolated prototype for the campaign revamp. It does not call the Quest Lab API, mutate `progress.json`, touch Supabase, or reset either PTY.

## Start it in WSL

From the repository root:

```bash
bash tools/campaign-v1-prototype.sh
```

Then open <http://127.0.0.1:5207/>.

## v1 design contract

- The campaign map is a three-POI menu: **Home**, **Market**, and **Bounty Office**. It is deliberately not a route tree.
- Home is a camp menu with selectable Hearth, Armory, Pantry, and Study stations. The action panel changes with the selected station while the live armor/trinket loadout and supplies stay visible below.
- Market is an auction-house scene: speak with Rook first, then open the day’s lots. The stock contains coins-priced armor, trinkets, and supplies; buy in Market and equip from Home.
- Bounty Office contains main project bounties and optional village tasks. Village tasks are local jobs that use learning challenges such as output prediction, tracing, bug hunting, and tiny transfer work.
- Forge encounters keep the local self-check terminal beneath the editor and a tall PYR / AI event terminal on the right. The provider row can select Codex, Claude, AGY, or Copilot as the prototype's PYR channel; it is a local presentation control, not a live provider connection.
- The prototype uses fixture data. Main bounties and village tasks share the same eventual Forge handoff, but the actual validator is represented by a clearly labelled design-lab control.
- The combat model separates **Guard** (mob defense), **Resolve** (player guard-break impact), and the **Finisher** (the complete correct Forge submission). Guard Break stuns the mob for one submission window and suppresses its primary mechanic; it never replaces the coding requirement.
- Run is a self-check only. Submit is the future validation boundary. In this lab, the `Verify checkpoint` control stands in for bounded AST/runtime/output evidence so the Guard Break loop can be reviewed visually.
- The encounter left rail now includes the equipped armor/trinket plus encounter supplies. A bandage heals locally; an Ember tonic is a one-use buffer that halves the next failed-submission damage. The center Forge terminal and right PYR channel use terminal-style output windows; they are local design-lab output surfaces, not live PTY connections.
- Elites remain single-phase in v1. Boss phases are intentionally deferred until this core loop feels correct.

The prototype is a design lab, not a production save or balance system. Once the flow is approved, the next slice should add the state-service event contract and a real disposable validator before any canonical campaign wiring.

Run isolated checks with:

```bash
npm test --prefix prototypes/campaign-v1
npm run build --prefix prototypes/campaign-v1
```
