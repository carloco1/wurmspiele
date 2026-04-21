# HARDWARE / SOFTWARE INTERFACE SPECIFICATION
## NXP i.MX6 Quad SabreSD — Linux BSP Driver Package

**Document ID:** HSI-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 3 (HW/SW Interface Contract)
**Pairs with:** Stage 13 — HW/SW Integration Tests (HSIT-IMX6Q-BSP-001)
**Traces upward to:** SAD-IMX6Q-BSP-001 v1.0, SRS-IMX6Q-BSP-001 v1.0
**Target SoC:** i.MX6 Quad (MCIMX6Q5EYM12AD, rev 1.2/1.3 TO)
**Target Board:** MCIMX6Q-SDB (SabreSD)
**Reference Manual:** IMX6DQRM Rev. 7, 03/2022
**Data Sheet:** IMX6DQCEC Rev. 5

---

## 0. DOCUMENT CONVENTIONS

- All addresses in C-style hex (`0x12345678`).
- Register names match NXP IMX6DQRM and mainline Linux `arch/arm/boot/dts/nxp/imx/imx6q.dtsi`.
- "R/W" column: **R** = read-only, **W** = write-only, **RW** = read/write, **W1C** = write-1-to-clear, **RO/V** = read-only/volatile.
- Reset values per IMX6DQRM power-on reset ("POR" column).
- Pin naming: `<SoC_pad_name>` per IOMUXC chapter; J-connectors per SabreSD schematic SPF-27392_C.
- Bit-fields use `[MSB:LSB]` inclusive.

---

## 1. REGISTER MAP

The i.MX6Q AIPS bus exposes peripherals at deterministic base addresses. Only registers touched by the BSP drivers are enumerated; full peripheral register maps are in IMX6DQRM.

### 1.1 IOMUXC — I/O Multiplexer Controller

**Base:** `0x020E0000` (AIPS-1) — used by `pinctrl-imx6q` driver.

| Register Name | Base Addr | Offset | Bit-fields | R/W | Reset Value | Description |
|---|---|---|---|---|---|---|
| `IOMUXC_SW_MUX_CTL_PAD_<PAD>` | `0x020E0000` | `0x04C–0x36C` | `[4]=SION`, `[2:0]=MUX_MODE` | RW | `0x00000005` (pad-dependent) | ALT-function selection (0–8) |
| `IOMUXC_SW_PAD_CTL_PAD_<PAD>` | `0x020E0000` | `0x360–0x680` | `[16]=HYS`, `[15:14]=PUS`, `[13]=PUE`, `[12]=PKE`, `[11]=ODE`, `[7:6]=SPEED`, `[5:3]=DSE`, `[0]=SRE` | RW | pad-default | Drive/pull/slew for pad |
| `IOMUXC_<periph>_SELECT_INPUT` | `0x020E0000` | `0x7B8–0x93C` | `[2:0]=DAISY` | RW | `0x00000000` | Daisy-chain input selection |
| `IOMUXC_GPR1` | `0x020E0000` | `0x004` | `[25]=EXC_MON`, `[13:0]=PCIe/SATA cfg` | RW | `0x04600000` | General-purpose control |
| `IOMUXC_GPR13` | `0x020E0000` | `0x034` | SATA PHY controls | RW | `0x00000000` | (not used — no SATA on SabreSD) |

### 1.2 CCM / CCM_ANALOG — Clock Controller

**Base:** `0x020C4000` (CCM), `0x020C8000` (CCM_ANALOG / ANATOP).

