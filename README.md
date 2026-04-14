# Darkroom Toolkit

A small web-based toolkit for analog film photographers, designed to run locally on a Raspberry Pi or any machine with Docker. It consists of two tools: a thermodynamic temperature mixing calculator for preparing chemicals at the correct temperature, and a development timer with audio agitation reminders.

---

## The Problem

Temperature control is critical in film development. Black-and-white developers typically require 20°C, while colour processes (C-41, E-6) demand 38°C with tolerances as tight as ±0.3°C. The traditional approach — placing chemical bottles in a water bath and waiting — is slow.

## The Idea

A chemical working solution is mixed from concentrate + water anyway. That water doesn't have to be room temperature. If you keep a bottle of distilled water in the fridge (typically ~4°C) alongside your room-temperature water (~20–22°C), you can calculate the exact volumes of each to mix so the final solution lands precisely at your target temperature. No waiting, no thermostatic inertia.

The calculation is a simple heat balance equation. Since all components are water-based and share approximately the same specific heat capacity, it cancels out and the problem reduces to a weighted average of temperatures by volume.

**For colour processes**, the same principle applies in reverse: pre-warm water to ~45°C, then blend it with cold water to hit 38°C precisely. A brief equilibration in a sous-vide bath can correct for any residual error from the concentrate's slightly different specific heat — but the blending step dramatically reduces the time spent waiting.

## The Equation

```
m_cold · T_cold + m_warm · T_warm + m_chem · T_chem = m_total · T_target

m_cold + m_warm + m_chem = m_total
```

Where `m` is volume in ml and `T` is temperature in °C. The chemical volume is fixed by the dilution ratio (e.g. 1+9 means 1 part concentrate to 9 parts water, so 30 ml chemical in 300 ml total). Solving for `m_cold` gives:

```
m_cold = (m_total · T_target − m_chem · T_chem − m_water · T_warm) / (T_cold − T_warm)
m_warm = m_water − m_cold
```

---

## Features

**Chemical Mixer**
- **Interactive CLI** — run without arguments, enter values one by one
- **Non-interactive CLI** — pass all arguments as flags, scriptable
- **Web interface** — minimal dark-themed UI served locally, works in any browser
- **Input validation** — catches impossible temperature targets and warns about negative volumes
- **Verification** — always reports the actual calculated mixture temperature as a sanity check

**Development Timer**
- **Countdown** with configurable minutes and seconds
- **Three distinct audio signals** synthesised entirely in the browser via Web Audio API — no server connection required
- **Overdevelopment tracking** — at 0:00 the timer continues upward with a negative sign, so you always know how far over you are
- **Event log** — timestamped record of every signal fired during the session
- **Docker support** — runs on Raspberry Pi or any ARM/x86 machine

---

## Installation

### Plain Python

Requires Python 3.10+ and Flask (only needed for the web interface).

```bash
pip install flask
```

### Docker

```bash
docker compose up -d
```

The web interface will be available at `http://localhost:5000`.

For Raspberry Pi, the standard `python:3.12-slim` image supports ARM64 out of the box.

---

## Usage

### Interactive mode

Run without arguments and the calculator will prompt for each value:

```
$ python app.py

╔══════════════════════════════════════╗
║   Darkroom Chemical Mixer Calculator ║
╚══════════════════════════════════════╝

  Cold water temperature [°C]: 4
  Warm water temperature [°C]: 22
  Chemical concentrate temperature [°C]: 22
  Target temperature [°C]: 20
  Dilution ratio (e.g. 1+9, 1+14): 1+9
  Desired total volume [ml]: 300

════════════════════════════════════════
  RESULT
════════════════════════════════════════
  Cold water:        33.3 ml
  Warm water:       236.7 ml
  Chemical:          30.0 ml
  ────────────────────────────────────
  Total:            300.0 ml
  Mix temp:         20.00 °C  (target: 20°C)
════════════════════════════════════════
```

### Non-interactive mode

All inputs as flags — useful for scripting or keyboard shortcuts:

```bash
python app.py --cold 4 --warm 22 --chem 22 --target 20 --ratio 1+9 --volume 300
```

Short flags:

```bash
python app.py -c 4 -w 22 -k 22 -t 20 -r 1+9 -v 300
```

| Flag | Short | Description |
|---|---|---|
| `--cold` | `-c` | Cold water temperature (°C) |
| `--warm` | `-w` | Warm water temperature (°C) |
| `--chem` | `-k` | Chemical concentrate temperature (°C) |
| `--target` | `-t` | Desired final temperature (°C) |
| `--ratio` | `-r` | Dilution ratio, e.g. `1+9` or `1:9` |
| `--volume` | `-v` | Desired total volume (ml) |

### Web interface

Start the server:

```bash
python server.py
```

Then open `http://localhost:5000` in a browser. On a Raspberry Pi on your local network, access it from any device at `http://<pi-ip>:5000`.

The mixer and timer are linked — a button at the bottom of each page navigates between them.

---

## Development Timer

The timer is available at `/timer.html` and runs entirely client-side — the audio engine uses the Web Audio API and requires no server connection after the page loads.

### Signals

| Signal | When | Purpose |
|---|---|---|
| Beep 1 (double pip, 880 Hz) | At 0:30, then every 60 s | Agitation reminder |
| Beep 2 (descending, 660→550 Hz) | At 10 s remaining; every 60 s if overdeveloping | Pour-off warning |
| Beep 3 (triple tone, descending) | At 0:00 | End of development |

### Agitation logic

The first 30 seconds of development require continuous agitation. At the 0:30 mark, Beep 1 fires and the log reads "Stop agitation — let tank rest". After that, Beep 1 fires every 60 seconds as a prompt to agitate again for approximately 10 seconds.

### Overdevelopment

When the timer reaches 0:00, Beep 3 fires and the display turns red and continues counting upward with a negative sign (e.g. -0:05, -0:10...). Beep 2 fires every 60 seconds as a reminder. Press Stop to end the session.

---

## Practical examples

**Black-and-white developer at 20°C** (e.g. Kodak HC-110, dilution B = 1+31)

```bash
python app.py -c 4 -w 22 -k 22 -t 20 -r 1+31 -v 300
```

**Colour developer at 38°C** (C-41, dilution 1+4, pre-warmed water at 45°C)

```bash
python app.py -c 4 -w 45 -k 22 -t 38 -r 1+4 -v 500
```

**Hybrid method for colour processes:** blend to approximately 38°C using this calculator, then place the beaker in a sous-vide bath set to exactly 38°C for a minute or two. The calculator eliminates the bulk of the warming time; the sous-vide corrects for the concentrate's slightly different specific heat capacity and any measurement imprecision.

---

## Limitations

The calculation assumes all components have the same specific heat capacity as water (4.18 J/g·K). Chemical concentrates deviate slightly from this, which introduces a small error — typically less than 0.5°C in normal dilutions. For black-and-white work this is negligible. For colour processes using the hybrid method described above, the sous-vide step corrects for it automatically.

---

## File structure

```
.
├── app.py            # Calculator logic + CLI + Flask API
├── server.py         # Web server entry point
├── static/
│   ├── index.html    # Chemical mixer web UI
│   └── timer.html    # Development timer web UI
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## License

MIT
