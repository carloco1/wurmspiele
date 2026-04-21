# DETAILED DESIGN DOCUMENT
## NXP i.MX6Q SabreSD — Linux BSP Driver Package

**Document ID:** DDD-IMX6Q-BSP-001
**Version:** 1.0
**Stage:** V-Model Stage 6 (Detailed Design)
**Pairs with:** Stage 10 — Unit Tests (SwUT-IMX6Q-BSP-001)
**Traces upward to:** SAD-IMX6Q-BSP-001 v1.0, SwRS-IMX6Q-BSP-001 v1.0
**Target Kernel:** Linux 6.6 LTS
**Target Toolchain:** arm-linux-gnueabihf-gcc 13.2 (-march=armv7-a -mfpu=vfpv3-d16 -mfloat-abi=hard)

---

## 0. CONVENTIONS

- `DDD-Mxx-nn` = Detailed-design item `nn` belonging to module `Mxx`.
- WCET numbers assume i.MX6Q @ 996 MHz, L1 warm, no cache stalls unless noted. Measured with `arch_timer` (cnt @ 8 MHz, 125 ns tick).
- Stack budgets sum caller-saved + locals + one nested call, rounded up to 8 B.
- All register offsets and bit masks come from **i.MX 6Dual/6Quad Applications Processor Reference Manual, Rev. 5, 06/2019** (hereafter "RM").
- "Test build" = `CONFIG_KUNIT=y` + `CONFIG_BSP_UT=y`; exposes `static` symbols via `__visible_for_testing` macro.

---

## 1. MODULE DETAILED DESIGNS

---

### M01 — `mach-imx6q` (arch/arm/mach-imx/mach-imx6q.c)

#### 1.1 PURPOSE & SCOPE (DDD-M01-01)
Register the SabreSD machine descriptor, perform SoC-wide platform quirks (ARM errata 761320/794072, PLxxx bus fabric init, PSCI bringup), then yield control to Device-Tree-driven driver probing. Module owns **no** runtime state after `late_initcall`; it is effectively boot-only.

#### 1.2 STATE MACHINE (DDD-M01-02)

```
   +-----------+  smp_init_cpus()  +-----------+
   | PRE_SMP   |------------------>|  SMP_UP   |
   +-----------+                   +-----------+
         |                                |
         | init_early()                   | init_machine()
         v                                v
   +-----------+                   +-----------+
   | EARLY_OK  |------------------>| DT_POPUL  |
   +-----------+                   +-----------+
                                         |
                                         | late_initcall()
                                         v
                                   +-----------+
                                   |  RUNTIME  |  (no further state changes)
                                   +-----------+
```

State × Event → Next / Action:

| State     | Event                     | Next      | Action                                 |
|-----------|---------------------------|-----------|----------------------------------------|
| PRE_SMP   | `smp_init_cpus`           | SMP_UP    | Read `ARM_GIC` base; patch PSCI ops    |
| SMP_UP    | `init_early`              | EARLY_OK  | Apply ARM errata, enable L2310         |
| EARLY_OK  | `init_machine`            | DT_POPUL  | `of_platform_default_populate()`       |
| DT_POPUL  | `late_initcall (quirks)`  | RUNTIME   | Apply SabreSD SoC quirks, print banner |
| RUNTIME   | (any)                     | RUNTIME   | no-op                                  |

#### 1.3 ALGORITHMS & DATA STRUCTURES (DDD-M01-03)

No non-trivial algorithms; single-shot initialisation sequence.

```
function imx6q_init_machine():
    soc_dev = imx_soc_device_init()   # reads OCOTP for silicon rev
    if soc_dev == NULL: WARN; continue
    of_platform_default_populate(NULL, NULL, parent=soc_dev)
    imx_anatop_init()
    cpu_is_imx6q() ? imx6q_pm_init() : imx6dl_pm_init()
    return
```

Complexity: O(N) in DT nodes, N ≤ 128 on SabreSD → < 5 ms on cold cache.

#### 1.4 INTERNAL DATA LAYOUT (DDD-M01-04)

| Symbol                         | Type                     | Init      | Access                  |
|--------------------------------|--------------------------|-----------|-------------------------|
| `imx6q_dt_compat[]`            | `const char * const[]`   | `"fsl,imx6q-sabresd", …, NULL` | read-only, text segment |
| `imx6q_dt_fixup`               | `static void(*)(void)`   | `&imx6q_1588_init` | read-only |
| `mach_soc_id`                  | `static u32`             | 0         | write-once in `init_early` |

No runtime mutable globals.

#### 1.5 FUNCTION-LEVEL DESIGN (DDD-M01-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `imx6q_init_early` | — | void | Sets `outer_cache` ops; CPU errata MSRs | MMU on, GIC mapped | L2 cache enabled |
| `imx6q_init_machine` | — | void | Populates platform-bus; bringup imx-anatop | EARLY_OK | All DT platform_devices exist |
| `imx6q_init_late` | — | void | Registers cpufreq, cpuidle; prints banner | DT_POPUL | RUNTIME |
| `imx6q_map_io` | — | void | `iotable_init()` for AIPS-1/2 | Before MMU late | Static I/O mapping present |
| `imx6q_1588_init` | — | void | Patch ENET_REF clk to 50 MHz oscillator | clk-imx6q probed | fec_main probes OK |

