# System Requirements Specification (SRS)
## NXP i.MX6 Quad SABRE Smart Device Board — Linux BSP Driver Package

**Document ID:** SRS-IMX6Q-BSP-001
**Version:** 1.0
**Target Platform:** i.MX6 Quad SabreSD (MCIMX6Q-SDB)
**Target Kernel:** Linux 6.6 LTS
**Yocto Layer:** Scarthgap (5.0)
**Toolchain:** arm-linux-gnueabihf (GCC 13+, hard-float VFPv3-D16)

---

## 1. STAKEHOLDER NEEDS

### 1.1 Stakeholders
| Stakeholder | Concern |
|-------------|---------|
| **OEM Product Integrators** | Ready-to-use BSP to accelerate time-to-market on i.MX6Q-based products |
| **Embedded Linux Developers** | Mainline-quality drivers, stable ABI, upstream-ready DTS |
| **QA / Certification Teams** | Traceable, testable drivers compliant with Linux coding standards |
| **End-Product Users** | Reliable, low-latency multimedia, connectivity, and I/O |
| **Yocto/Buildroot Maintainers** | Clean meta-layer integration, reproducible builds |
| **Field Service** | Stable boot, debug console, recoverable from firmware updates |

### 1.2 Problem Statement
The i.MX6Q SabreSD integrates a large number of heterogeneous peripherals (multimedia, connectivity, storage, sensors, display). A unified, mainline-compatible BSP driver package is required so that downstream products can rely on stable kernel interfaces rather than maintaining vendor forks.

### 1.3 Operational Scenarios (Use Cases)

**UC-01 — Headless Gateway Boot:**
Board boots from eMMC via uSDHC, brings up GbE, loads CAN/SPI/I2C drivers, and exposes SocketCAN + spidev + iio devices within 15 s.

**UC-02 — HMI Display Panel:**
MIPI-DSI or HDMI panel initialised through DRM/KMS; touch controller (I2C) feeds evdev; audio codec SGTL5000 provides UI sound via SAI.

**UC-03 — Camera Capture Pipeline:**
MIPI-CSI sensor streams via V4L2 to user-space (GStreamer) at 1080p30 without frame drops.

**UC-04 — Wireless Connectivity:**
Bluetooth HCI over UART (HCI-H4) + Wi-Fi/SDIO combo via uSDHC3 enumerated and managed by BlueZ/wpa_supplicant.

**UC-05 — Industrial I/O:**
CAN-FD-like FlexCAN bus exchanges frames with external MCUs; PMIC status via I2C; analog inputs read via IIO ADC; PWM drives backlight and fans.

**UC-06 — Firmware Update / Recovery:**
USB OTG device mode exposes fastboot; SD card boot allows factory recovery.

**UC-07 — E-Ink Signage (Optional Variant):**
EPDC drives E-ink panel on SabreSD EPDC header for low-power signage mode.

**UC-08 — PCIe Expansion:**
PCIe Mini-card (e.g., NVMe/Wi-Fi) enumerated at boot and functional with MSI interrupts.

---

## 2. SYSTEM FUNCTIONAL REQUIREMENTS (SFR)

### 2.1 Boot & Platform Infrastructure
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-001** | MUST | The system SHALL boot Linux 6.6 LTS from eMMC, SD card, or USB within 15 s from U-Boot hand-off to `init` on a cold boot. |
| **SFR-002** | MUST | The BSP SHALL provide a device tree (`imx6q-sabresd.dts`) covering every on-board peripheral enumerated in §2.2–2.16. |
| **SFR-003** | MUST | All drivers SHALL register via `platform_driver` / OF match tables and use the standard `pinctrl`, `clk`, and `regulator` frameworks. |
| **SFR-004** | MUST | The BSP SHALL integrate cleanly into Yocto Scarthgap (`meta-imx6q-sabresd` layer) with a `core-image-full-cmdline` build passing `bitbake`. |
| **SFR-005** | SHOULD | Runtime PM SHALL be supported by every driver that owns a clock or regulator. |

