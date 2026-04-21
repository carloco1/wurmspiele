# SYSTEM ARCHITECTURE SPECIFICATION
## NXP i.MX6 Quad SabreSD — Linux BSP Driver Package

**Document ID:** SAD-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 2 (System Architecture / HW-SW Split)
**Pairs with:** Stage 13 — HW/SW Integration Tests
**Traces upward to:** SRS-IMX6Q-BSP-001 v1.0

---

## 1. SYSTEM ARCHITECTURE OVERVIEW

### 1.1 Context

This architecture is unusual in that most of the "hardware" is fixed (the MCIMX6Q-SDB reference board) and the design effort is concentrated on the **software stack** — Linux kernel drivers, device tree, and Yocto integration. The HW/SW split is therefore framed as:

- **HW (immutable):** SoC IP blocks and board-level peripherals on the SabreSD reference design.
- **SW (deliverable):** BSP layer — boot firmware, DTS, kernel drivers, user-space glue, meta-layer.

### 1.2 Top-Level Block Diagram

```
                  ┌─────────────────────────────────────────────────────────────────┐
                  │                     USER-SPACE APPLICATIONS                     │
                  │  GStreamer | BlueZ | wpa_supplicant | SocketCAN apps |          │
                  │  Weston/Wayland | fastboot | systemd | iio-utils               │
                  └──────────────────────────────┬──────────────────────────────────┘
                                                 │ syscalls / libc / libdrm / V4L2
                  ╔══════════════════════════════╪══════════════════════════════════╗
                  ║                    LINUX 6.6 LTS KERNEL (SMP, 4 cores)          ║
                  ║  ┌──────────┬──────────┬──────────┬──────────┬──────────────┐   ║
                  ║  │  DRM/KMS │   V4L2   │  ALSA/   │  Net/    │ Input/evdev  │   ║
                  ║  │ (imx-drm)│ (imx6-  │  SoC     │ SocketCAN│  (touch)     │   ║
                  ║  │  HDMI/   │  mipi-  │ (SGTL5000│ (FlexCAN)│              │   ║
                  ║  │  DSI/    │  csi)   │  + SAI)  │ (FEC-GbE)│              │   ║
                  ║  │  EPDC)   │         │          │          │              │   ║
                  ║  ├──────────┴──────────┴──────────┴──────────┴──────────────┤   ║
                  ║  │  SUBSYSTEM FRAMEWORKS                                    │   ║
                  ║  │  pinctrl | clk | regulator | PM/runtime-PM | dma-engine  │   ║
                  ║  │  regmap  | IIO | MMC/SDIO | USB | PCIe | tty/serial      │   ║
                  ║  ├──────────────────────────────────────────────────────────┤   ║
                  ║  │  BSP DRIVER PACKAGE (this deliverable)                   │   ║
                  ║  │  flexcan | ecspi | i2c-imx | imx-uart | fec | usdhc      │   ║
                  ║  │  ci_hdrc | pci-imx6 | imx-sdma | imx-pwm | imx-wdog      │   ║
                  ║  │  mipi-csi | ipu-drm | hdmi-tx | epdc | sgtl5000 | ...    │   ║
                  ║  ├──────────────────────────────────────────────────────────┤   ║
                  ║  │  Device Tree (imx6q-sabresd.dts + *.dtsi)                │   ║
                  ║  └──────────────────────────────────────────────────────────┘   ║
                  ╚══════════════════════════════╪══════════════════════════════════╝
                                                 │ OF / platform_bus
     ┌─────────────────────────────────────┐     │
     │       U-Boot (SPL + proper)         │─────┘  (hand-off: DT blob, initramfs)
     └─────────────────────────────────────┘
                                                 │
╔════════════════════════════════════════════════╧════════════════════════════════════╗
║                    i.MX6 QUAD SoC  (4× Cortex-A9 @ 1.0 GHz, NEON, VFPv3)            ║
║  ┌────────────┬───────────────────────────┬─────────────────────────────────────┐   ║
║  │  CPU/NEON  │  Multimedia Accelerators  │      Connectivity / I/O IP          │   ║
║  │  L1/L2$    │  IPU1/IPU2 | VPU | GPU3D  │  FEC(GbE MAC) | USB OTG×2 | PCIe    │   ║
║  │  GIC-390   │  EPDC | HDMI-TX (Synopsys)│  FlexCAN×2 | eCSPI×5 | I²C×3        │   ║
║  │  SCU       │  MIPI-CSI | MIPI-DSI      │  UART×5 | SAI/SSI×3 | ESAI          │   ║
║  │  SDMA      │  eLCDIF                   │  uSDHC×4 | GPT | EPIT | PWM×4       │   ║
║  │  OCRAM     │                           │  SNVS | WDOG×2 | IOMUXC | CCM       │   ║
║  └────────────┴───────────────────────────┴─────────────────────────────────────┘   ║
║                                     │ AXI / AHB                                     ║
║                           ┌─────────┴──────────┐                                    ║
║                           │  DDR3 Controller   │──→  2 GiB DDR3 @ 0x10000000       ║
║                           └────────────────────┘                                    ║
╚═════════════════════════════════════════════════════════════════════════════════════╝
                                                 │
╔════════════════════════════════════════════════╧════════════════════════════════════╗
║                           SABRE-SD BOARD PERIPHERALS                                ║
║                                                                                      ║
║  Storage:   eMMC (uSDHC4) | µSD (uSDHC2/3) | SPI-NOR (eCSPI1)                       ║
║  Display:   HDMI Tx | MIPI-DSI header | LVDS | EPDC header                          ║
║  Camera:    MIPI-CSI sensor (OV5640)                                                ║
║  Audio:     SGTL5000 codec (I²C ctrl + SAI/SSI data) | 3.5 mm jack | DMIC           ║
║  Input:     Capacitive touch (I²C) | GPIO buttons                                   ║
║  Connect:   RGMII → AR8031 PHY → RJ-45 | USB OTG + Host | PCIe Mini-card            ║
║             Wi-Fi/BT combo (SDIO + UART H4) | FlexCAN transceivers TJA1041          ║
║  Sensors:   MMA8451 accel (I²C) | ADC inputs | board thermal                        ║
║  Power:     PF0100 PMIC (I²C) | Li-ion charger | 5 V barrel jack                    ║
║  Debug:     UART1 @ J500 (console) | JTAG 20-pin | 7-seg LEDs                       ║
╚═════════════════════════════════════════════════════════════════════════════════════╝
```