#### 1.6 TIMING & RESOURCE USAGE (DDD-M01-06)

| Function           | WCET     | Stack |
|--------------------|----------|-------|
| `imx6q_init_early` | 80 µs    | 64 B  |
| `imx6q_map_io`     | 20 µs    | 48 B  |
| `imx6q_init_machine` | 4.5 ms | 192 B |
| `imx6q_init_late`  | 1.2 ms   | 128 B |
| `imx6q_1588_init`  | 15 µs    | 32 B  |

---

### M02 — `clk-imx6q` (drivers/clk/imx/clk-imx6q.c)

#### 2.1 PURPOSE & SCOPE (DDD-M02-01)
Construct the full i.MX6Q clock graph (≈ 240 clocks: 7 PLLs, 24 PFDs, muxes, dividers, gates), expose it to CCF via `CLK_OF_DECLARE`, before any peripheral probe. Driver owns a single `clk_onecell_data` array indexed by `IMX6QDL_CLK_*`.

#### 2.2 STATE MACHINE (DDD-M02-02)

```
  +---------+ probe  +----------+ register +----------+ of_clk_add  +----------+
  |  NONE   |------->| PLL_INIT |--------->| TREE_REG |------------>|  READY   |
  +---------+        +----------+          +----------+             +----------+
                         | fail                                          |
                         v                                               v
                     +---------+                                   +----------+
                     |  FAULT  |<----------------------------------|  READY   |
                     +---------+    (unrecoverable)                +----------+
```

| State    | Event                  | Next     | Action                                 |
|----------|------------------------|----------|----------------------------------------|
| NONE     | `of_clk_init`          | PLL_INIT | ioremap CCM, ANATOP; assert PLL lock   |
| PLL_INIT | all PLLs locked        | TREE_REG | `imx_clk_hw_fixed/mux/divider/gate`    |
| PLL_INIT | PLL lock timeout (1 ms)| FAULT    | `panic("PLL not locked")`              |
| TREE_REG | `of_clk_add_hw_provider` OK | READY| Unmask pm-runtime                      |

#### 2.3 ALGORITHMS & DATA STRUCTURES (DDD-M02-03)

**PLL lock wait** (RM §18.5):

```
wait_pll_lock(pll_base, bit):
    t0 = ktime_get()
    while (readl(pll_base) & bit) == 0:
        if ktime_to_us(ktime_sub(ktime_get(), t0)) > 1000:
            return -ETIMEDOUT
        cpu_relax()
    return 0
```

Time complexity O(polling), bounded 1 ms ⇒ WCET 1 ms hard cap.

**Tree registration** is table-driven:

```
for each entry in clk_table[]:
    clks[id] = imx_clk_hw_<kind>(name, parent, reg, shift, width)
clks_init_data.hws = clks
clks_init_data.num = IMX6QDL_CLK_END
of_clk_add_hw_provider(np, of_clk_hw_onecell_get, &clks_init_data)
```

Time O(N) for N=240 clocks, ≈ 2 ms.

#### 2.4 INTERNAL DATA LAYOUT (DDD-M02-04)

| Symbol                     | Type                                  | Init          | Access rules             |
|----------------------------|---------------------------------------|---------------|--------------------------|
| `clks[IMX6QDL_CLK_END]`    | `struct clk_hw *`                     | all NULL      | write during probe only  |
| `clk_hw_onecell_data`      | `struct clk_hw_onecell_data`          | zero          | written once, read by CCF|
| `ccm_base`                 | `void __iomem *`                      | NULL          | written once             |
| `anatop_base`              | `void __iomem *`                      | NULL          | written once             |
| `ccm_lock`                 | `DEFINE_SPINLOCK`                     | unlocked      | guards RMW on CCM regs   |

`IMX6QDL_CLK_END = 280`, array size ≈ 1.1 KiB of `struct clk_hw *`.

#### 2.5 FUNCTION-LEVEL DESIGN (DDD-M02-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `imx6q_clocks_init(np)` | DT node | void | ioremap; populates `clks[]` | ANATOP + CCM in DT | TREE READY |
| `imx_clk_hw_pllv3(...)` | type, name, parent, base, div_mask | `clk_hw *` | `kzalloc` via devm | CCM locked | PLL registered, not enabled |
| `imx_clk_hw_pfd(...)`   | name, parent, reg, idx | `clk_hw *` | kzalloc | PLL3/PLL2 ready | PFD clock node created |
| `wait_pll_lock(base,bit)` | regs | `0/-ETIMEDOUT` | none | PLL powered | lock bit set |
| `_readl/_writel_ccm()` | reg, val | val | MMIO + memory barriers | map present | RMW atomic per `ccm_lock` |
| `imx6q_mmdc_ch1_mask_handshake()` | — | void | clears handshake bit | before PLL retune | bypass completes ≤100 µs |

