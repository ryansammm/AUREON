# PROJECT SPECIFICATION
## Advanced MIDI Composition Engine — "Not Sekadar Generator, Tapi Music Brain"

---

## 0. CARA MEMBACA DOKUMEN INI (untuk AI Coding Agent)

Dokumen ini adalah **single source of truth** untuk seluruh scope project. Kalau kamu (AI agent) mengerjakan bagian mana pun dari project ini:

1. Baca **Section 1 (Product Vision)** dulu — jangan mulai coding sebelum paham *kenapa* project ini ada dan apa yang membedakannya dari generator MIDI biasa.
2. Ikuti urutan **Roadmap (Section 9)** — jangan lompat ke Layer 4/5 sebelum Layer 1-3 solid, karena kualitas layer atas bergantung pada fondasi di bawahnya.
3. Setiap modul punya **Definition of Done** eksplisit (Section 10) — jangan klaim "selesai/tested/verified" kalau kriteria di situ belum terpenuhi secara nyata (jalankan test-nya, jangan asumsi).
4. Semua tool/library WAJIB dari daftar **Free/Open-Source Stack (Section 4)** kecuali ada justifikasi tertulis kenapa perlu exception — cost philosophy project ini adalah local-first, gratis semaksimal mungkin.
5. Kalau ada ambiguitas requirement, JANGAN asumsi diam-diam — tanyakan balik ke user dengan opsi konkret, atau tulis assumption secara eksplisit di code comment/commit message.
6. Arsitektur harus modular — setiap layer adalah modul independen yang bisa ditest sendiri (unit test), tidak boleh saling hardcode/tight-coupled.

---

## 1. PRODUCT VISION

### 1.1 Problem Statement
Generator MIDI yang ada di pasaran (LLM-prompt-to-MIDI seperti "MIDI Agent", atau template-based generator) menghasilkan pattern yang **secara teori benar tapi terasa generic/monoton** — karena mereka pada dasarnya memprediksi token linear tanpa struktur musikal jangka panjang (arc, development, arrangement).

Di sisi lain, model audio generatif (Suno dkk) menghasilkan musik yang terasa "hidup dan indah", tapi **bukan MIDI** — outputnya waveform, tidak bisa diedit note-per-note di DAW.

### 1.2 Product Goal
Membangun **composition engine** yang menghasilkan file MIDI dengan kualitas struktural setara komposer manusia berpengalaman menengah: progresi harmoni yang mengalir, melodi yang berkembang (bukan diulang identik), arrangement yang punya bentuk (intro-build-climax-resolve), dan velocity/timing yang terasa "dimainkan" bukan "diprogram".

### 1.3 Non-Goals (Penting — supaya scope tidak melebar)
- **BUKAN** audio synthesis engine — tidak menghasilkan suara, hanya data MIDI (note, velocity, timing, CC).
- **BUKAN** vocal/lyric generator.
- **BUKAN** real-time performance tool (live coding) — fokus pada generate-then-export workflow.
- **BUKAN** replika Suno — jangan buang waktu riset ke arah audio diffusion model.

### 1.4 Target Output
User memilih genre (misal "dubstep") + role instrumen (misal "bass") → sistem generate file `.mid` yang:
- Punya progresi chord yang secara teori solid dan sesuai karakter genre.
- Melodi/bassline berkembang lewat teknik motif development (sequence, variation), bukan loop identik.
- Punya arrangement bertahap (section dengan energy curve berbeda).
- Velocity & micro-timing sudah humanized.
- Bisa langsung di-drag ke instrument/preset apa pun di DAW.

---

## 2. FUNCTIONAL REQUIREMENTS

### FR-1 — Genre & Role Input
- User input: genre (dubstep, house, trap, dnb, dst — extensible), role (bass, lead, pad, drum, chord).
- Parameter opsional: key, BPM, panjang (jumlah bar), tingkat kompleksitas (simple/medium/complex).

### FR-2 — Harmonic Generation
- Sistem generate chord progression yang valid secara teori musik, sesuai karakter genre (lihat Section 5.1).
- Mendukung modulasi/scale change antar section.

### FR-3 — Melodic/Bassline Generation
- Sistem generate garis melodi/bass yang terikat pada chord progression (chord-tone awareness), dengan motif development.
- Tidak boleh ada not di luar scale yang ditentukan (kecuali passing tone yang disengaja & valid secara teori).

