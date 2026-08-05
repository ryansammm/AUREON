import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import PianoRoll, { buildPitchIndex, findNote } from './PianoRoll.jsx'

const tracks = [
  { role: 'bass', midi: [[48, 0, 1], [48, 2, 0.5], [50, 3, 1]] },
  { role: 'lead', midi: [[72, 0, 4], [74, 1, 0.5], [72, 3, 0.5]] },
]

describe('buildPitchIndex', () => {
  it('flattens tracks into notes in order', () => {
    const idx = buildPitchIndex(tracks)
    expect(idx.notes).toHaveLength(6)
    expect(idx.notes[0]).toEqual({ role: 'bass', pitch: 48, start: 0, dur: 1 })
    expect(idx.notes[4]).toEqual({ role: 'lead', pitch: 74, start: 1, dur: 0.5 })
  })

  it('groups notes by pitch and sorts each group by start', () => {
    const idx = buildPitchIndex(tracks)
    const p48 = idx.byPitch.get(48)
    expect(p48.map((n) => n.start)).toEqual([0, 2])
    const p72 = idx.byPitch.get(72)
    expect(p72.map((n) => n.start)).toEqual([0, 3])
    expect(idx.byPitch.get(99)).toBeUndefined()
  })

  it('tracks the max duration seen per pitch', () => {
    const idx = buildPitchIndex(tracks)
    expect(idx.maxDurByPitch.get(48)).toBe(1)
    expect(idx.maxDurByPitch.get(72)).toBe(4)
  })

  it('pads the visible pitch range by 2 semitones', () => {
    const idx = buildPitchIndex(tracks)
    expect(idx.minPitch).toBe(46)
    expect(idx.maxPitch).toBe(76)
  })

  it('handles empty / missing tracks', () => {
    const empty = buildPitchIndex([])
    expect(empty.notes).toEqual([])
    expect(empty.byPitch.size).toBe(0)
    const undef = buildPitchIndex(undefined)
    expect(undef.notes).toEqual([])
  })
})

describe('findNote (binary search)', () => {
  const idx = buildPitchIndex(tracks)

  it('finds a note exactly at its start beat', () => {
    const n = findNote(idx.byPitch, idx.maxDurByPitch, 0, 48)
    expect(n).toMatchObject({ pitch: 48, start: 0, dur: 1 })
  })

  it('finds a long note when the cursor is inside its duration', () => {
    const solo = buildPitchIndex([{ role: 'lead', midi: [[72, 0, 4]] }])
    const n = findNote(solo.byPitch, solo.maxDurByPitch, 3.5, 72)
    expect(n).toMatchObject({ pitch: 72, start: 0, dur: 4 })
  })

  it('returns null when no note covers the beat', () => {
    expect(findNote(idx.byPitch, idx.maxDurByPitch, 1.5, 48)).toBeNull()
  })

  it('returns null for a pitch with no notes', () => {
    expect(findNote(idx.byPitch, idx.maxDurByPitch, 0, 99)).toBeNull()
  })

  it('returns null when the beat is before the earliest note', () => {
    expect(findNote(idx.byPitch, idx.maxDurByPitch, 5, 74)).toBeNull()
  })

  it('back-scans over overlapping notes and returns the covering one', () => {
    const idx2 = buildPitchIndex([{ role: 'bass', midi: [[48, 0, 2], [48, 0.5, 0.5]] }])
    const n = findNote(idx2.byPitch, idx2.maxDurByPitch, 1.5, 48)
    expect(n).toMatchObject({ start: 0, dur: 2 })
    const short = findNote(idx2.byPitch, idx2.maxDurByPitch, 0.75, 48)
    expect(short).toMatchObject({ start: 0.5, dur: 0.5 })
  })

  it('handles a single-note pitch', () => {
    const n = findNote(idx.byPitch, idx.maxDurByPitch, 3, 50)
    expect(n).toMatchObject({ pitch: 50, start: 3, dur: 1 })
  })
})

describe('PianoRoll component', () => {
  it('renders the header, hint and a canvas', () => {
    render(<PianoRoll tracks={tracks} bpm={120} totalBeats={16} />)
    expect(screen.getByText('Piano roll')).toBeInTheDocument()
    expect(screen.getByText(/drag to pan · scroll to zoom/)).toBeInTheDocument()
    expect(document.querySelector('canvas')).toBeInTheDocument()
  })

  it('shows a tooltip when hovering over a note', async () => {
    const { container } = render(<PianoRoll tracks={tracks} bpm={120} totalBeats={16} />)
    const wrap = container.querySelector('.cursor-grab')
    const idx = buildPitchIndex(tracks)
    // Aim at pitch 48 on beat 0: y = ruler(34) + (maxPitch - 48) rows.
    fireEvent.mouseMove(wrap, {
      clientX: 0,
      clientY: 34 + (idx.maxPitch - 48) * 10,
    })
    expect(await screen.findByText('C3')).toBeInTheDocument()
  })
})
