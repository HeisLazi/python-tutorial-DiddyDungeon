import { lanternItemArt } from './lanternItemArt.js'

// Individual campaign art takes precedence. The remaining inventory uses
// illustrated object types until a bespoke sprite is made for that item.
const ITEM_ART = {
  // Elite keepsakes use existing object art until each receives a bespoke icon.
  'elite-00-lantern-vale-echo-knot': 'bandage', 'elite-00-lantern-vale-delivery-seal': 'scroll',
  'elite-00-lantern-vale-caravan-gear': 'key', 'elite-00-lantern-vale-open-road-token': 'compass',
  'elite-04-casino-slots-debt-ghoul-token': 'silver-coin', 'elite-04-casino-slots-greed-spirits-coin': 'poker-chip',
  'elite-04-casino-slots-balancers-weight': 'abacus', 'elite-04-casino-slots-front-door-key': 'key',
  'elite-05-dungeon-crawler-seeded-maze-knot': 'bandage', 'elite-05-dungeon-crawler-star-seekers-lens': 'gemstone',
  'elite-05-dungeon-crawler-context-keepers-seal': 'scroll', 'elite-05-dungeon-crawler-lantern-keepers-wick': 'flame-charm',
  'elite-05-dungeon-crawler-inquisitors-sigil': 'shield',
  'bj-dealer-s-waistcoat': 'dealer-waistcoat', 'bj-velvet-felt-jacket': 'velvet-jacket', 'bj-pit-boss-coat': 'pit-coat',
  'bj-card-edge-dagger': 'card-dagger', 'bj-croupier-s-rake': 'croupier-rake', 'bj-ace-of-spades-blade': 'ace-blade',
  'bj-lucky-chip': 'poker-chip', 'bj-marked-card': 'playing-card', 'bj-counting-abacus': 'abacus', 'bj-free-bar-peanuts': 'peanuts', 'bj-casino-coffee': 'coffee', 'bj-midnight-club-sandwich': 'sandwich', 'bj-high-roller-steak': 'steak', 'bj-pit-boss-espresso': 'coffee',
  'cas-doorman-s-livery': 'doorman-coat', 'cas-silver-sequin-vest': 'sequin-vest', 'cas-auditor-s-waistcoat': 'auditor-vest',
  'cas-coin-roll-club': 'coin-club', 'cas-lever-arm-mace': 'lever-mace', 'cas-reel-spinner-chakram': 'chakram',
  'cas-silver-dollar': 'silver-coin', 'cas-weighted-die': 'dice', 'cas-auditor-s-ledger': 'ledger', 'cas-buffet-shrimp': 'shrimp', 'cas-lucky-fortune-cookie': 'fortune-cookie', 'cas-all-night-breakfast': 'steak', 'cas-jackpot-platter': 'shrimp', 'cas-auditor-s-black-tea': 'coffee',
  'lv-06': 'leather-coat', 'lv-07': 'blue-coat', 'lv-08': 'brigandine',
  'lv-16': 'bread', 'lv-17': 'soup', 'lv-18': 'soup', 'lv-19': 'bread', 'lv-20': 'green-tonic', 'lv-21': 'red-tonic',
  'dc-miner-s-pickaxe': 'pickaxe', 'dc-lantern-lit-shortsword': 'shortsword', 'dc-deepvein-warhammer': 'hammer',
  'dc-canvas-mining-smock': 'hunter-coat', 'dc-riveted-leather': 'leather-coat', 'dc-deepvein-brigandine': 'brigandine',
  'dc-compass-needle': 'compass', 'dc-ore-sniffer-charm': 'gemstone', 'dc-canary-feather': 'flame-charm',
  'dc-miner-s-pasty': 'bread', 'dc-tin-cup-broth': 'soup', 'dc-deep-mushroom-stew': 'soup', 'dc-brigid-s-feast-loaf': 'bread', 'dc-glowcap-tonic': 'green-tonic', 'dc-deepvein-draught': 'red-tonic',
  'aid-pyrs-favour': 'flame-charm', 'aid-ward-shield': 'shield', 'aid-pyrs-blessing': 'flame-charm', 'aid-aegis-of-patience': 'shield',
  'aid-scholar-note': 'scroll', 'aid-lantern-ward': 'shield', 'aid-travellers-kit': 'bandage',
  'merchant-vigil-sabre': 'ornate-sword', 'merchant-moonlit-staff': 'key', 'merchant-nightfall-greatsword': 'hammer',
  'merchant-road-rations': 'consumable-road-rations', 'merchant-orchard-apple': 'consumable-orchard-apple',
  'merchant-herbal-tea': 'consumable-herbal-tea', 'merchant-wayside-stew': 'consumable-wayside-stew',
  'merchant-scholars-tea': 'consumable-scholars-tea', 'merchant-warding-draught': 'consumable-warding-draught',
  'merchant-hearth-pie': 'consumable-hearth-pie', 'merchant-steadfast-tonic': 'consumable-steadfast-tonic',
  'merchant-traders-tonic': 'consumable-traders-tonic', 'merchant-hunters-feast': 'consumable-hunters-feast',
  'merchant-insight-elixir': 'consumable-insight-elixir', 'merchant-lucky-ward': 'consumable-lucky-ward',
  'merchant-grand-banquet': 'consumable-grand-banquet', 'merchant-sages-resolve': 'consumable-sages-resolve',
  'merchant-gilded-aegis': 'consumable-gilded-aegis',
  'dungeon-heal': 'bread', 'dungeon-bandage': 'bandage', 'dungeon-ration': 'bread', 'dungeon-tonic': 'red-tonic', 'dungeon-ward': 'shield', 'dungeon-field-jacket': 'hunter-coat', 'dungeon-syntax-cuirass': 'breastplate',
  'field-bandage': 'bandage', 'ember-tonic': 'red-tonic', 'camp-meal': 'soup',
  'debugger-plate': 'breastplate', 'ledgerguard-coat': 'blue-coat', 'emberweave-mantle': 'hunter-coat',
}
const SLOT_ART = { weapon: 'shortsword', armor: 'leather-coat', trinket: 'gemstone', food: 'bread', tonic: 'green-tonic', aid: 'shield', supply: 'bandage', relic: 'gemstone' }

export function merchantItemArt(item) {
  const custom = lanternItemArt(item?.id)
  if (custom) return custom
  const name = ITEM_ART[item?.id] || item?.art || SLOT_ART[item?.slot] || 'gemstone'
  return `${import.meta.env?.BASE_URL || '/'}campaign-art/items/merchant/${name}.png`
}
