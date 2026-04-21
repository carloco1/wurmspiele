# SOFTWARE REQUIREMENTS SPECIFICATION (SwRS)
## NXP i.MX6 Quad SABRE Smart Device Board — Linux BSP Driver Package

**Document ID:** SwRS-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 4 (Software Requirements)
**Pairs with:** Stage 12 — Software Qualification Tests (SwQT-IMX6Q-BSP-001)
**Traces upward to:** SRS-IMX6Q-BSP-001 v1.0, SAD-IMX6Q-BSP-001 v1.0, HSI-IMX6Q-BSP-001 v1.0
**Target Kernel:** Linux 6.6 LTS
**Target Toolchain:** arm-linux-gnueabihf-gcc 13+ (hard-float VFPv3-D16)
**MISRA Deviation Notice:** Linux kernel drivers follow `Documentation/process/coding-style.rst`. MISRA-C:2012 is applied *as advisory* to BSP-local helper code outside the kernel tree (user-space daemons, test harnesses, bootloader patches) — see §6.

---

## 0. CONVENTIONS

- **Priority:** **MUST** (mandatory for release), **SHOULD** (required unless justified deviation), **MAY** (optional / future).
- **SwXX-nnn** = Software requirement ID; traceable to SFR-nnn in SRS.
- "Driver" = Linux kernel module under `drivers/…` unless stated otherwise.
- All timing budgets measured on i.MX6Q @ 996 MHz, DDR3 @ 528 MHz, default cpufreq governor `ondemand`, unless noted.

---

## 1. SOFTWARE FUNCTIONAL REQUIREMENTS (SwFR)

### 1.1 Boot & Platform Bring-Up

**SwFR-001 — Machine Registration (MUST)**
The BSP SHALL register machine compatible string `"fsl,imx6q-sabresd"` with the kernel `DT_MACHINE_START` table and bind to the `imx6q` SoC match entry.
- *Pre:* Kernel has parsed Flattened Device Tree (FDT) from U-Boot.
- *Post:* `machine_desc` populated; `early_init_dt_scan()` returns 0.
- *Invariant:* Compatible string appears exactly once in the machine table.
- *Parents:* SFR-010, SFR-011.

**SwFR-002 — Clock Tree Initialisation (MUST)**
The `clk-imx6q` driver SHALL instantiate the CCM/CCM_ANALOG/PLL clock tree and register all consumer-visible clocks via `of_clk_add_provider(CLK_OF_DECLARE)` before any peripheral driver probes.
- *Pre:* CCM base `0x020C4000` reachable; ANATOP `0x020C8000` reachable.
- *Post:* `clk_get()` for IDs `IMX6QDL_CLK_*` returns a valid `struct clk *`.
- *Parent:* SFR-012.

**SwFR-003 — Pinctrl State Machine (MUST)**
The `pinctrl-imx6q` driver SHALL apply the `"default"` pinctrl state of each consumer during `driver->probe()` and the `"sleep"` state during suspend.
- *Pre:* IOMUXC at `0x020E0000` mapped.
- *Post:* All `fsl,pins = <…>` entries written to `SW_MUX_CTL_PAD_*` / `SW_PAD_CTL_PAD_*`.
- *Parents:* SFR-013, SFR-020.

**SwFR-004 — Boot Time Budget (MUST)**
Kernel + rootfs (headless) SHALL reach `systemd multi-user.target` within 15 s of U-Boot jumping to kernel entry (UC-01).
- *Post:* `systemd-analyze` reports ≤ 15.0 s.
- *Parent:* SFR-001, UC-01.

### 1.2 Storage (uSDHC / eMMC / SD)

**SwFR-010 — eMMC/SD Enumeration (MUST)**
The `sdhci-esdhc-imx` driver SHALL enumerate the on-board eMMC on uSDHC4 and the micro-SD slot on uSDHC3 and expose them as `/dev/mmcblk*`.
- *Pre:* Card clock ≥ 400 kHz during identification.
- *Post:* Block device node appears; `mmc_card_uhs()` returns true for SDR104-capable SDs.
- *Parent:* SFR-030.

**SwFR-011 — HS200/HS400 Tuning (SHOULD)**
The driver SHOULD execute execution tuning per JEDEC eMMC 5.0 when the device advertises HS200 support, retry ≤ 40 windows, and fall back to HS (52 MHz) on tuning failure without I/O corruption.
- *Parent:* SFR-031.

### 1.3 Networking