### FR-4 — Arrangement Structure
- Sistem generate struktur section (intro, build, drop/chorus, breakdown, outro) sesuai template genre.
- Setiap section punya energy/density profile berbeda (tidak flat).

### FR-5 — Multi-Candidate Generation + Selection
- Sistem generate N kandidat per section, score otomatis (voice-leading smoothness, repetition ratio, dissonance rate), pilih terbaik atau tampilkan top-3 ke user.

### FR-6 — Humanization Layer
- Micro-timing offset per note (bukan grid perfect).
- Velocity curve mengikuti kontur melodi (bukan random flat).

### FR-7 — MIDI Export
- Output standard `.mid` file (Type 1, multi-track), readable oleh semua DAW mayor (Ableton, FL Studio, Logic, Cubase).
- Metadata tempo, time signature, key signature ter-embed dengan benar.

### FR-8 — Preset/Instrument Tagging (sesuai request awal user)
- User bisa mengklasifikasikan track MIDI dengan label instrument-intent (misal "bass — wobble style", "lead — pluck") sebagai metadata/track name, supaya user tinggal assign ke VST/preset di DAW-nya sendiri.
- **PENTING**: sistem TIDAK render audio atau memilih VST — hanya memberi label/metadata track supaya user tahu instrumen apa yang cocok.

---

## 3. NON-FUNCTIONAL REQUIREMENTS

| Kategori | Requirement |
|---|---|
| Cost | Seluruh pipeline harus bisa berjalan tanpa biaya berulang (no mandatory paid API). Free tier AI (Gemini) boleh dipakai sebagai *opsional enhancement*, bukan dependency inti. |
| Offline capability | Core generation (Layer 1-3, rule-based) harus bisa jalan 100% offline/local. Layer neural (kalau dipakai) juga local-hosted, bukan API berbayar wajib. |
| Modularity | Setiap layer (harmony, melody, arrangement, selector, humanizer) adalah modul terpisah dengan interface jelas — bisa diganti/upgrade tanpa merusak modul lain. |
| Extensibility | Menambah genre baru = menambah config/template baru, TIDAK menulis ulang engine. |
| Performance | Generate 1 track (4-8 bar, semua layer) target < 10 detik di hardware biasa (non-GPU) untuk mode rule-based; neural mode boleh lebih lambat tapi harus async/non-blocking di UI. |
| Testability | Setiap modul punya unit test yang memverifikasi output valid secara teori musik (misal: semua not dalam scale, tidak ada overlap timing ilegal). |
| Maintainability | Tidak ada hardcoded value musikal (misal daftar chord) di dalam logic — semua di config/data file yang bisa diedit tanpa sentuh kode. |

---

## 4. TECH STACK (Free / Open-Source First)

| Kebutuhan | Pilihan Utama (Free/OSS) | Alasan |
|---|---|---|
| Bahasa inti | Python 3.11+ | Ekosistem music theory & MIDI library paling matang |
| Music theory & validasi | `music21` (MIT license) | Validasi chord, scale, voice-leading — gratis, sudah battle-tested akademik |
| MIDI read/write | `mido` atau `pretty_midi` | Baca/tulis file MIDI standard, ringan |
| Rule-based generation (Layer 1-3) | Custom logic Python + `music21` | Kontrol penuh, tidak butuh training data/compute |
| Neural backbone (opsional, Layer 2 advanced) | Self-host model open source seperti **Magenta** (MusicVAE, Melody RNN) — jalan di CPU untuk model kecil | Gratis, tidak butuh API key |
| AI enhancement (opsional) | Gemini API (free tier, sesuai yang kamu punya) — dipakai HANYA untuk hal seperti: generate deskripsi/label genre character, atau bantu tuning parameter, BUKAN untuk generate not secara langsung | Sesuai preferensi: AI dipakai di mana reasoning/semantic understanding beneran dibutuhkan, bukan trivial |
| Storage config genre | JSON/YAML files (chord pool, scale rules, section templates per genre) | Editable tanpa recompile, versionable di git |
| UI (kalau dibutuhkan, opsional Phase lanjutan) | CLI dulu (Phase 1-2), lalu simple local web UI (Flask/FastAPI + HTML, semua local) | Tidak perlu hosting berbayar |
| Testing | `pytest` | Standard, gratis |
| Version control | Git (local / GitHub free tier) | — |

