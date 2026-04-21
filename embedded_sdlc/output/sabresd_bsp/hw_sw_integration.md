# HW/SW INTEGRATION TEST SPECIFICATION
## NXP i.MX6 Quad SabreSD — Linux BSP Driver Package

**Document ID:** HSIT-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 13 (HW/SW Integration Testing)
**Pairs with:** HSI-IMX6Q-BSP-001 v1.0
**Traces upward to:** SwQT-IMX6Q-BSP-001, SRS-IMX6Q-BSP-001, SAD-IMX6Q-BSP-001
**Target Board:** MCIMX6Q-SDB (SabreSD), rev. C silkscreen
**Host OS:** Ubuntu 22.04 LTS, Python 3.10, pytest 7.x, labgrid 23.0
**Test Framework:** labgrid + pyvisa + sigrok-cli

---

## 0. DOCUMENT CONVENTIONS

- Each HIT test has a unique ID `HIT-nnn` and maps to exactly one HSI entry (register, pin, interrupt, DMA channel, clock, or power rail).
- Pass/Fail is expressed as a boolean predicate on a **measurement** (never on software self-report alone — the instrument is the oracle).
- All oscilloscope captures are archived under `/var/lib/hsit/captures/HIT-nnn/<run-id>.wfm`.
- All probe points refer to SabreSD schematic **SPF-27392_C**.
- "JTAG" means ARM 20-pin cTI header **J801**; "Console UART" means **J509** (UART1, 115 200 8N1).

---

## 1. HW/SW INTEGRATION TEST STRATEGY

### 1.1 Objectives

The HW/SW Integration Test (HIT) campaign shall:

1. Verify that every **register, bit-field, pin, interrupt, DMA channel, clock, and power rail** listed in HSI-IMX6Q-BSP-001 is correctly driven/read by the corresponding BSP driver on real silicon.
2. Confirm electrical compliance (voltage levels, rise/fall times, protocol timing) to IMX6DQCEC datasheet limits.
3. Measure interrupt latency, DMA throughput, clock accuracy, and power-mode wake-up time against HSI-specified targets.
4. Inject faults at the pin level and verify correct firmware fault handling.
5. Provide regression-quality evidence that all interfaces still pass after every firmware build.

### 1.2 Test Rig (Physical Bench)

```
                         ┌─────────────────────────────┐
                         │  Host PC (Ubuntu 22.04)     │
                         │  labgrid + pytest + pyvisa  │
                         └──┬──────┬───────┬───────┬───┘
                            │USB   │USB    │LXI    │USB
                            │      │       │GbE    │
         ┌──────────────────┘      │       │       │
         ▼                         ▼       ▼       ▼
  ┌──────────────┐        ┌─────────────┐ ┌──────────┐ ┌─────────┐
  │ Segger J-Link│        │ Saleae Pro16│ │ MSO58    │ │ DP832A  │
  │ Plus (JTAG)  │        │ Logic 500MS │ │ Tek 5GSa │ │ PSU ×3  │
  │ + RTT viewer │        │ 16ch        │ │ 4ch 1GHz │ │ 5V/3V3  │
  └──────┬───────┘        └──────┬──────┘ └────┬─────┘ └────┬────┘
         │JTAG (J801)            │Flying leads │Probes       │Barrel
         ▼                       ▼             ▼             ▼
  ┌───────────────────────────────────────────────────────────────┐
  │          i.MX6Q SabreSD (MCIMX6Q-SDB) — DUT                   │
  │  J509 Console UART ──► USB-Serial (FTDI) ──► Host             │
  │  J13  mPCIe │ J507 SD │ J1501 CAN │ J14  Audio │ J1302 ENET   │
  └───────────────────────────────────────────────────────────────┘
         ▲                       ▲
         │GPIO fault injection   │Signal generator AFG31052
         │(Relay matrix NI PXI)  │(I²C/SPI stimulus)
         └───────────────────────┘
```

### 1.3 Equipment List

| Ref  | Instrument                    | Model                  | Role                                            |
|------|-------------------------------|------------------------|-------------------------------------------------|
| E1   | Oscilloscope 1 GHz 4-ch       | Tektronix MSO58        | Clock, signal integrity, edge timing            |
| E2   | Logic analyser 16-ch 500 MS/s | Saleae Logic Pro 16    | Protocol decode (I²C, SPI, UART, SDIO)          |
| E3   | DMM 6½ digit                  | Keysight 34465A        | Voltage rails, static pin levels                |
| E4   | Arbitrary function generator  | Tek AFG31052 2-ch 50MHz| Analogue stimulus (ADC, audio)                  |
| E5   | Programmable PSU              | Rigol DP832A (×3)      | VDD_SOC, VDD_ARM, VDD_IO margin testing         |
| E6   | JTAG debug probe              | SEGGER J-Link Plus     | Register peek/poke, RTT, breakpoint latency     |
| E7   | Relay injection matrix        | NI PXIe-2527 (32×4)    | Open/short/over-voltage fault injection         |
| E8   | CAN bus analyser              | Kvaser Leaf Pro v2     | FlexCAN frame verification                      |
| E9   | USB protocol analyser         | LeCroy Voyager M4i     | USB OTG enumeration / eye-diagram               |
| E10  | Ethernet traffic generator    | Ixia Novus One         | GbE RGMII PHY timing + throughput               |
| E11  | Thermal chamber               | ESPEC SU-221           | –40…+85 °C soak (regression subset)             |
| E12  | Climate-controlled RF probe   | Rohde&Schwarz NRP-Z81  | (Optional) Wi-Fi/BT module RF level             |