### 2.2 FlexCAN (CAN Bus)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-010** | MUST | Both FlexCAN controllers (CAN1, CAN2) SHALL be exposed as SocketCAN network interfaces (`can0`, `can1`). |
| **SFR-011** | MUST | Bit rates from 10 kbit/s to 1 Mbit/s SHALL be configurable via `ip link set … bitrate`. |
| **SFR-012** | MUST | TX → bus-visible latency SHALL be < 500 µs at 1 Mbit/s for an 8-byte standard frame under 50 % CPU load. |
| **SFR-013** | MUST | Error states (error-active/passive/bus-off) SHALL be reported to user space via netlink. |

### 2.3 eCSPI (SPI)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-020** | MUST | The driver SHALL expose eCSPI1–eCSPI5 as `spi_master` controllers. |
| **SFR-021** | MUST | Modes 0–3, bit widths 8/16/32, and frequencies up to 60 MHz SHALL be supported. |
| **SFR-022** | MUST | DMA-assisted transfers SHALL be used for payloads ≥ 64 bytes. |
| **SFR-023** | SHOULD | Full-duplex transfer of 4 kB at 20 MHz SHALL complete in ≤ 2 ms including DMA setup. |

### 2.4 I²C
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-030** | MUST | I²C1–I²C3 SHALL be exposed as `i2c_adapter` at Standard (100 kHz) and Fast (400 kHz) modes. |
| **SFR-031** | MUST | The PFUZE100 PMIC SHALL be driven on I²C1 via the mainline `pfuze100-regulator` driver. |
| **SFR-032** | MUST | The SGTL5000 audio codec SHALL be enumerated on I²C and bound via ASoC. |
| **SFR-033** | MUST | The capacitive touch controller (MAX11801 / atmel_mxt_ts) SHALL produce input events via evdev. |
| **SFR-034** | MUST | Bus hang recovery (9-clock-pulse unstick) SHALL be implemented using pinctrl state switching. |

### 2.5 UART
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-040** | MUST | UART1 SHALL serve as Linux console at 115 200 8N1 (J509 DB9 header). |
| **SFR-041** | MUST | UART3 SHALL support CTS/RTS hardware flow control for Bluetooth HCI at 3 Mbit/s. |
| **SFR-042** | MUST | DMA-mode UART transfer SHALL be supported for baud rates ≥ 921 600. |
| **SFR-043** | SHOULD | Earlycon SHALL be available via `earlycon=ec_imx6q,0x02020000`. |

### 2.6 USB OTG (2×)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-050** | MUST | USB OTG1 SHALL support Host, Device, and OTG dual-role via `chipidea` USB driver. |
| **SFR-051** | MUST | USB Host1 (USB-H1 port) SHALL enumerate High-Speed (480 Mbit/s) devices. |
| **SFR-052** | MUST | VBUS over-current events SHALL be logged and cause controlled port shutdown. |
| **SFR-053** | SHOULD | USB gadget framework (`g_mass_storage`, `g_ether`, `fastboot`) SHALL be buildable. |

### 2.7 Gigabit Ethernet (FEC/ENET)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-060** | MUST | The ENET MAC + Atheros AR8031 PHY SHALL be exposed as `eth0` supporting 10/100/1000BASE-T auto-negotiation. |
| **SFR-061** | MUST | TCP throughput SHALL reach ≥ 900 Mbit/s (iperf3, MTU 1500) TX and RX. |
| **SFR-062** | MUST | PTP IEEE 1588 hardware timestamping SHALL be exposed via SO_TIMESTAMPING. |
| **SFR-063** | MUST | Wake-on-LAN (magic packet) SHALL be supported. |

### 2.8 uSDHC (SD / eMMC)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-070** | MUST | uSDHC2 SHALL support external micro-SD (UHS-I SDR104 up to 104 MB/s). |
| **SFR-071** | MUST | uSDHC3 SHALL support SDIO Wi-Fi (4-bit, 50 MHz). |
| **SFR-072** | MUST | uSDHC4 SHALL support on-board eMMC 4.5 (HS200, 8-bit). |
| **SFR-073** | MUST | Card-detect (CD) and write-protect (WP) GPIOs SHALL generate hot-plug uevents. |
| **SFR-074** | SHOULD | eMMC sequential read SHALL achieve ≥ 150 MB/s measured by `fio`. |

