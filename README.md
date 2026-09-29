# TAT Channel Relay Calculator

A small Python utility that computes the relay configuration needed to set a **TAT Channel** programmable resistor network to a target resistance. Given a value in ohms, it returns the closest achievable resistance, the quantization error, and the open/closed state of every relay in the network.

- **Range:** 30.000 Ω to 125.875 Ω
- **Resolution:** 0.125 Ω (768 discrete settings)
- **Relays:** 26 (R4-1, R4-2, R3-1…R3-8, R2-1…R2-8, R1-1…R1-8)

---

## Hardware Overview

![TAT Channel schematic](docs/tat_channel_schematic.png)

### Resistor network

The channel is a series chain of one fixed resistor and four relay-controlled stages, connected between **TAT_L1** (top) and **TAT_L2 / TAT_L3** (bottom).

| Stage | Elements | Relays | Contribution | Selection |
|-------|----------|--------|--------------|-----------|
| Fixed | 1 × 30 Ω | — | 30 Ω (always in circuit) | — |
| Row 4 | 1 × 32 Ω | R4-1, R4-2 | 0 or 32 Ω | Both relays in parallel across the 32 Ω. **Closed = bypass (0 Ω)**, **Open = inserted (32 Ω)** |
| Row 3 | 7 × 8 Ω in series | R3-1 … R3-8 | 0 – 56 Ω, 8 Ω steps | Tap selector: closing **R3-k** puts **(k − 1) × 8 Ω** in the path |
| Row 2 | 7 × 1 Ω in series | R2-1 … R2-8 | 0 – 7 Ω, 1 Ω steps | Tap selector: closing **R2-k** puts **(k − 1) × 1 Ω** in the path |
| Row 1 | 7 × 0.125 Ω in series | R1-1 … R1-8 | 0 – 0.875 Ω, 0.125 Ω steps | Tap selector: closing **R1-k** puts **(k − 1) × 0.125 Ω** in the path |

Total resistance:

```
R_total = 30 + R4 + R3 + R2 + R1
        = 30 + {0 | 32} + 8·a + 1·b + 0.125·c      where a, b, c ∈ {0 … 7}
```

Rows 3, 2 and 1 each have 8 positions and step ratios of 64 : 8 : 1 (in units of 0.125 Ω), so together they behave like a **3-digit octal number** covering 0 – 511 steps (0 – 63.875 Ω). Row 4 adds a 256-step (32 Ω) offset on top of that.

> In each tap-selector row (R3, R2, R1), **exactly one relay is closed** by this code. The rows are tap selectors, not independent bypass switches.

### Relay drive (ULN)

The relay coils are driven by a **ULN-series Darlington driver** stage, shown on the schematic as a **29-line bus ("ULN Drive")** entering the channel. The 26 relay coils listed above are driven from this bus; the output of this tool (`full_relay_states`) maps directly to which coils should be energized.

### Terminals and inputs

| Network node | Connected to |
|--------------|--------------|
| **TAT_L1** — top of network (after the fixed 30 Ω) | **TAT_INPUT_1** |
| **TAT_L2** — bottom of network (Row 1 end) | **TAT_INPUT_2** |
| **TAT_L3** — bottom of network (Row 1 end) | **TAT_INPUT_3** |

The programmed resistance appears between **TAT_L1** and **TAT_L2 / TAT_L3**.

---

## Installation

No external dependencies. Requires **Python 3.6+**.

```bash
git clone https://github.com/<your-username>/<repo-name>.git
cd <repo-name>
```

---

## Usage

### Run the built-in example

```bash
python tat_relay_calc.py
```

Output:

```
Target Resistance : 30.11 Ω
Actual Resistance : 30.125 Ω
Error             : 0.015 Ω

Active Relays:
  - R4-1: CLOSED (BYPASS)
  - R4-2: CLOSED (BYPASS)
  - R3-1: CLOSED
  - R2-1: CLOSED
  - R1-2: CLOSED
```