#### 2.6 TIMING & RESOURCE USAGE (DDD-M02-06)

| Function                  | WCET    | Stack |
|---------------------------|---------|-------|
| `imx6q_clocks_init`       | 3 ms    | 384 B |
| `wait_pll_lock`           | 1 ms    | 48 B  |
| `imx_clk_hw_pllv3`        | 45 µs   | 96 B  |
| `imx6q_mmdc_ch1_mask_handshake` | 100 µs | 32 B |

---

### M03 — `pinctrl-imx6q` (drivers/pinctrl/freescale/pinctrl-imx6q.c)

#### 3.1 PURPOSE & SCOPE (DDD-M03-01)
Drive the IOMUXC block (0x020E0000), expose pin-mux + pad-config groups to the `pinctrl` core. Uses the generic `pinctrl-imx` helper; i.MX6Q-specific only in its pad list.

#### 3.2 STATE MACHINE

Not applicable — stateless service after probe; each `pinctrl_select_state()` is a synchronous RMW burst.

#### 3.3 ALGORITHMS & DATA STRUCTURES (DDD-M03-03)

**Apply a pinctrl state** (per pin):

```
for pin in state.pins:
    writel(pin.mux_val,  iomuxc + pin.mux_reg)
    if pin.cfg_reg != 0:
        writel(pin.cfg_val, iomuxc + pin.cfg_reg)
    if pin.input_reg != 0:   # daisy-chain select
        writel(pin.input_val, iomuxc + pin.input_reg)
```

Complexity O(P), P = pins in state (typical 4…16), ~50 ns/pin → < 1 µs.

#### 3.4 INTERNAL DATA LAYOUT (DDD-M03-04)

| Symbol                | Type                              | Init            | Access                   |
|-----------------------|-----------------------------------|-----------------|--------------------------|
| `imx6q_pinctrl_pads[]`| `const struct pinctrl_pin_desc[]` | generated table | read-only                |
| `imx6q_pinctrl_info`  | `struct imx_pinctrl_soc_info`     | .pads=..., .npads=220 | read-only          |
| `ipctl->mmio_base`    | `void __iomem *`                  | from probe      | per-instance, write-once |

Pad table is ≈ 220 entries × 64 B = 14 KiB `.rodata`.

#### 3.5 FUNCTION-LEVEL DESIGN (DDD-M03-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `imx6q_pinctrl_probe(pdev)` | pdev | 0/-errno | devm ioremap; register pinctrl dev | DT pin groups valid | node in /sys/kernel/debug/pinctrl |
| `imx_pmx_set(pctldev,fn,grp)` | handles | 0/-EINVAL | writes mux regs | probed | mux active |
| `imx_pinconf_set(pctldev,pin,cfg,n)` | pin, cfg array | 0/-EINVAL | writes pad cfg | probed | pad cfg active |
| `imx_pinctrl_parse_groups()` | DT node | 0/-errno | kalloc group descr | DT ok | groups in pctldev |

#### 3.6 TIMING & RESOURCE USAGE (DDD-M03-06)

| Function        | WCET    | Stack |
|-----------------|---------|-------|
| `imx_pmx_set` (16 pins) | 1.2 µs | 64 B |
| `imx_pinconf_set` (1 pin) | 120 ns | 48 B |
| `imx6q_pinctrl_probe` | 6 ms | 512 B |

---

### M04 — `gpio-mxc` (drivers/gpio/gpio-mxc.c)

#### 4.1 PURPOSE & SCOPE (DDD-M04-01)
Drive 7 GPIO banks (32 lines each, 224 total), expose through gpiolib, multiplex bank-level IRQs into 32 line IRQs via an IRQ domain.

#### 4.2 STATE MACHINE (per line)

```
     unused  --request_gpio-->  OWNED  --set_direction-->  IN|OUT
       ^                                                    |
       |<----------- free_gpio --------------+--------------+
     masked  <--disable_irq--  IRQ_ON  --enable_irq-->  IRQ_ON
```

| State | Event | Next | Action |
|---|---|---|---|
| unused | `gpio_request` | OWNED | mark bitmap |
| OWNED  | `gpio_dir_in`  | IN    | clear GDIR bit |
| OWNED  | `gpio_dir_out` | OUT   | set GDIR bit |
| IN     | `irq_request_trigger` | IRQ_ON | program ICR1/2, unmask IMR |
| IRQ_ON | mask           | masked| clear IMR bit |

#### 4.3 ALGORITHMS (DDD-M04-03)

**Bank IRQ demux (`mxc_gpio_irq_handler`)**, hot path:

```
isr = readl(bank + GPIO_ISR) & readl(bank + GPIO_IMR)
while isr:
    n = __ffs(isr)                # 1-cycle ARMv7
    generic_handle_domain_irq(domain, n)
    isr &= ~(1 << n)
```

Complexity O(k) where k = set bits; WCET for k=32 bursty is ≈ 2.1 µs (incl. nested handler dispatch latency budget tracked separately).

#### 4.4 INTERNAL DATA LAYOUT (DDD-M04-04)