### 1.3 Hardware Subsystems & Responsibilities

| HW Subsystem | Responsibility |
|--------------|---------------|
| **i.MX6Q SoC** | Compute (4× Cortex-A9), DMA, IP controllers for all peripherals |
| **DDR3 / eMMC / SPI-NOR** | Volatile RAM, primary boot + root filesystem, redundant boot |
| **Clock / PLL tree (CCM)** | System, peripheral, and multimedia clock generation |
| **IOMUXC** | Pin-multiplexing, pad drive strength, pull configuration |
| **PMIC PF0100** | Regulated rails, power sequencing, supervisor |
| **AR8031 PHY** | 1000BASE-T PHY — MII management via FEC MDIO |
| **TJA1041 CAN transceivers** | Physical CAN bus interface |
| **SGTL5000** | Audio ADC/DAC, headphone amp |
| **Display stack (HDMI/DSI/LVDS/EPDC PHYs)** | Video signal egress |
| **MIPI-CSI sensor (OV5640)** | Image capture |
| **Watchdog (WDOG1)** | System-level reset on SW hang |
| **SNVS / RTC** | Secure non-volatile storage, wall-clock time |

### 1.4 Software Subsystems & Responsibilities

| SW Subsystem | Responsibility |
|--------------|---------------|
| **U-Boot (SPL + U-Boot proper)** | DDR init, boot media select, FIT image load, DT hand-off, fastboot recovery |
| **Device Tree (DTS/DTSI)** | Declarative description of HW; binds drivers to nodes |
| **Platform/Core drivers** | clk-imx6q, imx-pinctrl, imx-gpc, imx-sdma |
| **Storage drivers** | sdhci-esdhc-imx, spi-nor, mmc-core glue |
| **Connectivity drivers** | fec_main (GbE), flexcan, ci_hdrc_imx (USB), pci-imx6 |
| **Serial / Bus drivers** | imx-uart, spi-imx, i2c-imx |
| **Multimedia drivers** | imx-drm (IPU+HDMI+DSI+LVDS+EPDC), imx6-mipi-csi, imx-sdma, ASoC machine drv + SGTL5000 |
| **Input / IIO** | edt-ft5x06 touch, mma8451 accel, imx-adc |
| **Power management** | imx6q-cpufreq, runtime-PM hooks, suspend-to-RAM |
| **Yocto meta-layer** | `meta-imx6q-sabresd` recipes, SDK, image generation |
| **User-space enablement** | BlueZ, wpa_supplicant, SocketCAN tools, GStreamer plugins, libdrm |

---

## 2. HW/SW ALLOCATION TABLE

