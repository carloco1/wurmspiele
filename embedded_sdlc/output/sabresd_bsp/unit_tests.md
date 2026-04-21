# UNIT TEST SUITE — BSP-IMX6Q Core Helpers
**Document ID:** SwUT-IMX6Q-BSP-001
**Stage:** V-Model Stage 10 (Unit Testing)
**Traces to:** DDD-IMX6Q-BSP-001 §M00, SwRS-IMX6Q-BSP-001 SwFR-001..SwFR-005

---

## 1. TEST PLAN

### 1.1 Scope
Unit tests for the `bsp_core` module — the shared helper layer used by every other BSP driver. Functions under test:

| UT-ID  | Function                     | DDD ref    |
|--------|------------------------------|------------|
| UT-C01 | `bsp_poll_reg32`             | DDD-M00-07 |
| UT-C02 | `bsp_clk_get_enable`         | DDD-M00-03 |
| UT-C03 | `bsp_regulator_get_enable`   | DDD-M00-04 |
| UT-C04 | `bsp_of_require_compatible`  | DDD-M00-05 |

### 1.2 Tools
- **Unity** 2.6.x — assertions (`TEST_ASSERT_EQUAL_INT`, `TEST_ASSERT_NULL`, …).
- **CMock** 2.5.x — auto-generates mocks for the kernel APIs (`clk_get`, `clk_prepare_enable`, `regulator_get`, `regulator_enable`, `devm_add_action_or_reset`, `of_device_is_compatible`, `readl`, `udelay`, `dev_err`, …).
- **Ceedling** 0.31.x — build orchestration.
- **GCC/Gcov 13.x** — coverage instrumentation, host-native (x86-64 Linux).
- **gcovr 6.0** — HTML/XML reports.

### 1.3 Coverage Targets
| Metric              | Target | Applies to                          |
|---------------------|--------|--------------------------------------|
| Statement coverage  | ≥ 80 % | All module code                     |
| Branch coverage     | 100 %  | `bsp_poll_reg32` (safety-critical)  |
| Branch coverage     | ≥ 90 % | Remaining helpers                   |
| MC/DC               | 100 %  | Compound conditions in `bsp_poll_reg32` |
| Function coverage   | 100 %  | All public API                      |

### 1.4 Test Environment
- **Build:** host-native x86-64, `-O0 -g --coverage`, no target hardware required.
- **Harness:** Ceedling runs one test binary per source module; each test executes in its own process, so globals are reset between tests.
- **Kernel abstraction:** the Linux kernel API surface is replaced by CMock-generated mocks in `test/support/kernel_stubs/`. The stubs expose the same prototypes used in the driver but live in separate headers (`mock_clk.h`, `mock_regulator.h`, `mock_of.h`, `mock_io.h`, `mock_device.h`, `mock_delay.h`) so CMock can generate the expectations.

---

## 2. UNIT TEST FILES

<!-- FILE: test/support/kernel_stubs/linux/clk.h -->
```c
/* Minimal host-side surrogate of <linux/clk.h> for CMock.
 * Only the symbols used by bsp_core.c are declared. */
#ifndef STUB_LINUX_CLK_H
#define STUB_LINUX_CLK_H
#include <stdint.h>
#include <stddef.h>
#include "linux/device.h"
struct clk;
struct clk *devm_clk_get(struct device *dev, const char *id);
int         clk_prepare_enable(struct clk *clk);
void        clk_disable_unprepare(struct clk *clk);
long        IS_ERR(const void *ptr);           /* returns non-zero if err-ptr */
long        PTR_ERR(const void *ptr);          /* returns -errno             */
#endif
```

<!-- FILE: test/support/kernel_stubs/linux/regulator/consumer.h -->
```c
#ifndef STUB_LINUX_REGULATOR_H
#define STUB_LINUX_REGULATOR_H
#include "linux/device.h"
struct regulator;
struct regulator *devm_regulator_get(struct device *dev, const char *id);
int  regulator_enable(struct regulator *r);
int  regulator_disable(struct regulator *r);
long IS_ERR(const void *ptr);
long PTR_ERR(const void *ptr);
#endif
```