| Symbol | Type | Init | Access |
|---|---|---|---|
| `mxc_gpio_ports[7]` | `struct mxc_gpio_port` | zero | per-bank, locked by `port->lock` |
| `port->base`        | `void __iomem *` | probe | write-once |
| `port->gc`          | `struct gpio_chip` | built in probe | read-mostly |
| `port->lock`        | `raw_spinlock_t` | unlocked | protects GDIR/DR RMW in IRQ context |
| `port->both_edges`  | `u32` (bitmap) | 0 | updated by `mxc_gpio_set_irq_type` |

#### 4.5 FUNCTION-LEVEL DESIGN (DDD-M04-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `mxc_gpio_probe(pdev)` | pdev | 0/-errno | devm ioremap; gpiochip_add_data; irq_domain_add_linear | pinctrl up | bank ready |
| `mxc_gpio_get(gc,off)` | off | 0/1 | readl PSR | OWNED | — |
| `mxc_gpio_set(gc,off,v)` | off, v | void | rmw DR under lock | OUT | pin driven |
| `mxc_gpio_direction_input/output(gc,off[,v])` | off | 0 | rmw GDIR under lock | OWNED | dir set |
| `mxc_gpio_set_irq_type(d,type)` | d, flag | 0/-EINVAL | rmw ICR1/2 (+EDGE_SEL for BOTH) | masked | type programmed |
| `mxc_gpio_irq_handler(desc)` | desc | void | drains ISR, acks, dispatches | IRQ_ON | all pending handled |
| `mx3_mxc_gpio_handle_irq(isr)` | isr | void | inlined hot loop | in hardirq | — |

#### 4.6 TIMING & RESOURCE USAGE (DDD-M04-06)

| Function | WCET | Stack |
|---|---|---|
| `mxc_gpio_get` | 250 ns | 24 B |
| `mxc_gpio_set` | 420 ns | 32 B |
| `mxc_gpio_set_irq_type` | 900 ns | 48 B |
| `mxc_gpio_irq_handler` (32 lines) | 2.1 µs | 96 B |

---

### M05 — `sdhci-esdhc-imx` (drivers/mmc/host/sdhci-esdhc-imx.c)

#### 5.1 PURPOSE & SCOPE (DDD-M05-01)
Bind to uSDHC3 (SD card @ J500) and uSDHC4 (eMMC @ U18). Wraps the generic `sdhci` core with i.MX-specific clock control, tuning (HS200/HS400), DDR mode, voltage switch, and strobe DLL.

#### 5.2 STATE MACHINE (per host) (DDD-M05-02)

```
   RESET ---ios_init---> IDLE ---cmd_submit---> CMD_ACTIVE
                           ^                       |
                           |                       v
                           +----irq(cmd_done)---  DATA (if any)
                                                   |
                                            irq(xfer_done)
                                                   |
                                                   v
                                                 IDLE
   Any state ---error/timeout---> ERROR ---sw_reset---> IDLE
```

| State       | Event                | Next       | Action |
|-------------|----------------------|------------|--------|
| RESET       | `host->ops->reset`   | IDLE       | Reset CMD+DAT; reprogram tuning regs |
| IDLE        | `sdhci_send_command` | CMD_ACTIVE | write XFR_TYP |
| CMD_ACTIVE  | IRQ CC               | DATA/IDLE  | read RESP |
| DATA        | IRQ TC               | IDLE       | ADMA2 done; finish_tasklet |
| any         | ERRINT / timeout     | ERROR      | log, `sdhci_reset(CMD\|DATA)` |
| ERROR       | sw reset done        | IDLE       | re-issue or fail up |

#### 5.3 ALGORITHMS (DDD-M05-03)

**Tuning (HS200) — SW tuning loop**:

```
for tap in 0..127:
    esdhc_prepare_tuning(host, tap)
    status = mmc_send_tuning(host)
    pass_map[tap] = (status == 0)
window = longest_run_of_ones(pass_map, 128)
if window.len < MIN_WINDOW (=10): return -EIO
set_tap(host, window.center)
```

Complexity O(128) commands × ~80 µs = 10 ms worst case; bounded loop with fixed 128 iterations ⇒ MISRA-bounded.

**Window search** uses a linear two-pointer scan: O(N), N=128.

#### 5.4 INTERNAL DATA LAYOUT (DDD-M05-04)

| Symbol | Type | Init | Access |
|---|---|---|---|
| `imx_data` (per host) | `struct pltfm_imx_data` | zero | per-host `host->mmc->lock` |
| `imx_data.socdata` | `const struct esdhc_soc_data *` | table | RO |
| `imx_data.clk_per/ipg/ahb` | `struct clk *` | probe | RO after probe |
| `imx_data.is_ddr` | `bool` | false | set in set_ios |
| `imx_data.tuning_tap` | `u32` | 0 | set by tuning |
| `imx_data.adma_table` | `void *` (DMA coherent) | alloc | DMA-only access |

ADMA2 descriptor table: `ADMA_TABLE_SZ = (128 * 8)` = 1 KiB per host, coherent-DMA.

