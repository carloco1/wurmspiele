# SOFTWARE ARCHITECTURE DESIGN
## NXP i.MX6Q SabreSD — Linux BSP Driver Package

**Document ID:** SAD-IMX6Q-BSP-001-ARCH
**Stage:** V-Model Stage 5 (Software Architecture)
**Pairs with:** Stage 11 — Integration Tests (SwIT-IMX6Q-BSP-001)
**Traces upward to:** SwRS-IMX6Q-BSP-001 v1.0, HSI-IMX6Q-BSP-001 v1.0

---

## 1. ARCHITECTURE OVERVIEW

### 1.1 Layered View

The BSP is layered atop the mainline Linux 6.6 LTS kernel. Each layer only calls downward through a published API; upward calls are forbidden except via registered callbacks (observer pattern).

```
┌──────────────────────────────────────────────────────────────────────┐
│                      APPLICATION LAYER (user-space)                  │
│  systemd units · bsp-health daemon · mfgtool hooks · Qt demo · test  │
│  harnesses (pytest + libgpiod + v4l2-ctl + iperf3)                   │
├──────────────────────────────────────────────────────────────────────┤
│                      MIDDLEWARE / SERVICES LAYER                     │
│  libbsp (user-lib) · netlink uevent mux · thermal-throttle policy    │
│  mgr · OTA updater · cgroup-based QoS · GStreamer pipelines (VPU)    │
├──────────────────────────────────────────────────────────────────────┤
│                  HARDWARE ABSTRACTION LAYER (Kernel subsys)          │
│  Common Clock Framework (CCF) · pinctrl core · regmap-mmio ·         │
│  gpiolib · genirq · DMA engine · mmc core · V4L2 · DRM-KMS · IIO ·   │
│  regulator · thermal · net-core · tty-core · mtd                     │
├──────────────────────────────────────────────────────────────────────┤
│                   DRIVER LAYER (register-level, i.MX6-specific)      │
│  clk-imx6q · pinctrl-imx6q · gpio-mxc · sdhci-esdhc-imx · imx-uart · │
│  fec-main · imx-i2c · spi-imx · flexcan · imx-ipuv3 · imx-hdmi ·     │
│  imx-sdma · imx-thermal · imx6q-pm · snvs-rtc                        │
├──────────────────────────────────────────────────────────────────────┤
│                    BSP / CMSIS-equivalent / STARTUP                  │
│  U-Boot SPL · U-Boot proper · imx6q-sabresd.dts · bootROM ·          │
│  arch/arm/mach-imx/mach-imx6q.c · PSCI stubs · arm-gic · armv7 TLB   │
└──────────────────────────────────────────────────────────────────────┘
                                  │
                  ┌───────────────┴──────────────┐
                  │    i.MX6Q SILICON (AIPS-1/2) │
                  └──────────────────────────────┘
```

### 1.2 Architectural Principles

1. **Device-tree-first** — zero board code in drivers; everything comes from `imx6q-sabresd.dts`.
2. **Upstream-clean** — all driver sources conform to `Documentation/process/coding-style.rst`; out-of-tree delta kept < 500 LOC.
3. **Unidirectional dependencies** — Driver → HAL → subsystem core → user-space; no back-calls except registered ops tables.
4. **Defer probes, never poll-wait** — missing dependencies return `-EPROBE_DEFER`.
5. **Single owner per HW block** — exactly one driver binds to each compatible string (SwFR-001).
6. **Fail-safe defaults** — pads default to high-impedance GPIO on pinctrl fail; clocks gated; regulators off.

---

## 2. MODULE CATALOGUE

