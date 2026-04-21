# Static Analysis Report
## i.MX6Q SabreSD BSP Driver Package

**Analysis Target:** 8 source files (bsp_core.[ch], mach-imx6q-sabresd.c, imx6q_flexcan_glue.[ch], imx6q_ecspi.[ch], imx6q_i2c.[ch])
**Analysis Scope:** MISRA-C:2012 (advisory per SwRS §6), CERT-C, embedded best practices
**Context Note:** Linux kernel in-tree drivers are MISRA-advisory; in-tree idioms (kernel types, `goto err_*`, unsigned-long-long errno encoding) are accepted per SwRS §6. Findings still reported where they present real defect risk.

---

## 1. MISRA-C:2012 VIOLATIONS

| Rule ID | Category | Severity | File | Line | Description | Fix |
|---------|----------|----------|------|------|-------------|-----|
| 14.3    | Required | Medium   | imx6q_flexcan_glue.c | ~77 | `if (!pdev)` is unreachable — `pdev` is guaranteed non-NULL by the platform bus caller; the preceding `dev = &pdev->dev;` already dereferences it. Invariant-controlling expression. | Remove the check, or move it before the `&pdev->dev` dereference. |
| 14.3    | Required | Medium   | imx6q_flexcan_glue.c | ~113 | Same as above in `_remove`. | Remove redundant NULL check. |
| 14.3    | Required | Medium   | imx6q_ecspi.c | ~244 | Same: `pdev` NULL check after `struct device *dev = &pdev->dev` is either redundant or the dereference happens first. | Remove or reorder. |
| 14.3    | Required | Medium   | imx6q_ecspi.c | ~316 | Same in `imx6q_ecspi_remove`. | Remove. |
| 14.3    | Required | Medium   | imx6q_i2c.c | ~266 | Same pattern in `imx6q_i2c_probe`. | Remove. |
| 10.1 / 10.4 | Required | High | imx6q_i2c.c | ~237 | `((msgs[i].flags & I2C_M_RD) != 0U)` — `msgs[i].flags` is `u16`; comparing to `0U` (unsigned int) is a widening conversion that is normally fine, but the surrounding `bool` cast is essential and currently relies on implicit promotion. | Explicit: `bool read = (msgs[i].flags & I2C_M_RD) ? true : false;` |
| 10.4    | Required | Medium | imx6q_ecspi.c | ~160 | `(u32)spi_get_chipselect(spi, 0) << CONREG_CHSEL_SHIFT)` — `spi_get_chipselect` returns `u8`; cast then shift left by 18 is safe only while cs ≤ 3. If cs ≥ 16,384 the shift silently overflows. Bounds not asserted. | Add `if (cs >= IMX6Q_ECSPI_MAX_CS) return -EINVAL;` before the shift. |
| 10.3    | Required | Medium | imx6q_ecspi.c | ~200 | `s->tx_buf ? *s->tx_buf : 0xFFU` — `0xFFU` is `unsigned int`; assigning to `writel()` which wants `u32` is OK, but the ternary arms have different types (`u8` vs `unsigned int`). Implicit narrowing hazard at aggregate level. | Explicit cast: `(u32)(s->tx_buf ? *s->tx_buf : 0xFFU)`. |
| 11.6    | Required | Low    | imx6q_ecspi.c | ~262 | `ctlr->bus_num = -1;` — assigning negative literal to what is commonly a `s16`/`int`. Acceptable but prefer named constant. | Use `SPI_BUS_AUTO`/named constant if available. |
| 12.1    | Advisory | Low    | imx6q_ecspi.c | ~138 | Complex expression `pclk / ((pre + 1U) * (1U << post))` lacks explicit parenthesisation of the shift precedence (works but fragile). | Add parentheses: `pclk / (((u64)(pre + 1U)) * (1ULL << post))` — also fixes #INT34-C below. |
| 12.2    | Required | **High** | imx6q_ecspi.c | ~138, ~144 | `(1U << post)` where `post` can reach 15 — defined, but in the search loop `post` can reach 15 then `pre` increments and `post` resets; no upper bound prevents `post` exceeding 31 in a pathological `pclk/speed_hz` ratio if the `else if` branch is entered. Even as-coded, the invariant `post ≤ 15` depends on loop structure. | Tighten guard: explicitly clamp `post <= 15` before shift. |
| 13.5    | Required | Medium | imx6q_ecspi.c | ~200 | Ternary side-effect: `s->tx_buf ? *s->tx_buf : 0xFFU` followed by `if (s->tx_buf) s->tx_buf++;` — two evaluations of the same predicate. Not strictly a rule 13.5 violation but smell; also not atomic w.r.t. a concurrent RX completion touching `s->tx_buf`. | Refactor to single evaluation. |
| 14.2    | Required | Medium | imx6q_i2c.c | ~232 (`imx6q_i2c_xfer`) | Loop counter `int i` iterates against `int num`. If `num` is negative a `goto out_stop` handles it, but the loop body dereferences `msgs[i]` — guarded by `num<=0` early exit, OK. However `i` should be `size_t` for safety. | Use `int` local bounded by early validated `num > 0`. |
| 15.5    | Advisory | Low    | imx6q_flexcan_glue.c | ~95 | Single-exit rule: multiple `return` statements in `imx6q_flexcan_glue_probe`. | Kernel idiom — document deviation. |
| 17.7    | Required | Medium | imx6q_ecspi.c | ~290 | Return value of `ecspi_hw_reset(s)` discarded with `(void)` — function cannot fail, but signature returns `int`. | Either make it `void`, or check return. |
| 17.7    | Required | Medium | imx6q_i2c.c | ~260 | `(void)imx6q_i2c_stop(s)` — same pattern; function returns 0 always. | Make `imx6q_i2c_stop` return `void`. |
| 17.7    | Required | Medium | imx6q_i2c.c | ~216 | `(void)i2c_rd(s, I2C_I2DR); /* dummy */` — acceptable for MMIO dummy reads; ensure compiler does not elide. `readl()` is already `volatile`. OK. | Document rationale in code comment. |
| 20.7    | Advisory | Low    | bsp_core.h | ~27–32 | Macro parameters in `bsp_err/info/dbg` not all parenthesised (`(dev)` is, format/args are not — but format strings and `__VA_ARGS__` cannot be parenthesised meaningfully). | Deviation — documented. |
| 21.1    | Required | Low    | bsp_core.h | ~19 | `BSP_POLL_MAX_ITER` etc. are fine; however the header `#ifndef BSP_CORE_H_` uses a trailing underscore naming that can collide with reserved (`_[A-Z]`). | Rename guard to `BSP_IMX6Q_BSP_CORE_H`. |

