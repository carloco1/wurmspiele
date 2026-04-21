# SYSTEM VALIDATION TEST SPECIFICATION
## NXP i.MX6 Quad SabreSD — Linux BSP Driver Package

**Document ID:** SVT-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 14 (System Validation)
**Pairs with:** SRS-IMX6Q-BSP-001 v1.0
**Traces downward to:** HSIT-IMX6Q-BSP-001, SwQT-IMX6Q-BSP-001, FSA-IMX6Q-BSP-001
**Target Board:** MCIMX6Q-SDB (SabreSD) rev. C
**Target SW:** Yocto Scarthgap 5.0, Linux 6.6 LTS, U-Boot 2024.01
**Validation Owner:** System V&V Lead
**Sign-off Authority:** Chief Engineer, QA Manager, Customer (OEM) Representative

---

## 0. DOCUMENT CONVENTIONS

- Each validation test has a unique ID `SVT-nnn` and maps to one or more `SFR-xxx`.
- Pass/Fail is expressed against the **user-visible, black-box** behaviour — no knowledge of internal implementation is assumed beyond standard Linux interfaces (sysfs, netlink, evdev, V4L2, ALSA, DRM).
- Measurements are captured by external instruments wherever reasonable (scope, logic analyser, network analyser, thermal chamber, programmable PSU) so the oracle is independent of the DUT.
- All durations are wall-clock unless noted.
- All probe and connector references use SabreSD schematic **SPF-27392_C**.

---

## 1. SYSTEM VALIDATION STRATEGY

### 1.1 Objective

Demonstrate, by end-to-end black-box testing of the fully integrated SabreSD + Linux 6.6 BSP system in representative operating conditions, that:

1. Every `SFR-xxx` in SRS-IMX6Q-BSP-001 is satisfied.
2. Every stakeholder Use Case (UC-01 … UC-08) succeeds without operator intervention beyond its documented procedure.
3. Every Safety Requirement `SSR-xxx` from FSA-IMX6Q-BSP-001 is demonstrable at system level.
4. The system meets its non-functional targets (boot time, latency, throughput, reliability) across the full environmental envelope.

### 1.2 Validation Environment

```
          ┌──────────────────────────────────────────────────────┐
          │         THERMAL/CLIMATIC CHAMBER (-20 … +70 °C)      │
          │                                                      │
          │  ┌────────────────────────────────────────────────┐  │
          │  │     SabreSD DUT (rev. C) — representative       │  │
          │  │     cable harness, production enclosure         │  │
          │  │     eMMC-boot image = release candidate (RC)    │  │
          │  └────┬───────┬────────┬────────┬────────┬─────────┘  │
          └───────┼───────┼────────┼────────┼────────┼────────────┘
                  │       │        │        │        │
             UART │   GbE │   CAN  │  HDMI  │  USB   │  DSI/Touch
                  ▼       ▼        ▼        ▼        ▼
          ┌─────────────────────────────────────────────────────┐
          │        Instrumentation Rack (outside chamber)        │
          │  • Prog. PSU (Keysight N6705C) — Vin 4.5 … 5.5 V     │
          │  • Oscilloscope (MSO 5-Series, 2 GHz)                │
          │  • Logic analyser (Saleae Pro 16)                    │
          │  • Network analyser (Spirent C1)                     │
          │  • CAN analyser (Vector VN1640A)                     │
          │  • HDMI capture (Quantum Data 780G)                  │
          │  • EMC chamber (periodic, §SVT-023)                  │
          │  • Test controller host (Ubuntu 22.04, pytest)       │
          └─────────────────────────────────────────────────────┘
```

Operating envelope verified:

| Parameter        | Nominal | Min   | Max   |
|------------------|---------|-------|-------|
| Vin (DC jack)    | 5.0 V   | 4.5 V | 5.5 V |
| Ambient T°       | 25 °C   | −20°C | +70°C |
| Relative humidity| 50 %    | 10 %  | 85 %RH (non-cond.) |
| GbE cable length | 1 m     | —     | 100 m |

### 1.3 Acceptance Testing Approach

- **Black-box end-to-end:** tests interact only via external interfaces (display, USB, GbE, CAN, audio, touch, serial console for test orchestration only).
- **Scenario-driven:** each Use Case UC-01 … UC-08 has a walkthrough SVT.
- **Instrument-based oracle:** scope, LA, protocol analyser, thermal sensor, etc. — never software self-report alone for PASS.
- **Representative build:** the exact release-candidate Yocto image is used. No debug kernel, no module-built-out-of-tree overrides. `CONFIG_DEBUG_*` disabled.
- **Operator procedure:** every SVT is executable by a field technician following the numbered steps without access to source code.

### 1.4 Stakeholder Sign-off Process

1. All SVT-nnn executed on 3 independent DUTs (S/N tracked).
2. Dry-run review with QA lead → freeze procedures.
3. Witnessed run: at least one OEM integrator + QA + safety officer present for SVT-001, SVT-023, SVT-028, SVT-029.
4. Results entered in §4 template and signed (wet signature or PKI-signed PDF).
5. Non-conformances (§5) dispositioned: **Fix / Waive / Defer** — waivers require customer acceptance.
6. Final sign-off via §7 checklist → release gate for BSP v1.0 → tagged in Yocto meta-layer.