| # | Module | Layer | Responsibility | Depends On | Exposes API |
|---|---|---|---|---|---|
| M01 | `mach-imx6q` | BSP/Startup | Register `"fsl,imx6q-sabresd"`, SMP bring-up, platform quirks | OF, PSCI, GIC | `DT_MACHINE_START` |
| M02 | `clk-imx6q` | Driver | CCM/ANATOP/PLL clock tree | CCF, regmap-mmio | `of_clk_add_provider()`, clock IDs `IMX6QDL_CLK_*` |
| M03 | `pinctrl-imx6q` | Driver | IOMUXC pad mux + pad control | pinctrl core | `pinctrl-single`-style DT API |
| M04 | `gpio-mxc` | Driver | 7× GPIO banks, IRQ demux | gpiolib, genirq | `gpiod_*`, IRQ domain |
| M05 | `sdhci-esdhc-imx` | Driver | uSDHC3 (SD) + uSDHC4 (eMMC) | sdhci core, mmc core, dmaengine | `/dev/mmcblk*` |
| M06 | `imx-uart` | Driver | UART1 console + UART2..5 | tty-core, serial-core | `/dev/ttymxc*` |
| M07 | `fec-main` | Driver | 1 Gbit Ethernet MAC (AR8031 PHY) | net-core, phylib, mdio | `eth0` netdev |
| M08 | `imx-i2c` | Driver | I²C1..3 controllers | i2c-core | `/dev/i2c-*`, `i2c_adapter` |
| M09 | `spi-imx` | Driver | eCSPI1..5 | spi-core, dmaengine | `spi_master` |
| M10 | `flexcan` | Driver | CAN1/CAN2 | can-dev, net-core | `can0`, `can1` |
| M11 | `imx-sdma` | Driver | Smart DMA engine firmware + channel alloc | dmaengine, firmware-class | `dma_request_chan()` |
| M12 | `imx-ipuv3` + `imx-drm` | Driver | IPU display pipeline, HDMI-TX | DRM-KMS, clk, regulator | `/dev/dri/card0` |
| M13 | `imx-thermal` | Driver | Temp sensor + trip points | thermal core | thermal zone `cpu-thermal` |
| M14 | `imx6q-pm` | Driver | suspend-to-RAM, cpuidle | suspend/resume core | PM ops |
| M15 | `snvs-rtc` | Driver | SNVS LP RTC | rtc-core | `/dev/rtc0` |
| M16 | `imx-wdt` | Driver | WDOG1 (10 s) | watchdog core | `/dev/watchdog0` |
| M17 | `libbsp` | Middleware | User-space helper lib (GPIO, PWM, thermal, OTA) | libgpiod, sysfs | `libbsp.so` header `bsp.h` |
| M18 | `bsp-health` | Application | systemd daemon, watchdog pet, thermal telemetry | libbsp, systemd-sd_notify | JSON-RPC on UNIX socket |
| M19 | `bsp-ota` | Application | A/B dual-bank updater | libbsp, libcurl, libcrypto | CLI `bsp-ota` |
| M20 | `bsp-test-harness` | Application | Integration-test runner (pairs w/ Stage 11) | pytest, libbsp | pytest fixtures |

---

## 3. MODULE INTERFACE DEFINITIONS

### 3.1 Kernel-side DT binding contract — `clk-imx6q` (M02)

```c
/* drivers/clk/imx/clk-imx6q.h  — excerpt                                    */
/**
 * @file  clk-imx6q.h
 * @brief Public clock IDs and init hook for i.MX6Q CCM/ANATOP tree.
 *        Traces to SwFR-002, HSI §1.2 (CCM @ 0x020C4000, ANATOP @ 0x020C8000).
 */
#ifndef CLK_IMX6Q_H
#define CLK_IMX6Q_H

#include <dt-bindings/clock/imx6qdl-clock.h>   /* IMX6QDL_CLK_* IDs            */
#include <linux/clk-provider.h>

/* Clock-tree limits (Hz) — from IMX6DQCEC §4.1 */
#define IMX6Q_ARM_PLL_MIN_HZ        648000000UL
#define IMX6Q_ARM_PLL_MAX_HZ       1296000000UL
#define IMX6Q_AHB_MAX_HZ            132000000UL
#define IMX6Q_IPG_MAX_HZ             66000000UL

/**
 * @brief  Probe hook registered via CLK_OF_DECLARE("fsl,imx6q-ccm", ...)
 * @param  np  Device-tree node of CCM
 * @return 0 on success, -ENOMEM / -EIO on failure
 * @note   MUST complete before any peripheral driver probes (SwFR-002).
 */
int imx6q_clocks_init(struct device_node *np);

#endif /* CLK_IMX6Q_H */
```

