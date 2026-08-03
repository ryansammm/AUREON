export const ROLE_COLORS = {
  bass: '#7dd3fc',
  lead: '#ff7a1a',
  chord: '#a78bfa',
  pad: '#34d399',
  arp: '#f472b6',
  stab: '#fbbf24',
  sub_bass: '#22d3ee',
  counter_lead: '#fb7185',
  drum: '#e2e8f0',
  drum_layers: '#94a3b8',
}

export const roleColor = (r) => ROLE_COLORS[r] || '#fff'

export const roleLabel = (r) =>
  r.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