---

## 2. SYSTEM VALIDATION TEST CASES

> Cluster mapping: SVT-001 … SVT-027 cover functional SFRs; SVT-028 … SVT-032 cover non-functional / reliability / safety; SVT-033 covers soak.
> Where one SVT validates a cluster of related SFRs, all SFR-IDs are listed and the procedure exercises each independently.

---

### SVT-001 — SFR-001 — Cold boot time

| Field | Value |
|-------|-------|
| **SFR text** | The system SHALL boot Linux 6.6 LTS from eMMC, SD card, or USB within 15 s from U-Boot hand-off to `init` on a cold boot. |
| **Environment** | Chamber at 25 ± 2 °C, Vin 5.0 V, eMMC boot media, production image, no network. Logic analyser on UART1-TXD (J500) + GPIO probe on user LED1 (configured by `init` as heartbeat). |
| **Precondition** | DUT powered off ≥ 60 s; eMMC contains release-candidate image; boot switches SW6 = eMMC. |
| **Procedure** | 1. Arm LA trigger on "`Starting kernel ...`" string on UART1 (this is the U-Boot→kernel hand-off). <br>2. Close PSU output at t=0 (PSU sequencing profile: rise < 10 ms). <br>3. Capture time from trigger to first edge of `init`-driven LED heartbeat (shell prompt also logged). <br>4. Repeat 10 consecutive cold boots (≥ 60 s off between each). |
| **Expected** | t_boot ≤ 15.000 s on all 10 runs; mean reported. |
| **Pass/Fail** | PASS if max(t_boot) ≤ 15.0 s AND no boot failures. FAIL otherwise. |
| **Regression** | Yes. |

---

### SVT-002 — SFR-002 — Device tree completeness

| Field | Value |
|-------|-------|
| **SFR text** | The BSP SHALL provide `imx6q-sabresd.dts` covering every on-board peripheral. |
| **Environment** | DUT booted on bench (25 °C, 5.0 V). |
| **Precondition** | Release image booted, root shell available. |
| **Procedure** | 1. Run `dtc -I fs /proc/device-tree -O dts -o /tmp/live.dts`. <br>2. Compare against checklist of 47 on-board peripherals (Appendix A). <br>3. For each, verify a corresponding `status = "okay"` node exists. <br>4. Cross-check `/sys/bus/*/devices/` enumerations. |
| **Expected** | All 47 peripherals present & enabled; no `status = "disabled"` for populated devices. |
| **Pass/Fail** | PASS if checklist 47/47; FAIL otherwise. |
| **Regression** | Yes. |

---

### SVT-003 — SFR-003 cluster — Mainline driver usage / no out-of-tree

| Field | Value |
|-------|-------|
| **SFR text** | All drivers SHALL be mainline Linux drivers or upstream-submitted equivalents; out-of-tree modules prohibited. |
| **Environment** | Bench, 25 °C. |
| **Precondition** | Booted release image. |
| **Procedure** | 1. `lsmod` → capture module list. <br>2. For each module, `modinfo <mod> | grep intree` must report `Y`. <br>3. Verify no module signed with out-of-tree key (`modinfo ... | grep signer`). |
| **Expected** | 100 % in-tree modules. |
| **Pass/Fail** | PASS if all modules `intree: Y`. |
| **Regression** | Yes. |

---

### SVT-004 — UC-01 — Headless Gateway Boot walkthrough

| Field | Value |
|-------|-------|
| **SFR text** | UC-01 — boot from eMMC, GbE + CAN + SPI + I2C up, SocketCAN + spidev + iio available within 15 s. |
| **Environment** | Bench 25 °C, 5.0 V. GbE cable to Spirent port; CAN analyser on J1939; SPI loopback jumper on J501 (ecspi1); I2C temperature sensor on J25 (I2C3). |
| **Precondition** | SW6 = eMMC, no monitor attached. |
| **Procedure** | 1. Power on; start timer at U-Boot hand-off. <br>2. At t = 15 s, execute: `ip link show eth0` (must be `state UP`), `ip link show can0`, `ls /dev/spidev*`, `ls /sys/bus/iio/devices/`. <br>3. Inject 100 CAN frames at 500 kbit/s from analyser → `candump can0` must capture all. <br>4. `spidev_test -D /dev/spidev0.0 -s 1000000 -p deadbeef` loopback check. <br>5. `cat /sys/bus/iio/devices/iio:device0/in_temp_raw` non-zero. |
| **Expected** | All 4 subsystems usable at 15 s mark; 100/100 CAN frames received; SPI loopback matches; IIO read succeeds. |
| **Pass/Fail** | PASS only if all 5 checks succeed within the 15 s window. |
| **Regression** | Yes. |

---

### SVT-005 — UC-02 — HMI Display Panel