### 1.4 Test Software Stack

- **Host:** `labgrid-client` orchestrates DUT power, JTAG, UART, instruments over SCPI (pyvisa) / sigrok-cli.
- **DUT:** Linux 6.6 LTS kernel with BSP modules built as `CONFIG_BSP_IMX6Q_*=m`; test helper `bsp_hit_helper.ko` exposes debugfs pokes at `/sys/kernel/debug/bsp_hit/*`.
- **JTAG scripting:** OpenOCD 0.12 + Tcl, JLinkGDBServer fallback.
- **Reporting:** JUnit XML → Jenkins; waveforms archived as `.wfm` + PNG thumbnail.

### 1.5 Scope Coverage

| HSI Section | Item Count | HIT Tests       |
|-------------|------------|-----------------|
| §1.1 IOMUXC                            | ~150 pads   | HIT-010…HIT-019 (sampled) |
| §1.2 CCM / Clocks                      | 18 regs     | HIT-020…HIT-029            |
| §1.3 GPIO banks 1–7                    | 7 banks     | HIT-030…HIT-036            |
| §1.4 UART1/2/5                         | 3 UARTs     | HIT-040…HIT-049            |
| §1.5 I²C1/2/3                          | 3 buses     | HIT-050…HIT-055            |
| §1.6 eCSPI1                            | 1 bus       | HIT-060…HIT-063            |
| §1.7 USDHC2/3/4 (SD/eMMC)              | 3 hosts     | HIT-070…HIT-076            |
| §1.8 FEC (GbE)                         | 1 MAC       | HIT-080…HIT-086            |
| §1.9 FlexCAN1/2                        | 2 CAN       | HIT-090…HIT-094            |
| §1.10 USB OTG1/2 + PHY                 | 2 ports     | HIT-100…HIT-105            |
| §1.11 SDMA / APBH-DMA                  | 2 engines   | HIT-110…HIT-115            |
| §1.12 GIC-400 / IRQs                   | 128 SPIs    | HIT-120…HIT-125            |
| §1.13 WDOG1/2                          | 2 WDTs      | HIT-130…HIT-132            |
| §1.14 SNVS / RTC                       | 1           | HIT-140…HIT-142            |
| §1.15 PMU / Power rails                | 6 rails     | HIT-150…HIT-156            |
| §1.16 Power modes                      | WAIT/STOP   | HIT-160…HIT-163            |

Total: **~85 HIT tests**; 32 of them are flagged `@regression` and run per CI build.

---

## 2. PERIPHERAL VERIFICATION TESTS (HIT-xxx)

> Tests are presented by peripheral group. Each test is fully specified.

### 2.1 Clock Controller (CCM / ANATOP)

---

**HIT-020** — PLL1 (ARM_PLL) lock and frequency verification
**HSI Reference:** `CCM_ANALOG_PLL_ARM` @ `0x020C8000`, bits `[7:0]=DIV_SELECT`, `[13]=ENABLE`, `[31]=LOCK`
**Equipment:** E6 (JTAG), E1 (MSO58) on TP_CLK1_OUT (test point TP3 — CLKO1 mux)
**Procedure:**
1. Boot DUT, halt at U-Boot prompt.
2. Via OpenOCD: `mww 0x020E0208 0x000000EE` — mux CLKO1 = pll1_sw_clk/8, enable pad.
3. Resume Linux; run `echo pll1_sw_clk > /sys/kernel/debug/clk/clko1/clk_parent`.
4. Read `cat /sys/kernel/debug/clk/pll1_sys/clk_rate` → expect 792 000 000 Hz (DIV_SELECT=66, 24 MHz × 66 / 2).
5. MSO58: measure frequency at TP_CLKO1, 50 Ω termination, AC coupled, 200 MHz BW limit.
6. Sample 1 000 periods; compute mean and σ.

**Pass criteria:**
- `/sys/.../clk_rate` == 792 000 000 Hz exactly.
- Measured TP_CLKO1 frequency = 99.000 MHz ± 0.005 % (24 MHz XTAL accuracy ±50 ppm).
- `CCM_ANALOG_PLL_ARM[31]` (LOCK) reads `1` within 10 ms of ENABLE.
- Jitter (RMS) ≤ 50 ps measured over 1 000 cycles.

**Automation:** OpenOCD Tcl script `hit020.tcl` + pyvisa `scope.query('MEASU:MEAS1:VALUE?')`.

---