| SFR-ID | Function | Realised by HW | Realised by SW | Shared |
|--------|----------|:--:|:--:|:--:|
| SFR-001 | Boot < 15 s | eMMC/uSDHC, ROM boot | U-Boot, kernel, initramfs tuning | ✔ |
| SFR-002 | Complete DT | — | `imx6q-sabresd.dts` + `imx6q.dtsi` | |
| SFR-003 | Platform/OF drivers, pinctrl/clk/regulator | IOMUXC, CCM, PMIC | Driver code | ✔ |
| SFR-004 | Yocto integration | — | `meta-imx6q-sabresd` | |
| SFR-005 | Runtime PM | Clock gates, power domains (GPC) | PM ops in each driver | ✔ |
| SFR-010 | CAN SocketCAN `can0/1` | FlexCAN IP + TJA1041 PHY | `flexcan.ko` + DT | ✔ |
| SFR-011 | CAN bitrate 10 k–1 M | FlexCAN bit-timing regs | Netlink config, CAN-clk calc | ✔ |
| SFR-012 | TX latency < 500 µs @ 1 Mbit | FlexCAN MB, GIC | IRQ-threaded driver, RT tuning | ✔ |
| SFR-013 | CAN error reporting | FlexCAN ESR bits | netlink/CAN state machine | ✔ |
| SFR-02x | eCSPI spidev | eCSPI IP, SDMA | `spi-imx.c`, `spidev` | ✔ |
| SFR-03x | I²C devices | I²C IP + pull-ups | `i2c-imx.c` + client drivers | ✔ |
| SFR-04x | UART / console | UART IP, level shifter | `imx-uart.c`, tty | ✔ |
| SFR-05x | GbE 1000BASE-T | FEC MAC + AR8031 PHY | `fec_main.c`, PHY lib | ✔ |
| SFR-06x | USB OTG + host | USB PHY + ULPI | `ci_hdrc_imx.c`, gadget fastboot | ✔ |
| SFR-07x | SD/eMMC/SDIO | uSDHC controllers | `sdhci-esdhc-imx.c` | ✔ |
| SFR-08x | DRM display (HDMI/DSI/LVDS) | IPU + HDMI-Tx + MIPI-DSI PHY | `imx-drm`, `dw-hdmi`, `mxsfb` | ✔ |
| SFR-09x | V4L2 camera 1080p30 | MIPI-CSI PHY, IPU CSI, OV5640 | `imx6-mipi-csi`, `imx-media`, sensor drv | ✔ |
| SFR-10x | Audio playback | SGTL5000, SAI/SSI, DMA | ASoC machine + codec drv | ✔ |
| SFR-11x | Touch input | FT5x06 I²C controller | `edt-ft5x06` | ✔ |
| SFR-12x | PWM backlight/fan | PWM IP | `pwm-imx27`, `pwm-backlight` | ✔ |
| SFR-13x | IIO ADC | on-chip ADC | `imx-adc` | ✔ |
| SFR-14x | PCIe Mini-card + MSI | PCIe RC, REFCLK | `pci-imx6.c`, MSI ctrl | ✔ |
| SFR-15x | EPDC E-ink | EPDC IP, panel | `mxc_epdc_fb` / `epdc-drm` | ✔ |
| SFR-16x | Watchdog | WDOG1 | `imx2_wdt`, systemd-watchdog | ✔ |
| SFR-17x | Firmware update | USB-OTG, SD-boot pin-straps | U-Boot fastboot, A/B recipes | ✔ |

*(Allocation follows the requirement block structure implied by §2.2–2.16 of the SRS; row count reflects nominal SRS content.)*

---

## 3. HARDWARE ARCHITECTURE

### 3.1 SoC Selection — i.MX6 Quad (MCIMX6Q5EYM12AD)

**Justification (fixed by SRS target platform):**

| Attribute | Spec | Relevance |
|-----------|------|-----------|
| Cores | 4× Cortex-A9 @ 1.0 GHz, NEON, VFPv3-D16 HF | SMP Linux, GStreamer/NEON |
| Cache | 32 KB L1 I/D each core, 1 MB shared L2 (PL310) | Throughput-oriented workloads |
| Memory ctrl | 64-bit DDR3/LPDDR2 up to 533 MHz | Board populated with 2 GiB DDR3 |
| Multimedia | IPU1+IPU2, VPU (H.264 1080p60), GPU3D (Vivante GC2000) | UC-02, UC-03, UC-07 |
| Display | HDMI-Tx, MIPI-DSI, LVDS, EPDC, eLCDIF | UC-02, UC-07 |
| Camera | MIPI-CSI-2 + parallel CSI via IPU | UC-03 |
| Connectivity | GbE (FEC+RGMII), USB OTG×2, PCIe Gen2 ×1, FlexCAN×2, SDIO×4 | UC-01, UC-04, UC-08 |
| Low-speed I/O | eCSPI×5, I²C×3, UART×5, PWM×4, ADC, GPIO×7 banks | UC-05 |
| Security | CAAM, SNVS, TrustZone, HAB | Future secure-boot extension |
| Toolchain | arm-linux-gnueabihf (GCC 13+) | SRS §preamble |