<!-- FILE: test/support/kernel_stubs/linux/of.h -->
```c
#ifndef STUB_LINUX_OF_H
#define STUB_LINUX_OF_H
#include <stdbool.h>
struct device_node;
int of_device_is_compatible(const struct device_node *np, const char *compat);
#endif
```

<!-- FILE: test/support/kernel_stubs/linux/io.h -->
```c
#ifndef STUB_LINUX_IO_H
#define STUB_LINUX_IO_H
#include <stdint.h>
typedef uint32_t u32;
#define __iomem
u32  readl(const void __iomem *addr);
void writel(u32 v, void __iomem *addr);
#endif
```

<!-- FILE: test/support/kernel_stubs/linux/delay.h -->
```c
#ifndef STUB_LINUX_DELAY_H
#define STUB_LINUX_DELAY_H
void udelay(unsigned long us);
#endif
```

<!-- FILE: test/support/kernel_stubs/linux/device.h -->
```c
#ifndef STUB_LINUX_DEVICE_H
#define STUB_LINUX_DEVICE_H
struct device;
int devm_add_action_or_reset(struct device *dev, void (*fn)(void *), void *data);
/* dev_err / dev_info / dev_dbg intentionally NOT mocked — they are macro-expanded
 * to printf via the test_config.h below to keep the mock surface small. */
#endif
```

<!-- FILE: test/support/test_config.h -->
```c
/* Shared include that remaps kernel logging macros to printf for host builds.
 * Included via Ceedling's :defines: (-include). */
#ifndef TEST_CONFIG_H
#define TEST_CONFIG_H
#include <stdio.h>
#define dev_err(d, fmt, ...)  fprintf(stderr, "[err] " fmt "\n", ##__VA_ARGS__)
#define dev_info(d, fmt, ...) fprintf(stderr, "[inf] " fmt "\n", ##__VA_ARGS__)
#define dev_dbg(d, fmt, ...)  ((void)0)
#define ETIMEDOUT  110
#define EINVAL      22
#define ENODEV      19
#define ENOMEM      12
#define EIO          5
#endif
```