**HIT-021** — PLL3 (USB1_PLL) 480 MHz enable + USB clock gate
**HSI Reference:** `CCM_ANALOG_PLL_USB1` @ `0x020C8010` bits `[12]=POWER`, `[13]=ENABLE`, `[6]=EN_USB_CLKS`; `CCM_CCGR6[0:1]=CG0` (usboh3)
**Equipment:** E6 (JTAG peek), E1 scope on USB_H1_DP differential pair (after enumeration)
**Procedure:**
1. Cold boot with USB console disabled.
2. JTAG peek `0x020C8010` — expect POR `0x00012000`.
3. `modprobe ci_hdrc_imx` to activate USB1 PHY.
4. JTAG peek `0x020C8010` — expect `[12]=1`, `[13]=1`, `[6]=1`.
5. JTAG peek `0x020C8080` (CCGR6) — expect `CG0` bits `[1:0] = 0b11`.
6. Plug USB memory stick; verify `dmesg` shows enumeration.

**Pass criteria:** All three register bits set; device enumerated with VID/PID visible in `lsusb`; PLL3 lock (`[31]`) = 1.

**Automation:** pytest fixture `usb_pll_fixture`; asserts via `jlink.read32()`.

---

**HIT-022** — CCM_CCGR gate integrity (all 7 gates)
**HSI Reference:** `CCM_CCGR0..CCGR6` @ `0x020C4068..0x020C4080`
**Equipment:** E6 JTAG
**Procedure:**
1. Snapshot all 7 CCGR registers at Linux steady-state (post-`systemctl is-system-running`).
2. Cross-check every gate bit against `clk_summary` debugfs (`/sys/kernel/debug/clk/clk_summary`).
3. For every clock reporting `enable_cnt > 0`, the corresponding CCGR field must be `0b11`.
4. For every clock reporting `enable_cnt == 0`, field must be `0b00`.

**Pass criteria:** Zero mismatches across 112 gate bits.

**Automation:** Python diff of JTAG vs. debugfs; fails on any delta.

---

**HIT-023** — AHB/IPG/AXI divider ratios
**HSI Reference:** `CCM_CBCDR[18:16]=AHB_PODF`, `[15:13]=IPG_PODF`, `[12:10]=AXI_PODF`
**Equipment:** E6 JTAG, E1 on CLKO2 (probe AXI/8 via IOMUXC daisy)
**Procedure:** Route `axi_clk` to CLKO2 via `CCM_CCOSR`; verify 264 MHz / 8 = 33.0 MHz measured. Repeat for AHB (132 MHz → 16.5 MHz on /8). IPG is not muxable — verify via ARM_PODF inference and divider readback.

**Pass criteria:** Measured ≤ ±0.1 % of expected; register dividers match device-tree `clock-frequency` properties.

**Automation:** `hit023.py` parses DT and queries scope.

---

### 2.2 IOMUXC / Pinctrl (representative pads)

**HIT-010** — UART1 pad mux and pull-up verification
**HSI Reference:** `IOMUXC_SW_MUX_CTL_PAD_CSI0_DAT10` (UART1_TX) offset `0x0280`, `IOMUXC_SW_PAD_CTL_PAD_CSI0_DAT10` offset `0x0650`
**Equipment:** E6 JTAG, E3 DMM on J509 pin 3 (TXD)
**Procedure:**
1. JTAG peek mux reg — expect `[2:0]=3` (ALT3 = UART1_TX).
2. JTAG peek pad reg — expect `PUS=10b` (100 kΩ PU), `DSE≥4 mA`, `SPEED=2`.
3. DMM on TXD with line idle: expect 3.3 V ±5 %.
4. Run `stty -F /dev/ttymxc0 115200`; force break with `setserial` → DMM reads 0 V ±50 mV during break.

**Pass criteria:** Mux=3, pad conf matches HSI, idle level VOH ≥ 3.135 V.

**Automation:** `pytest hit010` uses jlink+DMM via VISA.

---

**HIT-011** — ENET_REF_CLK pad output drive (50 MHz RMII)
**HSI Reference:** `IOMUXC_SW_MUX_CTL_PAD_ENET_REF_CLK` offset `0x01D0`, ALT1; `IOMUXC_GPR1[21]=ENET_CLK_SEL`
**Equipment:** E1 MSO58 on R177 (series term before PHY)
**Procedure:** Bring up `fec` driver; probe ENET_REF_CLK. Capture 10 000 cycles.

**Pass criteria:**
- Frequency = 50.000 MHz ± 100 ppm
- Duty cycle 45–55 %
- VOH ≥ 2.4 V, VOL ≤ 0.4 V
- Rise/fall time ≤ 2 ns (HSI drive strength DSE=6, matches IMX6DQCEC Table 57)

---

**HIT-012** — GPIO drive-strength verification (4 mA / 8 mA / 40 Ω DSE levels)
**HSI Reference:** `IOMUXC_SW_PAD_CTL[5:3]=DSE`
**Equipment:** E1 MSO58, 100 Ω load resistor to GND on GPIO1_IO09 (J13 pin 5)
**Procedure:** Program DSE to each of values 1,2,4,6 via `bsp_hit_helper` debugfs; toggle GPIO at 1 MHz. Measure rise time 10→90 %.

**Pass criteria (per IMX6DQCEC Tab 60):**