### Use as a module

```python
from tat_relay_calc import get_relay_states

result = get_relay_states(77.3)

print(result["actual_resistance_ohms"])   # 77.25
print(result["error_ohms"])               # -0.05
print(result["full_relay_states"]["R3-2"])  # CLOSED
```

### Return value

`get_relay_states(target_resistance: float) -> dict`

| Key | Type | Description |
|-----|------|-------------|
| `target_resistance_ohms` | `float` | The value you requested (unclamped) |
| `actual_resistance_ohms` | `float` | Closest achievable resistance, rounded to 3 decimals |
| `error_ohms` | `float` | `actual − target` (positive = actual is higher) |
| `active_relays` | `list[str]` | Relays that are closed, plus R4-1/R4-2 in either state (see note below) |
| `full_relay_states` | `dict[str, str]` | State of all 26 relays |

Relay state strings:

- `"CLOSED"` / `"OPEN"` — Rows 3, 2, 1
- `"CLOSED (BYPASS)"` — Row 4, 32 Ω shorted out
- `"OPEN (ACTIVE)"` — Row 4, 32 Ω in circuit

> **Note:** `active_relays` always includes R4-1 and R4-2, whether they are bypassing (closed) or inserting the 32 Ω (open). To decide which coils to energize, use `full_relay_states`.

### Algorithm

1. Clamp the target to **[30, 125.875] Ω**.
2. Subtract the fixed 30 Ω and quantize the remainder to the nearest **0.125 Ω step** (`step_count`, 0 – 767).
3. If `step_count ≥ 256`, open R4-1/R4-2 (insert 32 Ω) and subtract 256 steps; otherwise close them (bypass).
4. Split the remaining steps into octal digits:
   - Row 3 index = `steps // 64`
   - Row 2 index = `(steps % 64) // 8`
   - Row 1 index = `steps % 8`
5. Close relay **index + 1** in each row.

---

## Examples / Truth Table

| Target (Ω) | Actual (Ω) | Error (Ω) | Row 4 (R4-1/R4-2) | Row 3 | Row 2 | Row 1 |
|-----------:|-----------:|----------:|-------------------|:-----:|:-----:|:-----:|
| 10.0 *(clamped)* | 30.000 | +20.000 | Closed (bypass) | R3-1 | R2-1 | R1-1 |
| 30.0 | 30.000 | 0.000 | Closed (bypass) | R3-1 | R2-1 | R1-1 |
| 30.11 | 30.125 | +0.015 | Closed (bypass) | R3-1 | R2-1 | R1-2 |
| 45.5 | 45.500 | 0.000 | Closed (bypass) | R3-2 | R2-8 | R1-5 |
| 62.0 | 62.000 | 0.000 | Open (32 Ω in) | R3-1 | R2-1 | R1-1 |
| 77.3 | 77.250 | −0.050 | Open (32 Ω in) | R3-2 | R2-8 | R1-3 |
| 100.0 | 100.000 | 0.000 | Open (32 Ω in) | R3-5 | R2-7 | R1-1 |
| 125.875 | 125.875 | 0.000 | Open (32 Ω in) | R3-8 | R2-8 | R1-8 |
| 150.0 *(clamped)* | 125.875 | −24.125 | Open (32 Ω in) | R3-8 | R2-8 | R1-8 |

Only the relay shown is closed in each of Rows 3, 2 and 1; all others in that row are open.

---

## Limitations

- Values outside 30 – 125.875 Ω are silently clamped; check `error_ohms` to detect this.
- The calculation uses nominal resistor values. Resistor tolerance, relay contact resistance and wiring resistance are not modeled.
- Relay switching sequence (e.g. make-before-break when changing settings) is not handled here and should be managed by the driving firmware.

---

## License

This project is licensed under the **MIT License**.

```
MIT License

Copyright (c) <year> <copyright holder>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