**Prinsip cost:** tidak ada satu pun komponen WAJIB berbayar. Kalau ke depan mau eksplor neural model besar (Museformer, MIDI-GPT full training), itu masuk kategori **Future/Experimental** (Section 9) dan butuh keputusan sadar soal compute cost — bukan default path.

---

## 5. SYSTEM ARCHITECTURE

```
[User Input: genre, role, key, bpm, length, complexity]
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 0 — Genre Config Loader               │
│  (load chord pool, scale rules, section       │
│   template, rhythm density profile dari       │
│   genre config file)                          │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 1 — Harmonic Engine                    │
│  Generate chord progression per section       │
│  (validasi via music21: voice-leading,        │
│   scale consistency)                           │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 2 — Melodic/Bassline Engine            │
│  Generate motif → develop (sequence,          │
│  inversion, variation) → chord-tone lock      │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 3 — Arrangement Engine                 │
│  Susun section (intro/build/drop/...),        │
│  atur energy/density curve per section        │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 4 — Candidate Generator + Selector     │
│  Generate N variasi per section, scoring      │
│  otomatis, pilih/tampilkan terbaik            │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 5 — Humanization Engine                │
│  Micro-timing offset + velocity curve         │
│  mengikuti phrase contour                     │
└─────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────┐
│  Layer 6 — MIDI Export                        │
│  Tulis .mid file, track naming/labeling       │
│  sesuai instrument-intent (FR-8)              │
└─────────────────────────────────────────────┘
        │
        ▼
   [Output: file.mid, siap dipakai di DAW]
```

### 5.1 Detail Layer 1 — Harmonic Engine
- **Data source**: config per genre berisi *chord pool* (progression umum genre itu) dan *transition rule* (probabilitas chord A → chord B, berbasis teori: ii-V-I, modal interchange, dst — bisa mulai dari Markov chain berbobot manual, bukan random uniform).
- **Validasi**: pakai `music21` untuk cek voice-leading (jarak antar not tidak lompat besar tanpa alasan) dan scale-consistency.
- **Output**: list of chord objects per bar, dengan metadata section (intro/verse/dst).

### 5.2 Detail Layer 2 — Melodic/Bassline Engine
- **Step 1**: generate 1 motif pendek (1-2 bar) sesuai chord pertama.
- **Step 2**: development techniques — sequence (transposisi motif ke chord berikutnya), inversion, augmentation/diminution, retrograde (opsional, tergantung genre).
- **Constraint**: setiap not harus valid terhadap chord/scale aktif saat itu (chord-tone atau passing-tone yang sah).
- **Genre-specific rhythm profile**: dubstep butuh syncopation & triplet/dotted-16th pattern; ini disimpan di genre config, bukan hardcode di logic.

### 5.3 Detail Layer 3 — Arrangement Engine
- **Section template** per genre (contoh dubstep: Intro → Buildup → Drop → Breakdown → Drop 2 → Outro), disimpan di config.
- **Energy curve**: tiap section punya parameter density (jumlah not per bar) dan register (rentang oktaf) yang berbeda — buildup naik gradual, drop paling padat/rendah (sub bass), breakdown minimalis.

### 5.4 Detail Layer 4 — Candidate Generator + Selector
- Generate N (misal 5) variasi untuk section yang sama.
- Scoring heuristic (semua bisa dihitung langsung tanpa ML, murni music theory):
  - Dissonance rate (rasio interval tidak konsonan berlebihan)
  - Repetition ratio (terlalu identik antar bar = skor turun)
  - Voice-leading smoothness (rata-rata jarak interval antar not berurutan)
- Pilih skor tertinggi, atau expose top-3 ke user untuk pilih manual (lebih baik untuk kontrol kreatif).

### 5.5 Detail Layer 5 — Humanization Engine
- Micro-timing: tambahkan offset kecil (misal ±10-25ms, random tapi terkontrol/tidak seragam) ke setiap note-on, KECUALI down-beat pertama tiap bar (biar tetap "nge-lock" ke grid).
- Velocity: base velocity dari posisi dalam phrase (naik mendekati climax section, turun di resolusi) + jitter kecil per note supaya tidak identik persis.