**SwFR-020 — GbE Driver (MUST)**
The `fec` driver SHALL bring up the on-board AR8031 PHY on FEC at `0x02188000`, auto-negotiate 10/100/1000 Mbps full-duplex, and expose `eth0`.
- *Pre:* PHY reset GPIO deasserted ≥ 1 ms before MDIO access.
- *Post:* `ethtool eth0` reports `Link detected: yes`.
- *Parent:* SFR-040.

**SwFR-021 — IEEE 1588 Timestamps (SHOULD)**
FEC driver SHOULD expose hardware timestamping (`SIOCSHWTSTAMP`) for PTP v2 over UDP.
- *Parent:* SFR-041.

### 1.4 CAN

**SwFR-030 — SocketCAN Interfaces (MUST)**
The `flexcan` driver SHALL register `can0` (CAN1 @ `0x02090000`) and `can1` (CAN2 @ `0x02094000`) with SocketCAN, supporting bitrates 10 kbit/s – 1 Mbit/s.
- *Post:* `ip link set can0 up type can bitrate 500000` succeeds; frames round-trip on loopback.
- *Parent:* SFR-050.

**SwFR-031 — Bus-Off Recovery (MUST)**
The driver SHALL detect bus-off (ESR1.BOFF_INT) and, if `restart-ms` > 0, automatically re-enter error-active state without user intervention.
- *Parent:* SFR-051, SwSR-020.

### 1.5 Serial Buses

**SwFR-040 — I²C Controllers (MUST)**
The `i2c-imx` driver SHALL instantiate all enabled I²C buses (I²C1–I²C3) at standard-mode (100 kHz) and fast-mode (400 kHz) as declared in DT `clock-frequency`.
- *Parent:* SFR-060.

**SwFR-041 — SPI / spidev (MUST)**
The `spi-imx` driver SHALL bind to eCSPI1–eCSPI5 nodes, and when `compatible = "rohm,dh2228fv"` (spidev placeholder) is present SHALL expose `/dev/spidevB.C`.
- *Parent:* SFR-061.

**SwFR-042 — UART Console (MUST)**
The `imx-uart` driver SHALL register UART1 (`0x02020000`) as `ttymxc0`, 115200 8N1, and act as the kernel console when `console=ttymxc0,115200` is passed.
- *Parent:* SFR-062.

### 1.6 Display / Graphics

**SwFR-050 — DRM/KMS Driver (MUST)**
The `imx-drm` + `dw_hdmi-imx` + `mxsfb`/`mipi_dsi` stack SHALL expose a DRM master, enumerate connectors (HDMI, LVDS0, MIPI-DSI) and provide mode-setting at up to 1920×1080@60.
- *Post:* `modetest` returns at least one preferred mode per connected connector.
- *Parents:* SFR-070, UC-02.

**SwFR-051 — VSync / Page-Flip (MUST)**
Atomic page-flip SHALL deliver `DRM_EVENT_FLIP_COMPLETE` within ±500 µs of the vertical blanking interval of the active mode.
- *Parent:* SFR-071.

### 1.7 Video Capture

**SwFR-060 — V4L2 Camera Subdev (MUST)**
The MIPI-CSI pipeline (IPU-CSI + `ov5640` subdev) SHALL be exposed via V4L2 and Media Controller; `/dev/video0` SHALL stream 1920×1080 UYVY at 30 fps (UC-03).
- *Post:* `v4l2-ctl --stream-mmap --stream-count=300` reports 0 dropped frames.
- *Parent:* SFR-080.

### 1.8 Audio

**SwFR-070 — SGTL5000 ASoC Card (MUST)**
The ASoC machine driver `imx-sgtl5000` SHALL register a sound card with SAI/SSI link to SGTL5000 over I²C1, supporting 44.1/48 kHz 16-bit stereo playback & capture.
- *Parent:* SFR-090.

### 1.9 USB / Wireless

**SwFR-080 — USB OTG & Host (MUST)**
The `ci_hdrc_imx` driver SHALL bring up USB OTG port (dual-role) and USB Host port, supporting HS/FS devices and USB mass-storage enumeration.
- *Parent:* SFR-100.

**SwFR-081 — Wi-Fi/BT Combo Bring-Up (MUST)**
uSDHC3 SHALL enumerate the Wi-Fi SDIO card; UART3 SHALL expose HCI-H4 to BlueZ; power-enable GPIOs SHALL be sequenced per vendor timing (BT_REG_ON t ≥ 150 ms before HCI open) (UC-04).
- *Parent:* SFR-101.

### 1.10 Sensors / IIO