### 3.2 Kernel-side — `gpio-mxc` (M04)

```c
/**
 * @file  gpio-mxc.h
 * @brief i.MX GPIO bank driver — 7 banks × 32 lines.
 *        Traces to SwFR-020..024, HSI §1.4.
 */
#ifndef GPIO_MXC_H
#define GPIO_MXC_H

#include <linux/gpio/driver.h>

#define MXC_GPIO_NR_BANKS          7U
#define MXC_GPIO_PINS_PER_BANK    32U
#define MXC_GPIO_IRQ_HI_OFFSET    16U  /* ISR[31:16] maps to ICR2              */

enum mxc_gpio_icr {
    MXC_GPIO_ICR_LOW_LEVEL  = 0U,
    MXC_GPIO_ICR_HIGH_LEVEL = 1U,
    MXC_GPIO_ICR_RISING     = 2U,
    MXC_GPIO_ICR_FALLING    = 3U,
};

/**
 * @brief  Configure interrupt sensitivity for a GPIO line.
 * @param  gc   gpio_chip owning the line
 * @param  off  bit offset 0..31
 * @param  icr  desired sensitivity enum
 * @return 0, or -EINVAL if line not in this bank
 */
int mxc_gpio_set_irq_type(struct gpio_chip *gc, u32 off, enum mxc_gpio_icr icr);

#endif /* GPIO_MXC_H */
```

### 3.3 User-space — `libbsp.h` (M17)

```c
/**
 * @file    bsp.h
 * @brief   SabreSD BSP user-space helper library (libbsp).
 * @version 1.0
 * @note    MISRA-C:2012 advisory; CERT-C mandatory.
 *          Thread-safety: all handles are opaque; caller serialises per-handle.
 */
#ifndef BSP_H
#define BSP_H

#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Library version — semantic versioning */
#define BSP_VERSION_MAJOR   1U
#define BSP_VERSION_MINOR   0U
#define BSP_VERSION_PATCH   0U

/* Fixed resource limits */
#define BSP_MAX_GPIO_HANDLES    32U
#define BSP_MAX_PATH_LEN       256U
#define BSP_THERMAL_TRIP_MDC   95000  /* critical trip, milli-°C (SwFR-060) */

/** @brief Canonical error codes (negated errno convention). */
typedef enum {
    BSP_OK               =   0,
    BSP_E_INVAL          =  -1,
    BSP_E_NODEV          =  -2,
    BSP_E_IO             =  -3,
    BSP_E_TIMEOUT        =  -4,
    BSP_E_BUSY           =  -5,
    BSP_E_NOMEM          =  -6,
    BSP_E_PERM           =  -7,
    BSP_E_FAULT          =  -8,
    BSP_E_OVERTEMP       =  -9
} bsp_status_t;

typedef struct bsp_gpio_handle  bsp_gpio_handle_t;
typedef struct bsp_therm_handle bsp_therm_handle_t;

typedef enum {
    BSP_GPIO_DIR_IN  = 0,
    BSP_GPIO_DIR_OUT = 1
} bsp_gpio_dir_t;

/**
 * @brief   Open a GPIO line by DT-compatible label.
 * @param[in]  label     null-terminated label from DT `gpio-line-names`
 * @param[in]  dir       direction
 * @param[out] out_hdl   receives opaque handle
 * @return  BSP_OK on success, BSP_E_NODEV if label not found.
 * @note    Implemented via libgpiod v2 chardev; no sysfs (deprecated).
 */
bsp_status_t bsp_gpio_open(const char       *label,
                           bsp_gpio_dir_t    dir,
                           bsp_gpio_handle_t **out_hdl);

/**
 * @brief   Release a GPIO line. Safe on NULL.
 * @param[in,out] hdl    handle pointer; zeroed on return
 */
void bsp_gpio_close(bsp_gpio_handle_t **hdl);

/**
 * @brief   Read current thermal-zone temperature.
 * @param[in]  hdl       open thermal handle
 * @param[out] milli_c   temperature in milli-°C
 * @return  BSP_OK or BSP_E_IO; BSP_E_OVERTEMP when ≥ crit trip.
 */
bsp_status_t bsp_therm_read(const bsp_therm_handle_t *hdl,
                            int32_t                  *milli_c);

/**
 * @brief   Pet the kernel watchdog (/dev/watchdog0). Must be called ≤ 5 s.
 * @return  BSP_OK or BSP_E_IO.
 * @note    Pairs with SwFR-052.
 */
bsp_status_t bsp_wdt_kick(void);

#ifdef __cplusplus
}
#endif
#endif /* BSP_H */
```