| Field | Value |
|-------|-------|
| **SFR text** | UC-02 — DSI/HDMI panel via DRM/KMS; I2C touch → evdev; SGTL5000 audio via SAI. |
| **Environment** | HDMI panel 1080p60 attached to J508; capacitive touch panel on I2C2; headphones on J16. HDMI capture (Quantum Data 780G) in parallel via splitter. |
| **Precondition** | Booted. |
| **Procedure** | 1. `modetest -M imx-drm -s <CONN>:1920x1080@60` → capture HDMI output. <br>2. Verify capture reports 1920×1080 @ 60.000 ± 0.5 Hz, RGB888. <br>3. `evtest /dev/input/event0` while technician performs 10 touches at known coordinates → record reported (x,y). <br>4. `aplay -D plughw:0 /usr/share/sounds/alsa/Front_Center.wav`; measure 1 kHz tone at headphone jack with scope. |
| **Expected** | Video mode locked; touches reported within ±10 px of expected; audio 1 kHz ± 1 Hz @ ≥ 300 mV p-p into 32 Ω. |
| **Pass/Fail** | PASS if all three measurements within tolerance. |
| **Regression** | Yes (automated via HDMI-capture + robotic stylus). |

---

### SVT-006 — UC-03 — Camera capture 1080p30

| Field | Value |
|-------|-------|
| **SFR text** | UC-03 — MIPI-CSI sensor streams via V4L2 at 1080p30 without frame drops. |
| **Environment** | OV5640 on MIPI-CSI port (J5). Bench 25 °C. |
| **Precondition** | Sensor cable seated; `/dev/video0` enumerates. |
| **Procedure** | 1. `gst-launch-1.0 -v v4l2src device=/dev/video0 ! video/x-raw,width=1920,height=1080,framerate=30/1 ! fpsdisplaysink text-overlay=false video-sink=fakesink -v` for 120 s. <br>2. Parse `current-fps=` from stderr; also read driver-reported `v4l2-ctl --all` frame-sequence counter before/after. <br>3. Frame drops = (expected − received). |
| **Expected** | 30.00 ± 0.10 fps sustained; 0 dropped frames in 120 s (= 3600 frames). |
| **Pass/Fail** | PASS if drops = 0 AND fps ∈ [29.9, 30.1]. |
| **Regression** | Yes. |

---

### SVT-007 — UC-04 — Wireless connectivity (BT + Wi-Fi)

| Field | Value |
|-------|-------|
| **SFR text** | UC-04 — BT HCI over UART + Wi-Fi SDIO combo enumerates and is manageable. |
| **Environment** | Murata combo module on uSDHC3 + UART3; reference AP 802.11n 2.4 GHz, reference BT LE peripheral. |
| **Precondition** | Booted; modules loaded. |
| **Procedure** | 1. `hciconfig hci0 up` → verify `UP RUNNING`. <br>2. `hcitool lescan` for 10 s → reference peripheral MAC must appear. <br>3. `wpa_supplicant -B -i wlan0 -c test.conf` → associate. <br>4. `ping -c 100 -i 0.1 <AP_IP>` → all 100 replies. |
| **Expected** | BT scan discovers reference device; Wi-Fi ping loss 0/100, RTT mean < 20 ms. |
| **Pass/Fail** | PASS if all above. |
| **Regression** | Yes. |

---

### SVT-008 — UC-05 — Industrial I/O (CAN/PMIC/ADC/PWM)

| Field | Value |
|-------|-------|
| **SFR text** | UC-05 — FlexCAN exchange; PMIC status via I2C; IIO ADC; PWM backlight/fan. |
| **Environment** | Vector VN1640A on CAN1; PMIC PF0100 live; ADC1 input = precision 1.000 V reference; PWM1 → scope. |
| **Precondition** | Booted. |
| **Procedure** | 1. `ip link set can0 up type can bitrate 500000`; exchange 10 000 frames bidirectionally at 500 kbit/s → 0 errors. <br>2. `i2cdump -y 1 0x08` → PMIC register map non-zero, VGEN5 ≈ 1.80 V reported. <br>3. `cat /sys/bus/iio/devices/iio:device0/in_voltage0_raw` → convert via scale → reading ∈ [0.995, 1.005] V. <br>4. `echo 1000000 > /sys/class/pwm/pwmchip0/pwm0/period`, duty 500000, enable → scope measures 1 kHz, 50 ± 1 % duty. |
| **Expected** | CAN 0 errors; ADC within ±0.5 %; PWM within 1 %. |
| **Pass/Fail** | PASS if all four within tolerance. |
| **Regression** | Yes. |

---

### SVT-009 — UC-06 — Firmware Update / Recovery

| Field | Value |
|-------|-------|
| **SFR text** | UC-06 — USB OTG fastboot device mode; SD-card factory recovery boot. |
| **Environment** | Host PC with `fastboot`; blank recovery SD card (factory image). |
| **Precondition** | DUT booted. |
| **Procedure** | 1. `reboot fastboot` (or U-Boot `fastboot usb 0`). <br>2. Host: `fastboot devices` must list DUT. <br>3. `fastboot flash boot boot.img`; `fastboot reboot` → normal boot succeeds, new build-ID reported in `/etc/os-release`. <br>4. Power off; set SW6 = SD; insert factory SD; power on → system boots to recovery shell within 15 s. |
| **Expected** | Fastboot flash OK; booted image ID matches flashed; SD recovery shell reached. |
| **Pass/Fail** | PASS if both update and recovery paths complete without operator recourse to JTAG. |
| **Regression** | Yes (automated with USB mux + SD mux). |

