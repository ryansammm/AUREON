import { describe, it, expect } from 'vitest'
import { writeMidi } from 'midi-file'
import { parseRoleNotes, groupByRole } from './LivePlayer.jsx'

function makeMidiBuffer() {
  return Buffer.from(
    writeMidi({
      header: { format: 1, numTracks: 2, ticksPerBeat: 480 },
      tracks: [
        [{ type: 'setTempo', deltaTime: 0, microsecondsPerBeat: 500000 }],
        [
          { type: 'noteOn', deltaTime: 0, noteNumber: 60, velocity: 100 },
          { type: 'noteOff', deltaTime: 480, noteNumber: 60, velocity: 0 },
          { type: 'noteOn', deltaTime: 0, noteNumber: 64, velocity: 80 },
          { type: 'noteOff', deltaTime: 240, noteNumber: 64, velocity: 0 },
        ],
      ],
    }),
  )
}

describe('parseRoleNotes', () => {
  it('reads tempo from the conductor track and skips it for notes', () => {
    const notes = parseRoleNotes(makeMidiBuffer())
    expect(notes).toHaveLength(2)
  })

  it('converts ticks to seconds at the MIDI tempo', () => {
    const notes = parseRoleNotes(makeMidiBuffer())
    // 120 BPM => 0.5 s per beat; 480 ticks = 1 beat.
    expect(notes[0].start).toBeCloseTo(0)
    expect(notes[0].dur).toBeCloseTo(0.5)
    // 240 ticks = 0.5 beat => 0.25 s, starting at beat 1.
    expect(notes[1].start).toBeCloseTo(0.5)
    expect(notes[1].dur).toBeCloseTo(0.25)
  })

  it('preserves note number and velocity', () => {
    const notes = parseRoleNotes(makeMidiBuffer())
    expect(notes[0].note).toBe(60)
    expect(notes[0].vel).toBe(100)
    expect(notes[1].note).toBe(64)
    expect(notes[1].vel).toBe(80)
  })

  it('clamps sub-80ms notes to a minimum duration', () => {
    const buffer = Buffer.from(
      writeMidi({
        header: { format: 1, numTracks: 2, ticksPerBeat: 480 },
        tracks: [
          [{ type: 'setTempo', deltaTime: 0, microsecondsPerBeat: 500000 }],
          [
            { type: 'noteOn', deltaTime: 0, noteNumber: 55, velocity: 90 },
            { type: 'noteOff', deltaTime: 1, noteNumber: 55, velocity: 0 },
          ],
        ],
      }),
    )
    const [n] = parseRoleNotes(buffer)
    expect(n.dur).toBeCloseTo(0.08)
  })

  it('returns an empty array for a track with no note events', () => {
    const buffer = Buffer.from(
      writeMidi({
        header: { format: 1, numTracks: 1, ticksPerBeat: 480 },
        tracks: [[{ type: 'setTempo', deltaTime: 0, microsecondsPerBeat: 500000 }]],
      }),
    )
    expect(parseRoleNotes(buffer)).toEqual([])
  })
})

describe('groupByRole', () => {
  const plan = [
    { role: 'bass', start: 1, note: 48, vel: 90, dur: 0.5 },
    { role: 'lead', start: 0, note: 72, vel: 70, dur: 1 },
    { role: 'bass', start: 2, note: 50, vel: 90, dur: 0.5 },
    { role: 'drum', start: 0, note: 36, vel: 100, dur: 0.1 },
  ]

  it('groups a sorted plan into per-role [start, note] pairs for Tone.Part', () => {
    const byRole = groupByRole(plan)
    expect([...byRole.keys()]).toEqual(['bass', 'lead', 'drum'])
    expect(byRole.get('bass')).toEqual([
      [1, plan[0]],
      [2, plan[2]],
    ])
    expect(byRole.get('lead')).toEqual([[0, plan[1]]])
    expect(byRole.get('drum')).toEqual([[0, plan[3]]])
  })

  it('keeps in-role order identical to the input plan order', () => {
    const byRole = groupByRole(plan)
    expect(byRole.get('bass').map(([s]) => s)).toEqual([1, 2])
  })

  it('omits roles with no events', () => {
    const byRole = groupByRole([{ role: 'pad', start: 4, note: 60, vel: 60, dur: 2 }])
    expect([...byRole.keys()]).toEqual(['pad'])
    expect(byRole.get('bass')).toBeUndefined()
  })
})
