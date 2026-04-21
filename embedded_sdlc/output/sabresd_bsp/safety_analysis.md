# FUNCTIONAL SAFETY ANALYSIS
## NXP i.MX6Q SabreSD — Linux BSP Driver Package

**Document ID:** FSA-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 3 (Safety Analysis)
**Standards applied:** IEC 61508:2010 (primary), ISO 26262:2018 (where automotive gateway use case applies)
**Traces upward to:** SRS-IMX6Q-BSP-001 v1.0, SAD-IMX6Q-BSP-001 v1.0

---

## 0. SCOPE & ASSUMPTIONS

The i.MX6Q SabreSD BSP is a **general-purpose Linux BSP** — it is not itself a safety-certified product. However, downstream integrators may deploy it in applications where safety analysis is mandatory (industrial gateway, medical HMI, automotive infotainment/telematics). This analysis therefore treats the BSP as a **SEooC — Safety Element out of Context (ISO 26262-10 §9)**, establishing safety claims and assumptions that integrators must confirm.

**Assumed highest usage class:** Industrial gateway + HMI with remote update (UC-01, UC-02, UC-04).
**Out of scope:** Random-hardware-fault analysis of the i.MX6Q silicon itself (NXP responsibility — see AN5306 and i.MX6 FMEDA datasheet).
**In scope:** BSP driver software, DTS, boot firmware, systemd units, user-space `bsp-health` daemon.

---

## 1. SAFETY INTEGRITY LEVEL DETERMINATION

### 1.1 Hazard Identification (HARA summary)

| HAZ-ID | Hazard | Use Case | Triggering Condition |
|--------|--------|----------|----------------------|
| HAZ-01 | Loss of CAN traffic (SocketCAN frames dropped/stale) | UC-01 | Gateway forwarding CAN→Ethernet |
| HAZ-02 | Incorrect CAN frame delivered (data corruption, silent failure) | UC-01 | Misrouted control message |
| HAZ-03 | HMI display frozen, operator unaware | UC-02 | DRM/KMS deadlock, VPU hang |
| HAZ-04 | HMI touch input lost / phantom touches | UC-02 | I²C glitch, evdev flood |
| HAZ-05 | Filesystem corruption on eMMC (loss of calibration/logs) | UC-01/UC-02 | Power-loss during write, uSDHC error |
| HAZ-06 | Overheating — thermal runaway, silicon damage | All | Thermal driver failure, fan/throttle loss |
| HAZ-07 | Failed OTA → unbootable device (brick) | UC-05 | Image corruption, power loss mid-flash |
| HAZ-08 | Unauthorised firmware accepted (security → safety) | UC-05 | Signature verification bypass |
| HAZ-09 | Camera pipeline silently stuck on last frame | UC-03 | V4L2 DMA starvation |
| HAZ-10 | Watchdog fails to reset a hung kernel | All | WDT driver mis-petted by stuck task |

### 1.2 IEC 61508 Risk Matrix (Industrial Gateway Profile)

Severity (S) × Frequency of exposure (F) × Probability of avoidance (P) × Demand-rate (W).

| HAZ | S | F | P | W | SIL (derived) | Rationale |
|-----|---|---|---|---|---------------|-----------|
| HAZ-01 | S2 | F2 | P2 | W2 | **SIL 2** | Loss of gateway comms → production stop; recoverable via reboot |
| HAZ-02 | S3 | F2 | P3 | W2 | **SIL 3** | Silent mis-delivery can trigger incorrect actuator command downstream |
| HAZ-03 | S2 | F2 | P2 | W2 | **SIL 2** | Operator may issue wrong command against stale display |
| HAZ-04 | S2 | F2 | P2 | W2 | **SIL 2** | Lost/phantom input → unintended operator action |
| HAZ-05 | S1 | F2 | P2 | W2 | **SIL 1** | Log loss, recoverable; calibration loss handled by failsafe defaults |
| HAZ-06 | S3 | F2 | P2 | W1 | **SIL 2** | Latent damage; slow-developing → mitigable |
| HAZ-07 | S2 | F1 | P3 | W1 | **SIL 2** | Field service needed, no injury |
| HAZ-08 | S3 | F1 | P3 | W1 | **SIL 3** | Rooted device → arbitrary safety violation |
| HAZ-09 | S1 | F2 | P2 | W2 | **SIL 1** | Monitoring only; diverse means likely |
| HAZ-10 | S3 | F2 | P2 | W2 | **SIL 2** | Watchdog is last-line defence |

### 1.3 ISO 26262 ASIL (if deployed as automotive telematics/HMI gateway)