Selection is mandated by the SRS (`MCIMX6Q-SDB`); no trade-off is open at the SoC level.

### 3.2 External Components (board inventory honoured by BSP)

| Component | IF to SoC | Used by UC |
|-----------|-----------|-----------|
| Micron eMMC 4/8 GiB | uSDHC4 (HS200) | UC-01, UC-06 |
| µSD slot | uSDHC2 | UC-01, UC-06 |
| SPI-NOR (recovery/config) | eCSPI1 CS0 | UC-05 |
| AR8031 GbE PHY | RGMII + MDIO (FEC) | UC-01 |
| TJA1041 CAN transceivers ×2 | FlexCAN1/2 | UC-05 |
| SGTL5000 audio codec | I²C1 (ctrl) + SAI2/SSI2 (I²S) | UC-02 |
| FT5x06 capacitive touch | I²C2 + GPIO IRQ | UC-02 |
| MMA8451Q accelerometer | I²C1 | UC-05 |
| OV5640 MIPI-CSI sensor | MIPI-CSI2 + I²C2 | UC-03 |
| PF0100 PMIC | I²C2 + ONOFF | All |
| BCM Wi-Fi/BT combo | uSDHC3 + UART3 (H4) | UC-04 |
| PCIe Mini-card slot | PCIe RC + 100 MHz refclk | UC-08 |
| USB OTG Micro-B + USB-A host | USB-OTG1/2 + HSIC | UC-06 |
| HDMI Tx connector | HDMI-Tx (Synopsys DWC) | UC-02 |
| MIPI-DSI / LVDS / EPDC headers | DSI / LVDS / EPDC | UC-02, UC-07 |
| WDOG external reset | WDOG_B → PMIC | Safety |

### 3.3 Power Supply Design Summary

Fully defined on SabreSD reference board; BSP responsibility is only correct modelling:

- Input: 5 V DC jack or Li-ion battery (charger managed by PMIC).
- PF0100 PMIC provides: SW1ABC (VDD_ARM_CORE), SW2 (VDD_SOC), SW3AB (DDR3 1.5 V), SW4 (3.0 V IO), SWBST (5 V boost), VGEN1/2/3/4/5/6 (auxiliary rails — PHY, codec, sensor).
- Regulators modelled in DT under `pmic@8` with `regulator-name`, `regulator-min/max-microvolt`, `regulator-always-on` flags.
- Runtime-PM (SFR-005) permits gating non-critical rails via `regulator_enable/disable`.

### 3.4 PCB Partitioning Notes (BSP perspective)

The BSP must respect SabreSD's existing partitioning:

- **Noise-sensitive analog:** audio codec and ADC grouped; DTS marks `vdda-supply` rails `regulator-always-on` where the board ties AVDD to a clean rail.
- **High-speed differential:** RGMII, HDMI-Tx, MIPI-CSI/DSI, PCIe, USB — BSP sets only pinctrl drive strength per IOMUXC pad config (no re-layout possible).
- **Boot media pin-straps:** BOOT_MODE + BOOT_CFG[4:0] selects eMMC/SD/USB — observed by U-Boot, documented in `board-info.txt`.

---

## 4. SOFTWARE SUBSYSTEMS

### 4.1 Subsystem Catalogue

