# KONTEKS DISKUSI — Advanced MIDI Composition Engine

Dokumen ini adalah catatan latar belakang (rationale log) dari diskusi yang menghasilkan `PROJECT_SPEC_MIDI_Composition_Engine.md`. Tujuannya supaya AI coding agent paham **kenapa** keputusan arsitektur di spec itu diambil — bukan cuma **apa** yang harus dibangun.

Gunakan file ini sebagai referensi kalau AI agent butuh memahami reasoning di balik requirement, atau kalau user (Ryan) bertanya "kenapa dulu kita putuskan begini" saat development berjalan.

---

## 1. Titik Awal: Audio-to-MIDI (Piano Transcription)

Diskusi dimulai dari pertanyaan berbeda: apakah bisa mengisolasi suara piano dari file musik instrumental dan mengonversinya ke MIDI (dengan velocity & tempo). Jawabannya ya, lewat pipeline 2 tahap:
- **Source separation** (isolasi piano dari mix) — tools: Demucs, Spleeter.
- **Piano transcription** (audio piano bersih → MIDI) — tools: ByteDance Piano Transcription, Transkun, NeuralNote.
- Model transcription murni (audio piano bersih) sudah sangat akurat (F1-score >0.97 pada dataset MAESTRO). Titik lemah justru di tahap separation kalau piano tercampur instrumen lain.
- Model terbaru seperti **MuScriptor** (Mirelo AI + Kyutai) bisa langsung multi-instrumen tanpa separation manual, sekaligus deteksi chord/key/tempo.

*Relevansi ke project ini: berbeda arah — bagian ini adalah "audio → MIDI" (transcription), sedangkan project MIDI Composition Engine adalah "generate MIDI dari nol" (composition). Dua domain berbeda, tidak langsung dipakai di spec, tapi jadi konteks awal kenapa user familiar dengan ekosistem tools MIDI/AI musik.*

---

## 2. Transisi ke Generative MIDI

Pertanyaan berkembang: bisakah aplikasi generate MIDI sample yang unik dan menyesuaikan genre (contoh konkret: dubstep bass untuk dipakai di DAW)?

Ditemukan dua pendekatan generative MIDI yang ada di industri:
- **Model generatif musik murni** (dilatih langsung dari corpus MIDI): MIDI-GPT, Magenta (MusicVAE, dll). Sudah terintegrasi ke DAW nyata (Cubase, plugin Ableton), dipakai untuk rilis album & scoring game.
- **LLM-as-composer** (prompt teks → LLM generate data MIDI): contoh nyata "MIDI Agent" — plugin VST yang kirim prompt ke Claude/GPT/Gemini, hasilnya MIDI notes yang bisa diedit di piano roll. Mereka bahkan punya varian khusus dubstep (wobble bass, syncopated rhythm).

Poin penting yang muncul di sini: LLM generic (prediksi token linear) cenderung menghasilkan pattern yang "benar teori tapi generic", sedangkan model yang dilatih khusus corpus MIDI (MIDI-GPT, Museformer, dst) lebih baik menangkap struktur ritmis/harmonis otentik.

---

## 3. Klarifikasi Kritis: Suno vs MIDI — Dua Domain Berbeda

User awalnya minta MIDI yang "se-advance Suno". Ini butuh diklarifikasi karena **Suno bukan model MIDI** — Suno pakai arsitektur hybrid diffusion + transformer yang mensintesis **audio waveform langsung**, bukan data simbolik. "Rasa hidup" hasil Suno sebagian besar berasal dari layer sintesis audio (timbre, mikro-artikulasi suara), yang secara desain TIDAK ADA di representasi MIDI (MIDI hanya note number, velocity, timing — tidak membawa nuansa suara).