---

### SVT-010 — UC-07 — EPDC E-Ink (optional variant)

| Field | Value |
|-------|-------|
| **SFR text** | UC-07 — EPDC drives E-ink panel on SabreSD EPDC header. |
| **Environment** | ED060SC4 E-ink panel on EPDC connector J9. |
| **Precondition** | DTS overlay `imx6q-sabresd-epdc.dtbo` selected; booted. |
| **Procedure** | 1. `fbset -fb /dev/fb0` → report 800×600, 8 bpp. <br>2. Draw test pattern: `fb-test-app --pattern=grid /dev/fb0`. <br>3. Visually confirm grid rendered; capture with reference camera. |
| **Expected** | Panel shows grid with no ghosting > 1 frame residual. |
| **Pass/Fail** | PASS if grid visible and waveform update completes < 700 ms. |
| **Regression** | Only on EPDC-variant builds. |

---

### SVT-011 — UC-08 — PCIe Expansion

| Field | Value |
|-------|-------|
| **SFR text** | UC-08 — PCIe Mini-card enumerated at boot with MSI. |
| **Environment** | Reference NVMe M.2→mini-PCIe adapter + 256 GB NVMe SSD in J8. |
| **Precondition** | Booted. |
| **Procedure** | 1. `lspci -vv` → NVMe device present, MSI enabled (Capability: MSI ... Enable+). <br>2. `dd if=/dev/nvme0n1 of=/dev/null bs=1M count=1024 iflag=direct` → throughput recorded. <br>3. `cat /proc/interrupts | grep nvme` → MSI count increments during transfer. |
| **Expected** | Enumerates as Gen1 ×1; read throughput ≥ 180 MB/s; MSI count > 0. |
| **Pass/Fail** | PASS on all three. |
| **Regression** | Yes. |

---

### SVT-012 — SFR — GbE throughput & latency

| Field | Value |
|-------|-------|
| **SFR text** | GbE (FEC) SHALL sustain ≥ 940 Mbit/s TCP RX/TX with < 1 ms RTT on 1 m CAT-6. |
| **Environment** | Spirent C1 ↔ DUT, 1 m CAT-6. |
| **Precondition** | `ethtool eth0` reports 1000BaseT Full. |
| **Procedure** | 1. `iperf3 -c <host> -t 60` (TX) and `-R` (RX). <br>2. 1 000 × `ping -c 1 -s 64 <host>` RTT. |
| **Expected** | TX ≥ 940 Mbit/s, RX ≥ 940 Mbit/s, RTT max < 1 ms. |
| **Pass/Fail** | PASS if all thresholds met. |
| **Regression** | Yes. |

---

### SVT-013 — SFR — USB host throughput

| Field | Value |
|-------|-------|
| **SFR text** | USB 2.0 host SHALL enumerate HS devices and sustain ≥ 30 MB/s bulk. |
| **Environment** | USB3-to-USB2 reference mass-storage device (known-good). |
| **Precondition** | Booted. |
| **Procedure** | 1. Insert drive into J13. <br>2. `dd if=/dev/sda of=/dev/null bs=1M count=512 iflag=direct`. |
| **Expected** | Throughput ≥ 30 MB/s. |
| **Pass/Fail** | PASS if threshold met. |
| **Regression** | Yes. |

---

### SVT-014 — SFR — eMMC read/write endurance (short)

| Field | Value |
|-------|-------|
| **SFR text** | eMMC SHALL sustain ≥ 45 MB/s sequential write, ≥ 90 MB/s sequential read (HS200). |
| **Environment** | Bench 25 °C. |
| **Precondition** | Booted to RAM (overlayfs) so eMMC can be benched. |
| **Procedure** | 1. `fio --name=seqw --rw=write --bs=1M --size=1G --direct=1 --filename=/dev/mmcblk0p5`. <br>2. `fio --name=seqr --rw=read  --bs=1M --size=1G --direct=1 --filename=/dev/mmcblk0p5`. |
| **Expected** | W ≥ 45 MB/s, R ≥ 90 MB/s. |
| **Pass/Fail** | PASS both. |
| **Regression** | Yes. |

---

### SVT-015 — SFR — SD card hot-plug

| Field | Value |
|-------|-------|
| **SFR text** | SD cards SHALL be hot-pluggable with correct uevent generation. |
| **Environment** | SD mux controlled by test host; reference SDHC card. |
| **Precondition** | Booted, `udevadm monitor` running. |
| **Procedure** | 1. Insert card → capture `add` uevent + block node appears within 2 s. <br>2. `mount /dev/mmcblk1p1 /mnt` → succeeds. <br>3. `umount /mnt`; eject → `remove` uevent; block node gone ≤ 2 s. <br>4. Repeat 50 cycles. |
| **Expected** | 100/100 uevents correct; 0 kernel oops. |
| **Pass/Fail** | PASS if all cycles clean. |
| **Regression** | Yes. |