| # | Subsystem | Kernel Path / Recipe | Responsibility |
|---|-----------|----------------------|----------------|
| S01 | **Boot firmware** | `meta-imx6q-sabresd/recipes-bsp/u-boot` | SPL DDR calibration, FIT image, env, fastboot, altboot |
| S02 | **Device Tree** | `arch/arm/boot/dts/imx6q-sabresd.dts` | HW description for driver bind |
| S03 | **Core platform** | `drivers/clk/imx/clk-imx6q.c`, `drivers/pinctrl/freescale/*`, `drivers/soc/imx/gpc*` | Clock tree, pinmux, power domains |
| S04 | **DMA** | `drivers/dma/imx-sdma.c` | SDMA scripts, APBH-DMA |
| S05 | **Storage** | `drivers/mmc/host/sdhci-esdhc-imx.c`, `drivers/mtd/spi-nor/*` | eMMC/SD/SDIO, SPI-NOR |
| S06 | **Networking** | `drivers/net/ethernet/freescale/fec_*`, `drivers/net/phy/at803x.c` | GbE, MDIO, AVB-ready |
| S07 | **CAN** | `drivers/net/can/flexcan.c` | SocketCAN, netlink, error FSM |
| S08 | **SPI** | `drivers/spi/spi-imx.c` | spidev, flash, DMA-backed |
| S09 | **I²C** | `drivers/i2c/busses/i2c-imx.c` + client drivers | Codec/touch/sensor/PMIC |
| S10 | **UART / Serial** | `drivers/tty/serial/imx.c` | Console, Bluetooth HCI, RS-485 |
| S11 | **USB** | `drivers/usb/chipidea/ci_hdrc_imx.c` + gadget FFS/fastboot | Host + OTG device |
| S12 | **PCIe** | `drivers/pci/controller/dwc/pci-imx6.c` | RC mode, MSI, L1 ASPM |
| S13 | **Display / DRM** | `drivers/gpu/drm/imx/*`, `drivers/gpu/drm/bridge/synopsys/dw-hdmi*` | KMS pipelines IPU→HDMI/DSI/LVDS |
| S14 | **EPDC** | `drivers/gpu/drm/mxsfb/*` or `mxc_epdc_fb` | E-ink (UC-07) |
| S15 | **V4L2 camera** | `drivers/staging/media/imx/*`, `ov5640.c` | MIPI-CSI capture pipeline |
| S16 | **Audio (ASoC)** | `sound/soc/fsl/fsl_sai.c`, `sound/soc/codecs/sgtl5000.c`, machine drv | Playback/capture |
| S17 | **Input** | `drivers/input/touchscreen/edt-ft5x06.c` + keys | evdev |
| S18 | **IIO** | `drivers/iio/adc/*imx*`, `drivers/iio/accel/mma8452.c` | ADC + motion |
| S19 | **PWM / Backlight** | `drivers/pwm/pwm-imx27.c`, `drivers/video/backlight/pwm_bl.c` | Backlight, fan |
| S20 | **Watchdog** | `drivers/watchdog/imx2_wdt.c` | HW WDT + systemd hook |
| S21 | **Power mgmt** | `drivers/cpufreq/imx6q-cpufreq.c`, suspend handlers | DVFS, suspend-to-RAM |
| S22 | **Yocto meta-layer** | `meta-imx6q-sabresd` | Recipes, images, SDK |
| S23 | **User-space enablement** | BlueZ, wpa_supplicant, GStreamer plugins, can-utils, iio-utils | Integration tests |

### 4.2 Inter-Subsystem Dependency Graph

```
                        ┌──────────────────┐
                        │  S01 U-Boot/SPL  │
                        └─────────┬────────┘
                                  │ hands off
                                  ▼
                        ┌──────────────────┐
                        │  S02 Device Tree │◀─────── consumed by all drivers
                        └─────────┬────────┘
                                  ▼
          ┌─────────────── S03 clk / pinctrl / GPC ───────────────┐
          │                       │                                │
          ▼                       ▼                                ▼
     ┌────────┐              ┌─────────┐                      ┌─────────┐
     │ S04    │              │ S21 PM  │                      │ S20 WDT │
     │ SDMA   │◀─────┐       │ cpufreq │                      └─────────┘
     └───┬────┘      │       └─────────┘
         │           │
  ┌──────┼───────────┼──────────────────────────────────────────────────┐
  ▼      ▼           ▼                                                  ▼
┌────┐ ┌────┐ ┌───────────┐  ┌────┐ ┌─────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌───────┐
│S05 │ │S08 │ │  S09 I²C  │  │S07 │ │ S06 │ │ S10  │ │ S11  │ │ S12  │ │  S13  │
│MMC │ │SPI │ │           │  │CAN │ │ FEC │ │ UART │ │ USB  │ │ PCIe │ │ DRM   │
└────┘ └────┘ └─────┬─────┘  └────┘ └─────┘ └──┬───┘ └──────┘ └──────┘ └───┬───┘
                    │                          │                            │
           ┌────────┼────────┬──────────┐      │                    ┌───────┴────┐
           ▼        ▼        ▼          ▼      ▼                    ▼            ▼
       ┌──────┐ ┌──────┐ ┌──────┐  ┌────────┐┌────────┐       ┌────────┐  ┌────────┐
       │S16   │ │ S17  │ │ S18  │  │PMIC    ││BT HCI  │       │S14 EPDC│  │S15 CSI │
       │Audio │ │Touch │ │Sensor│  │regulatr││(BlueZ) │       └────────┘  └────────┘
       │SGTL  │ │FT5x06│ │MMA84 │  │        │└────────┘
       └───┬──┘ └──────┘ └──────┘  └────────┘
           │
           └─ depends on S04 SDMA (audio DMA path)

        ┌────────────────── S22 Yocto meta-layer ──────────────────┐
        │ packages & deploys:  U-Boot, kernel+DT, rootfs, SDK,      │
        │                      S23 user-space stacks                │
        └────────────────────────────────────────────────────────────┘
```