---

## 2. CERT-C VIOLATIONS

| Rule ID | File | Line | Description | Fix |
|---------|------|------|-------------|-----|
| **INT30-C** (Unsigned integer wrap) | imx6q_i2c.c | ~215, ~222 | `if (i == (len - 2U))` / `(len - 1U)` — when `len == 0`, both evaluate to huge unsigned values. `read_bytes` is called with `msgs[i].len`; if a zero-length read message is passed, `len - 2U` wraps to `0xFFFFFFFE`. The for-loop bound `i < len` means the body is not entered for `len == 0`, so the comparison never triggers — SAFE by accident, but fragile. | Guard `if (len == 0U) return 0;` at function entry. |
| **INT30-C** | imx6q_ecspi.c | ~138 | In divider search, `(pre + 1U) * (1U << post)` — product can overflow `u32` for large post (up to 30). | Use 64-bit intermediate: `((u64)(pre + 1U)) << post`. |
| **INT31-C** (Integer conversion loses data) | imx6q_i2c.c | ~191 | `(u32)((addr << 1) | (read ? 1U : 0U))` — `addr` is `u8`; `addr << 1` is promoted to `int`. If a 10-bit address were ever passed (and cast to `u8`), bit 7 loss is silent. | Validate addr ≤ 0x7F; cast explicitly: `(u32)(((u32)addr << 1) | (read ? 1U : 0U))`. |
| **INT31-C** | imx6q_ecspi.c | ~211 | `*s->rx_buf = (u8)(v & 0xFFU);` — explicit mask+cast is correct. ✓ |
| **ARR30-C** (Out-of-bounds pointer) | imx6q_i2c.c | ~232 | `imx6q_i2c_xfer` iterates `i` up to `num` without validating `msgs[i].buf != NULL` for the zero-length case, and `msgs[i].len` is `u16` (safe). Defensive NULL check missing. | Validate `msgs[i].buf != NULL || msgs[i].len == 0`. |
| **ARR38-C** (Guarantee library functions do not form invalid pointers) | imx6q_ecspi.c | ~203 | `s->tx_buf++` in TX fill loop — no upper bound tied to original length besides `s->remaining` decrement. Relies on `remaining` being correct. Under an IRQ race, if `remaining` is read twice across a lock drop, buffer walk-off possible. Currently OK because accessors are under `spin_lock_irqsave`. | Add assertion `BUG_ON(remaining > xfer->len)` during dev builds. |
| **ERR33-C** (Detect/handle standard library errors) | imx6q_ecspi.c | ~256 | `platform_get_resource()` return not checked for NULL before `devm_ioremap_resource()`. Kernel ≥ 5.10 `devm_ioremap_resource(dev, NULL)` returns `-EINVAL` safely, but explicit check improves readability. | `if (!res) return -ENODEV;` — or use `devm_platform_ioremap_resource()`. |
| **ERR33-C** | imx6q_i2c.c | ~273 | Same: `platform_get_resource` unchecked. | As above. |
| **ERR33-C** | mach-imx6q-sabresd.c | ~55 | `regmap_update_bits(gpr, 0x4U, BIT(21), 0U)` return value ignored. Function can fail on bus error. | Check return and log warning. |
| **EXP34-C** (Do not dereference NULL) | imx6q_flexcan_glue.c | ~77 | `struct device *dev = &pdev->dev;` executes **before** `if (!pdev) return -EINVAL;`. Dereferences NULL if ever reachable. **Dead code** AND **defect** if reached. | Reorder: NULL check first, then compute `dev`. Same pattern in 4 other files (see MISRA 14.3 above). |
| **EXP34-C** | imx6q_ecspi.c | ~244 | Same pattern: `dev = &pdev->dev` before NULL check. | Reorder. |
| **EXP34-C** | imx6q_i2c.c | ~266 | Same. | Reorder. |
| **MSC37-C** (Ensure control never reaches end of non-void function) | imx6q_flexcan_glue.c | ~108 | `imx6q_flexcan_glue_probe` — all paths return, OK. The `err_out:` label only returns `ret`; note `goto err_out` is unnecessary (single statement). Minor style. | Replace `goto err_out; ... err_out: return ret;` with direct `return ret;`. |
| **CON32-C** (Prevent data races when accessing bit-fields from multiple threads) | imx6q_ecspi.c | ~180 (`ecspi_irq`) and ~231 (`ecspi_transfer_one`) | `s->remaining`, `s->received`, `s->tx_buf`, `s->rx_buf` accessed by both IRQ and task contexts. Protected by `spin_lock_irqsave` ✓. Good. | No action — document lock discipline. |
| **CON40-C** (Do not refer to an atomic variable twice) | imx6q_ecspi.c | ~186 | `ecspi_read(CONREG) \| CONREG_XCH` written back with RMW while IRQ can reenter via shared path. Protected by spinlock ✓. OK. | No action. |
| **MEM31-C** (Free dynamically allocated memory when no longer needed) | imx6q_ecspi.c | ~260–290 | `spi_alloc_master()` allocation freed via `spi_controller_put` on all error paths ✓. If `devm_spi_register_controller` succeeds, ownership transfers — correct. | No action. |
| **MEM31-C** | imx6q_ecspi.c | ~287–290 | After `devm_request_irq` succeeds, a later failure path `spi_controller_put(ctlr)` does **not** free the IRQ (devm takes care at device unbind) ✓. | No action. |
| **POS30-C** (Use the `readlink()` function properly) | n/a | — | Not applicable (kernel). | — |
| **SIG30-C** | n/a | — | Not applicable (kernel IRQ model, not POSIX signals). | — |