---

### SVT-016 — SFR — I2C bus robustness & clock-stretching

| Field | Value |
|-------|-------|
| **SFR text** | I2C buses SHALL tolerate clock-stretching and recover from SDA-stuck-low. |
| **Environment** | I2C3 with programmable slave (stretches SCL up to 10 ms); bus-fault injector pulls SDA low for 500 ms. |
| **Procedure** | 1. 10 000 × `i2cget -y 2 0x50 0x00` with 5 ms stretching → 0 errors in dmesg. <br>2. Assert SDA-stuck fault; verify driver logs recovery and subsequent read succeeds. |
| **Expected** | No lockup; bus recovers within 1 s; no stale data. |
| **Pass/Fail** | PASS on both. |
| **Regression** | Yes. |

---

### SVT-017 — SFR — Audio latency & quality (SAI + SGTL5000)

| Field | Value |
|-------|-------|
| **SFR text** | Audio playback SHALL have < 20 ms round-trip latency; THD+N < 0.1 % at 1 kHz full-scale-6 dB. |
| **Environment** | Audio analyser (APx525) on line-in/out via SabreSD J16/J17. |
| **Procedure** | 1. `arecord -> aplay` loopback with timestamp pulse; measure round-trip. <br>2. APx test: 1 kHz, −6 dBFS → THD+N, SNR, frequency response 20 Hz–20 kHz. |
| **Expected** | Latency < 20 ms; THD+N < 0.1 %; SNR ≥ 90 dB; FR ±1 dB 20–20k. |
| **Pass/Fail** | PASS on all. |
| **Regression** | Yes. |

---

### SVT-018 — SFR — Real-time latency (PREEMPT/PREEMPT_RT profile)

| Field | Value |
|-------|-------|
| **SFR text** | With `PREEMPT_RT` patch, max scheduling latency SHALL be < 200 µs under load. |
| **Environment** | `cyclictest -p80 -t4 -l 10000000 -i 200` with parallel `stress-ng --cpu 4 --io 2 --vm 2`. |
| **Procedure** | Run for 1 h; log histogram. |
| **Expected** | Max latency < 200 µs; 99.99th pct < 100 µs. |
| **Pass/Fail** | PASS if thresholds met. |
| **Regression** | Yes (RT build only). |

---

### SVT-019 — SFR — Power consumption

| Field | Value |
|-------|-------|
| **SFR text** | Board SHALL draw ≤ 2.5 W idle, ≤ 6.0 W full-load @ 5.0 V. |
| **Environment** | Keysight N6705C sourcing 5.0 V, current logged. |
| **Procedure** | 1. Boot; measure 60 s idle average. <br>2. Run `stress-ng --cpu 4 --vm 2 --io 2` + GPU glmark2 + iperf3 TX → 60 s load average. |
| **Expected** | P_idle ≤ 2.5 W; P_load ≤ 6.0 W. |
| **Pass/Fail** | PASS if both. |
| **Regression** | Yes. |

---

### SVT-020 — SFR — Suspend / resume

| Field | Value |
|-------|-------|
| **SFR text** | System SHALL suspend to RAM (s2ram) and resume ≤ 3 s, preserving GbE, USB, console. |
| **Environment** | Bench. |
| **Procedure** | 1. `echo mem > /sys/power/state` → current drops to < 200 mA (scope). <br>2. Wake via UART RX char. <br>3. Re-verify `eth0`, `usb`, shell. <br>4. 100 cycles. |
| **Expected** | 100/100 resume ≤ 3 s; all devices functional. |
| **Pass/Fail** | PASS if 100/100. |
| **Regression** | Yes. |

---

### SVT-021 — SFR — Watchdog reset

| Field | Value |
|-------|-------|
| **SFR text** | Hardware WDOG1 SHALL reset the SoC within 128 s if software stops kicking. |
| **Environment** | Bench; scope on POR_B (TP12). |
| **Procedure** | 1. Open `/dev/watchdog0`, write once, stop kicking. <br>2. Start timer; wait for POR_B low pulse. |
| **Expected** | POR_B asserts within 128 ± 2 s; board reboots. |
| **Pass/Fail** | PASS if reset observed in window. |
| **Regression** | Yes. |

---

### SVT-022 — SFR — Thermal throttling

| Field | Value |
|-------|-------|
| **SFR text** | CPU SHALL throttle at ≥ 85 °C junction and shut down at ≥ 100 °C to protect the die. |
| **Environment** | Chamber ramped to 70 °C; stress-ng cpu-load. |
| **Procedure** | 1. Ramp until `/sys/class/thermal/thermal_zone0/temp` ≥ 85 000. <br>2. Verify `cpufreq` caps to lower OPP (observe via `cpupower frequency-info`). <br>3. Continue ramp to 100 °C → verify critical shutdown logged & POR_B asserted. |
| **Expected** | Throttle engages 83–87 °C; shutdown 98–102 °C; no unprotected behaviour. |
| **Pass/Fail** | PASS if both thresholds honoured. Covers SSR-004 (overheat protection). |
| **Regression** | Yes. |

---

### SVT-023 — SFR — EMC: radiated emissions + immunity