#### 5.5 FUNCTION-LEVEL DESIGN (DDD-M05-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `sdhci_esdhc_imx_probe(pdev)` | pdev | 0/-errno | clk_prepare_enable; dma coherent alloc; sdhci_add_host | pinctrl+clk+vmmc OK | `/dev/mmcblkX` live |
| `esdhc_readl_le/writel_le` | reg | val | byte-swap quirks on PRSSTAT | probed | — |
| `esdhc_pltfm_set_clock(host,hz)` | hz | void | reprogram SYS_CTRL DIV/PREDIV | host idle | clock settled 10 µs |
| `esdhc_set_tuning_block(host,tap)` | tap(0..127) | void | rmw MIX_CTRL + TUNING_CTRL | HS200 selected | tap active |
| `esdhc_executing_tuning(mmc,opcode)` | opcode | 0/-EIO | runs loop above | HS200 ready | tap programmed |
| `esdhc_change_pinstate(host,timing)` | timing | 0 | pinctrl_select_state() | states parsed | pad drive updated |
| `esdhc_set_uhs_signaling(host,timing)` | timing | void | MIX_CTRL ddr/hs400 bits | voltage switched | UHS mode live |
| `esdhc_reset(host,mask)` | mask | void | writeb SW_RST, wait; re-apply quirks | — | reset complete ≤100 ms |

#### 5.6 TIMING & RESOURCE USAGE (DDD-M05-06)

| Function | WCET | Stack |
|---|---|---|
| `esdhc_pltfm_set_clock` | 60 µs | 80 B |
| `esdhc_executing_tuning` | 11 ms (hard-bounded) | 192 B |
| `esdhc_reset` | 100 ms (spec max) | 96 B |
| `esdhc_change_pinstate` | 2 µs | 64 B |

---

### M06 — `imx-uart` (drivers/tty/serial/imx.c)

#### 6.1 PURPOSE & SCOPE (DDD-M06-01)
Serial driver for 5 UARTs. UART1 is the kernel console (`ttymxc0` @ 115200 8N1). Supports DMA on RX/TX above a threshold, polled console for `kdb`/`earlycon`.

#### 6.2 STATE MACHINE (per port)

```
              +--------+  startup  +--------+
              | CLOSED |---------->| OPEN_P |   (PIO mode)
              +--------+           +--------+
                  ^                    |
                  | shutdown           | rx>DMA_THRESH
                  |                    v
              +--------+           +--------+
              | CLOSED |<----------| OPEN_D |   (DMA mode)
              +--------+  shutdown +--------+
                                       |
                                       | RX idle
                                       v
                                  (back to OPEN_P)
```

| State | Event | Next | Action |
|---|---|---|---|
| CLOSED | startup | OPEN_P | request_irq, enable UCR1.UARTEN |
| OPEN_P | rx_len ≥ THRESH | OPEN_D | request dma chans, submit cyclic |
| OPEN_D | rx_idle>timeout | OPEN_P | terminate dma, fall back |
| any    | shutdown | CLOSED | mask UCR1, free IRQ, release dma |

#### 6.3 ALGORITHMS (DDD-M06-03)

**ISR** (hot path):

```
usr1 = readl(USR1) & readl(UCR1_mask)
if usr1 & RRDY: imx_uart_rxint(port)    # drain RX FIFO
if usr1 & TRDY: imx_uart_txint(port)    # fill TX FIFO
if usr1 & RTSD: handle_mctrl_change()
writel(acked_bits, USR1)
return IRQ_HANDLED
```

WCET: ≤ 24 B FIFO drained at 16 ns/reg = < 1 µs + tty push latency.

**DMA RX** uses cyclic SDMA descriptor of 4 × 1024 B, half+full callback via dmaengine.

#### 6.4 INTERNAL DATA LAYOUT (DDD-M06-04)

| Symbol | Type | Init | Access |
|---|---|---|---|
| `imx_uart_ports[8]` | `struct imx_port *` | NULL | ports[] guarded by driver registration |
| `sport->port.lock` | `spinlock_t` | unlocked | per-port, IRQ-safe |
| `sport->rx_buf` | DMA-coherent `u8[RX_BUF_SIZE]` | zero | producer = DMA, consumer = tasklet |
| `sport->dma_is_rxing` | `bool` | false | under `port.lock` |
| `RX_BUF_SIZE` | `#define` | 4096 | compile-time |
| `TX_BUF_SIZE` | `#define` | PAGE_SIZE | compile-time |

#### 6.5 FUNCTION-LEVEL DESIGN (DDD-M06-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `imx_uart_probe(pdev)` | pdev | 0/-errno | ioremap, uart_add_one_port | clk ok | `/dev/ttymxcN` |
| `imx_uart_startup(port)` | port | 0/-errno | request_irq; reset FIFOs; UCR1|=EN | CLOSED | OPEN_P |
| `imx_uart_shutdown(port)` | port | void | free_irq; dma_free | open | CLOSED |
| `imx_uart_set_termios(port,new,old)` | termios | void | recompute BIR/BMR for baud | open | baud active |
| `imx_uart_int(irq,data)` | irq, sport | IRQ_HANDLED | acks USR1/USR2, push to tty | open | FIFO drained |
| `imx_uart_console_write(co,s,n)` | str, n | void | polled PIO write | earlycon set | chars sent |
| `imx_uart_dma_rx_callback(arg)` | chan | void | push data, resubmit | OPEN_D | DMA chain alive |
| `imx_uart_setup_ufcr(port,rxtl,txtl)` | thresholds | void | writes UFCR | open | FIFO thresholds set |

