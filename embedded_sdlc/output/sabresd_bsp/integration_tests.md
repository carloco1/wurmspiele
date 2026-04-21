# INTEGRATION TEST SUITE — BSP-IMX6Q Driver Package

**Document ID:** SwIT-IMX6Q-BSP-001
**Stage:** V-Model Stage 11 (Integration Testing)
**Traces to:** SAD-IMX6Q-BSP-001-ARCH §1, SwRS-IMX6Q-BSP-001 v1.0
**Prerequisite:** SwUT-IMX6Q-BSP-001 (all UTs GREEN)

---

## 1. INTEGRATION TEST STRATEGY

### 1.1 Approach — Hybrid (Bottom-Up dominant)

| Layer | Approach | Rationale |
|-------|----------|-----------|
| L0 — `bsp_core` helpers | Already unit-tested; treated as **trusted base** | Bottom of dependency DAG |
| L1 — Individual drivers (`clk-imx6q`, `pinctrl-imx6q`, `gpio-mxc`, `imx-i2c`, `fec-main`, `imx-uart`, `sdhci-esdhc-imx`) | **Bottom-up** via Kunit + UML/QEMU | Each driver links against kernel subsystem core; no real HW |
| L2 — Inter-driver (clk ↔ pinctrl ↔ gpio; i2c ↔ regulator; fec ↔ phy-mdio) | **Bottom-up pair-wise** | Exercises published subsystem ops tables |
| L3 — Driver ↔ user-space (libbsp, netlink uevent mux) | **Top-down** from libbsp into faked sysfs | Validates ABI contract |
| L4 — Full probe chain on QEMU `-M sabrelite` | End-to-end smoke | Cheapest place to catch device-tree regressions |

**Justification.** Kernel drivers cannot be meaningfully validated with pure function mocks beyond the unit level — the subsystem cores (CCF, pinctrl, gpiolib, regmap) enforce the contracts that matter. A **bottom-up hybrid** lets us exercise those real cores while keeping silicon stubbed, satisfying SAD §1.2 principle #3 (unidirectional dependencies).

### 1.2 Test Environments

| Env | Target | Tools | Used For |
|-----|--------|-------|----------|
| **E1 — KUnit / UML** | `ARCH=um` in-kernel tests | KUnit, `kunit.py run` | L1, L2 (register-level via fake regmap) |
| **E2 — QEMU `-M sabrelite`** | Cortex-A9 user-mode Linux boot | QEMU 8.x, buildroot rootfs, expect | L3, L4 (real device-tree, probe order) |
| **E3 — pytest host-side** | Drives E2 over telnet/ssh | pytest 8.x, paramiko, libgpiod-python | L3 user-space contracts |
| **E4 — Defect injection** | Patched QEMU `imx6` machine model w/ register-corruption hooks | Custom QEMU fork + YAML fault-script | Section 5 |

### 1.3 Stubs vs Simulators

- **Simulators preferred** for CCF, pinctrl, gpiolib, regmap-mmio — we use the upstream `KUNIT_TEST` fake-regmap and `of-unittest` overlay mechanism so the *real* subsystem code runs.
- **Stubs** replace only the leaf hardware: a `fake-imx6q-regblock` that snapshots writes and returns scripted read values, and a `fake-phy` for FEC.
- **No direct silicon access** in any IT — a failed test must never require a physical SabreSD.

### 1.4 Entry / Exit Criteria

- **Entry:** all unit tests in SwUT-IMX6Q-BSP-001 pass; `checkpatch --strict` clean; sparse clean.
- **Exit:** 100 % of IT-xxx PASS; branch coverage ≥ 75 % across integrated driver pairs; zero new KASAN / UBSAN / lockdep splats.

---

## 2. INTEGRATION TEST CASES

### 2.1 Probe & Dependency Resolution

---