| DSE | Expected rise-time | Accept band |
|-----|--------------------|-------------|
| 001 (150 Ω) | 7.0 ns | 5.5–8.5 ns |
| 010 (100 Ω) | 4.8 ns | 3.5–6.0 ns |
| 100 (60 Ω)  | 2.4 ns | 1.8–3.0 ns |
| 110 (40 Ω)  | 1.6 ns | 1.2–2.0 ns |

---

### 2.3 GPIO

**HIT-030** — GPIO output direction & level (all banks)
**HSI Reference:** `GPIOn_DR`, `GPIOn_GDIR` (n=1..7)
**Equipment:** E3 DMM, E1 scope
**Procedure:** For each bank, for pads available on expansion connector J13/J21:
1. `echo out > /sys/class/gpio/gpioX/direction`
2. `echo 1 > value` → DMM reads 3.3 V ± 5 %.
3. `echo 0 > value` → DMM reads ≤ 0.1 V.
4. Toggle at 100 kHz; scope confirms clean edges.

**Pass criteria:** Static levels within spec; no glitches > 100 mV on idle lines.

---

**HIT-031** — GPIO input, interrupt-on-rising-edge, latency
**HSI Reference:** `GPIOn_ICR1/2`, `GPIOn_IMR`, `GPIOn_ISR`, GIC SPI 98–104
**Equipment:** E4 AFG31052 (TTL pulse), E6 J-Link RTT
**Procedure:**
1. Configure GPIO1_IO09 as input, IRQ rising edge via `request_irq` in test module.
2. ISR writes timestamp (`arch_counter_get_cntvct()`) to RTT channel.
3. AFG31052 generates single 3.3 V rising edge with TRIG_OUT cabled to scope CH2.
4. Scope CH1 on GPIO pin; cursor measures time from DUT GPIO edge to ISR entry flag (optional GPIO1_IO10 toggled at ISR entry).

**Pass criteria:**
- ISR entry latency (cold cache) ≤ 3 µs worst case over 1 000 pulses.
- No missed interrupts; count in `/proc/interrupts` == 1 000.

---

**HIT-032** — GPIO fault: stuck-at-1 / stuck-at-0 detection
**HSI Reference:** `GPIOn_PSR` (pad sampling)
**Equipment:** E7 Relay matrix
**Procedure:** Relay forces GPIO1_IO12 to 3.3 V while firmware tries to drive low. Firmware diagnostic (`bsp_gpio_selftest`) should flag mismatch between `DR` and `PSR` within 50 ms.

**Pass criteria:** `dmesg` reports `[bsp-imx6q] GPIO1_IO12 stuck-at-1`; no kernel crash.

---

### 2.4 UART

**HIT-040** — UART1 115 200 baud bit-time accuracy
**HSI Reference:** `UART1_BRM_INCR`, `UART1_BRM_DIVIDER`, `UART1_UFCR[9:7]=RFDIV`
**Equipment:** E2 Saleae Logic (UART decoder)
**Procedure:** Send `echo -n 'U' > /dev/ttymxc0` (0x55, max-toggle pattern). Capture at 24 MS/s.

**Pass criteria:**
- Bit time = 8.681 µs ± 2 % (per IMX6DQCEC Table 61, UART timing spec allows ±3 %).
- 8 data bits, 1 stop, no parity correctly decoded.
- 1 000 consecutive bytes decoded with 0 frame errors.

---

**HIT-041** — UART2 RS-485 RTS turnaround timing
**HSI Reference:** UART2_RTS (GPIO7_IO03 ALT4), driver RS-485 half-duplex mode
**Equipment:** E1 scope 2ch
**Procedure:** Enable RS-485 via `ioctl(TIOCSRS485)`. Transmit 16 bytes; measure delay from RTS-assert → first start bit, and last stop bit → RTS-deassert.

**Pass criteria:** Both times ≤ 1 bit period (≤ 8.681 µs @ 115 200).

---

**HIT-042** — UART5 flow-control CTS/RTS
**Equipment:** E2 Logic, loopback CTS to GPIO
**Procedure:** Fill TX FIFO while CTS=high (flow blocked). Verify no data egress until CTS=low.

**Pass criteria:** UART respects hardware CTS within 1 character time.

---

**HIT-043** — UART DMA receive (SDMA path)
**HSI Reference:** SDMA event 26 (UART1 RX), `UART1_UCR1[6]=ATDMAEN`
**Equipment:** E4 AFG31052 generates scripted serial stream at 3 Mbps
**Procedure:** Open `/dev/ttymxc0`, 3 000 000 baud, DMA mode. Stream 1 MiB known pattern.

**Pass criteria:** Received 1 MiB matches source SHA-256; zero framing/overrun errors in `/proc/tty/driver/IMX-uart`.

---

### 2.5 I²C

**HIT-050** — I²C1 bus timing (400 kHz Fast-mode)
**HSI Reference:** `I2C1_IFDR`, I²C1_SCL=GPIO3_IO21 ALT6, I²C1_SDA=GPIO3_IO28 ALT6
**Equipment:** E2 Logic (I²C decoder), E1 scope (edge timing)
**Procedure:** `i2cdetect -y 0`; scope on SCL/SDA.