### 3.4 User-space — `bsp-health` daemon (M18)

```c
/**
 * @file    bsp_health.h
 * @brief   systemd-managed health daemon. Pets watchdog, exports telemetry.
 */
#ifndef BSP_HEALTH_H
#define BSP_HEALTH_H

#include "bsp.h"

#define BSP_HEALTH_TICK_MS     1000U  /* 1 Hz main loop                       */
#define BSP_HEALTH_WDT_MS      4000U  /* pet well inside 10 s WDOG1 window    */
#define BSP_HEALTH_SOCK_PATH   "/run/bsp-health.sock"

typedef struct {
    int32_t  cpu_temp_mc;       /**< latest CPU temperature, milli-°C        */
    uint32_t uptime_s;          /**< since boot                              */
    uint32_t wdt_kicks;         /**< monotonically increasing                */
    uint8_t  thermal_state;     /**< 0=normal 1=warn 2=hot 3=crit            */
} bsp_health_snapshot_t;

/**
 * @brief   Entry point; does not return until SIGTERM.
 * @return  0 clean, <0 fatal.
 */
int bsp_health_main(void);

/**
 * @brief   Read-only snapshot publisher (observer pattern).
 * @param[out] snap  filled atomically.
 */
void bsp_health_get(bsp_health_snapshot_t *snap);

#endif /* BSP_HEALTH_H */
```

---

## 4. RTOS DESIGN

The target runs **Linux 6.6 LTS (CONFIG_PREEMPT)** — not an RTOS — but three concurrency domains exist. Kernel tasks and user-space tasks are tabulated as equivalent "tasks" for the integration test plan:

### 4.1 Kernel-space kthreads & workqueues

| Thread | Priority (nice/RT) | Stack | Period/Trigger | Shared Resources |
|---|---|---|---|---|
| `kworker/[0..3]:H` (highprio WQ) | RT 1 (MAX_RT_PRIO-1 for sdhci) | 8 kB | on-demand | mmc host mutex |
| `irq/56-2190000.usdhc` (threaded IRQ) | RT 50 | 8 kB | SD card IRQ | sdhci regs (spinlock) |
| `ksoftirqd/N` | nice 0 | 8 kB | per-CPU | — |
| `kcompactd0` | nice 0 | 8 kB | memory pressure | — |
| `fec_enet` NAPI poll | softirq (NET_RX) | IRQ stack | RX IRQ | RX ring (dma-coherent) |
| `flexcan` napi | softirq | IRQ stack | CAN RX FIFO | mailbox regs |

### 4.2 User-space tasks

| Task | sched policy / prio | Stack | Period/Trigger | Shared Resources |
|---|---|---|---|---|
| `bsp-health` main loop | SCHED_OTHER, nice -5 | 128 kB | 1 Hz timerfd | `/dev/watchdog0`, `/run/bsp-health.sock` |
| `bsp-health` WDT petter | SCHED_FIFO, prio 20 | 32 kB | 4 Hz itimer | `/dev/watchdog0` |
| `bsp-ota` | SCHED_OTHER, nice 10 | 256 kB | SIGUSR1 / cron | eMMC A/B partitions |
| `gstreamer-pipe` (demo) | SCHED_OTHER | 2 MB | video frames | `/dev/dri/card0`, VPU |

### 4.3 Synchronisation primitives