| HAZ | Severity | Exposure | Controllability | ASIL |
|-----|----------|----------|-----------------|------|
| HAZ-01 | S1 | E4 | C2 | **ASIL A** |
| HAZ-02 | S2 | E3 | C3 | **ASIL B** |
| HAZ-03 | S1 | E4 | C2 | **ASIL A** |
| HAZ-04 | S1 | E3 | C2 | **QM** |
| HAZ-06 | S2 | E4 | C2 | **ASIL B** |
| HAZ-08 | S3 | E4 | C3 | **ASIL D** (security-critical) |
| HAZ-10 | S2 | E4 | C3 | **ASIL C** |

### 1.4 Allocated SIL per Safety Function

| SF-ID | Safety Function | SIL | ASIL |
|-------|-----------------|-----|------|
| SF-01 | CAN frame integrity & delivery (SocketCAN + FlexCAN driver) | SIL 2 | B |
| SF-02 | End-to-end message authentication (app-layer, out of BSP scope — assumption) | SIL 3 | D |
| SF-03 | Display liveness watchdog (HMI pipeline freshness counter) | SIL 2 | A |
| SF-04 | Thermal protection (thermal zone + CPUfreq throttle + emergency shutdown) | SIL 2 | B |
| SF-05 | Watchdog management (WDT driver + userspace `bsp-health` petter) | SIL 2 | C |
| SF-06 | Secure boot chain (HAB → U-Boot → FIT signature → kernel) | SIL 3 | D |
| SF-07 | eMMC write integrity (journaling + power-fail safe FS) | SIL 1 | A |
| SF-08 | Bounded-latency boot (≤ 15 s per UC-01) | SIL 1 | QM |

---

## 2. FMEA — FAILURE MODE AND EFFECTS ANALYSIS

AIAG scale: S(1–10), O(1–10), D(1–10). RPN = S × O × D. **Action threshold: RPN ≥ 100 or S ≥ 9.**