**Pass criteria (NXP UM10204 Fm):**
- fSCL = 400 kHz ± 5 %
- tLOW ≥ 1.3 µs; tHIGH ≥ 0.6 µs
- tSU;STA ≥ 0.6 µs; tHD;DAT ≥ 0 µs; tSU;STO ≥ 0.6 µs
- Rise time (30–70 %) ≤ 300 ns with 2.2 kΩ pull-ups

---

**HIT-051** — I²C1 transaction to PMIC (PFUZE100) — read chip ID
**HSI Reference:** PMIC @ 7-bit addr `0x08`, register `0x00` (DEVICEID)
**Equipment:** E2 Logic for correlation
**Procedure:** `i2cget -y 0 0x08 0x00`.

**Pass criteria:** Returns `0x11` (PFUZE100 silicon rev); Logic decode shows: START, 0x10, ACK, 0x00, ACK, R-START, 0x11, ACK, 0x11, NACK, STOP.

---

**HIT-052** — I²C1 NACK recovery
**Equipment:** E7 relay pulls SDA to GND mid-transaction.
**Procedure:** During `i2cget`, inject SDA short for 100 µs. Driver should detect arbitration-lost / timeout, release bus (9 clock pulses), and retry.

**Pass criteria:** `dmesg` shows `i2c-imx 0: arbitration lost`; next transaction succeeds.

---

**HIT-053** — I²C1 clock stretching tolerance
**Procedure:** Slave (Arduino emulator on AFG31052) stretches SCL low for 25 ms mid-byte.

**Pass criteria:** Master waits (no timeout < 35 ms); transaction completes correctly.

---

### 2.6 eCSPI

**HIT-060** — eCSPI1 8/16/32-bit transfer correctness + MODE0 timing
**HSI Reference:** `ECSPI1_CONREG`, `ECSPI1_CONFIGREG`, pads ALT2 on EIM_D16..D19
**Equipment:** E2 Logic (SPI decoder), loopback MOSI→MISO
**Procedure:** `spidev_test -D /dev/spidev0.0 -s 10000000 -b 8|16|32 -p "<pattern>"`.

**Pass criteria:**
- fSCLK measured = 10 MHz ± 1 %
- CPOL=0/CPHA=0 edges match data-sheet Fig. 46 (setup ≥ 5 ns, hold ≥ 5 ns).
- Received bytes == transmitted bytes for 1 MiB pattern.

---

**HIT-061** — eCSPI1 CS0 → SCLK setup (tCSS) and CS hold (tCSH)
**Pass criteria:** tCSS ≥ 2 × tSCLK (measured ≥ 200 ns @ 10 MHz), tCSH ≥ 1 × tSCLK.

---

**HIT-062** — eCSPI1 SDMA read/write 64 KiB
**HSI Reference:** SDMA events 1 (TX) / 2 (RX)
**Procedure:** Full-duplex transfer via DMA; verify via SHA-256.

**Pass criteria:** Data integrity 100 %; `iostat` shows sustained ≥ 9 Mbps (near bus-limited).

---

### 2.7 USDHC (SD / eMMC)

**HIT-070** — USDHC3 (SD card) UHS-I SDR104 init sequence
**HSI Reference:** `USDHC3` @ `0x02198000`; CMD0/8/55/41/2/3/7 sequence; tuning `VEND_SPEC[1]`
**Equipment:** E2 Logic on CMD/CLK/DAT[0-3]
**Procedure:** Insert SanDisk Extreme Pro 64 GB. Boot; observe enumeration. Verify `mmc info /dev/mmcblk1` reports `SDR104`, 208 MHz.

**Pass criteria:**
- Enumeration sequence matches SD 6.0 spec.
- No re-tune events in first 60 s under `fio` read workload.
- Read throughput ≥ 80 MB/s sustained.

---

**HIT-071** — USDHC4 (eMMC) HS200 data CRC integrity
**Procedure:** `dd if=/dev/mmcblk2 bs=1M count=256 | sha256sum` ×3 runs.

**Pass criteria:** All 3 hashes identical; 0 CRC errors in `/sys/class/mmc_host/mmc0/errorstats`.

---

**HIT-072** — USDHC card-detect GPIO debouncing
**HSI Reference:** CD GPIO2_IO00 (USDHC3)
**Equipment:** E7 relay simulates 5 ms contact bounce.
**Procedure:** Toggle CD 20 times with random 0–10 ms bounce bursts.

**Pass criteria:** Exactly 20 insertion events reported by mmc subsystem; zero spurious.

---

### 2.8 FEC (Gigabit Ethernet)

**HIT-080** — FEC RGMII timing compliance
**HSI Reference:** FEC pads on ENET_*; `IOMUXC_GPR1[21]=ENET_CLK_SEL`
**Equipment:** E1 4-ch probes on TXC/TXD[0-3]/TX_CTL
**Procedure:** Start `iperf3 -c host -t 60`. Capture RGMII at 1 Gbps.

**Pass criteria (per RGMII v2.0):**
- TXC frequency = 125 MHz ± 50 ppm
- TXD setup to TXC edge ≥ 1.2 ns
- TXD hold after TXC edge ≥ 1.2 ns
- Skew ≤ 500 ps across 4 data lanes