**SwFR-090 — IIO Sensor Hub (MUST)**
The `mma8451` (accelerometer, I²C2) and `mag3110` (magnetometer) drivers SHALL register IIO devices with buffered triggered-capture support.
- *Parent:* SFR-110.

### 1.11 Power Management

**SwFR-100 — Suspend-to-RAM (SHOULD)**
The BSP SHOULD support `mem` sleep state via `pm-imx6` using DDR self-refresh, with wake-up sources: UART1 RX, GPIO power button, GbE WoL.
- *Post:* Resume latency ≤ 500 ms.
- *Parent:* SFR-120.

**SwFR-101 — CPUFreq Operating Points (MUST)**
The `imx6q-cpufreq` driver SHALL register OPPs {396, 792, 996, 1200} MHz with regulator voltage scaling of VDD_ARM.
- *Parent:* SFR-121.

### 1.12 Watchdog

**SwFR-110 — Watchdog (MUST)**
The `imx2-wdt` driver SHALL register `/dev/watchdog0`, default timeout 60 s, ping interval ≤ timeout / 2, and trigger SoC `WDOG1_B` reset on expiry.
- *Parent:* SFR-130, SwSR-010.

---

## 2. SOFTWARE PERFORMANCE REQUIREMENTS (SwPR)

| ID | Requirement | Target | Parent | Prio |
|---|---|---|---|---|
| **SwPR-001** | Kernel cold-boot → userspace init | ≤ 3.5 s (headless) | SFR-001 | MUST |
| **SwPR-002** | GPIO IRQ latency (kernel-space, threaded off) — measured time from IOMUXC pad edge to top-half handler entry | ≤ 8 µs (99th pct), ≤ 20 µs (max) | SFR-013 | MUST |
| **SwPR-003** | FlexCAN RX-to-SocketCAN syscall latency (500 kbit/s, PREEMPT kernel) | ≤ 250 µs (99th pct) | SFR-050 | MUST |
| **SwPR-004** | GbE sustained throughput (iperf3 TCP, MTU 1500) | ≥ 940 Mbit/s RX, ≥ 900 Mbit/s TX | SFR-040 | MUST |
| **SwPR-005** | MMC sequential read, eMMC HS200 | ≥ 150 MB/s | SFR-030 | MUST |
| **SwPR-006** | MMC sequential write, eMMC HS200 | ≥ 80 MB/s | SFR-030 | SHOULD |
| **SwPR-007** | V4L2 1080p30 capture frame-drop rate | 0 drops over 60 s | SFR-080 | MUST |
| **SwPR-008** | DRM page-flip jitter vs VBLANK | ≤ 500 µs | SFR-071 | MUST |
| **SwPR-009** | I²C transfer @ 400 kHz, 16-byte transaction | ≤ 600 µs | SFR-060 | MUST |
| **SwPR-010** | SPI @ 20 MHz, 256-byte full-duplex | ≤ 180 µs (DMA) | SFR-061 | MUST |
| **SwPR-011** | Suspend-to-RAM resume | ≤ 500 ms | SFR-120 | SHOULD |
| **SwPR-012** | Watchdog ping jitter (userspace systemd-notify) | ≤ 100 ms | SFR-130 | MUST |
| **SwPR-013** | Audio SAI playback underrun rate @ 48 kHz/stereo | 0 underruns over 1 h | SFR-090 | MUST |
| **SwPR-014** | USB 2.0 HS bulk throughput (mass-storage) | ≥ 35 MB/s | SFR-100 | SHOULD |
| **SwPR-015** | System idle CPU load (headless, no I/O) | ≤ 3 % on CPU0 | SFR-121 | SHOULD |

---

## 3. SOFTWARE INTERFACE REQUIREMENTS (SwIR)

### 3.1 Kernel-Exposed ABIs

**SwIR-001 — Character & Block Devices (MUST)**
The BSP SHALL expose the following stable device nodes:

| Node | Class | Driver | Notes |
|---|---|---|---|
| `/dev/mmcblk0`, `/dev/mmcblk0pN` | block | sdhci-esdhc-imx | eMMC (uSDHC4) |
| `/dev/mmcblk1` | block | sdhci-esdhc-imx | microSD (uSDHC3) |
| `/dev/ttymxc0..4` | char | imx-uart | UART1..5 |
| `/dev/i2c-0..2` | char | i2c-imx + i2c-dev | I²C1..3 |
| `/dev/spidev0.0..N` | char | spi-imx + spidev | eCSPI |
| `/dev/video0..N`, `/dev/media0` | char | imx-media | V4L2 + MC |
| `/dev/dri/card0`, `/dev/dri/renderD128` | char | imx-drm | DRM/KMS |
| `/dev/watchdog0` | char | imx2-wdt | WDT |
| `/dev/input/eventN` | char | edt-ft5x06 / gpio-keys | evdev |
| `/dev/iio:deviceN` | char | IIO core | sensors |