| ID | Component / Function | Failure Mode | Cause | Effect | S | O | D | RPN | Mitigation |
|----|----------------------|--------------|-------|--------|---|---|---|-----|------------|
| F-001 | FlexCAN driver (`flexcan_mod`) — RX path | Frames silently dropped | RX FIFO overrun, IRQ coalescing, lost NAPI budget | Gateway loses telemetry (HAZ-01) | 7 | 4 | 5 | 140 | Enable RX-FIFO overflow IRQ; expose `/sys/.../rx_overruns`; `bsp-health` alarms on non-zero delta |
| F-002 | FlexCAN driver — TX path | Frame corrupted in memory before TX | DMA coherency bug, cache aliasing | Wrong command on bus (HAZ-02) | 9 | 2 | 7 | 126 | Use `dma_map_single` with correct direction; CRC-15 is CAN-native; **SSR-007** end-to-end CRC at app layer |
| F-003 | FlexCAN driver — IRQ | IRQ never fires (lost interrupt) | GIC mis-config, shared-IRQ starvation | Bus silence (HAZ-01) | 7 | 3 | 4 | 84 | Hrtimer-based keepalive check; escalate to WDT if no RX for 2 s (SF-01) |
| F-004 | I²C controller (`i2c-imx`) | Bus hang after arbitration loss | Slave holding SDA low, glitch on clock | Touch & SGTL5000 unresponsive (HAZ-04) | 6 | 5 | 4 | 120 | Implement `i2c_imx_recovery_info` (9-clock SCL pulse + STOP); timeout 50 ms |
| F-005 | uSDHC / eMMC | Write error not reported | CMD/DATA CRC mis-masked, voltage droop | Silent FS corruption (HAZ-05) | 8 | 3 | 6 | 144 | Enable CMD23 reliable-write; ext4 with `data=journal` or F2FS; `mmc-utils` health poll |
| F-006 | uSDHC — power loss during write | Partial block write → ECC fail | Brown-out, PMIC trip | Unbootable (HAZ-07) | 8 | 3 | 5 | 120 | A/B partition scheme; U-Boot bootcount rollback; power-fail capacitor on VDD_3V3 |
| F-007 | Thermal driver (`imx_thermal`) | TEMPMON reads stuck value | ANATOP I²C-like bus glitch, regmap cache stale | Overheating undetected (HAZ-06) | 9 | 2 | 7 | 126 | Sanity check `ΔT/Δt`; regmap no-cache for TEMPMON; secondary sensor via PMIC |
| F-008 | Thermal policy | Throttle governor disabled | User-space `thermald` crash, cpufreq unloaded | Thermal runaway (HAZ-06) | 9 | 3 | 4 | 108 | Kernel-space `step_wise` governor as primary; user-space is secondary; critical-trip triggers `orderly_poweroff()` |
| F-009 | Watchdog (`imx2_wdt`) | WDT petted by zombie task | Kernel thread spins without real work; stuck userspace still schedules | Hang not reset (HAZ-10) | 9 | 3 | 6 | 162 | Windowed WDT mode; userspace `bsp-health` validates liveness via heartbeat-of-dependents pattern before pet |
| F-010 | Watchdog | WDT never enabled at boot | systemd unit ordering, `watchdog-timeout` DT missing | No last-line defence (HAZ-10) | 9 | 2 | 3 | 54 | Enable WDT in U-Boot; `nowayout=1` kernel param; DT property mandatory (SSR-012) |
| F-011 | DRM/KMS (`imx-drm`, `mxsfb`/`dcss` equivalent) | Display frozen but driver reports OK | IPU page-flip IRQ lost, VSYNC missed | Operator sees stale UI (HAZ-03) | 7 | 4 | 7 | 196 | Vblank timeout detection; userspace "heartbeat pixel" + screensaver liveness check (SF-03) |
| F-012 | V4L2 / MIPI-CSI | DMA stuck, last frame replayed | IPU CSI FIFO overflow, buffer queue starve | Stale video (HAZ-09) | 5 | 4 | 6 | 120 | V4L2 `sequence` counter monotonic check in userspace; `vb2` timeout → reset CSI |
| F-013 | eCSPI driver | SPI clock glitch → bit flip | PCB coupling, long trace, fast edge | Sensor reads wrong (propagates) | 6 | 3 | 7 | 126 | CRC on sensor protocol; reduce SPI clock under EMC stress; pinctrl slew-rate config |
| F-014 | Pinctrl / IOMUXC | Wrong pad mux after resume | `pinctrl-state-default` not re-applied | Peripheral dead after suspend | 6 | 3 | 5 | 90 | Verify with `pinmux-pins` debugfs in PM callback; regression test in SwIT-PM-001 |
| F-015 | Clock framework (CCF) | Clock gated while peripheral active | Reference-count bug, `clk_disable_unprepare` too eager | Peripheral freeze | 7 | 3 | 6 | 126 | Enable `CLK_IS_CRITICAL` on core clocks; runtime-PM fences; clk debugfs audit |
| F-016 | Regulator framework | PMIC rail dropped out | I²C to PFUZE100 fails | Total peripheral failure | 8 | 2 | 4 | 64 | `regulator_always_on`; PMIC IRQ monitored; bsp-health publishes |
| F-017 | DDR3 controller (MMDC) | Uncorrectable bit error | Temperature, radiation, aging | Kernel panic / silent corruption | 10 | 1 | 8 | 80 | Enable ECC if board supports (SabreSD does not — **document limitation**); periodic memtest in idle |
| F-018 | GbE (`fec_main`) driver | TX hang after link flap | BD ring pointer corruption | Comms loss | 5 | 4 | 4 | 80 | Netdev watchdog `tx_timeout`; PHY poll; auto-reset after 2 s |
| F-019 | USB OTG (`chipidea`) | Wrong role after cable swap | ID-pin debounce bug | Host/device confusion | 3 | 4 | 4 | 48 | Extcon-based detection with 200 ms debounce |
| F-020 | Secure boot (HAB + FIT) | Signature check bypassed | HAB fuse not blown (OEM error), weak key | Arbitrary code (HAZ-08) | 10 | 2 | 6 | 120 | Mandatory factory fuse burn step; `hab_status` read in U-Boot; reject `CLOSED != 1` |
| F-021 | OTA updater | Downgrade attack accepted | Version counter missing | Known-vulnerable image (HAZ-08) | 9 | 3 | 5 | 135 | Monotonic rollback counter in OTP fuse; RAUC/SWUpdate minimum-version check |
| F-022 | `bsp-health` userspace daemon | Daemon crashes, not restarted | systemd `Restart=on-failure` missing | WDT unpetted → reset (acceptable) OR pet-loop alive (unacceptable) | 8 | 3 | 5 | 120 | systemd `Restart=always`, `WatchdogSec=`; daemon itself pets kernel WDT only after verifying dependents |
| F-023 | Device tree | Wrong DDR timing in DT | Copy/paste from other i.MX6 variant | Early boot hang / memory corruption | 9 | 2 | 4 | 72 | DDR calibration tool (`MSCALE_DDR_Tool`) run per board revision; golden DTB in CI |
| F-024 | Kernel scheduler config | RT task starves `bsp-health` | Priority inversion, CPU isolation wrong | WDT reset spuriously | 6 | 3 | 5 | 90 | Use `SCHED_DEADLINE` for health daemon; CPU shielding for RT workload |
| F-025 | Bluetooth HCI-UART | Flow-control stall | RTS/CTS misrouted in DTS | BT unresponsive (not safety) | 2 | 4 | 3 | 24 | DTS review checklist; `hciconfig` smoke test |
| F-026 | CAN — CCF with I²C | Shared PMU rail fails | PFUZE100 SW1 rail drop | Both SocketCAN and touch dead (HAZ-01+HAZ-04) | 8 | 2 | 5 | 80 | See §4 CCF analysis |
| F-027 | Linux kernel — memory leak | OOM killer triggers | Driver ref-count leak | Long-run reliability | 7 | 3 | 8 | 168 | `kmemleak` in CI; uptime soak test ≥ 168 h; cgroup memory limits |