### 2.9 HDMI-TX (Synopsys DesignWare)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-080** | MUST | The HDMI-TX SHALL be integrated as a DRM/KMS connector through `dw_hdmi_imx`. |
| **SFR-081** | MUST | Display modes up to 1920×1080 @ 60 Hz (148.5 MHz pixel clock) SHALL be supported. |
| **SFR-082** | MUST | EDID SHALL be read via DDC and exposed in `/sys/class/drm`. |
| **SFR-083** | MUST | HDMI audio (I²S passthrough via HDMI transmitter) SHALL be available as an ALSA PCM device. |

### 2.10 MIPI-CSI Camera Input
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-090** | MUST | The MIPI-CSI-2 input SHALL be exposed through the V4L2 media controller framework. |
| **SFR-091** | MUST | An OV5640 reference sensor SHALL stream 1920×1080 @ 30 fps in UYVY/YUYV. |
| **SFR-092** | MUST | Frame drop rate SHALL be < 0.1 % over a 1-hour continuous capture. |

### 2.11 MIPI-DSI Display Output
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-100** | MUST | The MIPI-DSI interface SHALL be exposed as a DRM encoder/connector pair. |
| **SFR-101** | MUST | A reference Truly/HannStar 720p panel SHALL be supported via panel-simple bindings. |
| **SFR-102** | SHOULD | DSI lane count (1–4) and bit-rate SHALL be configurable via DT. |

### 2.12 PCIe
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-110** | MUST | The PCIe Gen2 x1 root complex SHALL enumerate endpoints at boot. |
| **SFR-111** | MUST | MSI interrupts SHALL be supported. |
| **SFR-112** | SHOULD | Hot-reset via `echo 1 > …/reset` SHALL recover a link-down endpoint without reboot. |

### 2.13 GPIO Expander
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-120** | MUST | The on-board PCA9555 (I²C GPIO expander) SHALL register 16 GPIO lines into the kernel GPIO subsystem. |
| **SFR-121** | MUST | Interrupt-capable lines SHALL be wired through `gpiolib-irqchip`. |

### 2.14 PWM
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-130** | MUST | PWM1–PWM4 SHALL register as `pwm_chip` instances. |
| **SFR-131** | MUST | PWM1 SHALL drive LCD backlight via `pwm-backlight`, with 256 brightness steps. |
| **SFR-132** | MUST | Output frequency range 50 Hz – 1 MHz SHALL be configurable. |

### 2.15 IIO ADC
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-140** | MUST | The VF610-compatible 12-bit ADC (or equivalent on-board ADC) SHALL expose channels via the IIO subsystem in `/sys/bus/iio`. |
| **SFR-141** | MUST | Sampling accuracy SHALL be ±2 LSB DNL across the full Vref range. |

### 2.16 EPDC (E-Ink)
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-150** | SHOULD | The EPDC controller SHALL be supported via `mxc_epdc_fb` / mainline equivalent when the EPDC daughterboard is present. |
| **SFR-151** | SHOULD | Waveform (.fw) loading SHALL occur via the `firmware_class` API. |

### 2.17 Audio SSI/SAI
| ID | Priority | Requirement |
|----|----------|-------------|
| **SFR-160** | MUST | SSI/SAI SHALL bind to the SGTL5000 codec through an ASoC machine driver (`imx-sgtl5000`). |
| **SFR-161** | MUST | Full-duplex playback/capture at 48 kHz / 16-bit SHALL be jitter-free (underrun count = 0) over 10 min. |
| **SFR-162** | SHOULD | Sample rates 8/16/32/44.1/48/96 kHz SHALL be supported. |

---

## 3. SYSTEM NON-FUNCTIONAL REQUIREMENTS (SNFR)

### 3.1 Performance
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-001** | MUST | Cold-boot to user-space login ≤ 15 s on eMMC. |
| **SNFR-002** | MUST | IRQ-to-top-half latency ≤ 50 µs (P99) under 80 % CPU load. |
| **SNFR-003** | MUST | Average CPU load of idle driver stack ≤ 5 % on one A9 core. |