<!-- FILE: test/unit/test_bsp_core.c -->
```c
/**
 * @file   test_bsp_core.c
 * @brief  Unit tests for drivers/bsp-imx6q/bsp_core.c
 * @note   Exercises every public function and every error path declared in
 *         bsp_core.h.  Target: 100% function coverage, 100% branch coverage
 *         for bsp_poll_reg32 (safety-critical polling primitive).
 */

#include "unity.h"
#include "mock_clk.h"
#include "mock_consumer.h"          /* regulator */
#include "mock_of.h"
#include "mock_io.h"
#include "mock_delay.h"
#include "mock_device.h"
#include "bsp_core.h"

/* ---------------------------------------------------------------------------
 *  Test fixture
 * ------------------------------------------------------------------------- */

/* Opaque handles used as "addresses" by the mocks.  We never dereference
 * them; they only need to be distinct non-NULL values. */
static struct device        g_dev_stub;
static struct device       *DEV = &g_dev_stub;
static struct clk           g_clk_stub;
static struct clk          *CLK = &g_clk_stub;
static struct regulator     g_reg_stub;
static struct regulator    *REG = &g_reg_stub;
static struct device_node   g_np_stub;
static struct device_node  *NP  = &g_np_stub;

/* A fake MMIO region — the mocks use the pointer value as a key. */
static uint32_t g_fake_mmio;
static void __iomem *REG_IO = (void __iomem *)&g_fake_mmio;

void setUp(void)
{
	/* Each test starts with a clean mock expectation list. */
}

void tearDown(void)
{
	/* CMock asserts that every Expect has been consumed. */
}

/* ===========================================================================
 *  UT-C01  bsp_poll_reg32
 *  ------------------------------------------------------------------
 *  Oracle (DDD-M00-07):
 *      if (reg == NULL || timeout_us == 0)     return -EINVAL;
 *      iter = 0;
 *      do {
 *          if ((readl(reg) & mask) == val)     return 0;
 *          udelay(BSP_POLL_INTERVAL_US);
 *          iter++;
 *      } while (iter < min(BSP_POLL_MAX_ITER,
 *                          timeout_us/BSP_POLL_INTERVAL_US));
 *      return -ETIMEDOUT;
 * ========================================================================= */

void test_bsp_poll_reg32_NullRegPointer_ReturnsEINVAL(void)
{
	int rc = bsp_poll_reg32(NULL, 0xFFu, 0xAAu, 100U);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_poll_reg32_ZeroTimeout_ReturnsEINVAL(void)
{
	int rc = bsp_poll_reg32(REG_IO, 0xFFu, 0xAAu, 0U);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_poll_reg32_ImmediateMatch_ReturnsZero(void)
{
	/* First read already yields the expected value -> no udelay. */
	readl_ExpectAndReturn(REG_IO, 0x000000AAu);
	int rc = bsp_poll_reg32(REG_IO, 0x000000FFu, 0x000000AAu, 100U);
	TEST_ASSERT_EQUAL_INT(0, rc);
}

void test_bsp_poll_reg32_MatchAfterSeveralPolls_ReturnsZero(void)
{
	/* Three misses, then hit.  udelay called once per miss. */
	readl_ExpectAndReturn(REG_IO, 0x00000000u);
	udelay_Expect(BSP_POLL_INTERVAL_US);
	readl_ExpectAndReturn(REG_IO, 0x000000A0u);  /* mask 0xFF still != 0xAA */
	udelay_Expect(BSP_POLL_INTERVAL_US);
	readl_ExpectAndReturn(REG_IO, 0x000000A9u);
	udelay_Expect(BSP_POLL_INTERVAL_US);
	readl_ExpectAndReturn(REG_IO, 0xDEADBEAAu);  /* masked -> 0xAA */

	int rc = bsp_poll_reg32(REG_IO, 0x000000FFu, 0x000000AAu, 1000U);
	TEST_ASSERT_EQUAL_INT(0, rc);
}

void test_bsp_poll_reg32_TimeoutElapses_ReturnsETIMEDOUT(void)
{
	/* timeout_us = 30, interval = 10 -> 3 iterations, all miss. */
	for (int i = 0; i < 3; i++) {
		readl_ExpectAndReturn(REG_IO, 0x00000000u);
		udelay_Expect(BSP_POLL_INTERVAL_US);
	}
	int rc = bsp_poll_reg32(REG_IO, 0xFFu, 0xAAu, 30U);
	TEST_ASSERT_EQUAL_INT(-ETIMEDOUT, rc);
}

void test_bsp_poll_reg32_MaxIterCap_ReturnsETIMEDOUT(void)
{
	/* Huge timeout forces the BSP_POLL_MAX_ITER safety cap to kick in. */
	for (unsigned i = 0; i < BSP_POLL_MAX_ITER; i++) {
		readl_ExpectAndReturn(REG_IO, 0x00000000u);
		udelay_Expect(BSP_POLL_INTERVAL_US);
	}
	int rc = bsp_poll_reg32(REG_IO, 0xFFu, 0xAAu, 0xFFFFFFFFu);
	TEST_ASSERT_EQUAL_INT(-ETIMEDOUT, rc);
}

void test_bsp_poll_reg32_MaskZero_MatchesWhenValZero(void)
{
	/* Boundary: mask=0 -> (x & 0) == 0 always, so val must be 0 to hit. */
	readl_ExpectAndReturn(REG_IO, 0xFFFFFFFFu);
	int rc = bsp_poll_reg32(REG_IO, 0x0u, 0x0u, 100U);
	TEST_ASSERT_EQUAL_INT(0, rc);
}

void test_bsp_poll_reg32_MaskZero_NeverMatchesWhenValNonZero(void)
{
	/* With mask=0, (x & 0)==0, so val=1 is unreachable -> times out. */
	for (int i = 0; i < 1; i++) {       /* timeout=10us -> 1 iter */
		readl_ExpectAndReturn(REG_IO, 0xFFFFFFFFu);
		udelay_Expect(BSP_POLL_INTERVAL_US);
	}
	int rc = bsp_poll_reg32(REG_IO, 0x0u, 0x1u, 10U);
	TEST_ASSERT_EQUAL_INT(-ETIMEDOUT, rc);
}

/* ===========================================================================
 *  UT-C02  bsp_clk_get_enable
 *  Oracle (DDD-M00-03):
 *      if (!dev || !name || !out)          return -EINVAL;
 *      clk = devm_clk_get(dev, name);
 *      if (IS_ERR(clk))                    return PTR_ERR(clk);
 *      rc = clk_prepare_enable(clk);
 *      if (rc)                             return rc;
 *      devm_add_action_or_reset(dev, clk_disable_unprepare, clk);
 *      *out = clk;                         return 0;
 * ========================================================================= */

void test_bsp_clk_get_enable_NullDev_ReturnsEINVAL(void)
{
	struct clk *out = NULL;
	int rc = bsp_clk_get_enable(NULL, "main", &out);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
	TEST_ASSERT_NULL(out);
}

void test_bsp_clk_get_enable_NullName_ReturnsEINVAL(void)
{
	struct clk *out = NULL;
	int rc = bsp_clk_get_enable(DEV, NULL, &out);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_clk_get_enable_NullOut_ReturnsEINVAL(void)
{
	int rc = bsp_clk_get_enable(DEV, "main", NULL);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_clk_get_enable_DevmClkGetFails_ReturnsPtrErr(void)
{
	struct clk *out = (struct clk *)0xdeadbeef;
	struct clk *errp = (struct clk *)(long)-ENODEV;

	devm_clk_get_ExpectAndReturn(DEV, "main", errp);
	IS_ERR_ExpectAndReturn(errp, 1);
	PTR_ERR_ExpectAndReturn(errp, -ENODEV);

	int rc = bsp_clk_get_enable(DEV, "main", &out);
	TEST_ASSERT_EQUAL_INT(-ENODEV, rc);
	TEST_ASSERT_NULL(out);                          /* must not be written */
}

void test_bsp_clk_get_enable_PrepareEnableFails_ReturnsErrno(void)
{
	struct clk *out = NULL;

	devm_clk_get_ExpectAndReturn(DEV, "osc", CLK);
	IS_ERR_ExpectAndReturn(CLK, 0);
	clk_prepare_enable_ExpectAndReturn(CLK, -EIO);

	int rc = bsp_clk_get_enable(DEV, "osc", &out);
	TEST_ASSERT_EQUAL_INT(-EIO, rc);
	TEST_ASSERT_NULL(out);
}

void test_bsp_clk_get_enable_HappyPath_ReturnsZeroAndSetsHandle(void)
{
	struct clk *out = NULL;

	devm_clk_get_ExpectAndReturn(DEV, "ipg", CLK);
	IS_ERR_ExpectAndReturn(CLK, 0);
	clk_prepare_enable_ExpectAndReturn(CLK, 0);
	devm_add_action_or_reset_ExpectAnyArgsAndReturn(0);

	int rc = bsp_clk_get_enable(DEV, "ipg", &out);
	TEST_ASSERT_EQUAL_INT(0, rc);
	TEST_ASSERT_EQUAL_PTR(CLK, out);
}

void test_bsp_clk_get_enable_DevmActionAddFails_PropagatesError(void)
{
	/* When devm_add_action_or_reset fails, it already invoked the cleanup
	 * (clk_disable_unprepare) itself, so the driver must propagate -ENOMEM
	 * and NOT write *out. */
	struct clk *out = NULL;

	devm_clk_get_ExpectAndReturn(DEV, "ipg", CLK);
	IS_ERR_ExpectAndReturn(CLK, 0);
	clk_prepare_enable_ExpectAndReturn(CLK, 0);
	devm_add_action_or_reset_ExpectAnyArgsAndReturn(-ENOMEM);

	int rc = bsp_clk_get_enable(DEV, "ipg", &out);
	TEST_ASSERT_EQUAL_INT(-ENOMEM, rc);
	TEST_ASSERT_NULL(out);
}

/* ===========================================================================
 *  UT-C03  bsp_regulator_get_enable
 *  Same control flow as UT-C02 but with regulator APIs.
 * ========================================================================= */

void test_bsp_regulator_get_enable_NullDev_ReturnsEINVAL(void)
{
	struct regulator *out = NULL;
	int rc = bsp_regulator_get_enable(NULL, "vdd", &out);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_regulator_get_enable_NullName_ReturnsEINVAL(void)
{
	struct regulator *out = NULL;
	int rc = bsp_regulator_get_enable(DEV, NULL, &out);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_regulator_get_enable_NullOut_ReturnsEINVAL(void)
{
	int rc = bsp_regulator_get_enable(DEV, "vdd", NULL);
	TEST_ASSERT_EQUAL_INT(-EINVAL, rc);
}

void test_bsp_regulator_get_enable_GetFails_ReturnsPtrErr(void)
{
	struct regulator *out = NULL;
	struct regulator *errp = (struct regulator *)(long)-EPROBE_DEFER;

	devm_regulator_get_ExpectAndReturn(DEV, "vdd", errp);
	IS_ERR_ExpectAndReturn(errp, 1);
	PTR_ERR_ExpectAndReturn(errp, -EPROBE_DEFER);

	int rc = bsp_regulator_get_enable(DEV, "vdd", &out);
	TEST_ASSERT_EQUAL_INT(-EPROBE_DEFER, rc);
}

void test_bsp_regulator_get_enable_EnableFails_ReturnsErrno(void)
{
	struct regulator *out = NULL;

	devm_regulator_get_ExpectAndReturn(DEV, "vdd", REG);
	IS_ERR_ExpectAndReturn(REG, 0);
	regulator_enable_ExpectAndReturn(REG, -EIO);

	int rc = bsp_regulator_get_enable(DEV, "vdd", &out);
	TEST_ASSERT_EQUAL_INT(-EIO, rc);
	TEST_ASSERT_NULL(out);
}

void test_bsp_regulator_get_enable_HappyPath_ReturnsZero(void)
{
	struct regulator *out = NULL;

	devm_regulator_get_ExpectAndReturn(DEV, "vdd-3v3", REG);
	IS_ERR_ExpectAndReturn(REG, 0);
	regulator_enable_ExpectAndReturn(REG, 0);
	devm_add_action_or_reset_ExpectAnyArgsAndReturn(0);

	int rc = bsp_regulator_get_enable(DEV, "vdd-3v3", &out);
	TEST_ASSERT_EQUAL_INT(0, rc);
	TEST_ASSERT_EQUAL_PTR(REG, out);
}

void test_bsp_regulator_get_enable_DevmActionFails_PropagatesError(void)
{
	struct regulator *out = NULL;

	devm_regulator_get_ExpectAndReturn(DEV, "vdd-3v3", REG);
	IS_ERR_ExpectAndReturn(REG, 0);
	regulator_enable_ExpectAndReturn(REG, 0);
	devm_add_action_or_reset_ExpectAnyArgsAndReturn(-ENOMEM);

	int rc = bsp_regulator_get_enable(DEV, "vdd-3v3", &out);
	TEST_ASSERT_EQUAL_INT(-ENOMEM, rc);
	TEST_ASSERT_NULL(out);
}

/* ===========================================================================
 *  UT-C04  bsp_of_require_compatible
 *  Oracle (DDD-M00-05):
 *      if (np == NULL || compat == NULL)    return -ENODEV;
 *      return of_device_is_compatible(np, compat) ? 0 : -ENODEV;
 * ========================================================================= */

void test_bsp_of_require_compatible_NullNode_ReturnsENODEV(void)
{
	int rc = bsp_of_require_compatible(NULL, "fsl,imx6q-sabresd");
	TEST_ASSERT_EQUAL_INT(-ENODEV, rc);
}

void test_bsp_of_require_compatible_NullCompat_ReturnsENODEV(void)
{
	int rc = bsp_of_require_compatible(NP, NULL);
	TEST_ASSERT_EQUAL_INT(-ENODEV, rc);
}

void test_bsp_of_require_compatible_Mismatch_ReturnsENODEV(void)
{
	of_device_is_compatible_ExpectAndReturn(NP, "fsl,foo", 0);
	int rc = bsp_of_require_compatible(NP, "fsl,foo");
	TEST_ASSERT_EQUAL_INT(-ENODEV, rc);
}

void test_bsp_of_require_compatible_Match_ReturnsZero(void)
{
	of_device_is_compatible_ExpectAndReturn(NP, BSP_IMX6Q_COMPAT_ROOT, 1);
	int rc = bsp_of_require_compatible(NP, BSP_IMX6Q_COMPAT_ROOT);
	TEST_ASSERT_EQUAL_INT(0, rc);
}
```