| Primitive | Used In | Protects |
|---|---|---|
| `spinlock_t` (IRQ-safe) | gpio-mxc, flexcan | register bank |
| `mutex` | clk-imx6q, pinctrl core | clock tree traversal |
| `completion` | sdhci request flow | MMC command done |
| `rcu_read_lock` | netdev rx path | netdev list |
| POSIX `pthread_mutex` + `PTHREAD_PRIO_INHERIT` | libbsp snapshot | `bsp_health_snapshot_t` double-buffer |
| `eventfd` | bsp-health → bsp-ota | update-trigger |
| Unix SOCK_SEQPACKET | JSON-RPC telemetry | N/A (message-passing) |

---

## 5. INTER-MODULE DATA FLOWS

### 5.1 Boot sequence (pairs with SwFR-001..004, UC-01)

```
 ROM ──► U-Boot SPL ──► U-Boot proper ──► Linux decompress @ 0x10008000
                                              │
                                              ▼
                           setup_arch() → unflatten FDT
                                              │
                                              ▼
                     CLK_OF_DECLARE  →  imx6q_clocks_init()      [M02]
                                              │
                                              ▼
                     of_platform_populate()                       [core]
                                              │
               ┌──────────────┬───────────────┼───────────────┐
               ▼              ▼               ▼               ▼
         pinctrl-imx6q   gpio-mxc       sdhci-esdhc-imx    imx-uart
            [M03]         [M04]            [M05]           [M06]
               │              │               │               │
               └──────────────┴───────┬───────┴───────────────┘
                                      ▼
                        rootfs mount on /dev/mmcblk3p2
                                      │
                                      ▼
                        systemd → multi-user.target  ≤ 15 s       (SwFR-004)
                                      │
                                      ▼
                        bsp-health.service starts                 [M18]
                                      │
                                      ▼
                        watchdog petting @ 4 Hz on /dev/watchdog0 (SwFR-052)
```

### 5.2 Thermal throttling state diagram (SwFR-06x)

```
        ┌───────────┐  T ≥ 80 °C   ┌───────────┐  T ≥ 90 °C  ┌─────────┐
        │  NORMAL   │─────────────►│   WARN    │────────────►│   HOT   │
        │  1.0 GHz  │              │  792 MHz  │             │ 396 MHz │
        └─────┬─────┘◄─────────────└─────┬─────┘◄────────────└────┬────┘
              │       T < 75 °C          │       T < 85 °C        │
              │                          │                        │  T ≥ 95 °C
              │                          │                        ▼
              │                          │                  ┌──────────┐
              └──────────────────────────┴─────────────────►│ CRIT →   │
                                                            │ orderly  │
                                                            │ shutdown │
                                                            └──────────┘
```

### 5.3 CAN frame RX path (data flow, SwFR-04x)

```
CAN bus ─► flexcan MB ─► IRQ ─► flexcan_irq() ─► napi_schedule()
                                                     │
                                          ▼ softirq
                                 flexcan_poll() → netif_receive_skb()
                                                     │
                                                     ▼
                                               AF_CAN / raw socket
                                                     │
                                                     ▼
                                     user task via recvmsg()/SocketCAN
```

---

## 6. ERROR HANDLING STRATEGY

### 6.1 Canonical error type

- **Kernel:** negative `errno` `int`, macros `ERR_PTR`, `IS_ERR`, `PTR_ERR`. Dev-level reporting via `dev_err_probe()`.
- **User-space (libbsp):** `bsp_status_t` (§3.3); `errno` preserved for POSIX calls.

### 6.2 Propagation rules

| Severity | Location | Action |
|---|---|---|
| Recoverable | any | return negative errno; caller retries or degrades |
| Probe-time dependency missing | driver `.probe()` | return `-EPROBE_DEFER` (no log spam) |
| Programming bug | kernel | `WARN_ON_ONCE()` + continue (no panic in BSP) |
| Data-corruption / impossible state | kernel | `BUG_ON()` only if continuing is unsafe — gated on `CONFIG_DEBUG_BSP` |
| Hardware fatal (bus error, ECC) | IRQ handler | disable device, notify thermal/health zone, set netif carrier off |
| Overtemp critical | thermal core | `orderly_poweroff(true)` (SwFR-063) |
| libbsp / daemon | user-space | log to journald (`LOG_ERR`), exit → systemd restart w/ backoff |
| User-space assertion | libbsp | `assert()` **compiled out** in release builds (NDEBUG); return `BSP_E_FAULT` |