#### 6.6 TIMING & RESOURCE USAGE (DDD-M06-06)

| Function | WCET | Stack |
|---|---|---|
| `imx_uart_int` | 5 µs | 96 B |
| `imx_uart_set_termios` | 80 µs | 128 B |
| `imx_uart_console_write` (80 chars, polled) | 7 ms @ 115200 | 48 B |
| `imx_uart_startup` | 250 µs | 160 B |

---

### M07 — `fec-main` (drivers/net/ethernet/freescale/fec_main.c)

#### 7.1 PURPOSE & SCOPE (DDD-M07-01)
Drive the FEC (Fast Ethernet Controller) IP paired with the AR8031 RGMII PHY. Provides 1 Gbit/s full-duplex MAC + NAPI RX, BQL TX, IEEE-1588 timestamping, MDIO bus.

#### 7.2 STATE MACHINE (netdev)

```
  DOWN ---ndo_open---> UP_LINKDOWN ---phy_link_up---> UP_LINKUP
   ^                      ^                              |
   |                      |                              |
   +---ndo_stop-----------+-------phy_link_down<---------+
```

| State | Event | Next | Action |
|---|---|---|---|
| DOWN | ndo_open | UP_LINKDOWN | ring alloc, request_irq(×3), phy_start |
| UP_LINKDOWN | phy link up | UP_LINKUP | program MAC speed/duplex, napi_enable, netif_carrier_on |
| UP_LINKUP | TX pkt | UP_LINKUP | fec_enet_start_xmit |
| UP_LINKUP | link down | UP_LINKDOWN | netif_carrier_off, stop TX queue |
| any UP | ndo_stop | DOWN | phy_stop, napi_disable, free rings |

#### 7.3 ALGORITHMS (DDD-M07-03)

**NAPI poll**:

```
budget_left = budget
while budget_left > 0 and (bdp = rx_next_dirty()).status & RX_OWN == 0:
    if (bdp.status & RX_LAST) and (bdp.status & ERRORS) == 0:
        skb = build_skb(page_addr)
        fec_1588_get_ts(skb, bdp)      # if TSTAMP enabled
        napi_gro_receive(napi, skb)
    refill_page(bdp)
    bdp.status = RX_EMPTY | RX_WRAP?
    dma_wmb()
    writel(RDAR, fec_reg)              # kick
    budget_left--
if budget_left > 0:
    napi_complete_done(napi, budget - budget_left)
    enable_rx_irq()
return budget - budget_left
```

Complexity: O(budget), budget = 64; WCET 55 µs at 1 Gb line rate.

#### 7.4 INTERNAL DATA LAYOUT (DDD-M07-04)

| Symbol | Type | Init | Access |
|---|---|---|---|
| `fep->rx_bd_base` | `struct bufdesc *` (DMA coherent) | alloc@open | CPU+DMA |
| `fep->tx_bd_base` | same | alloc@open | CPU+DMA |
| `fep->hw_lock` | `spinlock_t` | unlocked | MDIO bus |
| `fep->ptp_clock_info` | `struct ptp_clock_info` | static | RO |
| `RX_RING_SIZE` | `#define` | 16 (queue 0), 8 (AVB) | compile-time |
| `TX_RING_SIZE` | `#define` | 512 | compile-time |

#### 7.5 FUNCTION-LEVEL DESIGN (DDD-M07-05)

| Name | Inputs | Outputs | Side-effects | Pre | Post |
|---|---|---|---|---|---|
| `fec_probe(pdev)` | pdev | 0/-errno | alloc_netdev, mdio_register, register_netdev | clk+regulator ok | `ethN` up |
| `fec_enet_open(ndev)` | ndev | 0 | alloc rings, request_irq, phy_start | DOWN | UP_LINKDOWN |
| `fec_enet_close(ndev)` | ndev | 0 | reverse of open | UP_* | DOWN |
| `fec_enet_start_xmit(skb,ndev)` | skb | NETDEV_TX_OK/BUSY | dma_map, BD write | UP_LINKUP | skb enqueued |
| `fec_enet_interrupt(irq,dev)` | — | IRQ_HANDLED | mask, napi_schedule | UP | — |
| `fec_enet_rx_napi(napi,budget)` | budget | work_done | BD consume | scheduled | ring refilled |
| `fec_restart(ndev)` | ndev | void | ECR reset, reprogram | under rtnl | MAC re-inited |
| `fec_enet_mdio_read/write()` | bus, phy, reg[,val] | val | MDIO_DATA, wait MII bit | hw_lock | — |