**Items with RPN ≥ 100 or S ≥ 9 require corrective action — see §8 SSR list.**

---

## 3. FAULT TREE ANALYSIS

### 3.1 TOP-EVENT-1 : Incorrect CAN control frame delivered to bus (HAZ-02)

```
                    TE-1: Corrupted/wrong CAN frame on bus
                                   │
                                  OR
              ┌────────────────────┼────────────────────┐
              │                    │                    │
           [G1] TX data           [G2] Routing         [G3] Bit-flip
           corrupted pre-CAN      table wrong          in flight
              │                    │                    │
             AND                  OR                   OR
              │                ┌───┴────┐          ┌────┴────┐
        ┌─────┴─────┐          │        │          │         │
     [B1] DMA    [B2] CAN-    [B3]     [B4]      [B5]      [B6]
     coherency   native CRC   App      Config    CAN       PHY
     fault       masks it     logic    file      controller glitch
     (F-002)     (passes 15b) bug      corrupt   CRC err   (EMC)
                                       (F-005)   escaped   (F-013 analog)

Minimal cut sets (MCS):
  { B1 ∧ B2 }                       ← silent DMA corruption
  { B3 }                            ← app-layer routing bug  (out of BSP scope — SSR-007 required)
  { B4 }                            ← filesystem corruption of routing table
  { B5 }                            ← extremely rare (residual)
  { B6 }                            ← EMC-induced, mitigated by CAN 2x resampling
```

**Critical MCS order 1 (single-point failures):** {B3}, {B4} — must be mitigated by **end-to-end application CRC + monotonic sequence counter (SSR-007).**

### 3.2 TOP-EVENT-2 : HMI frozen, operator sees stale UI (HAZ-03)

```
                    TE-2: Stale image on display, no indication
                                   │
                                  AND
                     ┌─────────────┴─────────────┐
                     │                           │
                  [G1] Display                [G2] Freshness
                  stops updating              indicator fails
                     │                           │
                    OR                          OR
         ┌───────────┼───────────┐         ┌─────┴─────┐
       [B1]        [B2]        [B3]      [B4]        [B5]
      DRM page-   VPU hang    Compositor Heartbeat   Watchdog
      flip IRQ    (F-011)     (Weston)   pixel       on DRM
      lost        lost        crash      mechanism   vblank
      (F-011)                             not         disabled
                                          deployed

MCS:
  { B1 ∧ B4 }, { B1 ∧ B5 }
  { B2 ∧ B4 }, { B2 ∧ B5 }
  { B3 ∧ B4 }, { B3 ∧ B5 }
```

**All MCS are order-2.** Acceptable provided SF-03 (display liveness) is implemented.

### 3.3 TOP-EVENT-3 : Kernel hang not reset by watchdog (HAZ-10)

```
                    TE-3: System hung, no auto-recovery
                                   │
                                  AND
                     ┌─────────────┴─────────────┐
                     │                           │
                  [G1] Kernel/                [G2] WDT
                  userspace hung              not resetting
                     │                           │
                    OR                          OR
         ┌───────────┼──────┐         ┌─────────┼─────────┐
       [B1]        [B2]   [B3]      [B4]      [B5]      [B6]
      Deadlock   RT task  OOM       WDT       Zombie    WDT
      in driver  starves  livelock  disabled  task pets IRQ
                 sched              (F-010)   blindly   disables
                                              (F-009)   WDT clock

MCS:
  { B1 ∧ B4 } { B1 ∧ B5 } { B1 ∧ B6 }
  { B2 ∧ B4 } { B2 ∧ B5 } { B2 ∧ B6 }
  { B3 ∧ B4 } { B3 ∧ B5 } { B3 ∧ B6 }
```