Key hard dependencies:
- Every peripheral driver → **S03 (clk + pinctrl)** and **S02 (DT)**.
- **S07 CAN, S16 Audio, S08 SPI, S05 MMC** may use **S04 SDMA** for high-throughput transfers.
- **S13 DRM** depends on **S03 (IPU clocks)** and, for bridges, on **S09 I²C** (HDMI DDC, DSI panels).
- **S15 V4L2** depends on **S09** (sensor control) + **S03** (CSI clocks).
- **S11 USB gadget (fastboot)** depends on **S01** env cooperation.

---

## 5. COMMUNICATION ARCHITECTURE

### 5.1 Internal Buses (on-board / on-chip)

| Bus | Instance | Clients | Notes |
|-----|----------|---------|-------|
| **I²C1** | 100 kHz std | PMIC PF0100, MMA8451 | Always-on, regulator DT |
| **I²C2** | 400 kHz fast | FT5x06 touch, OV5640 | Touch IRQ via GPIO |
| **I²C3** | 400 kHz fast | SGTL5000, HDMI DDC | Shared with display EDID |
| **eCSPI1** | ≤ 20 MHz | SPI-NOR, spidev | DMA via SDMA |
| **eCSPI2–5** | configurable | spidev (headers) | User extension |
| **SAI2 / SSI2** | I²S | SGTL5000 | 48 kHz / 16-bit default |
| **RGMII** | 1 Gbit | AR8031 PHY | MDIO at address 0x0 |
| **MIPI-CSI-2** | 2-lane | OV5640 | 1080p30 budget |
| **MIPI-DSI** | 4-lane | Optional DSI panel | |
| **LVDS** | 2× single/dual link | Optional panel | |
| **HDMI-Tx** | Synopsys DWC | HDMI connector | HPD GPIO, CEC optional |
| **uSDHC2/3/4** | HS/HS200/SDIO | µSD, Wi-Fi, eMMC | 1.8 V signalling for eMMC |
| **USB OTG1/2** | HS 480 Mbit | Micro-B, Host-A | ULPI/UTMI |
| **PCIe Gen2 ×1** | 5 GT/s | Mini-card | MSI, refclk from SoC |
| **UART1** | 115 200 8N1 | Console | Fixed |
| **UART3** | up to 4 Mbit | Bluetooth HCI (H4) | RTS/CTS flow control |
| **FlexCAN1/2** | 10 k–1 Mbit | TJA1041 transceivers | SocketCAN |
| **PWM1/2** | variable | Backlight / fan | `pwm_bl` |

### 5.2 External Interfaces

| Interface | Physical | Protocol | Stack |
|-----------|----------|----------|-------|
| Ethernet | RJ-45 | 10/100/1000BASE-T | Linux net stack |
| USB-OTG1 | Micro-AB | USB 2.0 device (fastboot) / host | ChipIdea + libcomposite |
| USB Host | Type-A | USB 2.0 host | XHCI/EHCI equiv |
| CAN1/2 | DB-9 / header | ISO 11898-2 | SocketCAN |
| HDMI | Type-A | HDMI 1.4 | KMS + ALSA (HDMI audio) |
| MIPI-CSI connector | FPC | CSI-2 | V4L2 |
| Wi-Fi / BT | PCB antenna | 802.11 + BT 4.x | wpa_supplicant + BlueZ |
| PCIe Mini | slot | PCIe Gen2 | Linux PCI |
| µSD / eMMC | slot / soldered | SD 3.0 / eMMC 5.0 | MMC subsystem |
| JTAG | 20-pin ARM | JTAG/SWD | OpenOCD / J-Link |

### 5.3 Protocol Selection Justification

| Choice | Rationale |
|--------|-----------|
| **SocketCAN over FlexCAN** | Upstream, netlink config (satisfies SFR-011/013); portable APIs |
| **HCI-H4 over UART3** | Standard Linux BlueZ path; avoids proprietary 3-wire H5; CTS/RTS prevents overrun at 3 Mbit |
| **RGMII (not MII/RMII)** | Only mode giving 1000BASE-T throughput required by SFR/UC-01 |
| **SDIO for Wi-Fi** | mmc_core `sdio_func` allows vendor driver abstraction |
| **MIPI-CSI over parallel CSI** | Lower EMI, higher throughput for 1080p30 (UC-03, SFR-09x) |
| **fastboot for recovery** | De-facto Android standard; U-Boot supports; no custom tooling |
| **Upstream mainline drivers** | Meets "mainline-compatible BSP" stakeholder need; avoids vendor fork |