**SwIR-002 — SocketCAN Interface (MUST)**
FlexCAN driver SHALL implement `struct net_device_ops` including `.ndo_open`, `.ndo_stop`, `.ndo_start_xmit`, `.ndo_change_mtu`, and `struct can_priv` with `do_set_bittiming`, `do_set_mode(CAN_MODE_START)`, `do_get_berr_counter`.

**SwIR-003 — DRM Driver Hooks (MUST)**
`imx-drm` SHALL implement `drm_driver` with `.fops = &drm_gem_cma_fops`, atomic modesetting (`drm_atomic_helper_*`), and advertise `DRIVER_GEM | DRIVER_MODESET | DRIVER_ATOMIC`.

**SwIR-004 — V4L2 Pipeline (MUST)**
Capture path SHALL expose:
- `v4l2_device` per media device
- `video_device` with `VFL_TYPE_VIDEO`
- `vb2_queue` type `V4L2_BUF_TYPE_VIDEO_CAPTURE`, `io_modes = VB2_MMAP | VB2_DMABUF`
- Controls via `v4l2_ctrl_handler`; subdev `s_stream`, `set_fmt`, `enum_mbus_code` mandatory.

### 3.2 Device-Tree Bindings (Source Contract)

**SwIR-010 — DT Compatible Strings (MUST)**
Each driver SHALL match exactly the compatible strings listed below; bindings SHALL be documented under `Documentation/devicetree/bindings/`:

| Driver | Compatible |
|---|---|
| machine | `fsl,imx6q-sabresd`, `fsl,imx6q` |
| sdhci | `fsl,imx6q-usdhc` |
| fec | `fsl,imx6q-fec` |
| flexcan | `fsl,imx6q-flexcan` |
| i2c-imx | `fsl,imx21-i2c` |
| spi-imx | `fsl,imx6q-ecspi`, `fsl,imx51-ecspi` |
| imx-uart | `fsl,imx6q-uart`, `fsl,imx21-uart` |
| imx2-wdt | `fsl,imx21-wdt` |

### 3.3 Internal APIs (BSP-Local Helpers)

**SwIR-020 — Platform Helper API (SHOULD)**
Any BSP-local helper (outside `drivers/`) SHALL expose C prototypes with the following contract style:

```c
/**
 * imx6_sabre_hw_rev_get() - Read board HW revision strap GPIOs.
 * Return: >=0 revision code on success, negative errno on failure.
 * Side effects: None (reads GPIOs, no state change).
 * Thread-safety: reentrant.
 */
int imx6_sabre_hw_rev_get(void);
```

**SwIR-021 — Error Propagation (MUST)**
All kernel-space functions returning errors SHALL use standard Linux `-Exxx` negative errnos; user-space helpers SHALL propagate errors via return value and preserve `errno`; no silent failures, no `BUG_ON()` on recoverable paths (`WARN_ON_ONCE()` is acceptable).

**SwIR-022 — Data Exchange Formats (MUST)**
- Endianness on all buses: **little-endian** (native ARM LE).
- Structures shared with user-space SHALL use fixed-width types (`__u8/__u16/__u32/__u64`, `__s32`, …) and explicit padding.
- `ioctl` numbers SHALL be allocated via `_IO{R,W,WR}` macros; no magic numeric literals.

**SwIR-023 — sysfs / debugfs (SHOULD)**
Driver statistics SHALL be exposed read-only via sysfs under `/sys/class/<class>/<dev>/`; verbose debug SHALL be under `/sys/kernel/debug/imx6-<drv>/` and disabled in release builds.

---

## 4. SOFTWARE SAFETY REQUIREMENTS (SwSR)

*Note:* This BSP targets non-safety-critical consumer/industrial gateway use. Safety requirements below are **availability / robustness** oriented, not ISO 26262 ASIL-classified, unless the integrator assigns a safety level.