**IT-001: Deferred-probe propagation clk → pinctrl → gpio**
Objective   : verify that when `clk-imx6q` has not yet probed, downstream drivers correctly return `-EPROBE_DEFER` and re-probe succeeds once the clock provider appears (SAD §1.2 #4).
Modules     : `clk-imx6q` + `pinctrl-imx6q` + `gpio-mxc`
Setup       : QEMU E2 boot with a DT overlay that delays `ccm` node until userspace `echo` via configfs-overlay. Kernel cmdline `initcall_debug`.
Stimulus    :
 1. Boot — confirm `pinctrl-imx6q probe deferred` in dmesg.
 2. `echo 1 > /sys/kernel/config/device-tree/overlays/ccm/status`.
 3. Wait 500 ms.
Expected    : dmesg shows: `clk-imx6q: registered`, then `pinctrl-imx6q: probed`, then `gpio-mxc: probed` — strictly in that order; no `-ENODEV`.
Pass/Fail   : exit code 0 from `scripts/check-probe-order.py` comparing timestamped dmesg against ordered list.

---

**IT-002: devm-managed cleanup on deferred probe**
Objective   : no clock or regulator leaks across a defer → retry cycle.
Modules     : `bsp_core` + `clk-imx6q` + `imx-i2c`
Setup       : E1 KUnit; `fake-regulator` returns `-EPROBE_DEFER` on first 3 `regulator_get()` calls.
Stimulus    : Call `imx_i2c_probe()` 4 times.
Expected    : `clk_put` and `regulator_put` counter deltas == `clk_get`/`regulator_get` counter deltas after each failing probe. 4th probe succeeds; final enable counts == 1.
Pass/Fail   : `KUNIT_EXPECT_EQ(clk_get_ct, clk_put_ct + 1)` on success path.

---

### 2.2 Clock Framework ↔ Driver

---

**IT-010: CCF gate/ungate propagation to UART**
Objective   : enabling UART1 via `clk_prepare_enable` drives the CCGR1 CG12 bit in CCM_CCGR1 through `clk-imx6q`.
Modules     : `clk-imx6q` + `imx-uart` + fake-regblock (CCM)
Setup       : E1 KUnit. Fake CCM reg @ 0x020C_4000 zero-initialised.
Stimulus    : `uart_probe()` on faked UART1 node.
Expected    : fake-regblock shows CCM_CCGR1 bit[25:24] == 0b11 (UART1 gate on); parent clock `uart_serial_podf` enable_count == 1.
Pass/Fail   : register snapshot matches expected mask; `clk_get_rate()` returns 80 MHz.

---

**IT-011: Clock rate change triggers UART re-divisor compute**
Objective   : when the UART module clock rate changes, `imx-uart` re-writes UBIR/UBMR.
Modules     : `clk-imx6q` + `imx-uart`
Setup       : UART probed at 80 MHz, baud 115 200 — capture UBIR/UBMR snapshot S1.
Stimulus    : `clk_set_rate(uart_clk, 66_500_000)`; issue TTY `tcsetattr` with same baud.
Expected    : UBIR/UBMR snapshot S2 ≠ S1; computed baud error < 2 %.
Pass/Fail   : `abs(actual_baud − 115200) / 115200 < 0.02`.

---

### 2.3 Pinctrl ↔ GPIO / Peripheral

---

**IT-020: pinctrl state switch claims GPIO mux**
Objective   : requesting GPIO1_IO09 flips IOMUXC SW_MUX_CTL_PAD to ALT5 via pinctrl, and a later `gpiod_set_value(1)` writes GPIO1_DR bit 9.
Modules     : `pinctrl-imx6q` + `gpio-mxc`
Setup       : E1. Fake IOMUXC + GPIO1 regblocks.
Stimulus    : `gpiod_get(dev, "status-led", GPIOD_OUT_LOW)` → `gpiod_set_value(1)`.
Expected    : IOMUXC_SW_MUX_CTL_PAD_GPIO1_IO09 == 0x5; GPIO1_DR bit 9 == 1; GPIO1_GDIR bit 9 == 1.
Pass/Fail   : three register assertions.

---

**IT-021: pinctrl mutual exclusion (single owner)**
Objective   : two drivers requesting the same pad → second gets `-EBUSY` (SAD §1.2 #5).
Modules     : `pinctrl-imx6q` + `gpio-mxc` + `imx-i2c`
Setup       : fake DT where I2C3 SCL node and a GPIO consumer both claim pad `KEY_COL4`.
Stimulus    : probe I2C first, then GPIO consumer.
Expected    : I2C probe OK; GPIO consumer probe returns `-EBUSY`; dmesg contains `pin KEY_COL4 already requested`.
Pass/Fail   : `KUNIT_EXPECT_EQ(ret, -EBUSY)`.

---

### 2.4 I2C ↔ Regulator ↔ Codec (data-flow)

---

**IT-030: I2C transaction end-to-end through regmap**
Objective   : `regmap_write()` on an I2C-backed codec lands on the wire as a valid start + addr + reg + data frame.
Modules     : `imx-i2c` + `regmap-i2c` + fake-i2c-slave
Setup       : fake-i2c-slave configured as 7-bit 0x1A, 8-bit reg space.
Stimulus    : `regmap_write(rmap, 0x42, 0xA5)`.
Expected    : slave log: `START | 0x34(W) | 0x42 | 0xA5 | STOP`; I2C status register shows `IIF=1, TXAK=0`.
Pass/Fail   : byte-for-byte match on slave log.

---

**IT-031: Regulator enable sequencing before I2C access**
Objective   : codec regulator is enabled *before* the first I2C transfer (SwFR-023 power sequencing).
Modules     : `regulator-core` + `imx-i2c` + fake-codec-driver
Setup       : `pm-trace` enabled; fake regulator records enable timestamp; fake-i2c-slave records first-byte timestamp.
Stimulus    : codec `probe()`.
Expected    : `t_first_i2c − t_regulator_on ≥ 1 ms` (datasheet T_startup) and both events present in order.
Pass/Fail   : timestamp delta within [1 ms, 100 ms].

---

### 2.5 FEC (Ethernet) ↔ MDIO ↔ PHY

---

**IT-040: FEC link-up propagates netif_carrier**
Objective   : PHY link event reaches `net-core` and wakes the TX queue.
Modules     : `fec-main` + `phylib` + fake-phy + `net-core`
Setup     : E1 with fake-phy initial state = DOWN.
Stimulus    : `ifconfig eth0 up`; then fake-phy triggers LINK_UP autoneg 1000FD.
Expected    : `netif_carrier_ok(netdev) == 1`; `netif_queue_stopped(netdev,0) == 0`; ethtool `link == yes`, `speed == 1000`.
Pass/Fail   : three netdev state assertions + one ethtool output parse.

---

**IT-041: FEC RX path — SDMA → skb → net-core**
Objective   : an injected RX frame traverses BD ring, gets built into an `sk_buff`, and is delivered to `netif_receive_skb`.
Modules     : `fec-main` + `imx-sdma` + `net-core`
Setup     : fake-regblock FEC with RX BDs pre-populated; packet-injection hook writes 64-byte ICMP echo into RX0 buffer, sets BD ready+last.
Stimulus    : raise FEC RX IRQ.
Expected    : `netif_receive_skb` hook fires exactly once with `skb->len == 64` and correct checksum; RX BD wrapped (E bit cleared).
Pass/Fail   : single call to hook, payload memcmp == 0.

---

### 2.6 eSDHC ↔ mmc-core ↔ block

---

**IT-050: SD card CMD sequence on probe**
Objective   : `sdhci-esdhc-imx` emits the mandated CMD0→CMD8→ACMD41→CMD2→CMD3 sequence through `mmc_core`.
Modules     : `sdhci-esdhc-imx` + `mmc-core` + fake-sd-card
Setup     : fake-sd-card models SDHC 4 GB, responds to CMD8 with 0x1AA.
Stimulus    : trigger `mmc_rescan`.
Expected    : CMD log exactly: `[0, 8(0x1AA), ACMD41×N, 2, 3, 7]`; card state == TRAN.
Pass/Fail   : CMD log equality.

---

**IT-051: Data-transfer error propagation (CRC fail)**
Objective   : CRC-error from fake-sd-card reaches block layer as `BLK_STS_IOERR`.
Modules     : `sdhci-esdhc-imx` + `mmc-core` + `block`
Setup     : fake-sd-card injects CRC16 error on next READ_SINGLE_BLOCK.
Stimulus    : `dd if=/dev/mmcblk0 of=/dev/null bs=512 count=1`.
Expected    : bio completion status == `BLK_STS_IOERR`; `/sys/block/mmcblk0/stat` ioerr counter increments by 1; retry attempted ≤ 3 times.
Pass/Fail   : status match + ioerr delta == 1.

---

### 2.7 Thermal ↔ CPUfreq (cross-subsystem)

---

**IT-060: TMU trip-point triggers cpufreq throttle**
Objective   : when `imx-thermal` crosses the passive trip, cpufreq-policy notifier drops CPU frequency.
Modules     : `imx-thermal` + `cpufreq-dt` + `thermal-core`
Setup     : fake-TMU MMIO; policy: passive=85 °C, critical=100 °C; cpufreq table [396, 792, 996] MHz.
Stimulus    : ramp fake TMU register from 40 °C → 88 °C in 1 °C steps.
Expected    : at 85 °C, `scaling_cur_freq` drops by ≥ 1 OPP step within 500 ms; thermal_zone0/mode=enabled; trip_point_0_temp=85000.
Pass/Fail   : OPP step decrease observed + event timing < 500 ms.

---

### 2.8 User-space ABI (top-down)

---

**IT-070: libbsp GPIO request via libgpiod**
Objective   : user-space gpio request/set goes through chardev → gpiolib → gpio-mxc and reaches GPIO1_DR.
Modules     : libbsp (user) + `/dev/gpiochip0` + `gpio-mxc`
Setup     : E3 pytest drives E2.
Stimulus    : `gpioset gpiochip0 9=1`.
Expected    : QEMU-trace shows MMIO write at GPIO1_DR bit 9 → 1.
Pass/Fail   : MMIO trace grep.

---

**IT-071: netlink uevent mux — hotplug event delivery**
Objective   : a synthetic `change` uevent from `gpio-mxc` reaches the `bsp-health` user-space listener intact.
Modules     : `kobject_uevent` + netlink-mux + `bsp-health`
Setup     : E3. bsp-health started with `--socket=/run/bsp.sock`; pytest listens.
Stimulus    : `echo change > /sys/class/gpio/gpio9/uevent`.
Expected    : user-space listener receives JSON `{"subsystem":"gpio","action":"change","devpath":"/devices/…/gpio9"}` within 200 ms.
Pass/Fail   : JSON schema match + latency.

---

### 2.9 RTOS-equivalent — Kernel Concurrency

---

**IT-080: SPI + DMA concurrent I2C — no priority-inversion deadlock**
Objective   : a high-priority I2C client does not block behind a long SPI-DMA transfer sharing the same SDMA channel pool.
Modules     : `spi-imx` + `imx-sdma` + `imx-i2c`
Setup     : E1 with stress thread issuing 4 MiB SPI DMA; second thread does 100 × I2C byte reads at RT prio 80.
Stimulus    : run concurrently for 10 s.
Expected    : I2C max latency < 10 ms; no lockdep splat; no `hung_task` detected.
Pass/Fail   : p99 latency check + zero kernel warnings.

---

**IT-081: Runtime-PM reference-count integrity under parallel open/close**
Objective   : 16 parallel threads opening/closing `/dev/ttymxc0` leave `power/runtime_usage` at 0.
Modules     : `imx-uart` + `pm-runtime`
Setup     : E2.
Stimulus    : pytest xdist 16 × 1000 open/close loops.
Expected    : final `cat /sys/.../power/runtime_usage == 0`.
Pass/Fail   : exact equality.

---

## 3. STUB / DRIVER FAKE SPECIFICATIONS

| Stub / Fake | Replaces | Behaviour |
|-------------|----------|-----------|
| **fake-regblock** | Any i.MX6Q MMIO register bank | 4 KB backing array; `readl`/`writel` route to array; optional write-mask & read-side-effect callbacks per offset; snapshot & diff API. |
| **fake-ccm** | CCM @ 0x020C_4000 | Tracks CCGR gate bits; models PLL lock (returns lock=1 after ≥ 5 reads). |
| **fake-iomuxc** | IOMUXC @ 0x020E_0000 | Plain register array + ownership tracker for pad conflicts (IT-021). |
| **fake-sdma** | `imx-sdma` DMA engine ops | Accepts `dmaengine_submit`; completes after scripted delay; provides callback thread. Supports forced failure injection. |
| **fake-phy** | Realtek/Atheros PHY | Implements MDIO regs 0–31, configurable link state, autoneg completion simulated on demand. |
| **fake-i2c-slave** | Wire-level slave | 128-byte reg map; logs `(start, addr, rw, bytes, stop)` tuples; supports NACK / arbitration-lost injection. |
| **fake-sd-card** | SD/MMC card | State machine per JEDEC-84; responds to CMD0/8/ACMD41/2/3/7/17/24; CRC-error injection (IT-051). |
| **fake-tmu** | TMU register block | One RW register; a `sysfs` node sets simulated temperature. |
| **fake-regulator** | GPIO/PMIC regulator | Records enable timestamps; first N `get()` calls can return `-EPROBE_DEFER` (IT-002). |
| **kunit-pinctrl-fixture** | Standard pinctrl core (not replaced) | Provides helpers to build a synthetic pinctrl-state from C source rather than DT. |

All fakes live under `drivers/bsp-imx6q/test/fakes/`, compiled only under `CONFIG_BSP_IMX6Q_KUNIT=y`.

---

## 4. INTEGRATION TEST BUILD CONFIGURATION

<!-- FILE: test/integration/CMakeLists.txt -->
```cmake
# ---------------------------------------------------------------------------
# SwIT-IMX6Q-BSP-001 — Integration Test Build
# Host-side harness (pytest + CMake driver) that orchestrates:
#   * in-kernel KUnit runs (E1, under UML)
#   * QEMU-based full-probe runs  (E2, sabrelite)
#   * pytest top-down runs        (E3 driving E2)
# ---------------------------------------------------------------------------
cmake_minimum_required(VERSION 3.22)
project(bsp_imx6q_integration_tests
        VERSION 1.0.0
        LANGUAGES C)

# --- Options ----------------------------------------------------------------
option(BSP_IT_ENABLE_KUNIT    "Build & run KUnit L1/L2 tests (UML)"      ON)
option(BSP_IT_ENABLE_QEMU     "Boot QEMU sabrelite for L3/L4 tests"      ON)
option(BSP_IT_ENABLE_FAULTINJ "Enable defect-injection QEMU patches"     ON)
option(BSP_IT_COVERAGE        "Collect gcov across kernel test modules"  OFF)

# --- Paths ------------------------------------------------------------------
set(KERNEL_SRC   "${CMAKE_SOURCE_DIR}/../../linux"      CACHE PATH "kernel tree")
set(KERNEL_OUT   "${CMAKE_BINARY_DIR}/linux-build")
set(BUILDROOT_IMG "${CMAKE_SOURCE_DIR}/images/rootfs.ext4" CACHE FILEPATH "rootfs")
set(DTB_PATH     "${KERNEL_OUT}/arch/arm/boot/dts/imx6q-sabresd-test.dtb")
set(QEMU_BIN     "qemu-system-arm" CACHE FILEPATH "qemu binary")

# --- Toolchain sanity -------------------------------------------------------
find_program(PYTEST_BIN  pytest  REQUIRED)
find_program(QEMU_CHECK  ${QEMU_BIN})
if(BSP_IT_ENABLE_QEMU AND NOT QEMU_CHECK)
    message(FATAL_ERROR "qemu-system-arm not found; set -DQEMU_BIN=…")
endif()

# --- KUnit (UML) build ------------------------------------------------------
if(BSP_IT_ENABLE_KUNIT)
    set(KUNIT_CFG "${CMAKE_SOURCE_DIR}/kunit/bsp_imx6q.config")
    add_custom_target(kunit_build
        COMMAND ${CMAKE_COMMAND} -E make_directory ${KERNEL_OUT}
        COMMAND ${KERNEL_SRC}/tools/testing/kunit/kunit.py config
                --build_dir=${KERNEL_OUT} --kunitconfig=${KUNIT_CFG}
        COMMAND ${KERNEL_SRC}/tools/testing/kunit/kunit.py build
                --build_dir=${KERNEL_OUT} --kunitconfig=${KUNIT_CFG} --jobs=8
        COMMENT "Building KUnit (UML) integration tests"
        VERBATIM)

    add_custom_target(kunit_run
        COMMAND ${KERNEL_SRC}/tools/testing/kunit/kunit.py run
                --build_dir=${KERNEL_OUT} --kunitconfig=${KUNIT_CFG}
                --json=${CMAKE_BINARY_DIR}/kunit-results.json
        DEPENDS kunit_build
        COMMENT "Running KUnit IT-002, IT-010/011, IT-020/021, IT-030/031, IT-040/041, IT-080")
endif()

# --- Device-tree overlay compile -------------------------------------------
add_custom_command(OUTPUT ${DTB_PATH}
    COMMAND make -C ${KERNEL_SRC} O=${KERNEL_OUT}
            ARCH=arm CROSS_COMPILE=arm-linux-gnueabihf-
            imx6q-sabresd-test.dtb
    DEPENDS ${CMAKE_SOURCE_DIR}/dts/imx6q-sabresd-test.dts
    COMMENT "Compiling IT device-tree overlay")
add_custom_target(dtb ALL DEPENDS ${DTB_PATH})

# --- QEMU launcher script ---------------------------------------------------
if(BSP_IT_ENABLE_QEMU)
    configure_file(${CMAKE_SOURCE_DIR}/scripts/run_qemu.sh.in
                   ${CMAKE_BINARY_DIR}/run_qemu.sh @ONLY)

    add_custom_target(qemu_smoke
        COMMAND bash ${CMAKE_BINARY_DIR}/run_qemu.sh
                --kernel ${KERNEL_OUT}/arch/arm/boot/zImage
                --dtb    ${DTB_PATH}
                --rootfs ${BUILDROOT_IMG}
                --timeout 90
        DEPENDS dtb
        COMMENT "QEMU smoke boot (IT-001, IT-070, IT-071)")
endif()

# --- pytest top-down driver -------------------------------------------------
add_custom_target(pytest_topdown
    COMMAND ${PYTEST_BIN}
            -v --maxfail=1
            --junitxml=${CMAKE_BINARY_DIR}/it-pytest.xml
            ${CMAKE_SOURCE_DIR}/pytest
    DEPENDS qemu_smoke
    COMMENT "Running top-down IT-050/051, IT-060, IT-070, IT-071, IT-081")

# --- Defect-injection suite -------------------------------------------------
if(BSP_IT_ENABLE_FAULTINJ)
    add_custom_target(faultinj_run
        COMMAND ${PYTEST_BIN} -v
                --junitxml=${CMAKE_BINARY_DIR}/it-faultinj.xml
                ${CMAKE_SOURCE_DIR}/faultinj
        DEPENDS dtb
        COMMENT "Defect-injection tests DIT-100..DIT-107")
endif()

# --- Coverage aggregation ---------------------------------------------------
if(BSP_IT_COVERAGE)
    find_program(LCOV_BIN lcov REQUIRED)
    find_program(GENHTML_BIN genhtml REQUIRED)
    add_custom_target(coverage_report
        COMMAND ${LCOV_BIN} --capture --directory ${KERNEL_OUT}/drivers/bsp-imx6q
                --output-file ${CMAKE_BINARY_DIR}/cov.info
        COMMAND ${GENHTML_BIN} ${CMAKE_BINARY_DIR}/cov.info
                -o ${CMAKE_BINARY_DIR}/coverage_html
        DEPENDS kunit_run pytest_topdown
        COMMENT "Aggregating integration-test coverage")
endif()

# --- Meta target ------------------------------------------------------------
add_custom_target(integration_all
    DEPENDS kunit_run qemu_smoke pytest_topdown
    $<$<BOOL:${BSP_IT_ENABLE_FAULTINJ}>:faultinj_run>
    $<$<BOOL:${BSP_IT_COVERAGE}>:coverage_report>)

# --- CTest registration -----------------------------------------------------
enable_testing()
add_test(NAME IT-KUnit    COMMAND ${CMAKE_COMMAND} --build . --target kunit_run)
add_test(NAME IT-QEMU     COMMAND ${CMAKE_COMMAND} --build . --target qemu_smoke)
add_test(NAME IT-Pytest   COMMAND ${CMAKE_COMMAND} --build . --target pytest_topdown)
if(BSP_IT_ENABLE_FAULTINJ)
    add_test(NAME IT-Faultinj COMMAND ${CMAKE_COMMAND} --build . --target faultinj_run)
endif()

set_tests_properties(IT-KUnit    PROPERTIES TIMEOUT 600)
set_tests_properties(IT-QEMU     PROPERTIES TIMEOUT 300)
set_tests_properties(IT-Pytest   PROPERTIES TIMEOUT 900)
```

---

## 5. DEFECT-INJECTION TESTS

Located under `test/integration/faultinj/`. Each test patches the fake model at runtime via a YAML script consumed by the custom QEMU hook.

---

**DIT-100: Corrupted I2C SCL glitch → driver re-arbitrates**
Inject      : fake-i2c-slave drops ACK on bytes 3–4 of 10 successive writes.
Module path : `imx-i2c` → `regmap-i2c` → `codec`.
Expected    : driver logs `i2c arbitration lost, retrying`; ≤ 3 retries then success or `-EIO`; no kernel oops; `errors_arlo` sysfs counter increments.
Pass/Fail   : counter == 10 and final transfers OK.

---

**DIT-101: FEC RX buffer descriptor overrun**
Inject      : fake-fec sets RX BD E=0 on all descriptors (ring full) while injecting 1000 frames.
Expected    : `rx_fifo_errors` increments; driver re-arms DMA after draining; no panic; `ifconfig eth0 down && up` recovers.
Pass/Fail   : counter monotonic, `ping` works after recovery.

---

**DIT-102: SDHC command timeout**
Inject      : fake-sd-card stops responding to CMD17 mid-transfer.
Expected    : `sdhci` reports `Command timeout`; `mmc_core` issues `CMD12` (stop); block layer returns `BLK_STS_TIMEOUT`; card re-initialised on next access.
Pass/Fail   : dmesg sequence exact; subsequent read succeeds.

---

**DIT-103: Clock gate stuck**
Inject      : fake-ccm refuses to clear CCGR bit on `clk_disable`.
Expected    : `clk_summary` still shows enable_count transition; driver does not deadlock; `bsp_poll_reg32` returns `-ETIMEDOUT` at most one caller, logged once.
Pass/Fail   : no hung_task, exactly one `-ETIMEDOUT` log line.

---

**DIT-104: Regulator under-voltage event**
Inject      : fake PMIC raises UV IRQ mid-I2C write.
Expected    : `regulator-core` broadcasts `REGULATOR_EVENT_UNDER_VOLTAGE`; codec driver marks itself DEAD; future I2C returns `-ENODEV`; sysfs `state` == `disabled`.
Pass/Fail   : event observed, state transition logged.

---

**DIT-105: Thermal runaway — critical trip**
Inject      : fake-TMU ramps to 110 °C in 2 s.
Expected    : `thermal-core` calls `orderly_poweroff()`; kernel reaches `Power down` within 30 s; no data-corruption on mmcblk0 (checksum before/after).
Pass/Fail   : poweroff observed + checksum match.

---

**DIT-106: Pinctrl bogus state — invalid mux value**
Inject      : DT overlay sets `fsl,pinmux-id` to reserved 0x7.
Expected    : `pinctrl-imx6q` probe rejects state with `-EINVAL`; dependent I2C3 probe fails cleanly, no partial registration in `/sys/class/i2c-dev`.
Pass/Fail   : exactly one `-EINVAL` log, sysfs absent.

---

**DIT-107: Concurrent unbind during active transfer**
Inject      : while 16 MiB SPI DMA in flight, `echo spi0.0 > /sys/bus/spi/drivers/.../unbind`.
Expected    : unbind blocks until DMA completes or aborts cleanly; no use-after-free (KASAN); `dmaengine_terminate_sync` invoked.
Pass/Fail   : zero KASAN reports, unbind returns 0.

---

## 6. TRACEABILITY MATRIX

| IT-ID  | SW Architecture Element                         | SwFR-IDs               | Unit-Test Prerequisites |
|--------|-------------------------------------------------|------------------------|-------------------------|
| IT-001 | SAD §1.1 Driver layer; §1.2 #4 defer-probe      | SwFR-002, SwFR-010     | UT-C04                  |
| IT-002 | bsp_core devm cleanup                           | SwFR-003, SwFR-004     | UT-C02, UT-C03          |
| IT-010 | CCF ↔ Driver layer                              | SwFR-011, SwFR-030     | UT-C02                  |
| IT-011 | CCF rate-change notifier                        | SwFR-030, SwFR-050     | UT-C02                  |
| IT-020 | pinctrl core ↔ gpio-mxc                         | SwFR-020, SwFR-021     | UT-C01                  |
| IT-021 | SAD §1.2 #5 single-owner                        | SwFR-022               | UT-C04                  |
| IT-030 | regmap-i2c ↔ imx-i2c                            | SwFR-040               | UT-C01                  |
| IT-031 | regulator ↔ I2C sequencing                      | SwFR-023, SwFR-041     | UT-C03                  |
| IT-040 | net-core ↔ fec-main ↔ phylib                    | SwFR-060, SwFR-061     | —                       |
| IT-041 | fec-main ↔ imx-sdma ↔ net-core                  | SwFR-060, SwFR-062     | —                       |
| IT-050 | mmc-core ↔ sdhci-esdhc-imx                      | SwFR-070, SwFR-071     | —                       |
| IT-051 | mmc-core ↔ block error propagation              | SwFR-072, SwFR-005     | UT-C01                  |
| IT-060 | thermal-core ↔ cpufreq-dt ↔ imx-thermal         | SwFR-080, SwFR-081     | —                       |
| IT-070 | libbsp ↔ gpiolib ↔ gpio-mxc                     | SwFR-021, SwFR-100     | UT-C04                  |
| IT-071 | kobject_uevent ↔ netlink-mux                    | SwFR-101               | —                       |
| IT-080 | SDMA concurrency, RT latency                    | SwFR-090, SwFR-091     | —                       |
| IT-081 | runtime-PM refcount                             | SwFR-092               | —                       |
| DIT-100| I2C arbitration recovery                        | SwFR-005, SwFR-040     | UT-C01                  |
| DIT-101| FEC overrun handling                            | SwFR-005, SwFR-062     | —                       |
| DIT-102| SDHC timeout recovery                           | SwFR-005, SwFR-071     | UT-C01                  |
| DIT-103| Clock timeout                                   | SwFR-005, SwFR-030     | UT-C01, UT-C02          |
| DIT-104| Regulator UV event                              | SwFR-005, SwFR-023     | UT-C03                  |
| DIT-105| Thermal critical                                | SwFR-005, SwFR-080     | —                       |
| DIT-106| Invalid pinmux state                            | SwFR-005, SwFR-020     | UT-C04                  |
| DIT-107| Unbind-during-transfer (UAF resistance)         | SwFR-005, SwFR-092     | —                       |

---

**END OF DOCUMENT — SwIT-IMX6Q-BSP-001**