---

**HIT-081** — FEC 1 Gbps TCP throughput
**Equipment:** E10 Ixia
**Procedure:** Bidirectional 1 500-byte frames, 60 s.

**Pass criteria:** ≥ 940 Mbps each direction; 0 FCS errors.

---

**HIT-082** — FEC PHY reset pulse width (AR8031 requires ≥ 10 ms)
**HSI Reference:** ENET_PHY_RESET GPIO1_IO25
**Equipment:** E1 scope
**Pass criteria:** Measured reset pulse 12 ms ± 2 ms; link-up within 500 ms after de-assert.

---

### 2.9 FlexCAN

**HIT-090** — FlexCAN1 bit-timing @ 500 kbps
**HSI Reference:** `FLEXCAN1_CTRL1[PRESDIV,RJW,PSEG1,PSEG2,PROPSEG]`
**Equipment:** E8 Kvaser
**Procedure:** `ip link set can0 up type can bitrate 500000`. Transmit 10 000 frames standard ID.

**Pass criteria:**
- Nominal bit time 2 µs ± 0.5 %
- Sample point 75 % ± 2 %
- 0 bus-off events

---

**HIT-091** — FlexCAN1 bus-off recovery
**Equipment:** E7 forces CANH=CANL (dominant stuck)
**Procedure:** Start TX; after 1 s remove short.

**Pass criteria:** `ip -s -d link show can0` reports bus-off; auto-restart within 1 s (per `restart-ms=1000`); normal TX resumes.

---

**HIT-092** — FlexCAN1 loopback data integrity 128 frames
**Pass criteria:** All frames RX match TX; DLC, ID, payload equal.

---

### 2.10 USB OTG

**HIT-100** — USB OTG1 host-mode enumeration of HS device
**HSI Reference:** USB_OTG_ID pad, USB1_VBUS
**Equipment:** E9 LeCroy Voyager
**Procedure:** Attach certified USB-IF HS test device. `lsusb`.

**Pass criteria:** VID/PID match; chapter-9 tests (descriptor fetch, SET_CONFIG) pass via `usbtest`.

---

**HIT-101** — USB OTG1 HS eye-diagram (differential)
**Equipment:** E1 with differential probe P6247
**Pass criteria:** Eye opens > 525 mV, crossing 40–60 %, meets USB 2.0 Template 1 at TP2.

---

**HIT-102** — USB OTG1 VBUS over-current fault
**Equipment:** E7 relay shorts VBUS→GND (via 1 A current limit).
**Pass criteria:** PMIC flags OC within 10 ms; driver disables port; `dmesg` shows `over-current`.

---

### 2.11 DMA (SDMA)

**HIT-110** — SDMA mem-to-mem 4 MiB
**HSI Reference:** `SDMA_CHnENBL`, script RAM, event mux
**Equipment:** E6 JTAG watchpoint on completion IRQ
**Procedure:** Test module initiates DMA; measure end-to-start.

**Pass criteria:**
- Throughput ≥ 250 MB/s
- Destination SHA-256 == source
- Completion IRQ delivered within budget (< 5 µs after BD DONE)

---

**HIT-111** — SDMA scatter-gather 32 buffers
**Pass criteria:** All 32 BDs processed; 0 errors in `SDMA_EVTERR`.

---

**HIT-112** — SDMA channel priority under contention
**Procedure:** 3 channels running simultaneously at priorities 1/3/7.
**Pass criteria:** High-prio completion time unchanged within 10 % vs. idle case.

---

### 2.12 GIC / Interrupts

**HIT-120** — GIC-400 SPI routing & priority
**HSI Reference:** GIC distributor @ `0x00A01000`, `GICD_ICFGRn`, `GICD_IPRIORITYRn`
**Equipment:** E6 JTAG
**Procedure:** For SPIs used by BSP (list of 38 IDs), verify configured polarity and priority match `/proc/interrupts` and device-tree `interrupts = <..>`.

**Pass criteria:** 100 % match; no SPI at reserved priority 0xFF.

---

**HIT-121** — Interrupt latency worst-case (CPU0 affinity)
**Procedure:** GPIO IRQ stimulus (HIT-031) under `stress-ng --cpu 4` + `cyclictest`.
**Pass criteria:** 99.9-percentile latency ≤ 25 µs; max ≤ 80 µs over 1 hour.

---

### 2.13 Watchdog

**HIT-130** — WDOG1 reset on expiry
**HSI Reference:** `WDOG1_WCR`, `WDOG1_WSR`
**Equipment:** E1 scope on `POR_B` + E5 PSU current monitor
**Procedure:** `systemctl stop watchdog`; let WDOG1 expire (128 s max).

**Pass criteria:** `POR_B` pulses low within 128 s + 0.5 s; DUT reboots; reset cause reg `SRSR[4]=WDOG`=1.

---

**HIT-131** — WDOG1 refresh sequence timing
**Procedure:** User-space ping via `/dev/watchdog`. Scope `WDOG1_B` stays high.
**Pass criteria:** For timeout=10 s and ping=5 s, WDOG never triggers over 24 h soak.

---