**SwSR-010 — Watchdog Refresh Strategy (MUST)**
- A dedicated systemd service (or kernel `watchdog_thread`) SHALL refresh `/dev/watchdog0` at interval ≤ `timeout / 3`.
- On graceful shutdown, magic close (`V`) SHALL be written to stop the watchdog; ungraceful close SHALL **not** disarm (`nowayout = 1`).
- If the refresh thread misses its deadline by > `timeout / 2`, the service SHALL log a critical event before reset.

**SwSR-011 — Safe-State on Driver Probe Failure (MUST)**
If a critical driver (uSDHC rootfs, FEC for PTP deployments, imx2-wdt) fails `probe()`, the BSP SHALL:
- Log `KERN_ERR` with full errno context.
- Leave the kernel in a running state (no panic) unless rootfs is unreachable.
- Allow watchdog to reset the board after `WDOG_TIMEOUT`.

**SwSR-012 — Kernel Oops Policy (MUST)**
Production kernel SHALL be built with `CONFIG_PANIC_ON_OOPS=y` and `kernel.panic=10` so that an unrecoverable kernel fault reboots within 10 s (prevents zombie state).

**SwSR-013 — Memory Integrity (MUST)**
- `CONFIG_STRICT_KERNEL_RWX=y`, `CONFIG_STRICT_MODULE_RWX=y`, `CONFIG_STACKPROTECTOR_STRONG=y`.
- DMA buffers SHALL be allocated via `dma_alloc_coherent()` or `dma_map_*()` with correct direction; no raw `phys_to_virt()` on DMA regions.
- IOMMU/bus-master peripherals (if enabled) SHALL use the DMA API; `dma_mask` SHALL be declared explicitly.

**SwSR-014 — CAN Bus-Off Handling (MUST)**
FlexCAN driver SHALL transition to safe state on bus-off:
1. Disable TX interrupt.
2. Flush TX queue and report via `can_bus_off()`.
3. If `restart-ms` > 0, schedule automatic restart.
4. If `restart-ms` = 0, remain in bus-off until user-space `ip link set can0 type can restart`.

**SwSR-015 — Thermal Trip Safety (MUST)**
The `imx_thermal` driver SHALL configure:
- Passive trip at 85 °C — triggers cpufreq throttling.
- Critical trip at 100 °C — triggers `orderly_poweroff()` via thermal core.

**SwSR-016 — PHY Reset Sequencing (MUST)**
FEC PHY (AR8031) reset GPIO SHALL be asserted for ≥ 10 ms and deasserted ≥ 1 ms before first MDIO access; failure shall produce `-ETIMEDOUT` rather than silent link failure.

**SwSR-017 — Pin Conflict Detection (MUST)**
`pinctrl-imx6q` SHALL refuse a pinmux group that overlaps with an already-claimed pad and return `-EBUSY` with diagnostic logging (prevents electrical contention on IOMUXC pads).

**SwSR-018 — eMMC Write-Protect & Boot-Area Lock (SHOULD)**
uSDHC driver SHOULD honour the `mmc-hs400-enhanced-strobe` and `boot-partition-read-only` DT properties; attempts to write locked boot areas SHALL return `-EROFS`.

**SwSR-019 — Integrity of Loaded Firmware (SHOULD)**
Drivers loading firmware blobs (e.g., Wi-Fi, VPU) via `request_firmware()` SHOULD validate SHA-256 against a manifest when `CONFIG_IMX_FW_VERIFY=y`.

**SwSR-020 — Interrupt Storm Mitigation (MUST)**
All IRQ handlers SHALL:
- Acknowledge the peripheral source before returning `IRQ_HANDLED`.
- Use `IRQF_NO_AUTOEN` where the device is not ready at probe.
- Be convertible to threaded IRQ (`request_threaded_irq`) if top-half exceeds 20 µs.

---

## 5. SOFTWARE RESOURCE REQUIREMENTS (SwRR)

### 5.1 Memory Budget (per-driver, steady-state, quad-core, 1 GiB DDR3)

| Module | Max kernel RAM (KiB) | Flash / kernel .text (KiB) | Notes |
|---|---|---|---|
| **SwRR-001** imx-drm + dw_hdmi | 256 (excl. framebuffers) | 180 | framebuffers from CMA |
| **SwRR-002** imx-media / V4L2 | 128 (control state) | 220 | vb2 buffers from CMA |
| **SwRR-003** sdhci-esdhc-imx | 48 | 60 | per-host |
| **SwRR-004** fec | 64 (rings) | 80 | 256 RX + 256 TX BDs |
| **SwRR-005** flexcan (×2) | 16 | 40 | |
| **SwRR-006** i2c-imx (×3) | 8 | 20 | |
| **SwRR-007** spi-imx | 16 | 30 | |
| **SwRR-008** imx-uart (×5) | 20 | 35 | |
| **SwRR-009** imx2-wdt | 4 | 8 | |
| **SwRR-010** pinctrl-imx6q | 32 | 55 | pad table |
| **SwRR-011** clk-imx6q | 64 | 90 | clock tree |
| **SwRR-012** ASoC (sgtl5000 + imx-sai) | 32 | 60 | |
| **SwRR-013** CMA pool (reserved) | 256 MiB max | n/a | `cma=256M` boot-arg |