#### 7.6 TIMING & RESOURCE USAGE (DDD-M07-06)

| Function | WCET | Stack |
|---|---|---|
| `fec_enet_start_xmit` | 3.2 µs | 128 B |
| `fec_enet_rx_napi` (budget=64) | 55 µs | 192 B |
| `fec_restart` | 12 ms (cable renegotiation excl.) | 256 B |
| `fec_enet_mdio_read` | 25 µs (MDC=2.5 MHz, 32 clocks) | 64 B |

---

*(Modules M08–M15: `imx-i2c`, `spi-imx`, `flexcan`, `imx-ipuv3`, `imx-hdmi`, `imx-sdma`, `imx-thermal`, `imx6q-pm`, `snvs-rtc` follow the same template. Condensed here due to length; full text in appendices A1–A9 of this document.)*

---

### M08 — `imx-i2c` (DDD-M08)

- Purpose: drive 3 I²C controllers @ up to 400 kHz; byte-level PIO, no DMA.
- States per controller: **IDLE → START → ADDR → DATA → STOP → IDLE**; **ARB_LOST** recovery by bus recover via pinctrl bit-bang.
- Key algorithm — `i2c_imx_xfer()`: for each msg (n ≤ I2C_MAX_MSGS=32): write I2CR.MSTA, wait IBB (timeout 500 ms), write IADR, for each byte wait IIF flag. WCET per byte ≈ 25 µs at 400 kHz; per 32-byte transfer ≈ 1.1 ms.
- Static data: `struct imx_i2c_struct` per controller; completion `cmd_complete`.
- Recovery: on timeout → SCL bit-bang 9 clocks via pinctrl state `gpio`.

### M09 — `spi-imx` (DDD-M09)

- Purpose: 5 eCSPI + uSPI controllers, up to 60 MHz; DMA above 32-byte FIFO threshold.
- State: **IDLE → SETUP → XFER_PIO|XFER_DMA → DONE → IDLE**.
- Algorithm: ring-FIFO pushing; DMA via SDMA channel pair (TX+RX); `spi_imx_isr` drains RX FIFO on TCEN/RRDY.
- Data: `spi_imx_data *` per master; `wait_for_completion` sync; `rx/tx_buf` pointers advanced.
- WCET: 4 kB transfer @ 25 MHz DMA → 1.4 ms incl. cache maintenance.

### M10 — `flexcan` (DDD-M10)

- Purpose: CAN 2.0B @ 1 Mbit/s on CAN1; 64 MB mailboxes; queue-based RX via RX-FIFO (8 msgs deep) + 6 TX mailboxes.
- State: **RESET → FREEZE → NORMAL → BUS_OFF → NORMAL** (auto-recover).
- Key algorithm: `flexcan_start_xmit()` picks first free TX MB, writes CS+ID+DATA, sets CODE=TX_DATA; ISR services IFLAG1/2, copies frames to skb, calls `netif_rx`.
- Data: `struct flexcan_priv`, `can_bittiming` from netlink.
- WCET ISR: 22 µs for 8 RX + 1 TX done combined.

### M11 — `imx-ipuv3` + `imx-drm` (DDD-M11)

- Purpose: DRM/KMS driver for IPU display pipeline + HDMI encoder. Two CRTCs, one HDMI connector.
- State machines: CRTC (OFF/ON/FLUSH), Plane (disabled/enabled/flip_pending).
- Algorithm: atomic commit — validate → flush → wait vblank; page-flip via DI0/DI1 channel switch using IDMAC double-buffering.
- Static: per-IPU `struct ipu_soc`, 3 sub-blocks (IDMAC, DI, DC) with their own regmap.
- WCET atomic_commit: 8.2 ms worst case (vblank wait dominates).

### M12 — `imx-sdma` (DDD-M12)

- Purpose: SDMA controller + script RAM; provides 32 virtual channels to dmaengine.
- States per channel: **FREE → ALLOCATED → PREPARED → RUNNING → IDLE|ERR**.
- Algorithm: `sdma_prep_slave_sg()` builds BD chain in `sdma_buffer_descriptor[]` (≤ MAX_BD=64), writes channel context, triggers HSTART.
- Static: firmware image `sdma-imx6q.bin` (loaded once via `request_firmware`).
- WCET issue_pending: 8 µs; completion callback latency bounded by tasklet.

### M13 — `imx-thermal` (DDD-M13)

- Purpose: on-die temperature sensor via ANATOP TEMPMON; exposes `thermal_zone`.
- State: **DISABLED → ENABLED (periodic 1 s) → TRIP_PASSIVE (cpufreq cap) → TRIP_CRITICAL (orderly poweroff)**.
- Algorithm: `imx_get_temp()` triggers measure, waits FINISHED bit, converts: `T = c1 - n_meas * c2` (calibration from OCOTP fuse).
- WCET: 250 µs per reading.

### M14 — `imx6q-pm` (arch/arm/mach-imx/pm-imx6.c) (DDD-M14)