### 2.14 RTC / SNVS

**HIT-140** — SNVS RTC tick accuracy over 24 h
**Equipment:** GPS-disciplined 10 MHz ref (Trimble Thunderbolt-E) on counter input.
**Pass criteria:** Drift ≤ ±5 s over 24 h (≈58 ppm — spec of 32.768 kHz XTAL Y3 is ±20 ppm; margin for thermal).

---

**HIT-141** — SNVS coin-cell backup retention
**Procedure:** Unplug main power with CR2032 on BT501 for 12 h; power up; read RTC.
**Pass criteria:** Time continues counting within ±2 s of expected.

---

### 2.15 Power Rails & Modes

**HIT-150** — Power rail sequencing at cold boot
**HSI Reference:** PMIC (PFUZE100) SW1AB → SW1C → SW2 → SW3AB → SW4 → VGEN2/3/5/6
**Equipment:** E1 4 ch scope on rail test-points; long record mode 500 ms.
**Pass criteria:** All rails rise in datasheet order; each within 2 ms of expected offset; no rail overshoot > 5 %.

---

**HIT-151** — VDD_ARM voltage during DVFS transition
**HSI Reference:** PFUZE100 SW1AB dynamic voltage scaling
**Procedure:** `cpufreq-set -g performance` ↔ `powersave` alternation; scope on VDD_ARM.
**Pass criteria:** Each step ≤ 12.5 mV; settling ≤ 100 µs; no undershoot.

---

**HIT-160** — WAIT-mode wake-up from GPIO (latency)
**HSI Reference:** `CCM_CLPCR[1:0]=LPM=01`, GPC wake mask
**Equipment:** E1 scope — CH1 on GPIO wake source; CH2 on test GPIO toggled first thing in resume.
**Pass criteria:** Wake latency ≤ 50 µs from rising edge to CH2 toggle.

---

**HIT-161** — STOP-mode wake-up + DDR self-refresh exit
**Pass criteria:** Wake latency ≤ 5 ms; memory contents intact (CRC over 64 MiB pre/post match); system current in STOP ≤ 25 mA.

---

**HIT-162** — STOP-mode current draw
**Equipment:** E3 DMM in series with 5 V input; 6½-digit.
**Pass criteria:** Idle+STOP current ≤ 50 mA @ 25 °C (HSI §1.16 budget).

---

## 3. HARDWARE-IN-THE-LOOP (HIL) TEST CASES

HIL tests verify **end-to-end firmware behaviour** when hardware conditions change. They exercise the driver stack plus service-level code.

---

**HIL-001** — SD card hot-removal during write
**Stimulus:** Relay opens USDHC3 card-detect + power simultaneously while `dd of=/dev/mmcblk1 bs=1M count=1024` is in progress.
**Expected firmware response:**
- `mmc0: card removed` logged within 200 ms.
- `dd` terminates with `-EIO`, does not hang.
- Re-insertion within 5 s re-enumerates card; filesystem mountable (after fsck).
- No kernel oops; `dmesg` clean afterwards.

---

**HIL-002** — Ethernet cable unplug/replug flapping
**Stimulus:** E7 relay toggles link 10 times at 200 ms intervals during `iperf3` stream.
**Expected:** Driver recovers each time; NetworkManager reports `connected` after last reconnect within 3 s; no memory leak (`slabtop` stable ±5 %).

---

**HIL-003** — CAN bus short to ground
**Stimulus:** Short CANH→GND for 500 ms.
**Expected:** Controller enters error-passive → bus-off; restart-ms policy recovers; no silent frame loss (frame counters consistent).

---

**HIL-004** — I²C SDA stuck-low recovery
**Stimulus:** Relay forces SDA low for 10 ms (simulating slave glitch).
**Expected:** Driver issues 9-clock recovery sequence on SCL; subsequent transactions succeed.

---

**HIL-005** — Under-voltage on VDD_SOC
**Stimulus:** E5 PSU drops VDD_SOC from 1.375 V → 1.15 V (below min 1.175 V) for 100 ms.
**Expected:** PMIC trips UV comparator; system resets cleanly; `SRSR[3]=CSU` or equivalent reset cause set; no corruption of eMMC (post-boot `fsck` clean).

---

**HIL-006** — Over-voltage on a GPIO input (5 V on a 3.3 V pad)
**Stimulus:** Relay injects 5.0 V via 1 kΩ series for 10 ms onto GPIO1_IO09.
**Expected:** ESD/clamp diodes handle transient (verified by post-test continuity + GPIO toggle still works); no unintended IRQ storm (< 10 spurious IRQs counted).
**Note:** **Destructive-test candidate**; run on a sacrificial board every silicon-rev qualification.

---

**HIL-007** — Brown-out during firmware update
**Stimulus:** Kill 5 V supply mid-way through `dd` of rootfs image to eMMC.
**Expected:** After power restore, bootloader detects incomplete update (sha mismatch) and falls back to redundant partition; system boots.

---

**HIL-008** — Thermal stress cycle –40 → +85 °C
**Stimulus:** E11 chamber over 6 h, 3 cycles.
**Expected:** All regression HITs still pass; RTC drift within spec; no PLL loss of lock.

