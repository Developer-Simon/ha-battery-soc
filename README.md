# Battery SoC (LiFePO4 coulomb-counting)

A Home Assistant custom integration that estimates the **state of charge** of
one or two LiFePO4 battery banks from sensors you already have. It does not talk
to a BMS and needs no extra hardware — you point it at a charge-power sensor, a
discharge-power sensor and one voltage sensor per bank.

> **This is a monitoring/diagnostic estimate, not a safety-critical BMS
> function.** Do not use it for automatic shutdowns without independent
> protection (cell-level monitoring in the charger/BMS itself). Mirrors the
> disclaimer in the upstream MQTT service.

## How it works

1. **Coulomb counting (base SoC).** Net battery power — charger power minus
   inverter power, AC or DC — is integrated over time (Ah). This is the primary
   SoC source. It is accurate short-term but drifts slowly (measurement error,
   efficiency, self-discharge).
2. **Voltage recalibration at the ends.** A LiFePO4 cell's voltage curve is
   almost flat between roughly 15–85 % SoC, so mid-range voltage is useless for
   SoC. Only near empty and near full does voltage move measurably. There the
   coulomb counter is snapped back to 0 % / 100 % once the load-corrected
   voltage crosses a threshold and the current is low enough for the reading to
   pass as a resting voltage.
3. **Load compensation.** Instead of a family of voltage curves per load
   current, the measured voltage is corrected by a current-dependent offset
   (mΩ/cell) before it is compared with the resting-voltage curve.
4. **Topology-aware.** *Parallel / single bank* → one SoC (Kirchhoff forces a
   shared voltage; a per-bank split would be fictitious). *Series* → a per-bank
   SoC plus a combined "weakest bank" figure.

## Install (HACS custom repository)

1. HACS → ⋮ (top right) → **Custom repositories**.
2. Repository: `https://github.com/OWNER/ha-battery-soc` — Category:
   **Integration**. Add.
3. HACS → search **Battery SoC** → **Download**.
4. **Restart Home Assistant.**

## Configure

**Settings → Devices & Services → Add Integration → “Battery SoC (LiFePO4
coulomb-counting)”.**

- **Battery Configuration** (`user` step): name, topology (parallel/series),
  the charger and inverter power sensors (AC and/or DC), a voltage sensor per
  bank with an optional scale factor, per-bank capacity (Ah) and cell count,
  whether Bank B is enabled, chemistry and SoC curve profile.
- **Advanced Battery Parameters** (`advanced` step): empty/full volts per cell,
  charger/inverter/charge efficiencies, calibration tolerance and hold time,
  voltage/coulomb mismatch warning thresholds, imbalance threshold, stale-input
  and DC-age timeouts, internal resistance (mΩ/cell), fallback interval.

All of these are editable afterwards via the integration's **Configure** dialog
(Power & Voltage Sources / Tunable Battery Parameters).

## Entities

One device per configured battery. Highlights:

| Entity | Meaning |
|---|---|
| `sensor` **SoC** (`soc_combined`) | Primary state of charge (%). In series: the weakest bank. |
| `sensor` **Net battery power** (`net_power`) | Charge (+) / discharge (−) power (W). |
| `sensor` **Time to full / Time to empty** | Projection at the current rate (h, diagnostic). |
| `binary_sensor` **Inputs stale** | A source sensor stopped updating. |
| `binary_sensor` **AC fallback active** | Running on AC power sensors because DC is unavailable. |
| `sensor` **Voltage / Current / Remaining Ah / Load-corrected cell voltage** | Per unit (pack / bank A / bank B), diagnostic. |
| `sensor` **Calibration thresholds / Last calibration** | When and at what voltage the counter was last snapped. |
| `sensor` **Voltage-based SoC (uncertain)** + `binary_sensor` **Voltage/coulomb mismatch** | Sanity cross-check against the coulomb count. |
| series only: `sensor` **SoC Bank A/B**, **Voltage delta A/B**, `binary_sensor` **Banks imbalanced** | |
| `number` **Set manual SoC** (per bank in series) | Write a known SoC to anchor the counter. |

The full descriptor list lives in
[`battery_soc_core/entities.py`](custom_components/battery_soc/battery_soc_core/entities.py).

## Action: `battery_soc.set_state_of_charge`

Anchor the coulomb counter to a known value — e.g. right after a full charge, or
from a shunt-based reference.

```yaml
action: battery_soc.set_state_of_charge
target:
  device_id: <your battery device>
data:
  state_of_charge: 100     # percent, 0–100
  # bank: a                # series topology only: which bank to anchor
```

The **SoC** sensor jumps to the value immediately. The `number` entities do the
same thing from the UI.

## License

MIT — see [LICENSE](LICENSE).