---

## 3. CEEDLING PROJECT CONFIGURATION

<!-- FILE: test/project.yml -->
```yaml
# =============================================================================
#  Ceedling configuration for bsp-imx6q unit-test suite
#  Host-native build: x86-64 Linux, gcc-13, gcov-13
# =============================================================================
:project:
  :use_exceptions:      FALSE
  :use_test_preprocessor: TRUE
  :use_auxiliary_dependencies: TRUE
  :build_root:          build/
  :release_build:       FALSE
  :test_file_prefix:    test_
  :which_ceedling:      gem
  :default_tasks:
    - test:all
    - gcov:all

:environment: []

:extension:
  :executable:          .out

:paths:
  :test:
    - +:test/unit/**
    - -:test/unit/support
  :source:
    - drivers/bsp-imx6q/**
  :include:
    - drivers/bsp-imx6q/include
    - test/support
    - test/support/kernel_stubs          # stub kernel headers
  :support:
    - test/support

:defines:
  :common: &common_defines
    - UNITY_SUPPORT_64
    - UNITY_INCLUDE_DOUBLE
    - EPROBE_DEFER=517
  :test:
    - *common_defines
    - TEST
    - __KERNEL__=0
  :test_preprocess:
    - *common_defines
  :gcov:
    - *common_defines
    - TEST

:flags:
  :test:
    :compile:
      :*:
        - -Wall
        - -Wextra
        - -Werror
        - -std=gnu11
        - -g
        - -include test/support/test_config.h
  :gcov:
    :compile:
      :*:
        - -Wall
        - -Wextra
        - -std=gnu11
        - -g
        - -O0
        - --coverage
        - -include test/support/test_config.h
    :link:
      :*:
        - --coverage

:cmock:
  :mock_prefix:         mock_
  :plugins:
    - :ignore
    - :ignore_arg
    - :expect_any_args
    - :callback
    - :return_thru_ptr
  :includes:
    - linux/clk.h
    - linux/regulator/consumer.h
    - linux/of.h
    - linux/io.h
    - linux/delay.h
    - linux/device.h
  :treat_as:
    u32:   HEX32
    size_t: INT
  :treat_as_void:
    - __iomem
  :enforce_strict_ordering: TRUE
  :verbosity: 2

:gcov:
  :reports:
    - HtmlDetailed
    - Cobertura
  :gcovr:
    :html_medium_threshold: 80
    :html_high_threshold:   95
    :fail_under_line:       80
    :fail_under_branch:     90

:tools_gcov_report:
  :executable: gcovr
  :arguments:
    - --root .
    - --exclude test/
    - --exclude build/
    - --html-details build/artifacts/gcov/coverage.html
    - --xml         build/artifacts/gcov/coverage.xml
    - --print-summary

:plugins:
  :load_paths:
    - "#{Ceedling.load_path}"
  :enabled:
    - stdout_pretty_tests_report
    - module_generator
    - gcov
```