### 5.6 Detail Layer 6 — MIDI Export
- Multi-track MIDI: track terpisah per role (bass, lead, chord, drum jika ada).
- Track name = label instrument-intent (FR-8), contoh: `"Bass - Wobble Style (Dubstep)"`.
- Tempo & time signature meta event di track 1.

---

## 6. DATA MODEL

### 6.1 Genre Config Schema (JSON, per genre — extensible)
```json
{
  "genre": "dubstep",
  "default_bpm": 140,
  "scale_pool": ["natural_minor", "phrygian"],
  "chord_pool": [
    {"degree": "i", "weight": 1.0},
    {"degree": "vi", "weight": 0.7},
    {"degree": "iv", "weight": 0.6},
    {"degree": "v", "weight": 0.5}
  ],
  "transition_matrix": {
    "i": {"vi": 0.4, "iv": 0.3, "v": 0.3},
    "vi": {"iv": 0.5, "v": 0.5}
  },
  "section_template": ["intro", "buildup", "drop", "breakdown", "drop2", "outro"],
  "section_density": {
    "intro": 0.3,
    "buildup": 0.6,
    "drop": 1.0,
    "breakdown": 0.2,
    "outro": 0.3
  },
  "rhythm_profile": {
    "bass": ["syncopated_16th", "triplet_wobble"],
    "lead": ["straight_8th", "off_beat_accent"]
  }
}
```

### 6.2 Internal Note Representation
```python
{
  "pitch": 45,          # MIDI note number
  "start_beat": 2.5,     # posisi dalam bar (beat unit)
  "duration_beat": 0.5,
  "velocity": 92,
  "section": "drop",
  "role": "bass"
}
```

### 6.3 Output Track Metadata
```python
{
  "track_name": "Bass - Wobble Style (Dubstep)",
  "role": "bass",
  "suggested_preset_type": "sub_bass / wobble_synth",
  "notes": [ ... list of note objects ... ]
}
```

---

## 7. ERROR HANDLING

| Skenario | Handling |
|---|---|
| Genre config tidak ditemukan/invalid | Fallback ke genre "generic" + warning eksplisit ke user, JANGAN silent fail |
| Chord progression menghasilkan voice-leading invalid setelah N retry | Log warning, pakai kandidat terbaik yang ada (bukan crash), tandai di metadata sebagai "low confidence" |
| Melodic generation menghasilkan not di luar range instrumen (misal bass terlalu tinggi) | Clamp ke range valid per role (config-driven), jangan biarkan lolos ke export |
| File MIDI gagal ditulis (permission/disk) | Exception jelas dengan pesan actionable, jangan generic "error occurred" |
| Parameter user invalid (misal BPM negatif, panjang bar 0) | Validasi di input layer sebelum masuk pipeline, reject dengan pesan spesifik |

---

## 8. TESTING STRATEGY

- **Unit test per layer** (pytest): setiap layer harus bisa ditest terisolasi dengan input dummy.
  - Layer 1: cek semua chord yang dihasilkan valid dalam scale yang ditentukan.
  - Layer 2: cek semua not adalah chord-tone atau passing-tone sah, tidak ada not di luar scale tanpa alasan.
  - Layer 5: cek tidak ada velocity di luar range 1-127, tidak ada note timing negatif.
- **Integration test**: generate full track end-to-end, verifikasi file `.mid` valid (bisa dibuka ulang via `mido`/`pretty_midi` tanpa error, struktur track sesuai jumlah role yang diminta).
- **Regression test**: simpan beberapa output "baseline" yang sudah divalidasi manual (didengarkan/dicek teori), pastikan perubahan kode tidak merusak kualitas itu (bisa via snapshot testing pada representasi note, bukan audio).
- **Manual listening test** (tidak bisa diotomasi penuh): render sample output ke synth sederhana secara periodik untuk validasi subjektif "enak didengar" — ini tetap perlu meski sudah ada automated test, karena automated test hanya menjamin *valid secara teori*, bukan *enak didengar*.

---

## 9. ROADMAP (Fase Pengembangan)

### Phase 1 — MVP Rule-Based Core (Must)
- Layer 0, 1, 2 (versi sederhana: motif + 1 development technique), 6 (export).
- Satu genre config lengkap (dubstep) sebagai proof of concept.
- CLI interface sederhana.
- **Target**: bisa generate bassline dubstep 8 bar, chord progression valid, export .mid yang bisa dibuka di DAW.