| Register | Base | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|---|
| `CCM_CCR` | `0x020C4000` | `0x000` | `[26:24]=WB_COUNT`, `[10:8]=OSCNT` | RW | `0x040116FF` | CCM control |
| `CCM_CCSR` | `0x020C4000` | `0x00C` | `[8]=PLL3_SW_CLK_SEL`, `[2]=STEP_SEL`, `[0]=PLL1_SW_CLK_SEL` | RW | `0x00000100` | Clock source switch |
| `CCM_CACRR` | `0x020C4000` | `0x010` | `[2:0]=ARM_PODF` | RW | `0x00000000` | ARM clock divider |
| `CCM_CBCDR` | `0x020C4000` | `0x014` | `[18:16]=AHB_PODF`, `[15:13]=IPG_PODF`, `[12:10]=AXI_PODF` | RW | `0x00018D40` | Bus divider |
| `CCM_CBCMR` | `0x020C4000` | `0x018` | `[19:18]=PRE_PERIPH_CLK_SEL`, `[13:12]=PERIPH2_CLK2_SEL` | RW | `0x00A8A300` | Bus mux |
| `CCM_CSCMR1` | `0x020C4000` | `0x01C` | `[27:26]=ACLK_EMI_SEL`, `[29:28]=ACLK_EMI_PODF`, `[5:0]=PERCLK_PODF` | RW | `0x00F00000` | Serial clock mux |
| `CCM_CSCDR1` | `0x020C4000` | `0x024` | `[18:16]=USDHC4_PODF`, `[14:11]=USDHC3_CLK_SEL`… | RW | `0x00490B00` | SD/UART div |
| `CCM_CCGR0..6` | `0x020C4000` | `0x068–0x080` | 16× 2-bit gates `[31:0]` | RW | `0xFFFFFFFF` | Peripheral clock gates (0=off,1=run,3=run+stop) |
| `CCM_CLPCR` | `0x020C4000` | `0x054` | `[1:0]=LPM`, `[5]=ARM_CLK_DIS_ON_LPM`, `[11]=SBYOS` | RW | `0x00000079` | Low-power control |
| `CCM_ANALOG_PLL_ARM` | `0x020C8000` | `0x000` | `[7:0]=DIV_SELECT`, `[13]=ENABLE`, `[16]=BYPASS`, `[31]=LOCK` | RW | `0x00013042` | ARM PLL (PLL1) |
| `CCM_ANALOG_PLL_USB1` | `0x020C8000` | `0x010` | `[1:0]=DIV_SELECT`, `[6]=EN_USB_CLKS`, `[12]=POWER`, `[13]=ENABLE` | RW | `0x00012000` | USB PHY0 PLL (PLL3) |
| `CCM_ANALOG_PLL_SYS` | `0x020C8000` | `0x030` | `[7:0]=DIV_SELECT`, `[13]=ENABLE`, `[31]=LOCK` | RW | `0x00013001` | System PLL (PLL2) 528 MHz |
| `CCM_ANALOG_PLL_ENET` | `0x020C8000` | `0x0E0` | `[1:0]=DIV_SELECT`, `[13]=ENABLE`, `[20]=ENET_125M_EN` | RW | `0x00011001` | GbE PLL (PLL6) |
| `CCM_ANALOG_PFD_528` | `0x020C8000` | `0x100` | 4× `{FRAC[5:0],STABLE,CLKGATE}` per PFD | RW | `0x1311100C` | PLL2 PFDs |

### 1.3 GIC — ARM Generic Interrupt Controller (PL390)

**Base:** `0x00A00000` (PERIPHBASE). CPU interface at `+0x0100`, Distributor at `+0x1000`.

| Register | Base | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|---|
| `GICD_CTLR` | `0x00A01000` | `0x000` | `[0]=EnableGrp0` | RW | `0x00000000` | Distributor enable |
| `GICD_ISENABLERn` | `0x00A01000` | `0x100–0x13C` | 32×N enable bits | RW | `0x00000000` | Set-enable |
| `GICD_ICENABLERn` | `0x00A01000` | `0x180–0x1BC` | 32×N | RW | `0x00000000` | Clear-enable |
| `GICD_IPRIORITYRn` | `0x00A01000` | `0x400–0x5FC` | 8-bit priority, top 5 used | RW | `0x00000000` | Per-IRQ priority |
| `GICD_ITARGETSRn` | `0x00A01000` | `0x800–0x9FC` | 8-bit CPU target mask | RW | boot-CPU | SMP affinity |
| `GICD_ICFGRn` | `0x00A01000` | `0xC00–0xCFC` | 2-bit edge/level | RW | `0x00000000` | Trigger config |
| `GICC_CTLR` | `0x00A00100` | `0x000` | `[0]=Enable` | RW | `0x00000000` | CPU-IF enable |
| `GICC_PMR` | `0x00A00100` | `0x004` | `[7:0]=Priority` | RW | `0x00000000` | Priority mask |
| `GICC_IAR` | `0x00A00100` | `0x00C` | `[12:10]=CPUID`, `[9:0]=IntID` | RO | `0x000003FF` | Interrupt Ack |
| `GICC_EOIR` | `0x00A00100` | `0x010` | `[12:10]=CPUID`, `[9:0]=IntID` | WO | — | End-of-interrupt |

### 1.4 GPIO (GPIO1…GPIO7)

**Bases:** `0x0209C000` (GPIO1), `0x020A0000` (GPIO2), `0x020A4000`, `0x020A8000`, `0x020AC000`, `0x020B0000`, `0x020B4000`.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `DR` | `0x00` | `[31:0]` data | RW | `0x00000000` | Data (output drives pad; read = pad state) |
| `GDIR` | `0x04` | `[31:0]` 1=output | RW | `0x00000000` | Direction |
| `PSR` | `0x08` | `[31:0]` | RO | pad state | Pad sample |
| `ICR1` | `0x0C` | 16× 2-bit (pin 0–15): 00=LOW,01=HIGH,10=RISE,11=FALL | RW | `0x00000000` | Int config |
| `ICR2` | `0x10` | pins 16–31 | RW | `0x00000000` | Int config |
| `IMR` | `0x14` | `[31:0]` mask | RW | `0x00000000` | Interrupt mask |
| `ISR` | `0x18` | `[31:0]` W1C | RW | `0x00000000` | Interrupt status |
| `EDGE_SEL` | `0x1C` | `[31:0]` | RW | `0x00000000` | Any-edge override |