- Purpose: implement `suspend_ops.enter(PM_SUSPEND_MEM)`, DSM (Deep-Sleep-Mode) via MMDC self-refresh + PLL bypass + ARM WFI.
- State: **RUN → STANDBY → STOP → MEM → RUN** (wake via GPC pending IRQ).
- Assembly resume path in `suspend-imx6.S` — MMU off → reinit MMDC → enable MMU → jump to `cpu_resume`.
- Stack: 1 KiB save area in OCRAM (0x00900000).

### M15 — `snvs-rtc` (DDD-M15)

- Purpose: low-power RTC in SNVS block; seconds counter at 32 kHz.
- State: **DISABLED → ENABLED → ALARM_ARMED → ALARM_FIRED**.
- Algorithm: `snvs_rtc_read_time()` reads LPSRTCMR:LPSRTCLR with triple-read consistency check.
- WCET: 3 µs read, 12 µs write (sync bit poll).

---

## 2. CROSS-MODULE INTERACTIONS

### 2.1 Use-Case A — Cold Boot to User-Space (DDD-XM-01)

```
 U-Boot         mach-imx6q    clk-imx6q    pinctrl-imx6q   gpio-mxc   sdhci-esdhc-imx   fec-main    user
   |               |              |              |             |            |              |          |
   |--DT blob----->|              |              |             |            |              |          |
   |               |--map_io----->|              |             |            |              |          |
   |               |--init_early->|              |             |            |              |          |
   |               |--clocks_init>|              |             |            |              |          |
   |               |              |-of_clk_add-->|             |            |              |          |
   |               |--of_populate>|              |             |            |              |          |
   |               |              |              |<--probe-----|            |              |          |
   |               |              |              |--pinctrl OK>|            |              |          |
   |               |              |              |             |<--probe---|              |          |
   |               |              |<--clk_get----|             |<==DEFER==  |              |          |
   |               |              |--ready------>|             |--reprobe-->| mmc ready    |          |
   |               |              |              |             |            |<--probe------|          |
   |               |              |              |             |            |              |--rootfs->|
```

Deferred-probe is expected and bounded: max 3 rounds observed.

### 2.2 Use-Case B — TX of an Ethernet Frame (DDD-XM-02)

```
 user          net-core     fec-main     dmaengine   AR8031 (RGMII)
  |--sendto()--->|             |            |             |
  |              |--ndo_xmit-->|            |             |
  |              |             |-dma_map_single-> (coherent BD)
  |              |             |--BD.ready---|             |
  |              |             |--writel(TDAR)------------>|
  |              |             |                           |--tx done-->
  |              |             |<--IRQ---------------------|
  |              |             |--napi_schedule            |
  |              |<--tx_free---|                           |
  |<--ret--------|             |                           |
```

WCET path budget: 3.2 µs driver + 1 µs DMA setup + link-dep latency.

### 2.3 Use-Case C — SD-Card Read via ADMA2 + SDMA (DDD-XM-03)

```
 fs     blk-core     mmc-core       sdhci-esdhc-imx     SDMA      uSDHC3
  |--read-->|          |                |               |          |
  |         |--mmc_req>|                |               |          |
  |         |          |-do_request---->|               |          |
  |         |          |                |--build ADMA2--|          |
  |         |          |                |--CMD18------->|          |--issue-->
  |         |          |                |<--IRQ(CC)-----|<---------|
  |         |          |                |<--IRQ(TC)-----|<---------|
  |         |          |<--mmc_request_done             |          |
  |<--data--|          |                |               |          |
```

---

## 3. CONFIGURATION & COMPILE-TIME PARAMETERS (DDD-CFG-01)

| `#define` / Kconfig | Module | Range | Default | Description |
|---|---|---|---|---|
| `CONFIG_ARCH_MXC` | M01 | y/n | y | Enable i.MX arch |
| `CONFIG_SOC_IMX6Q` | M01 | y/n | y | SoC family |
| `CONFIG_COMMON_CLK_IMX6Q` | M02 | y/n | y | Clock driver |
| `IMX6QDL_CLK_END` | M02 | generated | 280 | Size of clks[] |
| `MXC_GPIO_IRQ_HIGH` / `_LOW` | M04 | 1/0 | 1 | Enables dual-edge sel |
| `RX_BUF_SIZE` | M06 | 1024..16384 | 4096 | UART RX DMA buffer |
| `TX_BUF_SIZE` | M06 | 1024..16384 | PAGE_SIZE | UART TX buffer |
| `RX_RING_SIZE` | M07 | 16..256 | 16 | FEC RX BDs queue-0 |
| `TX_RING_SIZE` | M07 | 64..512 | 512 | FEC TX BDs |
| `FEC_NAPI_BUDGET` | M07 | 32..128 | 64 | NAPI weight |
| `I2C_MAX_MSGS` | M08 | 1..64 | 32 | Max msgs per `xfer` |
| `SPI_IMX_DMA_THRESH` | M09 | 16..256 | 64 | PIO→DMA threshold |
| `FLEXCAN_TX_MB_RESERVED` | M10 | 1..6 | 2 | reserved for prio |
| `SDMA_MAX_BD` | M