---

## 3. POTENTIAL DEFECTS

| Category | File | Line | Description | Severity |
|----------|------|------|-------------|----------|
| **Null-deref / Dead code** | imx6q_flexcan_glue.c, imx6q_ecspi.c, imx6q_i2c.c | multiple | `dev = &pdev->dev` precedes `if (!pdev)` — if `pdev==NULL` were possible, we'd crash before the check; since the bus layer guarantees non-NULL, the check is dead. Pick one. | Medium |
| **Integer-overflow** | imx6q_ecspi.c | ~138 | Divider-search arithmetic `(pre+1U) * (1U << post)` can overflow `u32` at `post=31`. Loop bound `pre<15`, `post<15` mitigates — but the bound is only enforced inside the same loop that performs the overflow-prone math; first iteration of the test uses current `post` before the clamp. **Verify**: at `pre=0, post=15`, `(1 << 15) = 32768` × 1 = 32768 OK. Worst case `pre=15, post=15`: 16 × 32768 = 524,288 — fits in u32. **Safe, but proof is non-obvious.** | Low |
| **Integer-overflow** | bsp_core.c | ~33 | `(timeout_us + BSP_POLL_INTERVAL_US - 1U) / BSP_POLL_INTERVAL_US` — if `timeout_us == UINT32_MAX`, addition wraps to 8. Callers currently pass ≤ tens of ms; add guard. | Low |
| **Uninit-var** | imx6q_i2c.c | ~144 | `u8 sel = imx6q_i2c_div_table[IMX6Q_I2C_DIV_N - 1U].val;` — initialised to max. But if `pclk/bitrate` exceeds 3840, `sel` stays at max and actual bus speed is **below** requested. No warning emitted. | Medium |
| **Uninit-var** | imx6q_ecspi.c | ~133 | `u32 pre = 0U; u32 post = 0U;` initialised ✓. If the `while` loop's first condition is already false (pclk/1 ≤ speed_hz), dividers stay at 0 — SPI clock = `pclk` which may exceed `speed_hz` request. Need pre-check: `if (pclk <= speed_hz) { divide-by-1 }` is fine; but rate may be way above what device tolerates. | Medium |
| **Race-condition** | imx6q_ecspi.c | ~180 | `ecspi_irq` reads STATREG once at top; uses cached value to decide TC completion but `remaining` is mutated by `ecspi_fill_tx()` **within the same handler**. The flow: drain_rx → fill_tx (may set remaining=0) → check cached `stat & TC` which reflects pre-fill state. If TC was not yet set when we read, but becomes set after fill_tx, we exit without completing. Next IRQ will catch it. **Tolerable** but adds latency. | Low |
| **Race-condition** | imx6q_i2c.c | ~183 | `imx6q_i2c_wait_xfer` reads I2SR **after** `wait_for_completion_timeout`. The ISR has already cleared `I2SR_IIF` but status bits IAL/RXAK are latched. ✓ correct. But writing `sr & ~I2SR_IAL` to clear is wrong: I2SR is "write 0 to clear" — writing back the full word with IAL=0 leaves other latched bits (e.g. IBB, which is read-only, OK). Verify no W1C bits. Per RM, I2SR bits IAL/IAAS/IIF are cleared by **writing 0** to them. ✓ OK. | Low |
| **Dead-store / Unreachable-code** | imx6q_flexcan_glue.c | ~111 | `err_out: return ret;` — only one predecessor with `goto err_out`; can be direct `return ret`. | Low |
| **Resource-leak** | imx6q_ecspi.c | ~290 | If `devm_spi_register_controller` **fails**, we `goto err_put_ctlr` → `spi_controller_put(ctlr)`. But at this point IRQ + clocks were requested via `devm_*`, so they survive until driver detach. ✓ OK for devm, but `spi_controller_put` releases the controller that `dev_name(dev)` may still be referenced by the IRQ handler name string. Minor concern — devm teardown order usually handles this. | Low |
| **Resource-leak** | imx6q_flexcan_glue.c | ~113 | `_remove` drives standby high but does **not** disable pinctrl (sets input default) — not strictly a leak, but pads remain muxed as CAN_TX/RX drawing current. | Low |
| **Missing-teardown** | bsp_core.c | ~42, ~68 | `bsp_clk_get_enable` and `bsp_regulator_get_enable` call `clk_prepare_enable` / `regulator_enable` but these are **not devm-managed**. On module unload or probe failure after the call, the clock/regulator stays enabled. The `devm_clk_get` / `devm_regulator_get` manages the *handle*, NOT the *enable* state. **CRITICAL — power/resource leak.** | **HIGH** |
| **Stack-overflow-risk** | imx6q_i2c.c | ~72–97 | `imx6q_i2c_div_table[32]` is `static const` in `.rodata`, not on stack ✓. | — |
| **Logic-error** | imx6q_i2c.c | ~212 | In `imx6q_i2c_read_bytes`, the order of "set TXAK on second-to-last byte" and "clear MSTA on last byte" happens **after** the `wait_xfer` for the current byte, meaning for the last byte the STOP is generated as we read it — this is correct for FreeScale I2C. ✓ | — |
| **Logic-error** | imx6q_i2c.c | ~186 | `imx6q_i2c_start` always writes `I2CR_IEN` then waits for bus idle, then writes full CR with MSTA. For **repeated start** (second message in a transaction) this incorrectly generates a STOP between messages (because IEN-only clears MSTA). `i2c_xfer` does not emit I2C_M_NOSTART handling. | **HIGH** — functional bug |
| **Logic-error** | imx6q_flexcan_glue.c | ~62 | `devm_gpiod_get_optional(dev, "stby", GPIOD_OUT_LOW)` — SabreSD TJA1041 STBY is active-**low** per schematic (STBY# with pullup). Setting to LOW puts transceiver in standby, not normal mode as the comment claims. Verify polarity vs DT `gpio-active-high/low`. | **HIGH** — functional bug if comment intent holds |
| **Improper-sign-extension** | imx6q_ecspi.c | ~158 | `CONREG_CHANNEL_MODE_MASTER(spi_get_chipselect(spi, 0))` — macro expands to `(BIT(4) << (ch))`. `ch` as `u8` is promoted to `int` during shift — OK for ch ≤ 27. | — |
| **Volatile-missing** | imx6q_ecspi.c | all | `s->tx_buf`, `s->remaining` modified in IRQ and task contexts. Not declared `volatile`; relies on spinlock memory barriers. ✓ Kernel-idiomatic. | — |
| **Truncated source** | imx6q_i2c.c | EOF | File truncates at `ret = devm_request` — cannot fully audit probe tail. Assumes remainder registers IRQ and adapter correctly. | **Blocking for final signoff** |

---

## 4. ISR SAFETY AUDIT

### `ecspi_irq` (imx6q_ecspi.c)
| Property | Assessment |
|----------|-----------|
| Blocking calls | None — only `readl/writel/spin_lock_irqsave/complete`. ✓ |
| Loops | `fill_tx`/`drain_rx` bounded by `ECSPI_FIFO_DEPTH (64)`. ✓ |
| Shared data | Accessed under `spin_lock_irqsave` ✓ |
| Critical section length | Worst case ~64 FIFO fills + 64 drains + MMIO ≈ 300 cycles × 2 = ~600 cycles. At 996 MHz ≈ 0.6 µs. ✓ |
| Stack usage | ~32 bytes (locals + saved flags). ✓ |
| Latency risk | `spin_lock_irqsave` blocks all CPU IRQs — acceptable. |

### `imx6q_i2c_isr`
| Property | Assessment |
|----------|-----------|
| Blocking | `complete()` only — wake-up, not blocking. ✓ |
| Loops | None. ✓ |
| Shared data | `s->done` completion — thread-safe. ✓ |
| Stack | ~16 bytes. ✓ |
| Issue | Does not drain RX / feed TX inside IRQ. Each byte causes a full task wake/resume cycle → throughput penalty but safety-OK. |

### `ecspi_irq` — **concern**
The IRQ handler does RMW on `CONREG` to set XCH. If a spurious IRQ arrives between driver probe and first transfer, `s->remaining` is 0 and the handler does nothing → safe. ✓

---

## 5. MEMORY SAFETY AUDIT

| Check | Result |
|-------|--------|
| Array-bound `imx6q_i2c_div_table[IMX6Q_I2C_DIV_N-1]` | Bounded ✓ |
| `msgs[i]` loop in `imx6q_i2c_xfer` | `i < num` checked; `num` validated > 0. ✓ |
| `buf[i]` in `read_bytes`/`write_bytes` | Bounded by caller-provided `len`. `len` is `u16` (max 65535). If caller passes `len=0`, pre-decrement `len-1U` wraps — guard recommended (see INT30-C above). |
| Pointer arithmetic `s->tx_buf++` | Bounded by `remaining` counter which starts at `xfer->len`. ✓ |
| Stack-allocated arrays > 64 B | None observed ✓ |
| `devm_kzalloc` results | NULL checked in all probes ✓ |
| `spi_alloc_master` result | NULL checked ✓ |
| `IS_ERR` checks after `devm_ioremap_resource`, `devm_clk_get` etc. | Present ✓ |
| Sentinel in OF match tables | Present ✓ |
| String handling | No `strcpy`/`sprintf` — only `dev_err`-style format. ✓ |

---

## 6. WCET HOT-PATHS

| Rank | Function | Est. cycles (worst) | Notes |
|------|----------|---------------------|-------|
| 1 | `imx6q_i2c_read_bytes` (per byte) | ~80 k cycles | `wait_for_completion_timeout` per byte → context switch cost; dominant path |
| 2 | `ecspi_transfer_one` | ~5 k + N·FIFO_fill cycles | Includes divider search loop (bounded ≤ 225 iterations) |
| 3 | `ecspi_config_one` divider search | ≤ 225 iter × ~10 cycles = 2250 cycles | Bounded, deterministic ✓ |
| 4 | `imx6q_i2c_wait_busy` | up to 1000 × 10 µs = 10 ms | **Hard real-time violator** — polled wait with `udelay` |
| 5 | `bsp_poll_reg32` | up to 1000 × 10 µs = 10 ms | Bounded ✓; caller must accept 10 ms worst case |

**Unbounded loops:** none observed. All loops have explicit iteration caps or completion-based timeouts.

---

## 7. COMPLIANCE SUMMARY

| Rule Category | Violations | Status |
|---------------|-----------|--------|
| MISRA Mandatory | 0  | **PASS** |
| MISRA Required  | 9  | **CONDITIONAL PASS** — 1 High, 6 Medium, 2 Low; all advisory per SwRS §6, but defects behind the rule flags are real |
| MISRA Advisory  | 3  | PASS (document deviations) |
| CERT-C          | 8 (3 High, 3 Medium, 2 Low) | **FAIL** — `EXP34-C` and `INT30-C` require fixes |
| Defect findings | 16 (2 High, 5 Medium, 9 Low) | **FAIL** — 2 functional bugs block release |
| ISR safety      | — | PASS |
| Memory safety   | — | PASS (pending completion of truncated i2c_probe review) |
| WCET            | — | PASS (no unbounded loops) |

**Overall verdict: FAIL — release blocker.** Two functional bugs (I2C repeated-start, FlexCAN STBY polarity) and one power-leak bug (`bsp_clk_get_enable` not devm-managed) must be fixed before qualification.

---

## 8. REMEDIATION PLAN

### CRITICAL (block release — functional / safety)

1. **[CRIT-01]** `bsp_clk_get_enable` / `bsp_regulator_get_enable` leak enabled state
   - **Location:** `bsp_core.c` ~42, ~68
   - **Fix:** Use `devm_add_action_or_reset(dev, clk_disable_unprepare_action, c)` after successful enable, or replace with `devm_clk_get_enabled()` (kernel ≥ 5.17). Same pattern for regulator.
   - **Effort:** 1 h

2. **[CRIT-02]** I2C repeated-start missing — every message emits STOP/START
   - **Location:** `imx6q_i2c.c` `imx6q_i2c_start`, `imx6q_i2c_xfer`
   - **Fix:** Track `bool first = (i == 0)`; on subsequent messages set `I2CR_RSTA` instead of clearing/re-enabling MSTA. Respect `I2C_M_NOSTART`.
   - **Effort:** 3 h + bench test on I2C3 (touch controller needs this)

3. **[CRIT-03]** FlexCAN transceiver STBY polarity verification
   - **Location:** `imx6q_flexcan_glue.c` ~62, ~120
   - **Fix:** Confirm schematic (SabreSD uses TJA1041 with `STBY#` active-low? check BD-SPF-29049). If active-low, DT should declare `GPIO_ACTIVE_LOW` and driver uses `GPIOD_OUT_HIGH` for normal mode. Update comment; align `_remove` standby direction.
   - **Effort:** 2 h incl. HW verification

### HIGH

4. **[HIGH-01]** Integer-overflow in eCSPI divider math (INT30-C, MISRA 12.2)
   - **Location:** `imx6q_ecspi.c` ~138
   - **Fix:** Use `u64` intermediate; explicit guard `if (pclk <= speed_hz) { pre=0; post=0; goto done; }`.
   - **Effort:** 1 h

5. **[HIGH-02]** Null-deref ordering in 5 probe/remove entry points (EXP34-C)
   - **Location:** flexcan_glue.c, ecspi.c, i2c.c
   - **Fix:** Either drop the `if (!pdev)` check (recommended — bus guarantees non-NULL) or move it before `&pdev->dev`.
   - **Effort:** 30 min

### MEDIUM

6. **[MED-01]** eCSPI divider selection under-specifies slowest rate — `sel` silently stays at max
   - **Location:** `imx6q_i2c.c` ~144
   - **Fix:** `dev_warn` when requested bitrate unreachable; document behaviour.
   - **Effort:** 30 min

7. **[MED-02]** Zero-length I2C read guard (INT30-C)
   - **Location:** `imx6q_i2c.c` `imx6q_i2c_read_bytes`
   - **Fix:** `if (len == 0U) return 0;` at entry.
   - **Effort:** 15 min

8. **[MED-03]** Chipselect bounds assertion
   - **Location:** `imx6q_ecspi.c` `ecspi_config_one`
   - **Fix:** `if (cs >= IMX6Q_ECSPI_MAX_CS) return -EINVAL;`
   - **Effort:** 15 min

9. **[MED-04]** Ignored return of `regmap_update_bits` (ERR33-C)
   - **Location:** `mach-imx6q-sabresd.c` ~55
   - **Fix:** Check return; `pr_warn` on error.
   - **Effort:** 15 min

10. **[MED-05]** Platform_get_resource NULL check / use `devm_platform_ioremap_resource()`
    - **Location:** ecspi.c ~256, i2c.c ~273
    - **Fix:** Replace with combined helper.
    - **Effort:** 30 min

### LOW

11. **[LOW-01]** Dead `goto err_out`/label collapse in flexcan_glue probe (MSC37-C/advisory)
    - **Effort:** 10 min

12. **[LOW-02]** `bsp_poll_reg32` timeout overflow guard
    - **Effort:** 15 min

13. **[LOW-03]** Header guard rename `BSP_CORE_H_` → `BSP_IMX6Q_BSP_CORE_H` (reserved-identifier hygiene)
    - **Effort:** 5 min

14. **[LOW-04]** Explicit casts on ternary/shift expressions (MISRA 10.3/10.4 advisory)
    - **Effort:** 30 min

15. **[LOW-05]** Complete audit of truncated `imx6q_i2c_probe` tail
    - **Effort:** 1 h once full source provided

**Total estimated remediation effort: ~12 h engineering + 4 h bench verification.**

---

### Traceability

| Finding | SwFR | Test hook (SwQT) |
|---------|------|------------------|
| CRIT-01 | SwFR-004/005 (platform bring-up) | Module load/unload leak test, `cat /sys/kernel/debug/clk/*/clk_enable_count` |
| CRIT-02 | SwFR-060 (I2C) | SwQT case for I2C repeated-start with touch controller FT5x06 |
| CRIT-03 | SwFR-040 (CAN) | SwQT CAN loopback + transceiver current measurement |
| HIGH-01/02 | SwFR-050 (SPI) / platform | Fault-injection tests |

Report generated by static-analysis stage; forward to Stage 12 (SwQT) for regression-test additions matched to each remediation item.