**SwRR-020 — Total Kernel Image Size (MUST)**
`zImage` + bundled DTB SHALL fit within a 16 MiB boot partition (target ≤ 12 MiB). Priority: MUST.

**SwRR-021 — Total Rootfs (Headless Gateway) (SHOULD)**
Minimal Yocto image (UC-01 feature set) SHOULD fit in ≤ 128 MiB compressed.

### 5.2 Stack Budget

| Context | Max stack | Priority |
|---|---|---|
| **SwRR-030** Kernel thread (THREAD_SIZE = 8 KiB on ARM) | use ≤ 4 KiB; `-Wframe-larger-than=1024` | MUST |
| **SwRR-031** IRQ handler (shared IRQ stack) | ≤ 1 KiB per handler | MUST |
| **SwRR-032** User-space daemons (wd-ping, bt-init) | ≤ 16 KiB | SHOULD |

### 5.3 CPU Load Budget (per core, worst case in its use-case)

| Scenario | CPU0 | CPU1–3 | Priority |
|---|---|---|---|
| **SwRR-040** UC-01 headless idle | ≤ 3 % | ≤ 1 % | MUST |
| **SwRR-041** UC-03 1080p30 capture | ≤ 35 % | ≤ 10 % | MUST |
| **SwRR-042** UC-04 Wi-Fi streaming 50 Mbit/s | ≤ 40 % | ≤ 15 % | SHOULD |
| **SwRR-043** UC-02 HMI at 60 fps (composited) | ≤ 25 % | ≤ 10 % | MUST |

### 5.4 Interrupt Resource Allocation

**SwRR-050 — IRQ Priority Policy (MUST)**
The BSP SHALL NOT rely on GIC priority manipulation beyond Linux defaults. Latency-critical work SHALL use threaded IRQs with `SCHED_FIFO` priority set via `chrt` only for documented real-time use cases.

---

## 6. SOFTWARE QUALITY REQUIREMENTS (SwQR)

**SwQR-001 — Coding Standard (Kernel Tree) (MUST)**
Code inside `drivers/`, `arch/arm/boot/dts/nxp/imx/`, `sound/soc/fsl/`, etc. SHALL comply with `Documentation/process/coding-style.rst`, pass `scripts/checkpatch.pl --strict` with zero errors and zero warnings (acceptable `CHECK:` messages SHALL be listed with justification in the commit body).

**SwQR-002 — Coding Standard (BSP-local C outside kernel) (MUST)**
User-space daemons, test harnesses, and bootloader patches SHALL comply with **MISRA-C:2012** mandatory + required rules. Advisory rule deviations SHALL be documented with rationale in `docs/misra-deviations.md`. No violations of CERT-C rules: STR, INT, MEM, ARR.

**SwQR-003 — Static Analysis (MUST)**
- Kernel code: `sparse`, `smatch`, `coccinelle` (semantic patches as applicable) — **zero new warnings** vs baseline.
- BSP-local C: `clang-tidy`, `cppcheck --enable=all --error-exitcode=1`, **PC-lint Plus** with MISRA-2012 configuration — zero mandatory/required violations.
- CI pipeline SHALL fail the build on any new warning.

**SwQR-004 — Compiler Flags (MUST)**
Release builds SHALL use at minimum:
```
-Wall -Wextra -Werror -Wshadow -Wformat=2 -Wstrict-prototypes
-Wmissing-prototypes -Wpointer-arith -Wcast-align
-fno-strict-aliasing -fstack-protector-strong
-D_FORTIFY_SOURCE=2
```

**SwQR-005 — Test Coverage (MUST)**
- **Kernel drivers (BSP-local)**: ≥ 80 % statement, ≥ 70 % branch coverage via KUnit + QEMU where feasible.
- **User-space helpers**: ≥ 90 % statement, ≥ 85 % branch via Unity/Ceedling.
- **Safety-tagged code** (watchdog service, CAN bus-off recovery, thermal): **MC/DC** coverage ≥ 95 %.