**Order-2 throughout.** B5 (zombie pet) is the weakest link — addressed by windowed-WDT + dependency-verified pet (SF-05 / SSR-010).

### 3.4 TOP-EVENT-4 : Unauthorised firmware executes (HAZ-08)

```
                    TE-4: Malicious kernel/U-Boot image accepted
                                   │
                                  OR
              ┌────────────────────┼────────────────────┐
           [G1] HAB              [G2] FIT              [G3] Roll-
           bypassed              signature             back attack
              │                  bypassed                │
             OR                    OR                   OR
         ┌────┴────┐          ┌────┴────┐         ┌─────┴─────┐
       [B1]      [B2]       [B3]       [B4]     [B5]        [B6]
      SRK fuses SRK key     U-Boot     Key      Version     Monotonic
      not blown compromised verify     leaked   counter     counter
      (open                 disabled             not         not in
      device)               at build             checked     fuse

MCS: {B1}, {B2}, {B3}, {B4}, {B5 ∧ B6}
```

Single-point cuts {B1}..{B4} demand **defence in depth** — see SSR-013, SSR-014.

---

## 4. COMMON CAUSE FAILURE (CCF) ANALYSIS

### 4.1 Shared Resources

| Shared Resource | Functions Affected | CCF Hazard |
|-----------------|--------------------|------------|
| PFUZE100 PMIC — SW1 rail (VDD_ARM_IN) | All CPU cores, most peripherals | Total loss of function |
| I²C3 bus | SGTL5000 audio, touch controller, PMIC status, MAX7310 GPIO expander | Simultaneous loss of multiple subsystems |
| 24 MHz crystal XTALI | CCM PLL source for **every** clock | Single-point failure for entire SoC |
| DDR3 controller (MMDC) | Kernel, all drivers | Catastrophic, no graceful mode |
| GIC-400 interrupt controller | All IRQ-driven drivers | Lost IRQs across subsystems |
| Linux kernel (single image) | All drivers | Kernel panic → all safety functions lost |
| Same compiler (arm-linux-gnueabihf-gcc 13) | Entire BSP | Compiler bug manifests identically in redundant copies — **diversity not achievable within BSP** |

### 4.2 Mitigation Measures

| CCF-ID | Measure | Independence / Diversity |
|--------|---------|--------------------------|
| CCF-01 | External independent watchdog IC (e.g. MAX6369) on a GPIO not multiplexed with CPU — required by integrator | **Physical independence** from i.MX6Q WDT |
| CCF-02 | PMIC health monitored via dedicated PMIC_INT pin → GPIO IRQ, published to `bsp-health` | Independence from I²C path |
| CCF-03 | XTAL failure detected via RTC (separate 32.768 kHz oscillator) comparison | Diverse timebase |
| CCF-04 | Safety-critical CAN routing decisions done in **second MCU** (e.g. Cortex-M4 companion), not on Linux | Functional diversity (HW + SW) — **integrator SEooC assumption** |
| CCF-05 | End-to-end CRC + sequence at application layer, independent of any BSP transport | SW diversity across OSI stack |
| CCF-06 | A/B partition + rollback ensures compiler-bug in image N is recoverable to N−1 | Temporal diversity |
| CCF-07 | Critical regulator/clock marked `CLK_IS_CRITICAL`, `regulator-always-on` to avoid spurious gating | Defensive config |
| CCF-08 | CPU shielding (isolcpus) for safety-critical RT work separates it from best-effort Linux | Resource partitioning |

### 4.3 β-factor Estimate (IEC 61508-6 Annex D)

Qualitative β estimated at **≥ 10 %** for I²C-shared subsystems, **≥ 25 %** for PMIC-shared. Integrators must refine quantitatively for their deployment.

---

## 5. DIAGNOSTIC COVERAGE ANALYSIS