---

## 6. SAFETY ARCHITECTURE

This is a commercial BSP (not ISO 26262 / 61508 certified), but defensive measures apply.

### 6.1 Hardware Safety Measures

| Mechanism | Source | Coverage |
|-----------|--------|---------|
| **WDOG1 watchdog** | SoC | SW hang detection → board reset via PMIC `WDOG_B` |
| **PMIC voltage supervisor** | PF0100 | Rail UV/OV, POR generation |
| **ECC on DDR3** | Optional (board dependent) | Single-bit correct / double-bit detect |
| **Thermal monitor** | Anatop TEMPMON | OS trips at 95 °C, CRIT at 105 °C |
| **CAAM crypto + secure boot (HAB)** | SoC | Integrity of boot image (opt-in) |
| **SNVS tamper/RTC** | SoC | Secure time, tamper GPIO |
| **IOMUXC keeper/pull** | SoC pads | Known state on undriven nets |
| **Redundant boot source** | BOOT_MODE pins → eMMC + SD fallback | Recoverability (UC-06) |

### 6.2 Software Safety Mechanisms

| Mechanism | Description | SFR link |
|-----------|-------------|----------|
| **Kernel MMU** | Process isolation, driver addresses protected | Baseline |
| **IOMMU / ARM SMMU stubs** | Not available on i.MX6 → mitigated via kernel-only DMA buffers (`dma_alloc_coherent`) and bounce buffering | — |
| **Driver state machines** | Bounded loops in ISRs; no recursion; `dev_err` + `return -EIO` on timeout | SFR-012 |
| **IRQ threading** | FlexCAN, CSI use threaded handlers to cap ISR jitter | SFR-012 |
| **Watchdog userspace daemon** | `systemd-watchdog` pets WDOG1 every 10 s, margin 30 s | Liveness |
| **Kernel lockdep / KASAN builds** | Enabled in debug DT variant | QA |
| **Diversified boot paths** | U-Boot altboot counter → fallback image after 3 failed boots | UC-06 |
| **Regulator sequencing** | DT `regulator-always-on` / `regulator-boot-on` prevents brown-out | SFR-005 |
| **DT overlays validation** | Signed FIT images (optional HAB) | Supply chain |
| **MISRA-style guidelines** for any out-of-tree driver: volatile for MMIO, bounded loops, no dynamic alloc in ISR context | §C RULES | |

### 6.3 Diagnostic Coverage Estimate

| Fault class | DC estimate | Mechanism |
|-------------|-------------|----------|
| RAM permanent | ~60 % | Boot memtest (optional), ECC if fitted |
| RAM transient | ~60 % | ECC if fitted; else none |
| CPU stuck / deadlock | > 90 % | WDOG1 + systemd watchdog |
| Clock loss | ~80 % | PLL lock detect + WDOG |
| Power rail UV/OV | > 95 % | PMIC supervisor |
| Peripheral hang | ~70 % | Per-driver timeouts → netlink/sysfs error, reset via PM domain |
| FW image corruption | > 99 % | FIT hash + HAB signature (opt-in) |
| Bus error (CAN/I²C/SPI) | ≈ 85 % | Controller error regs surfaced via netlink / dev_err |

**Aggregate SW-layer DC:** ~70 % (acceptable for non-safety BSP; upgradeable via opt-in HAB, ECC, and lockstep-class add-on).

---

## 7. DESIGN DECISIONS & RATIONALE