### 3.2 Reliability
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-010** | MUST | Drivers SHALL pass 72-h continuous stress test (crashme, iperf, CAN flood, V4L2 capture) with zero kernel OOPS/BUG. |
| **SNFR-011** | MUST | MTBF of the driver stack ≥ 10 000 h under nominal load. |
| **SNFR-012** | MUST | No memory leaks detectable via `kmemleak` after 24 h. |
| **SNFR-013** | SHOULD | Watchdog (imx2_wdt) SHALL be integrated and capable of resetting the board within 128 s. |

### 3.3 Safety
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-020** | MUST | The BSP is rated **non-safety-critical** (IEC 61508 SIL 0 / ISO 26262 QM). Any downstream SIL use requires re-qualification. |
| **SNFR-021** | MUST | Driver code SHALL be free of `sparse`, `smatch`, and `checkpatch --strict` blocking warnings. |

### 3.4 Environmental
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-030** | MUST | Operate over commercial range 0 °C … +70 °C, 10 % … 90 % RH non-condensing (SabreSD reference). |
| **SNFR-031** | SHOULD | Thermal throttling via `cpufreq` SHALL engage at ≥ 85 °C die temperature. |
| **SNFR-032** | MUST | Comply with EMC limits of the SabreSD reference enclosure (CISPR 32 Class B). |

### 3.5 Power
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-040** | MUST | Board SHALL run from 5 V ± 5 % @ ≤ 3 A via barrel jack. |
| **SNFR-041** | MUST | Suspend-to-RAM (S3) SHALL be supported; resume time ≤ 2 s. |
| **SNFR-042** | SHOULD | Idle power draw with display off ≤ 1.5 W. |

### 3.6 Maintainability / Lifetime
| ID | Priority | Requirement |
|----|----------|-------------|
| **SNFR-050** | MUST | All driver source SHALL comply with `Documentation/process/coding-style.rst` and be `checkpatch.pl` clean. |
| **SNFR-051** | MUST | Each subsystem driver SHALL have a DT binding document in `Documentation/devicetree/bindings/` (YAML schema). |
| **SNFR-052** | SHOULD | The BSP SHALL be maintainable for ≥ 5 years aligned with Linux 6.6 LTS lifecycle (EOL Dec 2026 upstream, extended to 2036 via CIP). |
| **SNFR-053** | MUST | Firmware/waveform blobs SHALL be loaded through `request_firmware()`; no in-tree binary blobs. |

---

## 4. REGULATORY & STANDARDS COMPLIANCE (REG)

| ID | Priority | Standard / Norm |
|----|----------|-----------------|
| **REG-001** | MUST | Linux kernel source SHALL remain GPL-2.0 compliant; user-space LGPL-permissible. |
| **REG-002** | MUST | Yocto meta-layer SHALL pass `yocto-check-layer` and conform to Yocto Project Compatible v2. |
| **REG-003** | MUST | CISPR 32 Class B (EMC emissions) compliance at board level. |
| **REG-004** | MUST | IEC 61000-4-2/-4/-5 (ESD, EFT, surge) per SabreSD reference design. |
| **REG-005** | SHOULD | RoHS 3 (2015/863/EU) & REACH compliance of the reference hardware. |
| **REG-006** | MUST | FCC Part 15 Subpart B (US) and EN 55032 (EU) for marketed derivatives. |
| **REG-007** | SHOULD | Bluetooth/Wi-Fi modules SHALL carry independent SRRC/FCC/CE modular approvals. |
| **REG-008** | MUST | SPDX license tags in every source/DTS file (`SPDX-License-Identifier: GPL-2.0 OR MIT` for DT). |
| **REG-009** | MUST | IEEE 802.3ab (1000BASE-T), IEEE 1588-2008 (PTP) conformance for ENET. |
| **REG-010** | MUST | ISO 11898-1/-2 for CAN physical/data-link layers. |
| **REG-011** | MUST | HDMI 1.4a compliance of Synopsys DW HDMI-TX output (HDMI CTS not mandated for dev board). |
| **REG-012** | SHOULD | USB-IF Certification for OTG where product claims USB logo. |