---

## 4. MOCK SPECIFICATIONS

CMock auto-generates one mock file per stub header under `test/support/kernel_stubs/`.

| Generated Mock             | Source Stub Header                      | Symbols Mocked                                                                 | CMock Directives Needed                         |
|----------------------------|-----------------------------------------|--------------------------------------------------------------------------------|--------------------------------------------------|
| `mock_clk.c/h`             | `linux/clk.h`                           | `devm_clk_get`, `clk_prepare_enable`, `clk_disable_unprepare`, `IS_ERR`, `PTR_ERR` | `:plugins: [:ignore_arg, :return_thru_ptr]`      |
| `mock_consumer.c/h`        | `linux/regulator/consumer.h`            | `devm_regulator_get`, `regulator_enable`, `regulator_disable`, `IS_ERR`, `PTR_ERR` | same as above                                    |
| `mock_of.c/h`              | `linux/of.h`                            | `of_device_is_compatible`                                                      | none                                             |
| `mock_io.c/h`              | `linux/io.h`                            | `readl`, `writel`                                                              | `:treat_as_void: [__iomem]`                      |
| `mock_delay.c/h`           | `linux/delay.h`                         | `udelay`                                                                       | none                                             |
| `mock_device.c/h`          | `linux/device.h`                        | `devm_add_action_or_reset`                                                     | `:plugins: [:expect_any_args]`                   |