### 1.5 UART1 (Debug Console) — UART1..UART5

**Bases:** UART1 `0x02020000`, UART2 `0x021E8000`, UART3 `0x021EC000`, UART4 `0x021F0000`, UART5 `0x021F4000`.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `URXD` | `0x000` | `[15]=CHARRDY`, `[14]=ERR`, `[13]=OVRRUN`, `[12]=FRMERR`, `[11]=BRK`, `[10]=PRERR`, `[7:0]=RX_DATA` | RO/V | `0x00000000` | RX FIFO (32-deep) |
| `UTXD` | `0x040` | `[7:0]=TX_DATA` | WO | — | TX FIFO (32-deep) |
| `UCR1` | `0x080` | `[0]=UARTEN`, `[1]=DOZE`, `[4]=RRDYEN`, `[6]=TXMPTYEN`, `[14]=ADBR` | RW | `0x00000000` | Control 1 |
| `UCR2` | `0x084` | `[0]=SRST`, `[1]=RXEN`, `[2]=TXEN`, `[5]=WS`(1=8-bit), `[6]=STPB`, `[14]=IRTS` | RW | `0x00000001` | Control 2 |
| `UCR3` | `0x088` | `[2]=RXDMUXSEL` (must be 1), `[10]=ADNIMP` | RW | `0x00000700` | Control 3 |
| `UCR4` | `0x08C` | `[0]=DREN`, `[3]=TCEN` | RW | `0x00008000` | Control 4 |
| `UFCR` | `0x090` | `[15:10]=TXTL`, `[8:7]=RFDIV` (001=div2), `[5:0]=RXTL` | RW | `0x00000801` | FIFO ctl |
| `USR1` | `0x094` | `[13]=PARITYERR`, `[12]=RTSS`, `[9]=TRDY`, `[6]=RRDY`, `[5]=AGTIM` | RW/W1C | `0x00002040` | Status 1 |
| `USR2` | `0x098` | `[15]=ADET`, `[3]=TXDC`, `[0]=RDR` | RW/W1C | `0x00004028` | Status 2 |
| `UBIR` | `0x0A4` | `[15:0]=INC` | RW | `0x00000000` | Baud inc |
| `UBMR` | `0x0A8` | `[15:0]=MOD` | RW | `0x00000000` | Baud mod |
| `UTS` | `0x0B4` | `[6]=TXEMPTY`, `[5]=RXEMPTY`, `[4]=TXFULL`, `[0]=SOFTRST` | RW | `0x00000060` | Test/stat |

Baud rate: `BR = F_perclk / (16 × (UBMR+1)/(UBIR+1))`. With `F_perclk = 80 MHz`, `UBIR=71`, `UBMR=2499` ⇒ 115200 baud.

### 1.6 I²C (I2C1/I2C2/I2C3)