| Safety Mechanism | Failure Modes Covered | DC% | Standard Reference |
|------------------|-----------------------|-----|--------------------|
| CAN bus-off detection + auto-recovery | Stuck-dominant, short-circuit | 90 % | IEC 61508-2 Annex A, Tab A.7 |
| Netdev watchdog (`tx_timeout`) | TX ring hang (F-018) | 85 % | IEC 61508-7 A.7.4 (program-sequence monitoring) |
| RX FIFO overrun counter | Frame drop (F-001) | 99 % | IEC 61508-7 A.7.5 |
| I²C bus-recovery (9-clock) | Bus hang (F-004) | 80 % | IEC 61508-7 A.10 |
| CMD23 reliable write + journaling FS | Torn writes (F-005, F-006) | 95 % | IEC 61508-7 A.7.2 |
| Thermal ΔT/Δt sanity + secondary sensor | Stuck sensor (F-007) | 90 % | IEC 61508-7 A.13 (input comparison) |
| Windowed WDT + dependency-verified pet | Zombie-pet (F-009) | 95 % | IEC 61508-7 A.9.1 |
| External independent WDT (integrator) | i.MX6Q WDT CCF | 99 % | IEC 61508-2 §7.4.4 (diverse channels) |
| DRM vblank timeout + heartbeat pixel | Frozen display (F-011) | 90 % | IEC 61508-7 A.8 |
| V4L2 sequence monotonicity check | Stuck frames (F-012) | 85 % | IEC 61508-7 A.7 |
| `kmemleak` + soak test (development) | Memory leak (F-027) | 70 % (dev only; 0 % in field) | IEC 61508-7 C.5.7 |
| HAB CLOSED + FIT signature + rollback counter | Unauthorised FW (F-020, F-021) | 99 % | IEC 62443-4-2 CR 3.4; ISO 26262 cybersecurity ref. |
| MMDC — (no ECC on SabreSD) | DDR bit error (F-017) | **0 %** | **Gap — see §9** |
| Boot-time DTB hash check | DT corruption (F-023) | 99 % | IEC 61508-7 A.4 |
| Regulator-always-on + PMIC IRQ | Rail droop (F-016) | 80 % | IEC 61508-7 A.6 |

**Aggregate DC (Safety-related functions only):** ≈ **92 %** → **SIL 2 achievable** per IEC 61508-2 Tab 3 for the safety functions as specified, **subject to integrator adding external WDT (CCF-01)** and **DDR ECC limitation being accepted or mitigated at system level**.

---

## 6. SAFE STATE DEFINITION

| Hazard | Safe State | Detection Latency | Transition Time | Mechanism |
|--------|------------|-------------------|-----------------|-----------|
| HAZ-01 (CAN loss) | CAN interface **bus-off**, SocketCAN `netdev down`, upstream app notified via netlink | ≤ 500 ms | ≤ 100 ms | FlexCAN REC/TEC saturate → bus-off IRQ |
| HAZ-02 (wrong CAN frame) | Stop TX, raise `bsp-health` alarm, bus-off peer safety MCU | ≤ 200 ms (E2E CRC) | ≤ 50 ms | Application layer — SSR-007 |
| HAZ-03 (HMI freeze) | Display "SYSTEM NOT RESPONDING" overlay (rendered by independent path: kernel fbcon fallback), audible alarm | ≤ 2 s | ≤ 500 ms | Display liveness monitor SF-03 |
| HAZ-04 (touch loss) | Ignore input until reinitialised; UI shows "input unavailable" | ≤ 1 s | ≤ 500 ms | evdev disconnect + I²C recovery |
| HAZ-05 (FS corruption) | Remount RO; continue operation from RAM state; next boot → fsck | ≤ 100 ms | ≤ 200 ms | Kernel `errors=remount-ro` |
| HAZ-06 (overheat) | CPUfreq → min; if >105 °C `orderly_poweroff()`; hard cut at 125 °C via PMIC | ≤ 250 ms | ≤ 2 s (orderly) / ≤ 100 ms (hard) | Kernel thermal governor + PMIC thermal shutdown |
| HAZ-07 (brick) | Boot into previous slot via bootcount rollback; fallback to recovery partition | ≤ 30 s (2 boot attempts) | ≤ 60 s | U-Boot `bootcount`, RAUC |
| HAZ-08 (unauth FW) | Boot aborted by HAB, device enters NXP serial-download mode (requires physical access to escape) | Instant | 0 | HAB ROM |
| HAZ-09 (stuck frames) | V4L2 → `VIDIOC_STREAMOFF`, pipeline reset, last-known-good frame marked stale | ≤ 1 s | ≤ 500 ms | Userspace monitor |
| HAZ-10 (hang) | Watchdog reset → reboot → resume | ≤ `wdt_timeout` (default 10 s) | ≤ 5 s reset | `imx2_wdt` + external WDT |

---

## 7. RESIDUAL RISK ASSESSMENT