| Field | Value |
|-------|-------|
| **SFR text** | Board SHALL meet EN 55032 Class B emissions and EN 55035 immunity for HMI use. |
| **Environment** | 3 m anechoic chamber; full operational profile (UC-02). |
| **Procedure** | 1. Emission sweep 30 MHz–6 GHz per EN 55032. <br>2. Immunity: ESD ±8 kV contact, RF 3 V/m 80–1000 MHz, burst ±1 kV on power. <br>3. During immunity tests, monitor display integrity and network continuity. |
| **Expected** | Emissions ≤ Class B limits; no loss of function, no data corruption during immunity. |
| **Pass/Fail** | PASS only if both emissions + immunity pass with margin ≥ 3 dB (emissions). |
| **Regression** | Periodic (per hardware revision). |

---

### SVT-024 — SFR — Input voltage margin

| Field | Value |
|-------|-------|
| **SFR text** | System SHALL operate correctly with Vin = 4.5 … 5.5 V. |
| **Environment** | Bench; PSU swept. |
| **Procedure** | 1. At Vin = 4.5 V: boot + UC-01 walkthrough. <br>2. Repeat at 5.0 V and 5.5 V. |
| **Expected** | All three pass UC-01. |
| **Pass/Fail** | PASS if all three. |
| **Regression** | Yes. |

---

### SVT-025 — SFR — Temperature extremes (cold & hot boot)

| Field | Value |
|-------|-------|
| **SFR text** | System SHALL boot and sustain UC-01 at ambient −20 °C and +70 °C. |
| **Environment** | Thermal chamber. |
| **Procedure** | 1. Soak DUT 1 h at −20 °C; cold boot; run UC-01 for 30 min. <br>2. Soak DUT 1 h at +70 °C; cold boot; run UC-01 for 30 min. |
| **Expected** | Both soaks pass UC-01 with same KPIs as 25 °C. |
| **Pass/Fail** | PASS if both soaks. |
| **Regression** | Periodic. |

---

### SVT-026 — SFR — Power-cycle endurance

| Field | Value |
|-------|-------|
| **SFR text** | System SHALL survive ≥ 5000 power cycles without media or filesystem corruption. |
| **Environment** | PSU scripted: 20 s on, 10 s off, for 5000 cycles (~ 42 h). |
| **Procedure** | 1. Start cycle loop. <br>2. Every 100 cycles, run `e2fsck -n` on rootfs and `mmc extcsd read` to monitor wear. <br>3. At end, compare SHA-256 of /boot, /lib, /usr partitions against golden. |
| **Expected** | 5000/5000 boots; 0 fsck errors; hashes match. |
| **Pass/Fail** | PASS if all criteria. |
| **Regression** | Per release. |

---

### SVT-027 — SFR — Secure boot (HAB closed-mode) [if enabled]

| Field | Value |
|-------|-------|
| **SFR text** | When HAB is closed, only signed U-Boot images SHALL boot; tampered image SHALL be rejected. |
| **Environment** | DUT with HAB fuses closed (separate DUT; one-way). |
| **Procedure** | 1. Boot signed image → success; `hab_status` reports no events. <br>2. Flash image with byte-flip → power cycle → expect BootROM halt (USB SDP) and no kernel execution. |
| **Expected** | Tampered image does not execute kernel. |
| **Pass/Fail** | PASS if tampered case rejected. |
| **Regression** | Per release. Covers SSR-007 (integrity). |

---

### SVT-028 — Safety: Graceful degradation on peripheral fault

| Field | Value |
|-------|-------|
| **SFR text** | SSR-001: Failure of one peripheral driver SHALL NOT cascade to kernel panic or loss of console. |
| **Environment** | Bench. |
| **Procedure** | 1. While UC-01 active, physically short CAN_H/CAN_L → observe driver reports bus-off. <br>2. Verify console, GbE, SPI, I2C remain operational for 10 min. <br>3. Clear fault; `ip link set can0 type can restart` → recovers. |
| **Expected** | No panic; no reboot; can0 recovers on command. |
| **Pass/Fail** | PASS if all checks. |
| **Regression** | Yes. |

---

### SVT-029 — Safety: Safety function activation time

| Field | Value |
|-------|-------|
| **SFR text** | SSR-002: On detection of thermal critical or WDOG timeout, safe-state (reset) SHALL be reached within 500 ms of trigger. |
| **Environment** | Bench; scope on POR_B; precise temp ramp via TEC clamped to SoC (or force thermal IRQ via test hook). |
| **Procedure** | 1. Trigger critical-temp event; timestamp event log vs POR_B edge. <br>2. Stop watchdog; measure from last kick + timeout to POR_B; bounded separately by SVT-021 (128 s) but response-after-trigger must be ≤ 500 ms. |
| **Expected** | Thermal: POR_B ≤ 500 ms after event. WDOG: POR_B asserts within 500 ms after timeout window elapses. |
| **Pass/Fail** | PASS if both. |
| **Regression** | Yes. |

---

### SVT-030 — Safety: Memory protection on user-space fault