### 6.3 Watchdog refresh points

| Refresh Point | Period | Rationale |
|---|---|---|
| `bsp-health` WDT petter thread | 250 ms | Independent from main loop jitter |
| Main loop liveness check | 1 s | Skips pet if health aggregation faulted |
| WDOG1 window | 10 s (SwFR-052) | 40× safety margin |
| Pre-kexec / shutdown | final pet then disarm via `WDIOC_SETOPTIONS` magic-close | Clean reboot |

---

## 7. MEMORY LAYOUT PLAN

### 7.1 Physical map (i.MX6Q SabreSD, 1 GiB DDR3)

```
0x00000000 ─ 0x0000FFFF   BootROM
0x00900000 ─ 0x0093FFFF   OCRAM (256 kB)  ── PSCI/SMP trampoline, SDMA fw
0x02000000 ─ 0x02FFFFFF   AIPS-1 (per HSI §1)
0x03000000 ─ 0x03FFFFFF   AIPS-2
0x10000000 ─ 0x2FFFFFFF   DDR3 Bank 0 (512 MiB)
0x30000000 ─ 0x4FFFFFFF   DDR3 Bank 1 (512 MiB)
```

### 7.2 Kernel image placement

```
0x10008000   Image (_text)         zImage entry
0x12000000   DTB                   imx6q-sabresd.dtb  (U-Boot ${fdt_addr})
0x12800000   initramfs (if used)
0x14000000 ─ 0x17FFFFFF CMA pool (64 MiB — for VPU/IPU/DRM dma-buf)
0x18000000 ─ 0x1FFFFFFF reserved-memory "vpu-reserved" (128 MiB)
```

### 7.3 Kernel sections (as emitted by `vmlinux.lds`)

| Section | Location | Notes |
|---|---|---|
| `.text`, `.rodata` | PAGE_OFFSET+text_offset | read-only, `ro_after_init` applied post-boot |
| `.init.text/.data` | freed after `free_initmem()` | ~1 MiB reclaimed |
| `.data`, `.bss` | RW | per-CPU areas via `DEFINE_PER_CPU` |
| IRQ stacks | 8 kB per CPU | THREAD_SIZE |
| Process kernel stacks | 8 kB per task | VMAP_STACK enabled |
| vmalloc / ioremap | 240 MiB | peripheral MMIO |
| CMA | 64 MiB | dma_alloc_coherent backend |

### 7.4 User-space budgets

| Process | RSS target | Stack | Heap limit |
|---|---|---|---|
| `bsp-health` | < 4 MiB | 128 kB main / 32 kB helper | RLIMIT_DATA = 8 MiB |
| `bsp-ota` | < 16 MiB (during update) | 256 kB | 32 MiB |
| libbsp clients | — | 8 kB/thread default | — |

No dynamic allocation in `bsp-health` steady state (pre-allocated ring buffers + `mlockall()` on RT petter thread).

### 7.5 eMMC partition layout (SwFR-010, A/B OTA)

```
mmcblk3boot0   Primary U-Boot       (4 MiB)
mmcblk3boot1   Secondary U-Boot     (4 MiB)
mmcblk3p1      boot-A  (kernel+dtb) (64 MiB, ext4)
mmcblk3p2      boot-B  (kernel+dtb) (64 MiB, ext4)
mmcblk3p3      rootfs-A             (2 GiB, ext4, ro)
mmcblk3p4      rootfs-B             (2 GiB, ext4, ro)
mmcblk3p5      data                 (remainder, ext4, rw)
```

---

## 8. DESIGN PATTERNS USED & JUSTIFICATION