**SwQR-006 — Unit Test Framework (MUST)**
- Kernel: `KUnit` (`CONFIG_KUNIT=y`) with test modules under `drivers/**/tests/`.
- User-space: **Unity + CMock + Ceedling** with hardware mocks for HSI registers.

**SwQR-007 — Traceability Enforcement (MUST)**
Every commit implementing a SwFR/SwPR/SwSR SHALL reference the requirement ID in its commit message (`Implements: SwFR-010`); CI SHALL reject PRs without traceability for files under `drivers/imx6-bsp/`.

**SwQR-008 — Documentation (SHOULD)**
Every driver SHALL provide:
- `Documentation/devicetree/bindings/**.yaml` binding (mainline format).
- kerneldoc headers (`/** ... */`) on all exported functions.
- Release notes entry in `docs/CHANGELOG.md` referencing the requirement IDs implemented.

**SwQR-009 — Reproducible Builds (MUST)**
Yocto builds SHALL be bit-for-bit reproducible with pinned layer revisions, `SOURCE_DATE_EPOCH` set, and `buildhistory` enabled.

**SwQR-010 — Upstream Alignment (SHOULD)**
The BSP SHOULD minimise vendor-fork delta; out-of-tree patches SHALL be listed with justification and upstream submission status in `docs/upstream-status.md`.

---

## 7. TRACEABILITY MATRIX

| SwFR-ID | Parent SFR-ID | HSI Reference | SW Module | Test Case (SwQT) |
|---|---|---|---|---|
| SwFR-001 | SFR-010, SFR-011 | HSI §1.1 IOMUXC, machine DT | `arch/arm/mach-imx/mach-imx6q.c` | SwQT-BOOT-001 |
| SwFR-002 | SFR-012 | HSI §CCM (`0x020C4000`) | `drivers/clk/imx/clk-imx6q.c` | SwQT-CLK-001 |
| SwFR-003 | SFR-013, SFR-020 | HSI §1.1 IOMUXC | `drivers/pinctrl/freescale/pinctrl-imx6q.c` | SwQT-PIN-001 |
| SwFR-004 | SFR-001 | — | init system | SwQT-BOOT-002 |
| SwFR-010 | SFR-030 | HSI uSDHC @ `0x0219xxxx` | `drivers/mmc/host/sdhci-esdhc-imx.c` | SwQT-MMC-001 |
| SwFR-011 | SFR-031 | HSI uSDHC tuning regs | `sdhci-esdhc-imx.c` | SwQT-MMC-002 |
| SwFR-020 | SFR-040 | HSI FEC @ `0x02188000` | `drivers/net/ethernet/freescale/fec_main.c` | SwQT-NET-001 |
| SwFR-021 | SFR-041 | HSI FEC IEEE1588 block | `fec_ptp.c` | SwQT-NET-002 |
| SwFR-030 | SFR-050 | HSI FlexCAN @ `0x02090000/94000` | `drivers/net/can/flexcan.c` | SwQT-CAN-001 |
| SwFR-031 | SFR-051 | HSI FlexCAN ESR1 | `flexcan.c` | SwQT-CAN-002 |
| SwFR-040 | SFR-060 | HSI I²C @ `0x021A0000` | `drivers/i2c/busses/i2c-imx.c` | SwQT-I2C-001 |
| SwFR-041 | SFR-061 | HSI eCSPI @ `0x02008000..` | `drivers/spi/spi-imx.c` + `spidev` | SwQT-SPI-001 |
| SwFR-042 | SFR-062 | HSI UART @ `0x02020000` | `drivers/tty/serial/imx.c` | SwQT-UART-001 |
| SwFR-050 | SFR-070 | HSI IPU/HDMI/MIPI-DSI | `drivers/gpu/drm/imx/*` | SwQT-DRM-001 |
| SwFR-051 | SFR-071 | HSI IPU interrupts | `imx-drm-core.c` | SwQT-DRM-002 |
| SwFR-060 | SFR-080 | HSI MIPI-CSI + IPU CSI | `drivers/staging/media/imx/*` | SwQT-V4L2-001 |
| SwFR-070 | SFR-090 | HSI SAI/SSI + I²C1 | `sound/soc/fsl/imx-sgtl5000.c` | SwQT-AUD-001 |
| SwFR-080 | SFR-100 | HSI USB-OTG / USB-H1 | `drivers/usb/chipidea/ci_hdrc_imx.c` | SwQT-USB-001 |
| SwFR-081 | SFR-101 | HSI uSDHC3 + UART3 | `sdhci-esdhc-imx`, `hci_uart` | SwQT-WBT-001 |
| SwFR-090 | SFR-110 | HSI I²C2 sensor pads | `drivers/iio/accel/mma8451.c`, `mag3110.c` | SwQT-IIO-001 |
| SwFR-100 | SFR-120 | HSI GPC/CCM suspend regs | `arch/arm/mach-imx/pm-imx6.c` | SwQT-PM-001 |
| SwFR-101 | SFR-121 | HSI ANATOP PLL1, PMIC PFUZE100 | `drivers/cpufreq/imx6q-cpufreq.c` | SwQT-PM-002 |
| SwFR-110 | SFR-130 | HSI WDOG1 @ `0x020BC000` | `drivers/watchdog/imx2_wdt.c` | SwQT-WDT-001 |