| Hazard | Residual Risk | Accepted? | Justification |
|--------|---------------|-----------|---------------|
| HAZ-01 | Low | Yes | DC ≥ 90 %, safe state reachable, integrator adds E2E protocol |
| HAZ-02 | Low | **Conditional** | Only if SSR-007 (E2E CRC+seq) implemented by integrator; otherwise **REJECTED** |
| HAZ-03 | Low | Yes | Dual-channel liveness (heartbeat + vblank) — order-2 FT |
| HAZ-04 | Low | Yes | Temporary unavailability only; no actuation from BSP |
| HAZ-05 | Very Low | Yes | Journaling + A/B; recoverable |
| HAZ-06 | Low | Yes | Three-tier defence: SW throttle, SW shutdown, HW PMIC shutdown |
| HAZ-07 | Low | Yes | A/B + rollback + recovery partition |
| HAZ-08 | Low | **Conditional** | Requires HAB CLOSED at manufacturing (SSR-013); otherwise **REJECTED** |
| HAZ-09 | Low | Yes | Monitoring-only use case; SIL 1 |
| HAZ-10 | Low | **Conditional** | Requires external WDT (CCF-01); integrator SEooC assumption |
| **DDR3 bit error (F-017)** | Medium | Document as **limitation** | SabreSD has no ECC; not mitigable in BSP. Integrators requiring SIL 3 must choose ECC-capable hardware |
| **Compiler-induced CCF** | Medium | Yes | Accepted per IEC 61508-3 Annex C; GCC 13 has sufficient pedigree; diverse compilation infeasible |

---

## 8. SAFETY REQUIREMENTS DERIVED FROM ANALYSIS

New / refined requirements, traceable to FMEA / FTA:

| SSR-ID | Requirement | Trace | SIL |
|--------|-------------|-------|-----|
| SSR-001 | FlexCAN driver SHALL expose RX/TX error counters, RX-FIFO overrun count, and bus-off events via sysfs and netlink | F-001, F-003 | SIL 2 |
| SSR-002 | FlexCAN driver SHALL use DMA descriptors with explicit `dma_map_single(DMA_TO_DEVICE)` and SHALL NOT rely on cache-coherent mappings for data payload | F-002 | SIL 2 |
| SSR-003 | FlexCAN driver SHALL implement a keep-alive hrtimer that verifies IRQ liveness at 1 Hz and sets the netdev `operstate` to `DOWN` on failure | F-003 | SIL 2 |
| SSR-004 | `i2c-imx` driver SHALL implement bus-recovery GPIO callbacks and SHALL invoke recovery on any transfer timeout > 50 ms | F-004 | SIL 2 |
| SSR-005 | The MMC stack SHALL enable CMD23 reliable-write on eMMC and the rootfs SHALL be mounted with journaling and `errors=remount-ro` | F-005 | SIL 1 |
| SSR-006 | U-Boot SHALL implement A/B bootcount rollback; RAUC SHALL enforce monotonic version counter against OTP fuse | F-006, F-021 | SIL 2 |
| SSR-007 | **[INTEGRATOR]** Application layer SHALL provide end-to-end CRC-32 + monotonic sequence counter for all safety-relevant CAN traffic | F-002, FT-1/MCS-order-1 | SIL 3 |
| SSR-008 | Thermal driver SHALL validate consecutive samples (\|ΔT\| < 40 °C/s) and flag stuck-sensor fault | F-007 | SIL 2 |
| SSR-009 | Kernel thermal governor (`step_wise`) SHALL be primary; user-space `thermald` SHALL be secondary only; `critical` trip SHALL invoke `orderly_poweroff()` unconditionally | F-008 | SIL 2 |
| SSR-010 | `bsp-health` daemon SHALL pet the WDT only after successful verification of: (a) scheduler heartbeat, (b) at least one recent I/O event per monitored driver, (c) no unreaped orphans in its dependency list | F-009, FT-3/B5 | SIL 2 |
| SSR-011 | WDT driver SHALL be enabled in U-Boot before kernel handover; DT node SHALL be mandatory; `nowayout=1` SHALL be default | F-010 | SIL 2 |
| SSR-012 | `[INTEGRATOR]` An external independent watchdog IC SHALL be fitted to the carrier board and serviced via a dedicated GPIO | CCF-01, HAZ-10 | SIL 2 |
| SSR-013 | **[INTEGRATOR MFG]** HAB SHALL be CLOSED (SRK fuses blown) before device leaves factory; U-Boot `hab_status` check SHALL refuse to continue if `dev_closed != 1` in production images | F-020, FT-4/B1 | SIL 3 |
| SSR-014 | FIT-image signature verification (RSA-3072 or higher) SHALL be mandatory and SHALL NOT be compile-time disableable in production configs | F-020, FT-4/B3 | SIL 3 |
| SSR-015 | DRM driver SHALL implement vblank-miss detection; userspace compositor SHALL render a monotonic "heartbeat pixel" monitored by `bsp-health` | F-011, FT-2 | SIL 2 |
| SSR-016 | V4L2 pipeline SHALL increment `v4l2_buffer.sequence` monotonically; `bsp-health` SHALL flag staleness > 2 frame intervals | F-012 | SIL 1 |
| SSR-017 | Pinctrl `default` state SHALL be re-applied in PM resume callback for all safety-relevant peripherals; a PM regression test SHALL confirm | F-014 | SIL 2 |
| SSR-018 | Core clocks (IPG, AHB, MMDC_CH0, ARM) SHALL be marked `CLK_IS_CRITICAL` in DT/driver | F-015 | SIL 2 |
| SSR-019 | `bsp-health` systemd unit SHALL set `Restart=always`, `WatchdogSec=`, and start **before** any application unit | F-022 | SIL 2 |
| SSR-020 | CI pipeline SHALL run `kmemleak`, 168 h soak, and MMDC memtest as release gates | F-027, F-017 | SIL 1 |
| SSR-021 | DTB SHALL be signed and hash-verified at boot by U-Boot FIT | F-023 | SIL 2 |
| SSR-022 | Safety-relevant kernel threads SHALL be pinned with `SCHED_FIFO` priority ≥ 80 and CPU-isolated via `isolcpus=` | F-024 | SIL 2 |
| SSR-023 | The release shall include a **Safety Manual** documenting all `[INTEGRATOR]` assumptions, SEooC boundaries, and required external mitigations | All | n/a |