| Pattern | Where | Justification |
|---|---|---|
| **Strategy / ops-table** | `struct platform_driver.probe/remove`, `clk_ops`, `gpio_chip.ops`, `drm_driver` | Kernel-idiomatic; swap implementation without recompiling consumer |
| **Observer** | thermal notifiers, netdev notifier chain, reboot_notifier, uevent → udev | Decouples producers (driver) from policy consumers (daemon, udev) |
| **Singleton** | Global CCM/ANATOP regmap, single IOMUXC instance, WDOG1 chardev | Exactly one instance per SoC — enforced by `builtin_platform_driver_probe()` |
| **State machine** | thermal throttle (§5.2), OTA A/B boot-counter (`uboot env: bootcount`, `bootlimit`), FlexCAN error states (active/passive/bus-off) | Deterministic, testable transitions for SwQT |
| **Factory (deferred)** | `devm_*` resource acquisition, `-EPROBE_DEFER` | Resolves driver load-order without explicit dependency graph |
| **Facade** | `libbsp` over libgpiod + sysfs + chardev + netlink | Shields applications from Linux ABI churn |
| **Command** | `WDIOC_*` ioctls, `struct ethtool_ops` commands | Serialisable, remotable via JSON-RPC in `bsp-health` |
| **Double-buffer / RCU** | `bsp_health_snapshot_t` publisher, netdev stats | Lock-free readers, no priority inversion on WDT pet thread |
| **Producer-consumer** | NAPI (FEC, FlexCAN), SDMA channel rings | Batches IRQs, reduces ctx-switch load |
| **Memoisation / lazy-init** | CCF `clk_prepare_enable()` refcount; PLL locked once | Saves ~50 ms per boot |

---

## 9. TRACEABILITY

| SW Module | SwFR-IDs | HSI References |
|---|---|---|
| M01 `mach-imx6q` | SwFR-001, SwFR-004 | §0, `DT_MACHINE_START` |
| M02 `clk-imx6q` | SwFR-002 | §1.2 CCM `0x020C4000`, ANATOP `0x020C8000` |
| M03 `pinctrl-imx6q` | SwFR-003, SwFR-020 | §1.1 IOMUXC `0x020E0000` (MUX_CTL, PAD_CTL, SELECT_INPUT, GPR1) |
| M04 `gpio-mxc` | SwFR-020..024 | §1.4 GPIO1..7 banks |
| M05 `sdhci-esdhc-imx` | SwFR-010..012 | §1.5 uSDHC3 `0x02198000`, uSDHC4 `0x0219C000` |
| M06 `imx-uart` | SwFR-030..031 | §1.6 UART1 `0x02020000` (console, J500) |
| M07 `fec-main` | SwFR-040..043 | §1.7 FEC `0x02188000`, PHY AR8031 on MDIO |
| M08 `imx-i2c` | SwFR-033..034 | §1.8 I2C1 `0x021A0000`, I2C2 `0x021A4000`, I2C3 `0x021A8000` |
| M09 `spi-imx` | SwFR-035 | §1.9 eCSPI1 `0x02008000` .. eCSPI5 `0x02018000` |
| M10 `flexcan` | SwFR-045..046 | §1.10 CAN1 `0x02090000`, CAN2 `0x02094000` |
| M11 `imx-sdma` | SwFR-015 | §1.11 SDMA `0x020EC000`, firmware `sdma-imx6q.bin` |
| M12 `imx-ipuv3` / `imx-drm` | SwFR-070..074 | §1.12 IPU1/IPU2, HDMI-TX `0x00120000` |
| M13 `imx-thermal` | SwFR-060..063 | §1.13 ANATOP TEMPSENSE, OCOTP fuses |
| M14 `imx6q-pm` | SwFR-050..051 | §1.14 GPC `0x020DC000`, PL310 L2 ctrl |
| M15 `snvs-rtc` | SwFR-054 | §1.15 SNVS `0x020CC000` |
| M16 `imx-wdt` | SwFR-052..053 | §1.16 WDOG1 `0x020BC000` (10 s timeout) |
| M17 `libbsp` | SwFR-080..084 | n/a (user-space facade) |
| M18 `bsp-health` | SwFR-052, SwFR-062, SwFR-085 | WDOG1 via chardev |
| M19 `bsp-ota` | SwFR-090..094 | uSDHC4 (eMMC), U-Boot env |
| M20 `bsp-test-harness` | pairs Stage 11 IT-BSP-* | all board I/O pins per HSI §2 J-connectors |

---

**End of SAD-IMX6Q-BSP-001-ARCH v1.0 — ready for Stage 11 Integration Test design.**