---

## 5. SYSTEM BOUNDARY & CONTEXT DIAGRAM

```
                 +---------------------------------------------------+
                 |            i.MX6Q SabreSD BSP (System)            |
                 |                                                   |
  HDMI Sink <====|==HDMI-TX  <---- DRM/KMS (dw_hdmi_imx)             |
  DSI Panel <====|==MIPI-DSI <---- DRM (mxsfb / panel-simple)        |
  CSI Camera ===>|==MIPI-CSI ----> V4L2 (ov5640, ipu_csi)            |
                 |                                                   |
  CAN Node <====>|==CAN1/2  <----> SocketCAN (flexcan)               |
  SPI Devs <====>|==eCSPI1-5 <---> spidev / drivers (spi-imx)        |
  I2C Devs <====>|==I2C1-3  <----> PMIC/codec/touch (i2c-imx)        |
  Console  <====>|==UART1   <----> tty/serial (imx_uart)             |
  BT HCI   <====>|==UART3   <----> hci_uart                          |
  USB Dev  <====>|==USB-OTG <----> chipidea (host/gadget)            |
  Ethernet <====>|==ENET    <----> fec_main + AR8031 phy             |
  SD/eMMC  <====>|==uSDHC2-4<----> sdhci-esdhc-imx                   |
  PCIe EP  <====>|==PCIe    <----> pci-imx6                          |
  Expand IO<====>|==I2C->PCA9555 -> gpiolib                          |
  Backlight<====>|==PWM1-4  <----> pwm-imx + pwm-backlight           |
  Analog In===>  |==ADC     ----> IIO                                |
  E-Ink    <====>|==EPDC    <----> fb / drm-epdc                     |
  Speaker  <====>|==SSI/SAI <----> ASoC (fsl_sai + sgtl5000)         |
                 |                                                   |
                 |    Shared: clk_imx6q, regulators (pfuze100),      |
                 |    pinctrl-imx6q, iomuxc, gpio-mxc, dma-sdma      |
                 +--------------------^------------------------------+
                                      |
                              U-Boot + Linux 6.6 LTS
                              Yocto Scarthgap meta-layer
                              arm-linux-gnueabihf toolchain

Legend:  ===>  external signal flow     <--->  bidirectional
         System boundary = dashed rectangle
```

**External Actors:** HDMI display, DSI panel, CSI camera module, CAN bus network, SPI/I²C slaves, USB host or peripherals, Ethernet LAN/PTP grandmaster, SD/eMMC media, PCIe endpoint, backlight LEDs, analog sensors, E-ink film, speakers/mic.

---

## 6. ACCEPTANCE CRITERIA

| SFR | Acceptance Test (System-Level) |
|-----|-------------------------------|
| SFR-001 | Measure `systemd-analyze` boot time ≤ 15 s over 10 trials. |
| SFR-002 | `dtc -I dtb -O dts` dump enumerates every peripheral from §2; no `status = "disabled"`. |
| SFR-003 | `dmesg | grep -E "probe.*-E"` returns zero errors; all drivers bind. |
| SFR-004 | `bitbake core-image-full-cmdline` succeeds clean; image boots to prompt. |
| SFR-010–013 | `cangen can0 -g 1 -I i -L 8` loopback + bitrate sweep + `candump -e` shows no bus-off. |
| SFR-020–023 | `spidev_test` loopback at every mode/speed; DMA path proven via `ftrace`. |
| SFR-030–034 | `i2cdetect -y` lists PMIC/codec/touch/GPIO-expander; bus recovery triggered and verified. |
| SFR-040–043 | `agetty` login on UART1; HCI attach at 3 Mbaud via `hciattach`; earlycon output captured. |
| SFR-050–053 | Host enumerates USB HS mass storage; gadget `g_ether` pings over USB. |
| SFR-060–063 | `iperf3 -c … -t 60` ≥ 900 Mbit/s; `ptp4l` syncs < 1 µs; `ethtool -s wol g` works. |
| SFR-070–074 | `fio` sequential R/W meets thresholds; hot-plug causes udev event. |
| SFR-080–083 | `modetest`, `kmscube`, and `aplay -D plughw:CARD=HDMI` pass. |
| SFR-090–092 | `gst-launch v4l2src ! fakesink` runs 1 h; frame-count ≥ 107 892. |
| SFR-100–102 | Panel initialises; `modetest` shows correct DSI connector. |
| SFR-110–112 | `lspci -vv` lists endpoint with MSI cap; reset script recovers link. |
| SFR-120–121 | `gpioinfo` lists PCA9555 bank; interrupt test toggles and counts match. |
| SFR-130–132 | `pwm_test` sweeps 50 Hz–1 MHz; backlight dims 0–255. |
| SFR-140–141 | IIO channel read vs. calibrated reference ≤ ±2 LSB. |
| SFR-150–151 | EPDC panel refresh via `fb_test` pattern (if EPDC board fitted). |
| SFR-160–162 | `aplay`/`arecord` full-duplex; `xrun` count = 0 after 10 min. |