| # | Decision | Alternatives considered | Rationale |
|---|----------|------------------------|-----------|
| D-01 | **Mainline Linux 6.6 LTS**, minimal out-of-tree patches | NXP vendor kernel (5.15-lts + `meta-fsl-bsp-release`) | Stakeholder need "mainline-quality"; maintainability; upstream traceability |
| D-02 | **Yocto Scarthgap (5.0)** | Buildroot | Commercial-grade layer model, SDK generation, reproducible; SRS §preamble pins this |
| D-03 | **DTS lives in tree (`arch/arm/boot/dts/`)**, meta-layer only patches | Out-of-tree DT | Upstream-ready (SFR-002, stakeholder req) |
| D-04 | **SocketCAN** for CAN | Vendor ioctl API | Netlink configurability (SFR-011), portability, satisfies UC-05 |
| D-05 | **Threaded IRQs** for latency-critical paths (CAN, CSI) | Traditional top/bottom-half | Deterministic hand-off; PREEMPT-RT compatible |
| D-06 | **SDMA** for SPI/Audio/MMC high-throughput paths | CPU polling / PIO | CPU offload; meets 1080p30 (SFR-09x) and < 500 µs CAN latency (SFR-012) |
| D-07 | **ChipIdea + libcomposite fastboot** for UC-06 | Custom USB stack | Reuses upstream gadget framework |
| D-08 | **`imx-drm` (IPU-based) + `dw-hdmi` bridge** | Vendor MXC FB | DRM/KMS is mandated direction upstream; required by Weston/Wayland |
| D-09 | **EPDC via DRM (where supported) else mxc_epdc_fb** | Out-of-tree only | Variant flexibility (UC-07 optional) |
| D-10 | **PCIe RC mode default** | EP mode | UC-08 uses expansion cards; EP mode reserved for future variant |
| D-11 | **U-Boot FIT images** with multiple DTBs | Legacy uImage + separate DTB | Supports variants (SabreSD vs optional EPDC baseboard) |
| D-12 | **Runtime-PM opt-in per driver** | Aggressive always-on | Balances SFR-005 with stability; DT `regulator-always-on` where needed |
| D-13 | **Hard-float ABI (`arm-linux-gnueabihf`)** | soft-float | Performance; NEON/VFPv3-D16 available on all four cores |
| D-14 | **systemd init** | sysvinit / OpenRC | Parallel service start → 15 s boot budget (SFR-001) |
| D-15 | **meta-layer split** (`meta-imx6q-sabresd` depends on `meta-freescale`) | All-in-one | Reuse NXP board-support recipes for shared components |

---

## 8. REQUIREMENTS TRACEABILITY

| Architectural Element | SFR / UC IDs covered |
|-----------------------|---------------------|
| **S01 U-Boot / boot firmware** | SFR-001, SFR-004, UC-01, UC-06 |
| **S02 Device Tree (`imx6q-sabresd.dts`)** | SFR-002, SFR-003 (bind foundation) |
| **S03 clk / pinctrl / GPC** | SFR-003, SFR-005 |
| **S04 SDMA** | SFR-012 (CAN latency), SFR-09x (1080p30), SFR-08x |
| **S05 Storage (sdhci / spi-nor)** | SFR-001, SFR-07x, UC-01, UC-06 |
| **S06 FEC GbE** | SFR-05x, UC-01 |
| **S07 FlexCAN** | SFR-010, SFR-011, SFR-012, SFR-013, UC-05 |
| **S08 SPI** | SFR-02x (eCSPI), UC-01 |
| **S09 I²C** | SFR-03x, UC-02, UC-03, UC-05 |
| **S10 UART** | SFR-04x, UC-04 (Bluetooth HCI) |
| **S11 USB** | SFR-06x, UC-06 (fastboot) |
| **S12 PCIe** | SFR-14x, UC-08 |
| **S13 DRM (HDMI/DSI/LVDS)** | SFR-08x, UC-02 |
| **S14 EPDC** | SFR-15x, UC-07 |
| **S15 V4L2 MIPI-CSI** | SFR-09x, UC-03 |
| **S16 ASoC + SGTL5000** | SFR-10x, UC-02 |
| **S17 Input (touch, keys)** | SFR-11x, UC-02 |
| **S18 IIO (ADC, accel)** | SFR-13x, UC-05 |
| **S19 PWM / backlight** | SFR-12x, UC-02, UC-05 |
| **S20 Watchdog** | SFR-16x, Safety §6 |
| **S21 PM / cpufreq** | SFR-005 |
| **S22 Yocto meta-layer** | SFR-004 |
| **S23 User-space enablement** | UC-01..UC-08 (integration) |
| **HW: PF0100 PMIC** | SFR-005, all power-related SFRs |
| **HW: AR8031 PHY** | SFR-05x |
| **HW: TJA1041 transceivers** | SFR-010..013 |
| **HW: WDOG1 + PMIC WDOG_B** | SFR-16x, §6 |
| **HW: Secure boot (HAB/CAAM)** | UC-06 (optional), §6 |

---

### Forward-Linkage to V-Model Stage 13 (HW/SW Integration Tests)

Each "Shared" row in §2 shall generate at least one **integration test case** in Stage 13, e.g.:

- `IT-CAN-001` — FlexCAN1 TX latency < 500 µs measured with scope + `candump` timestamping (verifies SFR-012, covers S07 + HW).
- `IT-BOOT-001` — Cold boot eMMC → `systemd-analyze` < 15 s (SFR-001, S01+S02+S05+S22).
- `IT-CAM-001` — `gst-launch` 1080p30 from OV5640, zero dropped frames over 60 s (SFR-09x, S15+S04+S09+S13).
- `IT-WDT-001` — Inject kernel hang via `sysrq`, verify board resets within 30 s (S20).

A dedicated **Integration Test Plan** document (ITP-IMX6Q-BSP-001) will be raised at Stage 13 with full IT→SFR traceability closing the V.