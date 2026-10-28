import { HOME_DIRECTORY } from './homeDirectory.js'

// Small, readable furniture shapes make each chamber recognizable at map scale.
function Furniture({ id }) {
  switch (id) {
    case 'gallery': return <><path d="M8 8h6v5H8z M18 8h6v5h-6z M28 8h6v5h-6z" fill="#b5b5bc"/><path d="M7 14h8 M17 14h8 M27 14h8" stroke="#85818c"/></>
    case 'library': return <><path d="M4 4h9v3H4z M27 4h9v3h-9z" fill="#c4a67a"/><rect x="9" y="15" width="10" height="5" fill="#b17d52"/><circle cx="30" cy="17" r="2" fill="#76bbc3"/></>
    case 'pantry': return <><rect x="5" y="5" width="8" height="6" fill="#bd9770"/><rect x="24" y="5" width="9" height="5" fill="#a7895b"/><circle cx="11" cy="17" r="3" fill="#cf854e"/><rect x="21" y="17" width="9" height="5" fill="#927354"/></>
    case 'great_hall': return <><rect x="15" y="4" width="10" height="5" fill="#ab8b6b"/><rect x="18" y="6" width="4" height="2" fill="#f8a94e"/><rect x="17" y="13" width="6" height="12" fill="#9b3942"/><path d="M6 14h7v3H6z M27 14h7v3h-7z" fill="#aa8660"/></>
    case 'armory': return <><rect x="4" y="5" width="10" height="4" fill="#ae8b68"/><circle cx="29" cy="18" r="7" fill="none" stroke="#b38d68" strokeWidth="2"/><circle cx="29" cy="18" r="2" fill="#d6c4a6"/></>
    case 'war_room': return <><rect x="12" y="12" width="17" height="8" fill="#ae8b68"/><path d="M14 16l4-2 3 3 5-3" fill="none" stroke="#dfd29c"/><path d="M4 4h8v3H4z M29 4h7v3h-7z" fill="#a38b70"/></>
    case 'den': return <><path d="M4 5q6-5 12 0v4H4z" fill="#e6a777"/><path d="M22 9h12 M28 5v9" stroke="#c9a480" strokeWidth="2"/><ellipse cx="28" cy="21" rx="7" ry="4" fill="#94775e"/></>
    default: return null
  }
}

export default function CastleFloorPlan({ currentRoom, position }) {
  const current = HOME_DIRECTORY.find((entry) => entry.id === currentRoom) || HOME_DIRECTORY.find((entry) => entry.id === 'great_hall')
  const adjacent = new Set(Object.values(current.exits))
  const px = Math.max(0, Math.min(1, Number(position?.x ?? 160) / 320))
  const py = Math.max(0, Math.min(1, (Number(position?.y ?? 142) - 64) / 122))
  return <svg className="home-map-plan" viewBox="0 0 225 130" aria-hidden="true">
    <g className="castle-map-corridors"><path d="M30 35v15 M30 80v15 M50 65h15 M105 65h15 M140 35v15 M160 20h15" /></g>
    {HOME_DIRECTORY.map((entry) => <g key={entry.id} className={`castle-map-room ${entry.id === current.id ? 'current' : adjacent.has(entry.id) ? 'adjacent' : ''}`} transform={`translate(${entry.x} ${entry.y})`}>
      <rect className="castle-map-shadow" x="-2" y="-2" width="44" height="34" />
      <rect className="castle-map-walls" width="40" height="30" />
      <rect className={`castle-map-floor floor-${entry.id}`} x="3" y="3" width="34" height="24" />
      <Furniture id={entry.id} />
      {entry.id === current.id && <><circle className="castle-map-marker-edge" cx={5 + px * 30} cy={5 + py * 20} r="3.6"/><circle className="castle-map-marker" cx={5 + px * 30} cy={5 + py * 20} r="2.4"/></>}
    </g>)}
    <g className="castle-map-thresholds"><path d="M27 34h6 M27 50h6 M27 80h6 M27 95h6 M49 62v6 M65 62v6 M104 62v6 M120 62v6 M137 34h6 M137 50h6 M159 17v6 M175 17v6" /></g>
  </svg>
}