---

## 7. TRACEABILITY STUB

| SFR-ID | Stakeholder Need | Acceptance Test |
|--------|------------------|-----------------|
| SFR-001 | UC-01 Headless Gateway Boot | AT-001 Boot-time measurement (`systemd-analyze`) |
| SFR-002 | Developer – mainline DT coverage | AT-002 DTB enumeration |
| SFR-003 | Developer – kernel-framework compliance | AT-003 `dmesg` probe audit |
| SFR-004 | Yocto maintainer – layer integration | AT-004 `bitbake` CI build |
| SFR-010..013 | UC-05 Industrial I/O | AT-010 SocketCAN loopback & error-injection |
| SFR-020..023 | UC-05 | AT-020 spidev loopback DMA |
| SFR-030..034 | UC-02, UC-05 | AT-030 i2cdetect + bus-recovery |
| SFR-040..043 | UC-01, UC-04 Field Service | AT-040 Console & BT HCI tests |
| SFR-050..053 | UC-06 Firmware Update | AT-050 USB host/gadget matrix |
| SFR-060..063 | UC-01, UC-05 | AT-060 iperf + PTP + WoL |
| SFR-070..074 | UC-01, UC-04 | AT-070 fio + hot-plug |
| SFR-080..083 | UC-02 HMI | AT-080 DRM/KMS + HDMI audio |
| SFR-090..092 | UC-03 Camera | AT-090 V4L2 1 h capture |
| SFR-100..102 | UC-02 | AT-100 DSI panel bring-up |
| SFR-110..112 | UC-08 PCIe Expansion | AT-110 lspci + MSI + reset |
| SFR-120..121 | UC-05 | AT-120 gpiolib expander test |
| SFR-130..132 | UC-02 | AT-130 PWM backlight sweep |
| SFR-140..141 | UC-05 | AT-140 IIO accuracy |
| SFR-150..151 | UC-07 E-Ink Signage | AT-150 EPDC refresh pattern |
| SFR-160..162 | UC-02 | AT-160 ASoC full-duplex |
| SNFR-001..003 | Performance targets (OEM) | AT-N01 Boot/latency/load benchmarks |
| SNFR-010..013 | QA reliability | AT-N10 72-h stress + kmemleak |
| SNFR-020..021 | QA/Certification | AT-N20 Static-analysis CI gate |
| SNFR-030..032 | Environmental | AT-N30 Chamber + EMC pre-scan |
| SNFR-040..042 | Power | AT-N40 PSU margin + S3 resume |
| SNFR-050..053 | Maintainer lifetime | AT-N50 checkpatch + YAML bindings |
| REG-001..012 | Regulatory / Compliance | AT-R01…R12 Document & test evidence |

---

**End of SRS-IMX6Q-BSP-001 v1.0**
*Next stage (V-Model): System Architecture Specification (SAS) deriving HW/SW partitioning, kernel module decomposition, and DT hierarchy from this SRS.*