**Bases:** I2C1 `0x021A0000`, I2C2 `0x021A4000`, I2C3 `0x021A8000`.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `IADR` | `0x00` | `[7:1]=ADR` | RW | `0x00000000` | Slave address (controller's own) |
| `IFDR` | `0x04` | `[5:0]=IC` (divider LUT) | RW | `0x00000000` | Freq div; `0x15`=100 kHz, `0x0A`=400 kHz @ perclk=66MHz |
| `I2CR` | `0x08` | `[7]=IEN`, `[6]=IIEN`, `[5]=MSTA`, `[4]=MTX`, `[3]=TXAK`, `[2]=RSTA` | RW | `0x00000000` | Control |
| `I2SR` | `0x0C` | `[7]=ICF`, `[5]=IBB`, `[4]=IAL`, `[1]=IIF`(W1C), `[0]=RXAK` | RW | `0x00000081` | Status |
| `I2DR` | `0x10` | `[7:0]=DATA` | RW | `0x00000000` | Data |

### 1.7 eCSPI (eCSPI1..eCSPI5)

**Bases:** eCSPI1 `0x02008000`, eCSPI2 `0x0200C000`, eCSPI3 `0x02010000`, eCSPI4 `0x02014000`, eCSPI5 `0x02018000`.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `RXDATA` | `0x00` | `[31:0]` | RO | `0x00000000` | RX FIFO (64×32) |
| `TXDATA` | `0x04` | `[31:0]` | WO | — | TX FIFO (64×32) |
| `CONREG` | `0x08` | `[31:20]=BURST_LENGTH`, `[19:18]=CHANNEL_SELECT`, `[17:12]=DRCTL`, `[15:12]=PRE_DIV`, `[11:8]=POST_DIV`, `[7:4]=CHANNEL_MODE`(1=master), `[3]=SMC`, `[2]=XCH`, `[1]=HT`, `[0]=EN` | RW | `0x00000000` | Control |
| `CONFIGREG` | `0x0C` | `[27:24]=HT_LENGTH`, `[23:20]=SCLK_CTL`, `[19:16]=DATA_CTL`, `[15:12]=SS_POL`, `[11:8]=SS_CTL`, `[7:4]=SCLK_POL`, `[3:0]=SCLK_PHA` | RW | `0x00000000` | SPI mode |
| `INTREG` | `0x10` | `[0]=TEEN`, `[1]=TDREN`, `[2]=TFEN`, `[3]=RREN`, `[4]=RDREN`, `[5]=RFEN`, `[6]=ROEN`, `[7]=TCEN` | RW | `0x00000000` | IRQ enable |
| `DMAREG` | `0x14` | `[7:0]=RXTDEN/RXDMAEN/TXTDEN/TXDMAEN`, watermarks | RW | `0x00400040` | DMA control |
| `STATREG` | `0x18` | `[0]=TE`, `[1]=TDR`, `[2]=TF`, `[3]=RR`, `[4]=RDR`, `[5]=RF`, `[6]=RO`(W1C), `[7]=TC`(W1C) | RW | `0x00000003` | Status |
| `PERIODREG` | `0x1C` | `[21:16]=CSD_CTL`, `[15]=CSRC`, `[14:0]=SAMPLE_PERIOD` | RW | `0x00000000` | Timing |
| `TESTREG` | `0x20` | `[31]=LBC` | RW | `0x00000000` | Loopback |

### 1.8 FEC (10/100/1000 Ethernet MAC)

**Base:** `0x02188000`. 1000BASE-T via RGMII to AR8031 PHY.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `EIR` | `0x004` | `[31]=HBERR`, `[28]=UN`, `[27]=RL`, `[26]=LC`, `[25]=EBERR`, `[24]=MII`, `[23]=RXB`, `[22]=RXF`, `[21]=TXB`, `[20]=TXF`, `[19]=TS_AVAIL`, `[18]=TS_TIMER` | W1C | `0x00000000` | IRQ status |
| `EIMR` | `0x008` | mirrors EIR | RW | `0x00000000` | IRQ mask |
| `RDAR` | `0x010` | `[24]=RDAR` | W1C | `0x00000000` | Receive descriptor active |
| `TDAR` | `0x014` | `[24]=TDAR` | W1C | `0x00000000` | Transmit descriptor active |
| `ECR` | `0x024` | `[8]=DBSWP`, `[5]=SPEED`, `[4]=DBG_EN`, `[2]=MAGIC_EN`, `[1]=ETHEREN`, `[0]=RESET` | RW | `0xF0000000` | MAC enable |
| `MMFR` | `0x040` | MDIO frame | RW | `0x00000000` | MII mgmt frame |
| `MSCR` | `0x044` | `[8:1]=MII_SPEED`, `[0]=DIS_PRE` | RW | `0x00000000` | MII speed |
| `MIBC` | `0x064` | `[31]=MIB_DIS`, `[30]=MIB_IDLE`, `[29]=MIB_CLEAR` | RW | `0xC0000000` | MIB ctl |
| `RCR` | `0x084` | `[26]=GRS`, `[9]=RGMII_EN`, `[8]=RMII_MODE`, `[5]=MII_MODE`, `[2]=PROM`, `[1]=MII_LOOP`, `[0]=LOOP` | RW | `0x05EE0001` | RX control |
| `TCR` | `0x0C4` | `[10]=CRCFWD`, `[9]=ADDINS`, `[2]=FDEN` | RW | `0x00000000` | TX control |
| `PALR/PAUR` | `0x0E4/0x0E8` | 48-bit MAC | RW | fuse | Station address |
| `IAUR/IALR` | `0x118/0x11C` | hash | RW | `0x00000000` | Individual hash |
| `TFWR` | `0x144` | `[8]=STRFWD`, `[5:0]=TFWR` | RW | `0x00000000` | TX FIFO WM |
| `RDSR` | `0x180` | `[31:3]` aligned | RW | `0x00000000` | RX BD ring base (64-byte aligned) |
| `TDSR` | `0x184` | `[31:3]` aligned | RW | `0x00000000` | TX BD ring base |
| `MRBR` | `0x188` | `[13:4]` | RW | `0x00000000` | Max RX buffer |
| `RACC` | `0x1C4` | `[7]=SHIFT16`, `[6]=LINEDIS`, `[2]=PRODIS`, `[0]=PADREM` | RW | `0x00000000` | RX accelerator |

### 1.9 uSDHC (uSDHC1..uSDHC4)

**Bases:** uSDHC1 `0x02190000`, uSDHC2 `0x02194000`, uSDHC3 `0x02198000`, uSDHC4 `0x0219C000`.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `DS_ADDR` | `0x00` | `[31:0]` | RW | `0x00000000` | DMA sys addr |
| `BLK_ATT` | `0x04` | `[28:16]=BLKCNT`, `[12:0]=BLKSIZE` | RW | `0x00000000` | Block attrs |
| `CMD_ARG` | `0x08` | `[31:0]` | RW | `0x00000000` | Command arg |
| `CMD_XFR_TYP` | `0x0C` | `[29:24]=CMDINX`, `[23:22]=CMDTYP`, `[21]=DPSEL`, `[20]=CICEN`, `[19]=CCCEN`, `[17:16]=RSPTYP`, `[4]=MSBSEL`, `[2]=DTDSEL`, `[0]=DMAEN` | RW | `0x00000000` | Transfer type |
| `CMD_RSP0..3` | `0x10..0x1C` | 128-bit response | RO | `0x00000000` | Response |
| `DATA_BUFF_ACC_PORT` | `0x20` | `[31:0]` | RW | `0x00000000` | PIO data |
| `PRES_STATE` | `0x24` | `[24]=CDPL`, `[19]=CINHD`, `[18]=CINHC`, `[3]=SDSTB`, `[1]=DLA`, `[0]=CIHB` | RO | — | Status |
| `PROT_CTRL` | `0x28` | `[9:8]=DMASEL` (0=SDMA,2=ADMA2), `[2:1]=DTW` (00=1b,01=4b,10=8b) | RW | `0x00800020` | Protocol |
| `SYS_CTRL` | `0x2C` | `[27:24]=DTOCV`, `[23:16]=SDCLKFS`, `[15:12]=DVS`, `[28]=IPP_RST_N`, `[26]=INITA`, `[25:24]=SFTRST_T/A/C` | RW | `0x80800000` | Clock/reset |
| `INT_STATUS` | `0x30` | `[16]=CTOE`, `[17]=CCE`, `[0]=CC`, `[1]=TC`, `[6]=CINS`, `[7]=CRM` | W1C | `0x00000000` | IRQ status |
| `INT_STATUS_EN` | `0x34` | mirror | RW | `0x00000000` | IRQ enable |
| `INT_SIGNAL_EN` | `0x38` | mirror | RW | `0x00000000` | IRQ signal |
| `MIX_CTRL` | `0x48` | `[5]=AC12EN`, `[0]=DMAEN`, `[1]=BCEN`, `[2]=AC12EN`, `[4]=MSBSEL`, `[3]=DTDSEL` | RW | `0x80000000` | Mixer |
| `ADMA_SYS_ADDR` | `0x58` | `[31:2]` | RW | `0x00000000` | ADMA2 desc table |

### 1.10 FlexCAN (CAN1, CAN2)

**Bases:** CAN1 `0x02090000`, CAN2 `0x02094000`. 64 message buffers, CAN 2.0B.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `MCR` | `0x00` | `[31]=MDIS`, `[30]=FRZ`, `[28]=HALT`, `[27]=NOTRDY`, `[26]=WAK_MSK`, `[25]=SOFT_RST`, `[24]=FRZACK`, `[23]=SUPV`, `[16]=WRN_EN`, `[13]=LPM_ACK`, `[12]=SRX_DIS`, `[10]=IRMQ`, `[7:0]=MAXMB` | RW | `0xD890000F` | Module control |
| `CTRL1` | `0x04` | `[31:24]=PRESDIV`, `[23:22]=RJW`, `[21:19]=PSEG1`, `[18:16]=PSEG2`, `[15]=BOFF_MSK`, `[13]=ERR_MSK`, `[12]=CLK_SRC`(1=PERIPH), `[11]=LPB`, `[7]=SMP`, `[2:0]=PROPSEG` | RW | `0x00000000` | Bit-timing 1 |
| `TIMER` | `0x08` | `[15:0]` | RW | `0x00000000` | Free-running timer |
| `RXMGMASK` | `0x10` | `[31:0]` | RW | `0x00000000` | Global RX mask |
| `ECR` | `0x1C` | `[15:8]=RXERRCNT`, `[7:0]=TXERRCNT` | RO | `0x00000000` | Error counters |
| `ESR1` | `0x20` | `[18]=SYNCH`, `[17]=TWRN`, `[16]=RWRN`, `[15:10]=error bits`, `[9:8]=FLTCONF`, `[5]=TX`, `[4:2]=FLT`, `[1]=ERRINT`, `[0]=WAKINT` | W1C | `0x00000000` | Error/status |
| `IMASK1` | `0x28` | `[31:0]` per-MB enable | RW | `0x00000000` | MB0–31 mask |
| `IFLAG1` | `0x30` | `[31:0]` W1C | RW | `0x00000000` | MB0–31 flag |
| `MB[0..63]` | `0x80–0x47F` | 4×32b: CS, ID, DATA[0..1] | RW | `0x00000000` | Message buffers |
| `RXIMR[0..63]` | `0x880–0x97F` | per-MB mask | RW | `0x00000000` | Individual RX mask |

### 1.11 SDMA Controller

**Base:** `0x020EC000`. 32 channels, ARM926 core running scripts from OCRAM.

| Register | Offset | Bit-fields | R/W | Reset | Description |
|---|---|---|---|---|---|
| `MC0PTR` | `0x000` | `[31:0]` | RW | `0x00000000` | CCB array base (64-byte aligned) |
| `INTR` | `0x004` | `[31:0]` W1C | RW | `0x00000000` | Channel interrupt |
| `STOP_STAT` | `0x008` | `[31:0]` | RW | `0x00000000` | Channel stop |
| `HSTART` | `0x00C` | `[31:0]` | RW | `0x00000000` | Host start |
| `EVTOVR` | `0x010` | `[31:0]` | RW | `0x00000000` | Event override |
| `EVTPEND` | `0x018` | `[31:0]` | RW | `0x00000000` | DMA event pending |
| `RESET` | `0x024` | `[0]=RESCHED` | RW | `0x00000000` | Reset |
| `EVTERR` | `0x028` | `[31:0]` | RO | `0x00000000` | Event error |

### 1.12 Audio SSI/SAI, GPT, WDT, PWM, USB-OTG, HDMI, MIPI-CSI/DSI, IPU, PCIe

Full per-register tables for these blocks are sized >30 pages; the BSP driver list below locks the **base addresses** that device-tree `reg = <>` entries must resolve to. Driver-internal register access is through `regmap`; per-bit detail is delegated to IMX6DQRM chapters cited.

| Peripheral | Base Addr | Size | IMX6DQRM Ch. |
|---|---|---|---|
| AIPS-1 cfg | `0x0207C000` | 16 KiB | 9.3 |
| AIPS-2 cfg | `0x0217C000` | 16 KiB | 9.3 |
| GPT | `0x02098000` | 16 KiB | 30 |
| EPIT1 | `0x020D0000` | 16 KiB | 24 |
| EPIT2 | `0x020D4000` | 16 KiB | 24 |
| WDOG1 | `0x020BC000` | 16 KiB | 71 |
| WDOG2 (TZ) | `0x020C0000` | 16 KiB | 71 |
| PWM1..4 | `0x02080000`..`0x0208C000` | 16 KiB ea | 41 |
| SAI1..3 | `0x02028000`..`0x02030000` | — | 62 |
| SSI1..3 | `0x02028000`..`0x02030000` | 16 KiB ea | 61 |
| ASRC | `0x02034000` | 16 KiB | 22 |
| USB-OTG/USB-H1 | `0x02184000` | 2 KiB/port | 66 |
| USB-PHY0/1 | `0x020C9000`/`0x020CA000` | 4 KiB | 67 |
| IPU1 | `0x02600000` | 4 MiB | 37 |
| IPU2 | `0x02A00000` | 4 MiB | 37 |
| HDMI-TX | `0x00120000` | 32 KiB | 34 |
| MIPI-CSI | `0x021DC000` | 16 KiB | 38 |
| MIPI-DSI | `0x021E0000` | 16 KiB | 39 |
| VPU | `0x02040000` | 16 KiB + OCRAM | 73 |
| GPU3D (GC2000) | `0x00130000` | 16 KiB | 33 |
| GPU2D (GC320) | `0x00134000` | 16 KiB | 33 |
| PCIe controller | `0x01FFC000` | 16 KiB | 45 |
| OCOTP (fuses) | `0x021BC000` | 16 KiB | 42 |
| SNVS (RTC+SRTC) | `0x020CC000` | 16 KiB | 56 |
| MMDC (DDR ctl) | `0x021B0000` | 16 KiB | 36 |

---

## 2. PIN / SIGNAL ASSIGNMENT TABLE

Signals that the BSP's pinctrl groups must configure. Voltage is I/O-bank VDD; SabreSD uses NVCC_<bank> regulators from PMIC PF0100.

### 2.1 Boot, Debug & Power

| Pin Name | MCU Pad | Direction | Voltage | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `BOOT_MODE0/1` | `BOOT_MODE0/1` | In | 3V3 | PD | DC | Boot fuses (fuse=eMMC) |
| `PMIC_RDY` | `GPIO1_IO08` | In | 3V3 | PU | DC | PMIC PF0100 ready (PWRON) |
| `PWR_ON` | `GPIO1_IO00` | Out | 3V3 | — | DC | System power hold |
| `SYS_RST_B` | `POR_B` | In | 3V3 | PU | DC | Power-on reset |
| `CONSOLE_TXD` | `CSI0_DAT10` | Out push-pull | 3V3 | — | ≤3 Mb/s | UART1_TXD (ALT3) to J509 |
| `CONSOLE_RXD` | `CSI0_DAT11` | In | 3V3 | PU 100k | ≤3 Mb/s | UART1_RXD (ALT3) from J509 |
| `JTAG_TCK` | `JTAG_TCK` | In | 3V3 | PD | ≤10 MHz | JTAG clk (J507) |
| `JTAG_TMS/TDI/TDO/TRSTB` | `JTAG_*` | Bi | 3V3 | PU | — | JTAG |

### 2.2 Ethernet (RGMII to AR8031)

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `ENET_MDC` | `KEY_COL1` | Out | 3V3 | — | 2.5 MHz | MDC (ALT2) |
| `ENET_MDIO` | `KEY_COL2` | Bi OD | 3V3 | PU 100k | 2.5 MHz | MDIO (ALT2) |
| `RGMII_TXC` | `RGMII_TXC` | Out | 2V5 | — | 125 MHz | TX clock |
| `RGMII_TD[0:3]` | `RGMII_TD[0:3]` | Out | 2V5 | — | 125 MHz DDR | TX data |
| `RGMII_TX_CTL` | `RGMII_TX_CTL` | Out | 2V5 | — | 125 MHz | TX enable |
| `RGMII_RXC` | `RGMII_RXC` | In | 2V5 | — | 125 MHz | RX clock |
| `RGMII_RD[0:3]` | `RGMII_RD[0:3]` | In | 2V5 | — | 125 MHz DDR | RX data |
| `RGMII_RX_CTL` | `RGMII_RX_CTL` | In | 2V5 | — | 125 MHz | RX valid |
| `ENET_RST_B` | `ENET_CRS_DV` | Out | 3V3 | — | DC | PHY reset (active low) |
| `ENET_INT_B` | `ENET_RXD1` (GPIO1_26) | In | 3V3 | PU | DC | PHY interrupt |

### 2.3 eMMC (uSDHC4, 8-bit, 1V8/3V3 DDR)

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `eMMC_CLK` | `SD4_CLK` | Out | 1V8 | — | ≤200 MHz | uSDHC4 clk (HS200) |
| `eMMC_CMD` | `SD4_CMD` | Bi | 1V8 | PU 47k | | uSDHC4 CMD |
| `eMMC_D0..D7` | `SD4_DAT0..7` | Bi | 1V8 | PU 47k | | Data |
| `eMMC_RST` | `SD4_RESET` | Out | 1V8 | — | DC | eMMC H/W reset |

### 2.4 SD Card Slot (uSDHC3, 4-bit, UHS-I)

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `SD3_CLK` | `SD3_CLK` | Out | 3V3/1V8 | — | ≤208 MHz | clk |
| `SD3_CMD` | `SD3_CMD` | Bi | 3V3/1V8 | PU 47k | | cmd |
| `SD3_D[0:3]` | `SD3_DAT[0:3]` | Bi | 3V3/1V8 | PU 47k | | data |
| `SD3_CD` | `NANDF_D0` (GPIO2_0) | In | 3V3 | PU | DC | Card-detect |
| `SD3_WP` | `NANDF_D1` (GPIO2_1) | In | 3V3 | PU | DC | Write-protect |

### 2.5 I²C Buses

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `I2C1_SCL` | `EIM_D21` | OD | 3V3 | Ext PU 4k7 | 400 kHz | PMIC, codec (SGTL5000) |
| `I2C1_SDA` | `EIM_D28` | OD | 3V3 | Ext PU 4k7 | 400 kHz | |
| `I2C2_SCL` | `KEY_COL3` | OD | 3V3 | Ext PU 4k7 | 400 kHz | HDMI DDC, port expander |
| `I2C2_SDA` | `KEY_ROW3` | OD | 3V3 | Ext PU 4k7 | 400 kHz | |
| `I2C3_SCL` | `GPIO_3` | OD | 3V3 | Ext PU 4k7 | 400 kHz | Touch, mag/accel, light sensor |
| `I2C3_SDA` | `GPIO_6` | OD | 3V3 | Ext PU 4k7 | 400 kHz | |

### 2.6 SPI (eCSPI1 — user expansion)

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `ECSPI1_SCLK` | `EIM_D16` | Out | 3V3 | — | ≤52 MHz | SPI clock |
| `ECSPI1_MOSI` | `EIM_D17` | Out | 3V3 | — | ≤52 MHz | Master-out |
| `ECSPI1_MISO` | `EIM_D18` | In | 3V3 | PU 100k | ≤52 MHz | Master-in |
| `ECSPI1_SS0` | `EIM_D19` | Out | 3V3 | PU | ≤52 MHz | Chip-select 0 |

### 2.7 CAN (FlexCAN1)

| Pin Name | MCU Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `CAN1_TX` | `KEY_ROW2` | Out | 3V3 | — | ≤1 Mb/s | To TJA1041 transceiver |
| `CAN1_RX` | `KEY_COL2` | In | 3V3 | PU | ≤1 Mb/s | From transceiver |
| `CAN1_STBY` | `GPIO_2` | Out | 3V3 | — | DC | Transceiver standby |

### 2.8 Audio (SSI2 → SGTL5000)

| Pin | Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `AUD_TXC/RXC` | `DISP0_DAT20/19` | Bi | 3V3 | — | 12.288 MHz BCLK | I²S bit-clk |
| `AUD_TXFS/RXFS` | `DISP0_DAT21/18` | Bi | 3V3 | — | 48 kHz LRCK | Frame-sync |
| `AUD_TXD` | `DISP0_DAT23` | Out | 3V3 | — | — | I²S data out |
| `AUD_RXD` | `DISP0_DAT22` | In | 3V3 | PD | — | I²S data in |
| `AUDIO_MCLK` | `GPIO_0` (CCM_CLKO1) | Out | 3V3 | — | 24.576 MHz | Codec MCLK |

### 2.9 Display (HDMI + MIPI-DSI + LVDS) and Camera (MIPI-CSI)

| Pin | Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `HDMI_TX_D[0:2]±` | dedicated | Out diff | HDMI | — | ≤340 MHz TMDS | HDMI lanes |
| `HDMI_TX_CLK±` | dedicated | Out diff | HDMI | — | ≤340 MHz | HDMI pixel clk |
| `HDMI_CEC` | `KEY_ROW2` (ALT6) | OD | 3V3 | PU | 40 kHz | CEC |
| `MIPI_CSI_D[0:1]±/CLK±` | dedicated | In diff | MIPI | — | ≤1 Gb/s/lane | CSI-2 2-lane |
| `MIPI_DSI_D[0:1]±/CLK±` | dedicated | Out diff | MIPI | — | ≤1 Gb/s/lane | DSI 2-lane |
| `LVDS0_TX[0:3]±/CLK±` | dedicated | Out diff | LVDS | — | 85 MHz | LVDS ch0 |

### 2.10 USB

| Pin | Pad | Dir | V | Pull | Function |
|---|---|---|---|---|---|
| `USB_OTG_ID` | `ENET_RX_ER` (GPIO1_24) | In | 3V3 | PU | ID sense |
| `USB_OTG_PWR` | `EIM_D22` | Out | 3V3 | — | VBUS enable (USB1) |
| `USB_OTG_OC` | `KEY_COL4` | In | 3V3 | PU | Over-current |
| `USB_H1_PWR` | `ENET_TXD1` | Out | 3V3 | — | VBUS enable (H1) |
| `USB_H1_OC` | `EIM_D30` | In | 3V3 | PU | Over-current |

### 2.11 Touch (Atmel mXT224 — I²C3 + IRQ)

| Pin | Pad | Dir | V | Pull | Function |
|---|---|---|---|---|---|
| `TOUCH_IRQ` | `GPIO_9` (GPIO1_9) | In | 3V3 | PU | Falling-edge |
| `TOUCH_RST` | `SD1_DAT2` | Out | 3V3 | — | Active-low reset |

### 2.12 Wi-Fi/BT (uSDHC2 + UART3)

| Pin | Pad | Dir | V | Pull | Freq | Function |
|---|---|---|---|---|---|---|
| `WL_CLK/CMD/D0..3` | `SD2_*` | Bi | 1V8 | PU 47k | 50 MHz | SDIO to BCM4329 |
| `WL_REG_ON` | `EIM_D29` | Out | 3V3 | — | DC | Wi-Fi enable |
| `WL_HOST_WAKE` | `NANDF_CS1` | In | 3V3 | PU | edge | Wake signal |
| `BT_UART_TXD` | `EIM_D24` | Out | 3V3 | — | 3 Mb/s | UART3 TX |
| `BT_UART_RXD` | `EIM_D25` | In | 3V3 | PU | 3 Mb/s | UART3 RX |
| `BT_CTS/RTS` | `EIM_D26/27` | Bi | 3V3 | — | | H4 flow ctl |
| `BT_REG_ON` | `NANDF_CS0` | Out | 3V3 | — | DC | BT enable |

---

## 3. INTERRUPT ASSIGNMENT TABLE

GIC SPI numbering = IMX6DQRM "IRQ #" + 32. Priority: Cortex-A9 GIC supports 32 levels (upper 5 bits). Lower numeric value = higher priority. Latency budget measured from GIC pending to handler entry on CPU0.

| Interrupt Name | IRQ# (SPI) | GIC ID | Priority | Trigger | Max Latency | Handler (driver) |
|---|---|---|---|---|---|---|
| `SDMA` | 2 | 34 | 0x20 | Level | 5 µs | `imx_sdma` irq |
| `GPU3D` | 9 | 41 | 0xA0 | Level | 100 µs | `etnaviv` |
| `IPU1_SYNC` | 6 | 38 | 0x30 | Level | 1 frame period (16.6 ms) | `ipu-common` |
| `IPU1_ERR` | 5 | 37 | 0x40 | Level | 100 µs | `ipu-common` |
| `IPU2_SYNC` | 8 | 40 | 0x30 | Level | 16.6 ms | `ipu-common` |
| `VPU_JPEG` | 3 | 35 | 0x40 | Level | 1 ms | `coda` |
| `GP