| Field | Value |
|-------|-------|
| **SFR text** | SSR-003: A faulty user-space process SHALL NOT corrupt kernel memory or other processes. |
| **Environment** | Bench. |
| **Procedure** | 1. Run deliberate segfault harness (null deref, double free, stack smash) 10 000×. <br>2. Monitor dmesg for kernel OOPS; monitor parallel UC-01 workload. |
| **Expected** | 10 000 segfaults → 0 kernel oops; UC-01 unaffected. |
| **Pass/Fail** | PASS if 0 oops. |
| **Regression** | Yes. |

---

### SVT-031 — Reliability: MTBF observation window

| Field | Value |
|-------|-------|
| **SFR text** | System SHALL exhibit MTBF ≥ 50 000 h extrapolated from 168 h observation on 3 DUTs (no failures ⇒ 60 % confidence bound). |
| **Environment** | Continuous run (see §3 soak). |
| **Procedure** | See SVT-033. |
| **Expected** | 0 failures in 3 × 168 h = 504 device-hours. |
| **Pass/Fail** | PASS if 0 failures (χ² 60 %: MTBF ≥ ~548 h lower bound extrapolated via accelerated model per Appendix B to ≥ 50 000 h). |
| **Regression** | Per release candidate. |

---

### SVT-032 — Fault tolerance: brown-out recovery

| Field | Value |
|-------|-------|
| **SFR text** | After a brown-out (Vin drops to 3.5 V for 100 ms), system SHALL either continue or cleanly reboot without filesystem corruption. |
| **Environment** | PSU brownout profile; journaled ext4 rootfs. |
| **Procedure** | 1. During active write workload (`dd` 10 MB/s to rootfs), inject brown-out. <br>2. After recovery, `e2fsck -n` must be clean; 100 cycles. |
| **Expected** | 100/100 clean fsck; no silent corruption of known reference file. |
| **Pass/Fail** | PASS if 100/100. |
| **Regression** | Yes. |

---

## 3. SOAK / ENDURANCE TEST SPECIFICATION

**SVT-033 — Long-duration soak**

| Attribute | Value |
|-----------|-------|
| **Duration** | 168 h (7 days) continuous, on 3 DUTs in parallel (S/N tagged). |
| **Environmental profile** | 8 h cycles: 25 °C → +70 °C (2 h ramp + 2 h dwell) → +25 °C (2 h) → −20 °C (1 h dwell) → +25 °C. Vin toggled 4.75 V / 5.25 V every 12 h. |
| **Workload** | Concurrent: UC-01 (CAN @ 500 kbit/s, 100 frames/s), UC-02 (1080p60 display + audio loop), UC-03 (camera 1080p30 → /dev/null), UC-04 (Wi-Fi iperf 20 Mbit/s, BT LE advertising), GbE iperf 100 Mbit/s, rootfs fio 1 MB/s mixed RW. |
| **Monitors** | UART console log, kernel dmesg ring, `/proc/interrupts` deltas every 60 s, current/voltage telemetry, thermal zone temp, camera frame counter, ping-loss counter, CAN err counter, ECC/CRC counters where present. |
| **Failure criteria (any one ⇒ FAIL)** | 1. Kernel oops/panic. <br>2. Device enumeration lost (re-enumerates or stays gone). <br>3. GbE ping loss > 0.01 %. <br>4. Camera dropped frames > 0.1 %. <br>5. CAN bus-off > 2 events. <br>6. Rootfs fsck error on scheduled mid-test readonly check (hour 96). <br>7. Over-temp shutdown at ambient ≤ 70 °C. <br>8. Unexplained reboot. |
| **Exit criteria** | 168 h elapsed on all 3 DUTs with no failure criterion triggered. |

---

## 4. VALIDATION TEST RESULTS TEMPLATE

| SVT-ID  | SFR-ID   | DUT S/N | Measured                 | Spec             | Pass/Fail | Date       | Operator | Notes / Artefacts        |
|---------|----------|---------|--------------------------|------------------|-----------|------------|----------|--------------------------|
| SVT-001 | SFR-001  |         | t_boot max =       s     | ≤ 15.000 s       |           | YYYY-MM-DD |          | capture-IDs              |
| SVT-002 | SFR-002  |         |   / 47 peripherals       | 47 / 47          |           |            |          | live.dts archive         |
| SVT-003 | SFR-003  |         |   in-tree /   total      | 100 %            |           |            |          | lsmod.txt                |
| …       | …        |         | …                        | …                |           |            |          |                          |
| SVT-033 | soak     |         |   DUT-hours, 0 failures  | 3×168 h, 0 fail  |           |            |          | soak-logs.tar.zst        |

(Complete row set = SVT-001 … SVT-033 per DUT.)

---

## 5. NON-CONFORMANCE REPORT TEMPLATE