**Note on `IS_ERR` / `PTR_ERR`:** In the real kernel these are `inline` functions that perform pointer arithmetic. For host-native testing they are **stubbed as ordinary externs** in `linux/clk.h`, so CMock can mock them. This is why each happy-path test queues a paired `IS_ERR_ExpectAndReturn(…, 0)` immediately after the getter.

**Ordering:** `:enforce_strict_ordering: TRUE` — CMock will fail the test if the driver calls mocks in a different sequence than the Expect calls declare. This pins the driver's contract.

---

## 5. COVERAGE REPORT TEMPLATE

Populated by gcovr after `ceedling gcov:all utils:gcov`.

| Module      | Functions (cov/total) | Statements (%) | Branches (%) | MC/DC (%) | Status |
|-------------|-----------------------|----------------|--------------|-----------|--------|
| `bsp_core`  | 4 / 4                 | ≥ 95           | 100          | 100       | ☐ PASS / ☐ FAIL |
| **Overall** | 4 / 4                 | ≥ 95           | ≥ 95         | 100       | ☐ PASS / ☐ FAIL |

Gate (CI): the build fails if `statement < 80 %` or `branch < 90 %` on any file under `drivers/bsp-imx6q/`.

---

## 6. TRACEABILITY MATRIX

| Test ID | Test Function                                                | DDD Function                   | SwFR-ID   | Type       | Pass Criteria                                   |
|---------|--------------------------------------------------------------|--------------------------------|-----------|------------|-------------------------------------------------|
| UT-C01-01 | `test_bsp_poll_reg32_NullRegPointer_ReturnsEINVAL`         | `bsp_poll_reg32` / DDD-M00-07  | SwFR-003  | Null-ptr   | rc == `-EINVAL`, no MMIO access                 |
| UT-C01-02 | `test_bsp_poll_reg32_ZeroTimeout_ReturnsEINVAL`            | `bsp_poll_reg32` / DDD-M00-07  | SwFR-003  | Boundary   | rc == `-EINVAL`                                 |
| UT-C01-03 | `test_bsp_poll_reg32_ImmediateMatch_ReturnsZero`           | `bsp_poll_reg32` / DDD-M00-07  | SwFR-001  | Happy path | rc == 0, exactly 1 `readl`, 0 `udelay`          |
| UT-C01-04 | `test_bsp_poll_reg32_MatchAfterSeveralPolls_ReturnsZero`   | `bsp_poll_reg32` / DDD-M00-07  | SwFR-001  | Normal     | rc == 0 after N polls                            |
| UT-C01-05 | `test_bsp_poll_reg32_TimeoutElapses_ReturnsETIMEDOUT`      | `bsp_poll_reg32` / DDD-M00-07  | SwFR-002  | Error path | rc == `-ETIMEDOUT`, exactly `timeout/interval` polls |
| UT-C01-06 | `test_bsp_poll_reg32_MaxIterCap_ReturnsETIMEDOUT`          | `bsp_poll_reg32` / DDD-M00-07  | SwFR-002  | Bound cap  | ≤ `BSP_POLL_MAX_ITER` `readl` calls              |
| UT-C01-07 | `test_bsp_poll_reg32_MaskZero_MatchesWhenValZero`          | `bsp_poll_reg32` / DDD-M00-07  | SwFR-001  | Boundary   | rc == 0                                         |
| UT-C01-08 | `test_bsp_poll_reg32_MaskZero_NeverMatchesWhenValNonZero`  | `bsp_poll_reg32` / DDD-M00-07  | SwFR-002  | Boundary   | rc == `-ETIMEDOUT`                              |
| UT-C02-01 | `test_bsp_clk_get_enable_NullDev_ReturnsEINVAL`            | `bsp_clk_get_enable`/DDD-M00-03| SwFR-003  | Null-ptr   | rc == `-EINVAL`, `*out` untouched                |
| UT-C02-02 | `test_bsp_clk_get_enable_NullName_ReturnsEINVAL`           | `bsp_clk_get_enable`/DDD-M00-03| SwFR-003  | Null-ptr   | rc == `-EINVAL`                                 |
| UT-C02-03 | `test_bsp_clk_get_enable_NullOut_ReturnsEINVAL`            | `bsp_clk_get_enable`/DDD-M00-03| SwFR-003  | Null-ptr   | rc == `-EINVAL`                                 |
| UT-C02-04 | `test_bsp_clk_get_enable_DevmClkGetFails_ReturnsPtrErr`    | `bsp_clk_get_enable`/DDD-M00-03| SwFR-004  | Error path | rc == `-ENODEV`                                 |
| UT-C02-05 | `test_bsp_clk_get_enable_PrepareEnableFails_ReturnsErrno`  | `bsp_clk_get_enable`/DDD-M00-03| SwFR-004  | Error path | rc == `-EIO`, no devm action registered          |
| UT-C02-06 | `test_bsp_clk_get_enable_HappyPath_ReturnsZeroAndSetsHandle`| `bsp_clk_get_enable`/DDD-M00-03| SwFR-001  | Happy path | rc == 0, `*out == CLK`, devm action registered   |
| UT-C02-07 | `test_bsp_clk_get_enable_DevmActionAddFails_PropagatesError`| `bsp_clk_get_enable`/DDD-M00-03| SwFR-004  | Error path | rc == `-ENOMEM`, `*out` unchanged                |
| UT-C03-01 | `test_bsp_regulator_get_enable_NullDev_ReturnsEINVAL`      | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-003 | Null-ptr | rc == `-EINVAL`                                 |
| UT-C03-02 | `test_bsp_regulator_get_enable_NullName_ReturnsEINVAL`     | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-003 | Null-ptr | rc == `-EINVAL`                                 |
| UT-C03-03 | `test_bsp_regulator_get_enable_NullOut_ReturnsEINVAL`      | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-003 | Null-ptr | rc == `-EINVAL`                                 |
| UT-C03-04 | `test_bsp_regulator_get_enable_GetFails_ReturnsPtrErr`     | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-005 | Error path | rc == `-EPROBE_DEFER`                           |
| UT-C03-05 | `test_bsp_regulator_get_enable_EnableFails_ReturnsErrno`   | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-005 | Error path | rc == `-EIO`                                    |
| UT-C03-06 | `test_bsp_regulator_get_enable_HappyPath_ReturnsZero`      | `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-001 | Happy path | rc == 0, `*out == REG`                          |
| UT-C03-07 | `test_bsp_regulator_get_enable_DevmActionFails_PropagatesError`| `bsp_regulator_get_enable`/DDD-M00-04 | SwFR-005 | Error path | rc == `-ENOMEM`                             |
| UT-C04-01 | `test_bsp_of_require_compatible_NullNode_ReturnsENODEV`    | `bsp_of_require_compatible`/DDD-M00-05| SwFR-003 | Null-ptr | rc == `-ENODEV`                                 |
| UT-C04-02 | `test_bsp_of_require_compatible_NullCompat_ReturnsENODEV`  | `bsp_of_require_compatible`/DDD-M00-05| SwFR-003 | Null-ptr | rc == `-ENODEV`                                 |
| UT-C04-03 | `test_bsp_of_require_compatible_Mismatch_ReturnsENODEV`    | `bsp_of_require_compatible`/DDD-M00-05| SwFR-002 | Error path | rc == `-ENODEV`                                 |
| UT-C04-04 | `test_bsp_of_require_compatible_Match_ReturnsZero`         | `bsp_of_require_compatible`/DDD-M00-05| SwFR-001 | Happy path | rc == 0                                         |

**Execution:**
```sh
cd test
ceedling clobber
ceedling test:all           # Unity run -> pretty report
ceedling gcov:all utils:gcov  # coverage -> build/artifacts/gcov/coverage.html
```

All 26 test cases must pass; any fail fails the CI gate. Coverage below the thresholds declared in `project.yml` also fails the gate, preserving traceability from every SwFR-xxx back to a passing executable assertion.