### Phase 2 — Arrangement & Structure (Must)
- Layer 3 (section template + energy curve).
- Tambah genre kedua untuk validasi extensibility config-driven.

### Phase 3 — Quality & Humanization (Should)
- Layer 5 (humanization: timing + velocity).
- Layer 4 (multi-candidate + scoring, minimal 3 heuristic).

### Phase 4 — Multi-Role & Interaction (Should)
- Generate multi-track sekaligus (bass + lead + chord) dengan awareness antar track (tidak rhythm-clash).
- Web UI lokal sederhana (opsional, kalau CLI dirasa kurang nyaman).

### Phase 5 — Neural Enhancement (Could/Future)
- Eksplor self-hosted neural model (Magenta MelodyRNN, atau fine-tune kecil) sebagai *alternatif* Layer 2, dibandingkan head-to-head dengan rule-based.
- Hanya lanjut ke sini kalau Phase 1-4 sudah solid dan rule-based dirasa mentok secara kreatif.

### Phase 6 — Scoring Model Upgrade (Future/Experimental)
- Ganti scoring heuristic Layer 4 dengan model ML terlatih (kalau data cukup) — eksplisit optional, tidak prasyarat kelayakan produk.

---

## 10. DEFINITION OF DONE (per Phase)

- **Phase 1 DONE** kalau: unit test Layer 1 & 2 lulus, file `.mid` hasil generate terbuka valid di minimal 1 DAW nyata (bukan cuma parser Python), dan output telah didengarkan manual minimal 3x iterasi berbeda parameter tanpa ada not yang jelas "salah" secara teori.
- **Phase 2 DONE** kalau: 2 genre config berbeda berjalan lewat pipeline yang SAMA tanpa perubahan kode inti (hanya config berbeda) — ini bukti modularitas tercapai.
- **Phase 3 DONE** kalau: A/B listening test (dengan/tanpa humanization) menunjukkan perbedaan yang jelas terasa "lebih hidup", dan scoring heuristic terbukti konsisten memilih kandidat yang secara teori lebih baik (bukan random).
- Klaim "done" TIDAK BOLEH dibuat hanya karena kode "jalan tanpa error" — harus disertai bukti test yang relevan sesuai kriteria di atas.

---

## 11. SECURITY & DEPLOYMENT

- Karena ini tool local-first tanpa data sensitif user (tidak ada PII, tidak ada payment), risiko security minimal. Tetap terapkan:
  - Validasi input ketat (hindari path traversal kalau ada fitur load/save file custom).
  - Kalau nanti ada web UI lokal, jangan expose ke network publik tanpa auth minimal.
- **Deployment**: local Python environment (virtualenv), tidak butuh server/cloud. Kalau mau distribusi ke user lain, bisa packaging jadi executable (`pyinstaller`) — opsional, bukan prioritas awal.

---

## 12. INSTRUKSI UNTUK AI CODING AGENT (Ringkasan Kerja)

1. Mulai dari **Phase 1** saja. Jangan bangun Layer 4/5 sebelum Layer 1/2 lulus test.
2. Struktur folder yang disarankan:
   ```
   /config/genres/dubstep.json
   /engine/harmony.py
   /engine/melody.py
   /engine/arrangement.py
   /engine/selector.py
   /engine/humanizer.py
   /engine/exporter.py
   /tests/
   /cli.py
   ```
3. Setiap modul harus punya docstring yang jelas menyebutkan: input, output, dan asumsi musikal yang dipakai (misal "assumes 4/4 time signature" kalau memang masih dibatasi begitu di awal).
4. Semua chord pool, scale rule, section template WAJIB di config file, TIDAK di hardcode dalam logic Python.
5. Setiap fitur baru wajib disertai unit test sebelum dianggap selesai.
6. Kalau ragu soal keputusan musikal (misal: "apakah dubstep butuh secondary dominant?"), tulis sebagai TODO/assumption di kode dan laporkan ke user, jangan menebak diam-diam untuk hal yang berdampak besar ke kualitas output.

---

*Dokumen ini adalah living document — update sesuai keputusan yang diambil selama development, terutama Section 6 (Data Model) dan Section 9 (Roadmap) begitu Phase 1 mulai memberi feedback nyata.*