```
NON-CONFORMANCE REPORT — NCR-<nnn>
-----------------------------------
Related SVT-ID      :
Related SFR-ID(s)   :
DUT S/N / Build ID  :
Date / Operator     :

Description (observed vs expected):

Severity            : [ Critical | Major | Minor | Cosmetic ]
Safety impact       : [ Yes / No — if Yes, reference SSR-xxx ]
Reproducibility     : [ Always | Intermittent (rate) | Once ]

Evidence attached   : [ log | waveform | video | coredump ]

Root-cause analysis :
   Hypothesis        :
   Investigation     :
   Confirmed cause   :

Disposition         : [ Fix | Waive (customer-approved) | Defer-to-next-release ]
Corrective action   :
Verification test   : [ SVT-ID to re-run, or new SVT-ID proposed ]

Approvals           : QA ____   Eng Lead ____   Safety Officer ____   Customer ____
```

---

## 6. FINAL REQUIREMENTS COVERAGE TABLE

| SFR-ID    | SVT-ID             | HIT-ID (HSIT)          | QT-ID (SwQT)           | Status  |
|-----------|--------------------|------------------------|------------------------|---------|
| SFR-001   | SVT-001            | HIT-003, HIT-004       | QT-001, QT-002         | Covered |
| SFR-002   | SVT-002            | HIT-002                | QT-003                 | Covered |
| SFR-003   | SVT-003            | —                      | QT-004, QT-005         | Covered |
| SFR-UC01  | SVT-004, SVT-033   | HIT-010…HIT-020        | QT-010…QT-018          | Covered |
| SFR-UC02  | SVT-005            | HIT-030…HIT-036        | QT-020…QT-025          | Covered |
| SFR-UC03  | SVT-006            | HIT-040…HIT-045        | QT-030…QT-034          | Covered |
| SFR-UC04  | SVT-007            | HIT-050…HIT-055        | QT-040…QT-044          | Covered |
| SFR-UC05  | SVT-008            | HIT-060…HIT-067        | QT-050…QT-056          | Covered |
| SFR-UC06  | SVT-009            | HIT-070, HIT-071       | QT-060                 | Covered |
| SFR-UC07  | SVT-010            | HIT-080                | QT-070                 | Variant |
| SFR-UC08  | SVT-011            | HIT-090, HIT-091       | QT-080                 | Covered |
| SFR-GbE   | SVT-012            | HIT-100…HIT-102        | QT-090                 | Covered |
| SFR-USB   | SVT-013            | HIT-110                | QT-095                 | Covered |
| SFR-eMMC  | SVT-014            | HIT-120                | QT-100                 | Covered |
| SFR-SD    | SVT-015            | HIT-130                | QT-105                 | Covered |
| SFR-I2C   | SVT-016            | HIT-140                | QT-110                 | Covered |
| SFR-AUD   | SVT-017            | HIT-150                | QT-120                 | Covered |
| SFR-RT    | SVT-018            | —                      | QT-130                 | Covered |
| SFR-PWR   | SVT-019            | HIT-160                | QT-140                 | Covered |
| SFR-PM    | SVT-020            | HIT-170                | QT-150                 | Covered |
| SFR-WDG   | SVT-021, SVT-029   | HIT-180                | QT-160                 | Covered |
| SFR-THERM | SVT-022, SVT-029   | HIT-190                | QT-170                 | Covered |
| SFR-EMC   | SVT-023            | —                      | —                      | Covered |
| SFR-VMAR  | SVT-024            | HIT-200                | —                      | Covered |
| SFR-TEMP  | SVT-025, SVT-033   | —                      | —                      | Covered |
| SFR-PCYC  | SVT-026            | —                      | QT-180                 | Covered |
| SFR-SEC   | SVT-027            | HIT-210                | QT-190                 | Covered |
| SSR-001   | SVT-028            | HIT-220                | QT-200                 | Covered |
| SSR-002   | SVT-029            | HIT-180, HIT-190       | QT-160, QT-170         | Covered |
| SSR-003   | SVT-030            | —                      | QT-210                 | Covered |
| SSR-004   | SVT-022            | HIT-190                | QT-170                 | Covered |
| SSR-005   | SVT-033            | —                      | —                      | Covered |
| SSR-006   | SVT-032            | HIT-230                | QT-220                 | Covered |
| SSR-007   | SVT-027            | HIT-210                | QT-190                 | Covered |
| SFR-MTBF  | SVT-031, SVT-033   | —                      | —                      | Covered |

---

## 7. SYSTEM VALIDATION SIGN-OFF CHECKLIST

- [ ] All SFR-xxx verified by at least one SVT (ref. §6 coverage table — no "Uncovered" rows).
- [ ] All safety requirements SSR-001 … SSR-007 verified by SVT and cross-referenced in §6.
- [ ] All SVT-001 … SVT-033 executed on ≥ 3 DUTs (S/N logged in §4).
- [ ] Witnessed runs (SVT-001, SVT-023, SVT-028, SVT-029) signed by QA + Customer.
- [ ] Static analysis report (Coverity + Clang-SA + `checkpatch.pl`): zero Mandatory violations; advisory deviations documented with rationale.
- [ ] Dynamic analysis: 168 h soak (SVT-033) with KASAN/KCSAN build passed on 1 DUT.
- [ ] Code coverage (from SwQT): statement ≥ 90 %, branch ≥ 85 %, MC/DC on safety paths = 100 %.
- [ ] FMEA residual risks reviewed; each "Acceptable" risk signed by Safety Officer; each "ALARP" action closed or formally deferred.
- [