---

**HIL-009** — USB device insertion storm
**Stimulus:** Relay rapidly connects/disconnects USB stick 100 times (50 ms period).
**Expected:** Kernel enumeration eventually stabilises; no oops; `usbcore` error rate < 1 %.

---

**HIL-010** — Clock glitch (24 MHz XTAL)
**Stimulus:** Briefly short one XTAL leg via HF-rated relay for 10 µs.
**Expected:** Loss-of-clock detector in CCM (via `CCM_ANALOG_MISC0`) flags event; system resets via WDOG or PLL unlock; no silent mis-execution.

---

## 4. TIMING MEASUREMENT RESULTS TEMPLATE

Instrument reports are captured in YAML and transformed to this table per run.

### 4.1 Clock & PLL

| Signal          | HSI Spec (min/typ/max)       | Measured  | Instrument | Pass/Fail |
|-----------------|------------------------------|-----------|------------|-----------|
| XTAL 24 MHz     | 23.9988 / 24.000 / 24.0012   |           | E1         |           |
| PLL1 ARM_CLK    | — / 792.000 MHz / —          |           | E6+E1      |           |
| PLL3 USB        | — / 480.000 MHz / —          |           | E6         |           |
| ENET REF_CLK    | 49.995 / 50.000 / 50.005 MHz |           | E1         |           |
| RGMII TXC       | 124.99 / 125.00 / 125.01 MHz |           | E1         |           |
| USDHC3 SDR104   | — / 208.000 MHz / —          |           | E2         |           |
| USDHC4 HS200    | — / 200.000 MHz / —          |           | E2         |           |
| RTC 32.768 kHz  | ±20 ppm                      |           | Counter    |           |

### 4.2 Protocol Timing

| Signal          | HSI Spec (min/typ/max)       | Measured  | Instrument | Pass/Fail |
|-----------------|------------------------------|-----------|------------|-----------|
| UART1 bit time  | 8.4/8.681/8.93 µs @ 115k2    |           | E2         |           |
| I²C1 SCL freq   | 380 / 400 / 420 kHz          |           | E2/E1      |           |
| I²C1 tLOW       | ≥ 1.3 µs                     |           | E1         |           |
| I²C1 tHIGH      | ≥ 0.6 µs                     |           | E1         |           |
| eCSPI1 tCSS     | ≥ 200 ns                     |           | E1         |           |
| eCSPI1 tCSH     | ≥ 100 ns                     |           | E1         |           |
| RGMII setup     | ≥ 1.2 ns                     |           | E1         |           |
| RGMII hold      | ≥ 1.2 ns                     |           | E1         |           |
| CAN bit time    | 1.99 / 2.00 / 2.01 µs        |           | E8         |           |
| CAN sample pt   | 73 / 75 / 77 %               |           | E8         |           |

### 4.3 Interrupt & DMA

| Signal                       | HSI Spec     | Measured | Instrument | Pass/Fail |
|------------------------------|--------------|----------|------------|-----------|
| GPIO IRQ latency (idle)      | ≤ 3 µs       |          | E1+E6      |           |
| GPIO IRQ latency (loaded)    | ≤ 25 µs p99  |          | E1+E6      |           |
| SDMA mem→mem 4 MiB           | ≥ 250 MB/s   |          | SW timer   |           |
| WAIT mode wake               | ≤ 50 µs      |          | E1         |           |
| STOP mode wake               | ≤ 5 ms       |          | E1         |           |
| WDOG1 reset pulse            | 10–500 µs    |          | E1         |           |

### 4.4 Static Voltage

| Rail     | HSI Spec (min/typ/max)   | Measured | Instrument | Pass/Fail |
|----------|--------------------------|----------|------------|-----------|
| VDD_ARM  | 1.15 / 1.375 / 1.425 V   |          | E3         |           |
| VDD_SOC  | 1.175 / 1.375 / 1.425 V  |          | E3         |           |
| VDD_HIGH | 2.8 / 3.0 / 3.1 V        |          | E3         |           |
| NVCC_IO  | 3.135 / 3.3 / 3.465 V    |          | E3         |           |
| VDD_DDR  | 1.485 / 1.5 / 1.515 V    |          | E3         |           |
| STOP Idd | — / — / 50 mA            |          | E3         |           |

---

## 5. REGRESSION TEST SUITE

### 5.1 CI-Gating Subset (`@regression`)

Must pass on every firmware build pushed to `main`. Runs on dedicated bench in Jenkins stage `hit-regression`. Budget: **≤ 30 min per build**.

| HIT-ID  | Peripheral         | Why in regression                         | Runtime |
|---------|--------------------|-------------------------------------------|---------|
| HIT-020 | PLL1 lock          | Boot-critical                             | 30 s    |
| HIT-022 | CCGR gates         | Power correctness                         | 20 s    |
| HIT-023 | Bus dividers       | System stability                          | 30 s    |
| HIT-030 | GPIO out (all)     | Basic pinmux sanity                       | 2 min   |
| HIT-031 | GPIO IRQ latency   | RT guarantee                              | 3 min   |
| HIT-040 | UART1 baud         | Console must work                         | 30