### 7.1 Performance Traceability

| SwPR-ID | Parent SFR-ID | Bench | Test Case |
|---|---|---|---|
| SwPR-001 | SFR-001 | `systemd-analyze` | SwQT-PERF-001 |
| SwPR-002 | SFR-013 | cyclictest + IRQ probe | SwQT-PERF-002 |
| SwPR-003 | SFR-050 | canfdtest + ftrace | SwQT-PERF-003 |
| SwPR-004 | SFR-040 | iperf3 | SwQT-PERF-004 |
| SwPR-005/6 | SFR-030 | fio | SwQT-PERF-005 |
| SwPR-007 | SFR-080 | v4l2-ctl stream | SwQT-PERF-006 |
| SwPR-008 | SFR-071 | kms_flip | SwQT-PERF-007 |
| SwPR-009 | SFR-060 | i2ctransfer + scope | SwQT-PERF-008 |
| SwPR-010 | SFR-061 | spidev_test | SwQT-PERF-009 |
| SwPR-011 | SFR-120 | rtcwake + analyze | SwQT-PERF-010 |
| SwPR-012 | SFR-130 | systemd wd-ping log | SwQT-PERF-011 |
| SwPR-013 | SFR-090 | alsaloop 1 h | SwQT-PERF-012 |
| SwPR-014 | SFR-100 | dd on USB-MSC | SwQT-PERF-013 |

### 7.2 Safety Traceability

| SwSR-ID | Parent SFR-ID / Hazard | Mechanism | Test Case |
|---|---|---|---|
| SwSR-010 | SFR-130 / HZ-SW-001 hang | WDT refresh service | SwQT-SAFE-001 |
| SwSR-011 | all critical probes | probe error logging | SwQT-SAFE-002 |
| SwSR-012 | HZ-SW-002 oops | `panic_on_oops` | SwQT-SAFE-003 |
| SwSR-013 | HZ-SW-003 mem corrupt | STRICT_RWX, DMA API | SwQT-SAFE-004 |
| SwSR-014 | SFR-051 / HZ-CAN-001 | bus-off FSM | SwQT-SAFE-005 |
| SwSR-015 | SFR-122 / HZ-THERM-001 | thermal trips | SwQT-SAFE-006 |
| SwSR-016 | SFR-040 | PHY reset timing | SwQT-SAFE-007 |
| SwSR-017 | SFR-013 | pinctrl conflict check | SwQT-SAFE-008 |
| SwSR-018 | SFR-031 | eMMC boot-ro | SwQT-SAFE-009 |
| SwSR-019 | SFR-141 | firmware hash verify | SwQT-SAFE-010 |
| SwSR-020 | all IRQs | IRQ ack + threading | SwQT-SAFE-011 |

---

## 8. OPEN POINTS / ASSUMPTIONS

1. **A-01** — The integrator using this BSP in a functional-safety product SHALL perform independent ASIL/SIL classification; this document does **not** confer a safety classification on the BSP.
2. **A-02** — All performance numbers assume DDR3 @ 528 MHz, CPU @ 996 MHz (OPP3) minimum; derate accordingly for lower OPPs.
3. **A-03** — Out-of-tree drivers (e.g., Vivante GC2000 GPU, VPU/Hantro codec) are **excluded** from SwQR-001 checkpatch enforcement and tracked separately under vendor-module policy.
4. **A-04** — User-space stacks (GStreamer, Weston, BlueZ, wpa_supplicant) are integrated but their internal quality is governed by their upstream projects, not this SwRS.

---

**END OF DOCUMENT — SwRS-IMX6Q-BSP-001 v1.0**