---

## 9. COMPLIANCE GAPS

Gaps against IEC 61508 / ISO 26262 not yet addressed by the BSP alone:

| Gap-ID | Standard Clause | Gap Description | Resolution Path |
|--------|-----------------|-----------------|-----------------|
| GAP-01 | IEC 61508-2 §7.4.4.1 (HW architectural constraints) | SabreSD DDR3 has no ECC — SFF ≈ 90 % achievable only for Type-A subsystems; Type-B memory paths limit to SIL 2 | Document as hardware limitation; integrators requiring SIL 3 data path must use ECC-capable platform (i.MX8 family) |
| GAP-02 | IEC 61508-3 §7.4.4 (diverse SW) | Single kernel image, single compiler — no SW diversity | Accepted per Annex C; integrator adds diverse 2nd-channel MCU if diversity required |
| GAP-03 | IEC 61508-3 Table A.3 (semi-formal methods) | Linux kernel is not developed with semi-formal methods | Use **Route 2S — proven in use** (IEC 61508-7 C.2.10.2): kernel 6.6 LTS has > 10⁹ operational hours across the fleet — evidence to be compiled per integrator |
| GAP-04 | ISO 26262-6 §7.4.9 (freedom from interference) | Linux does not inherently provide FFI between partitions | Use CPU isolation + cgroups + SECCOMP; or integrate with hypervisor (e.g. Jailhouse) — integrator decision |
| GAP-05 | ISO 26262-10 §9 (SEooC) | BSP as delivered is SEooC; assumptions on integrator are many | **SSR-023** — Safety Manual mandatory deliverable |
| GAP-06 | IEC 61508-3 §7.9.2.12 (impact analysis for change) | Frequent kernel patches / CVE updates break freeze-point argument | Establish change-impact workflow; gate releases through regression + safety review |
| GAP-07 | ISO 26262-8 §11 (confidence in tool use) — TCL | GCC, binutils, buildroot, yocto — TCL not yet classified | Perform **T-CL determination** (ISO 26262-8 §11.4) per tool; likely TCL1 for build tools with output verification |
| GAP-08 | IEC 62443-4-2 (security-informed safety) | Security analysis separate from this FSA | Deliver companion **Threat Model** document; HAZ-08 is the interface |
| GAP-09 | IEC 61508-3 §7.4.4 (coding standard) | MISRA-C classified "advisory" per SwRS §6 for in-tree kernel code — conflict with SIL 3 expectations | Document justification: kernel idiomatic style + `sparse`/`smatch`/`coccinelle` static analysis + Coverity as compensating measures |
| GAP-10 | IEC 61508-1 §6 (FSM — functional safety management) | No SQM/FSM plan referenced in BSP deliverables | Add **FSM Plan** as Stage-0 artefact in V-model |

---

**End of FSA-IMX6Q-BSP-001 v1.0**
Next V-model stage: **Stage 4 — Software Requirements (SwRS)**, which shall ingest SSR-001…SSR-023 as inputs.