Konsekuensi penting:
- Model MIDI paling canggih sekalipun, kalau di-render pakai synth/sample biasa, tidak akan pernah semenarik audio-native model — karena elemen "hidup" itu memang bukan domain MIDI.
- Pembanding paling relevan di ranah MIDI-first adalah **AIVA** (symbolic composition, dipakai untuk scoring/orkestral), bukan Suno.
- Bahkan industri mengakui symbolic/MIDI generation punya langit-langit kualitas lebih rendah dari audio-native generation — bukan soal "belum secanggih", tapi keterbatasan representasi data (dataset MIDI berlabel jauh lebih kecil dari dataset audio training Suno).

---

## 4. Klarifikasi Final dari User — Ini yang Jadi Basis Spec

Setelah klarifikasi di atas, user mempertegas maksud sebenarnya:

> "Saya butuh file MIDI. Saya ingin tinggal mengklasifikasikan MIDI tersebut akan dipakai oleh instrumen/preset apa. Advance yang saya maksud: tidak monoton, terdengar indah — dari sisi pemilihan not, progresi, scale, dan aspek komposisi lainnya."

Ini pergeseran penting: target BUKAN "audio yang hidup seperti Suno" (domain audio synthesis, di luar scope), tapi **kualitas komposisi murni** — yang justru achievable dengan pendekatan symbolic/rule-based + selective neural enhancement, TANPA perlu menyaingi audio generation model.

Dari klarifikasi ini, disusun 5 layer arsitektur (yang jadi dasar Section 5 di file spec):

1. **Harmonic Engine** — progresi chord yang solid secara teori, bukan random. Ini + Layer 3 yang paling menentukan kesan "tidak monoton", bahkan lebih dari model AI paling canggih.
2. **Melodic/Bassline Engine** — motif development (sequence, inversion, variation), bukan pengulangan identik. Ini yang menciptakan kesan "berkembang/indah".
3. **Arrangement Engine** — struktur section (intro-build-drop-dst) dengan energy curve, supaya musik punya "bentuk", bukan loop pendek diulang.
4. **Candidate Generator + Selector** — generate beberapa variasi, scoring otomatis (voice-leading, repetition, dissonance), pilih yang terbaik — supaya kualitas konsisten, tidak tergantung hasil generate pertama yang belum tentu optimal.
5. **Humanization Engine** — micro-timing offset + velocity curve mengikuti kontur phrase, supaya tidak terasa robotic/grid-perfect.

---

## 5. Keputusan Strategis yang Perlu Diingat AI Agent Selama Development

- **Jangan mulai dari neural model besar.** Rule-based (music theory-driven) di Layer 1-3 harus solid dulu — ini murah, cepat diiterasi, dan terbukti paling berdampak ke kualitas "tidak monoton". Neural model (Museformer, MIDI-GPT, Magenta) masuk kategori Future/Experimental, hanya kalau rule-based sudah mentok secara kreatif.
- **Config-driven, bukan hardcoded.** Semua chord pool, scale rule, section template harus di file config per genre — supaya menambah genre baru tidak perlu menulis ulang engine (prinsip modularitas yang ditekankan Ryan).
- **Cost philosophy: free/OSS dulu.** `music21` untuk validasi teori musik, `mido`/`pretty_midi` untuk I/O MIDI — semua gratis. Gemini API (yang Ryan sudah punya) hanya untuk enhancement opsional, bukan dependency inti.
- **Jangan klaim "selesai" tanpa bukti.** Definition of Done di spec mensyaratkan test nyata (unit test + listening test), bukan sekadar "kode jalan tanpa error" — ini konsisten dengan preferensi Ryan soal no fake completion claims.
- **Selector/scoring pass itu sering dilewatkan tools generic** — ini pembeda penting yang bikin hasil project ini lebih konsisten bagus dibanding generator MIDI "sekali generate langsung pakai".

---

*File ini bersifat referensi historis — kalau ada keputusan baru yang mengubah arah project secara signifikan selama development, tambahkan sebagai section baru di sini, jangan edit ulang bagian yang sudah ada (supaya jejak keputusan tetap runtut).*
