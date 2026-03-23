function pickToken(foodName) {
  const s = String(foodName || '').toLowerCase()

  const rules = [
    { re: /juice|smoothie|coconut water|lassi/, emoji: '🧃', a: '#fde68a', b: '#f59e0b' },
    { re: /apple/, emoji: '🍎', a: '#fecaca', b: '#ef4444' },
    { re: /banana/, emoji: '🍌', a: '#fef08a', b: '#f59e0b' },
    { re: /orange/, emoji: '🍊', a: '#fed7aa', b: '#fb923c' },
    { re: /papaya|mango|pineapple/, emoji: '🥭', a: '#fde68a', b: '#f97316' },
    { re: /berry|strawberry|blueberry/, emoji: '🫐', a: '#ddd6fe', b: '#6366f1' },
    { re: /spinach|broccoli|kale|salad|lettuce/, emoji: '🥬', a: '#bbf7d0', b: '#16a34a' },
    { re: /carrot/, emoji: '🥕', a: '#fed7aa', b: '#f97316' },
    { re: /beet/, emoji: '🫒', a: '#fecaca', b: '#be123c' },
    { re: /potato|sweet potato/, emoji: '🥔', a: '#e9d5ff', b: '#a855f7' },
    { re: /rice|oats|millet|quinoa/, emoji: '🌾', a: '#e2e8f0', b: '#94a3b8' },
    { re: /paneer|curd|yogurt|milk|cheese/, emoji: '🥛', a: '#e0f2fe', b: '#38bdf8' },
    { re: /egg/, emoji: '🥚', a: '#fef9c3', b: '#facc15' },
    { re: /chicken|fish|salmon|tuna|mutton|prawn/, emoji: '🍗', a: '#fecaca', b: '#fb7185' },
    { re: /lentil|chickpea|beans|tofu/, emoji: '🫘', a: '#d9f99d', b: '#65a30d' },
  ]

  for (const r of rules) {
    if (r.re.test(s)) return r
  }
  return { emoji: '🥗', a: '#bbf7d0', b: '#22c55e' }
}

function svgToDataUri(svg) {
  return `data:image/svg+xml;charset=utf-8,${encodeURIComponent(svg)}`
}

export function getFoodImageSrc(foodName) {
  const { emoji, a, b } = pickToken(foodName)
  const title = String(foodName || 'Food')

  const svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="240" height="160" viewBox="0 0 240 160" role="img" aria-label="${title.replace(/"/g, '')}">
  <defs>
    <linearGradient id="g" x1="0" x2="1" y1="0" y2="1">
      <stop offset="0" stop-color="${a}"/>
      <stop offset="1" stop-color="${b}"/>
    </linearGradient>
    <filter id="s" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="10" stdDeviation="12" flood-color="#0f172a" flood-opacity="0.18"/>
    </filter>
  </defs>

  <rect width="240" height="160" rx="18" fill="url(#g)"/>
  <circle cx="60" cy="50" r="42" fill="rgba(255,255,255,0.22)"/>
  <circle cx="180" cy="120" r="58" fill="rgba(255,255,255,0.18)"/>

  <g filter="url(#s)">
    <text x="120" y="98" font-size="64" text-anchor="middle" dominant-baseline="middle">${emoji}</text>
  </g>
</svg>`

  return svgToDataUri(svg)
}
