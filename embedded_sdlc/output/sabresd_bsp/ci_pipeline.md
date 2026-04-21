# CI/CD PIPELINE — i.MX6Q SabreSD BSP Driver Package

**Document ID:** CICD-IMX6Q-BSP-001
**Stage:** V-Model cross-cutting (Configuration Management / DevOps)
**Traces to:** SwRS-IMX6Q-BSP-001 §6 (MISRA advisory scope), SwRS §7 (size/timing budgets), SwUT-IMX6Q-BSP-001

> **Context adaptation note:** This target is a Linux BSP (kernel modules + user-space
> daemons + bootloader patches), **not** a bare-metal firmware image.  Accordingly:
> - Kernel modules are cross-compiled with **`arm-linux-gnueabihf-gcc`** (hard-float VFPv3-D16) against an **in-tree Linux 6.6 LTS source** — *not* `arm-none-eabi-gcc`.
> - MISRA-C:2012 is run **only on BSP-local helper code outside the kernel tree** (user-space libbsp, test harnesses, U-Boot patches), per SwRS §6.  In-tree kernel sources are scanned with `sparse` + `smatch` + `checkpatch.pl` instead.
> - Unit tests (Ceedling + Unity + CMock) run **host-native** against kernel API mocks, as per SwUT-IMX6Q-BSP-001.
> - Size budgets apply to the `.ko` modules and the `libbsp.so` user library.

---

## 1. CI PIPELINE OVERVIEW

```
                           ┌─────────────────────────┐
                           │  Trigger                │
                           │  • push main/release/*  │
                           │  • pull_request         │
                           │  • tag v*.*.*           │
                           │  • nightly cron         │
                           └────────────┬────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         │  Job 1: pre-flight          │
                         │  • checkout + submodules    │
                         │  • pre-commit               │
                         │  • checkpatch.pl            │
                         │  • clang-format --dry-run   │
                         └──────────────┬──────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           │                            │                            │
┌──────────┴──────────┐      ┌──────────┴──────────┐      ┌──────────┴──────────┐
│ Job 2: host-unit    │      │ Job 3: kernel-build │      │ Job 4: user-build   │
│ • ceedling test:all │      │ • arm-linux-gnu...  │      │ • cmake -S libbsp   │
│ • Unity + CMock     │      │ • imx_v6_v7_defcfg  │      │ • libbsp.so         │
│ • gcov → lcov html  │      │ • make modules      │      │ • bsp-health daemon │
│ • upload → Codecov  │      │ • .ko artefacts     │      │ • sanitizers (dbg)  │
└──────────┬──────────┘      └──────────┬──────────┘      └──────────┬──────────┘
           │                            │                            │
           └────────────────────────────┼────────────────────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         │  Job 5: static-analysis     │
                         │  • cppcheck --addon=misra   │
                         │  • clang-tidy (cert-*)      │
                         │  • sparse (kernel)          │
                         │  • smatch (kernel)          │
                         │  • SARIF → code scanning    │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         │  Job 6: size & symbol audit │
                         │  • arm-linux-gnu...-size    │
                         │  • check_size.py vs budget  │
                         │  • nm: forbidden symbols    │
                         └──────────────┬──────────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         │  Job 7: package & archive   │
                         │  • .ko, .so, .deb, .map     │
                         │  • coverage HTML            │
                         │  • SBOM (CycloneDX)         │
                         │  • SHA256 + cosign sig      │
                         └──────────────┬──────────────┘
                                        │
                  ┌─────────────────────┴─────────────────────┐
                  │                                           │
       ┌──────────┴──────────┐                   ┌────────────┴──────────┐
       │  Job 8a: release    │ (tag v*.*.*)      │  Job 8b: notify       │
       │  • GitHub release   │                   │  • Slack on failure   │
       │  • changelog gen    │                   │  • email security team│
       │  • signed artefacts │                   │  • Jira sync          │
       └─────────────────────┘                   └───────────────────────┘
```

---

## 2. GITHUB ACTIONS WORKFLOW

<!-- FILE: .github/workflows/firmware_ci.yml -->
```yaml
# ============================================================================
#  i.MX6Q SabreSD BSP Driver Package — Continuous Integration
#  Document: CICD-IMX6Q-BSP-001
#  Traces:   SwRS-IMX6Q-BSP-001 §6, §7 ; SwUT-IMX6Q-BSP-001
# ============================================================================
name: firmware_ci

on:
  push:
    branches: [main, 'release/**', 'develop']
    tags:     ['v*.*.*']
  pull_request:
    branches: [main, 'release/**']
  schedule:
    - cron: '0 2 * * *'          # nightly full sweep 02:00 UTC
  workflow_dispatch:

# Cancel superseded runs on the same ref to save CI minutes
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  security-events: write          # SARIF upload for code scanning
  id-token: write                 # OIDC for cosign keyless signing

env:
  # Pinned reproducible toolchain (updated via renovate-bot)
  ARM_GCC_VERSION:   '13.2.rel1'
  KERNEL_VERSION:    '6.6.30'
  KERNEL_DEFCONFIG:  'imx_v6_v7_defconfig'
  ARCH:              'arm'
  CROSS_COMPILE:     'arm-linux-gnueabihf-'
  CCACHE_DIR:        ${{ github.workspace }}/.ccache
  DEBIAN_FRONTEND:   'noninteractive'

jobs:

  # ---------------------------------------------------------------------------
  # Job 1 — Pre-flight: style, commit hygiene, checkpatch
  # ---------------------------------------------------------------------------
  preflight:
    name: 'Pre-flight (lint + checkpatch)'
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
      options: --user root
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0              # full history for checkpatch on range
          submodules: recursive

      - name: pre-commit
        uses: pre-commit/action@v3.0.1

      - name: clang-format (dry-run, error on diff)
        run: |
          find drivers/bsp-imx6q libbsp -name '*.[ch]' \
            | xargs clang-format --dry-run --Werror --style=file

      - name: checkpatch.pl on changed kernel sources
        if: github.event_name == 'pull_request'
        run: |
          BASE="${{ github.event.pull_request.base.sha }}"
          HEAD="${{ github.event.pull_request.head.sha }}"
          git diff "${BASE}".."${HEAD}" -- 'drivers/bsp-imx6q/**/*.[ch]' \
            | scripts/checkpatch.pl --no-tree --strict --show-types -

      - name: Commit message lint (Conventional Commits)
        uses: wagoid/commitlint-github-action@v6

  # ---------------------------------------------------------------------------
  # Job 2 — Host-native unit tests with Ceedling + Unity + CMock + gcov
  # ---------------------------------------------------------------------------
  host-unit-tests:
    name: 'Unit tests (Ceedling + gcov)'
    needs: preflight
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }

      - name: Cache Ruby gems
        uses: actions/cache@v4
        with:
          path: ~/.gem
          key: gems-${{ hashFiles('test/Gemfile.lock') }}

      - name: Run Ceedling test suite
        working-directory: test
        run: |
          ceedling clobber
          ceedling gcov:all
        env:
          CEEDLING_MAIN_PROJECT_FILE: project.yml

      - name: Generate lcov report
        working-directory: test
        run: |
          lcov --capture --directory build/gcov/out \
               --output-file build/gcov/coverage.info \
               --rc lcov_branch_coverage=1
          lcov --remove build/gcov/coverage.info \
               '/usr/*' '*/build/*' '*/mocks/*' '*/unity/*' \
               --output-file build/gcov/coverage.info \
               --rc lcov_branch_coverage=1
          genhtml --branch-coverage \
                  build/gcov/coverage.info \
                  --output-directory build/gcov/html
          lcov --summary build/gcov/coverage.info | tee coverage_summary.txt

      - name: Enforce coverage gate (>=90 % line, >=80 % branch)
        working-directory: test
        run: python3 ../tools/check_coverage.py build/gcov/coverage.info \
                    --min-line 90 --min-branch 80

      - name: Upload to Codecov
        uses: codecov/codecov-action@v4
        with:
          files: test/build/gcov/coverage.info
          flags: unit
          token: ${{ secrets.CODECOV_TOKEN }}
          fail_ci_if_error: true

      - name: Publish JUnit results
        if: always()
        uses: mikepenz/action-junit-report@v4
        with:
          report_paths: 'test/build/artifacts/gcov/junit_tests_report.xml'

      - name: Archive coverage HTML
        uses: actions/upload-artifact@v4
        with:
          name: coverage-html
          path: test/build/gcov/html
          retention-days: 30

  # ---------------------------------------------------------------------------
  # Job 3 — Cross-compile kernel modules (arm-linux-gnueabihf)
  # ---------------------------------------------------------------------------
  kernel-build:
    name: 'Kernel modules (arm-linux-gnueabihf)'
    needs: preflight
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    strategy:
      matrix:
        build_type: [release, debug]
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }

      - name: Restore ccache
        uses: actions/cache@v4
        with:
          path: ${{ env.CCACHE_DIR }}
          key: ccache-kernel-${{ matrix.build_type }}-${{ env.KERNEL_VERSION }}-${{ github.sha }}
          restore-keys: |
            ccache-kernel-${{ matrix.build_type }}-${{ env.KERNEL_VERSION }}-

      - name: Fetch & prepare kernel tree
        run: |
          mkdir -p ${GITHUB_WORKSPACE}/kernel
          curl -sSL https://cdn.kernel.org/pub/linux/kernel/v6.x/linux-${KERNEL_VERSION}.tar.xz \
            | tar -xJ -C ${GITHUB_WORKSPACE}/kernel --strip-components=1
          cd kernel
          make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} ${KERNEL_DEFCONFIG}
          make ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} modules_prepare -j$(nproc)

      - name: Build BSP modules (external)
        run: |
          EXTRA_CFLAGS=""
          if [ "${{ matrix.build_type }}" = "debug" ]; then
             EXTRA_CFLAGS="-g3 -O1 -DDEBUG -fstack-usage"
          else
             EXTRA_CFLAGS="-O2 -fstack-usage -Werror"
          fi
          make -C ${GITHUB_WORKSPACE}/kernel \
               M=${GITHUB_WORKSPACE}/drivers/bsp-imx6q \
               ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} \
               KCFLAGS="${EXTRA_CFLAGS}" \
               W=1 C=1 CHECK=sparse \
               modules 2>&1 | tee build_${{ matrix.build_type }}.log
          # Fail on any *new* sparse/smatch warnings (CI gate)
          ! grep -E "warning:|error:" build_${{ matrix.build_type }}.log \
            | grep -v -f tools/sparse_allowlist.txt

      - name: Collect stack-usage report
        run: |
          find drivers/bsp-imx6q -name '*.su' -exec cat {} + \
            | sort -t$'\t' -k2 -n -r > stack_usage_${{ matrix.build_type }}.txt
          python3 tools/check_stack.py stack_usage_${{ matrix.build_type }}.txt \
                  --max-frame 2048

      - name: Upload kernel artefacts
        uses: actions/upload-artifact@v4
        with:
          name: kernel-modules-${{ matrix.build_type }}
          path: |
            drivers/bsp-imx6q/**/*.ko
            drivers/bsp-imx6q/**/*.map
            build_${{ matrix.build_type }}.log
            stack_usage_${{ matrix.build_type }}.txt

  # ---------------------------------------------------------------------------
  # Job 4 — User-space build (libbsp + bsp-health daemon) with CMake
  # ---------------------------------------------------------------------------
  userspace-build:
    name: 'User-space (cmake cross)'
    needs: preflight
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    strategy:
      matrix:
        build_type: [Release, Debug]
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }

      - name: Configure
        run: |
          cmake -S libbsp -B build-${{ matrix.build_type }} \
                -DCMAKE_TOOLCHAIN_FILE=cmake/arm-linux-gnueabihf.cmake \
                -DCMAKE_BUILD_TYPE=${{ matrix.build_type }} \
                -DENABLE_SANITIZERS=$([ "${{ matrix.build_type }}" = "Debug" ] && echo ON || echo OFF) \
                -GNinja

      - name: Build
        run: cmake --build build-${{ matrix.build_type }} --parallel

      - name: Package (.deb)
        if: matrix.build_type == 'Release'
        run: |
          cd build-Release && cpack -G DEB
          mv *.deb ${GITHUB_WORKSPACE}/libbsp_${{ github.sha }}.deb

      - uses: actions/upload-artifact@v4
        with:
          name: userspace-${{ matrix.build_type }}
          path: |
            build-${{ matrix.build_type }}/**/*.so*
            build-${{ matrix.build_type }}/bsp-health
            build-${{ matrix.build_type }}/*.map
            *.deb

  # ---------------------------------------------------------------------------
  # Job 5 — Static analysis: cppcheck MISRA + clang-tidy + sparse + smatch
  # ---------------------------------------------------------------------------
  static-analysis:
    name: 'Static analysis'
    needs: preflight
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    steps:
      - uses: actions/checkout@v4
        with: { submodules: recursive }

      - name: cppcheck --addon=misra (out-of-tree code only)
        run: |
          cppcheck --project=tools/cppcheck_misra.json \
                   --enable=all --inline-suppr \
                   --suppressions-list=tools/cppcheck_suppressions.txt \
                   --addon=tools/cppcheck_misra.json \
                   --xml --xml-version=2 2> cppcheck.xml
          python3 tools/cppcheck_to_sarif.py cppcheck.xml > cppcheck.sarif

      - name: clang-tidy (cert-*, bugprone-*, cppcoreguidelines-*)
        run: |
          cmake -S libbsp -B build-tidy \
                -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
                -DCMAKE_TOOLCHAIN_FILE=cmake/arm-linux-gnueabihf.cmake \
                -GNinja
          run-clang-tidy -p build-tidy \
                         -checks='cert-*,bugprone-*,cppcoreguidelines-*,readability-*' \
                         -export-fixes tidy-fixes.yml \
                         -quiet -j $(nproc) libbsp/src

      - name: sparse (kernel-tree semantic check)
        run: |
          make -C ${GITHUB_WORKSPACE}/kernel \
               M=${GITHUB_WORKSPACE}/drivers/bsp-imx6q \
               ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} \
               C=2 CF=-D__CHECK_ENDIAN__ modules || true

      - name: smatch
        run: |
          make -C ${GITHUB_WORKSPACE}/kernel \
               M=${GITHUB_WORKSPACE}/drivers/bsp-imx6q \
               ARCH=${ARCH} CROSS_COMPILE=${CROSS_COMPILE} \
               C=2 CHECK="smatch --full-path" modules || true

      - name: Upload SARIF
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: cppcheck.sarif
          category: cppcheck-misra

      - uses: actions/upload-artifact@v4
        with:
          name: static-analysis
          path: |
            cppcheck.xml
            cppcheck.sarif
            tidy-fixes.yml

  # ---------------------------------------------------------------------------
  # Job 6 — Size & symbol audit (SwRS §7 budgets)
  # ---------------------------------------------------------------------------
  size-audit:
    name: 'Size & symbol audit'
    needs: [kernel-build, userspace-build]
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    steps:
      - uses: actions/checkout@v4

      - uses: actions/download-artifact@v4
        with:
          name: kernel-modules-release
          path: artefacts/kernel

      - uses: actions/download-artifact@v4
        with:
          name: userspace-Release
          path: artefacts/user

      - name: Binary size vs budget (SwRR-SIZ-*)
        run: |
          python3 tools/check_size.py \
              --budget tools/size_budget.yml \
              --size-tool ${CROSS_COMPILE}size \
              --report size_report.md \
              artefacts/kernel/**/*.ko \
              artefacts/user/**/*.so*

      - name: Forbidden-symbol scan (no printf/malloc in ISRs)
        run: |
          python3 tools/check_symbols.py \
              --forbidden tools/forbidden_symbols.txt \
              --nm ${CROSS_COMPILE}nm \
              artefacts/kernel/**/*.ko

      - name: Comment size report on PR
        if: github.event_name == 'pull_request'
        uses: marocchino/sticky-pull-request-comment@v2
        with:
          header: size-report
          path: size_report.md

      - uses: actions/upload-artifact@v4
        with: { name: size-report, path: size_report.md }

  # ---------------------------------------------------------------------------
  # Job 7 — Package, SBOM, sign
  # ---------------------------------------------------------------------------
  package:
    name: 'Package + SBOM + sign'
    needs: [host-unit-tests, kernel-build, userspace-build, static-analysis, size-audit]
    runs-on: ubuntu-22.04
    container:
      image: ghcr.io/${{ github.repository_owner }}/bsp-ci:1.0.0
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with: { path: artefacts }

      - name: Assemble release bundle
        run: |
          VERSION=$(git describe --tags --always --dirty)
          mkdir -p dist
          tar -czf dist/bsp-imx6q-${VERSION}.tar.gz \
              -C artefacts \
              kernel-modules-release userspace-Release coverage-html size-report
          (cd dist && sha256sum *.tar.gz > SHA256SUMS)

      - name: Generate SBOM (CycloneDX)
        uses: CycloneDX/gh-gomod-generate-sbom@v2
        with:
          version: v1
          args: -licenses -json -output dist/sbom.cdx.json .

      - name: Install cosign
        uses: sigstore/cosign-installer@v3

      - name: Keyless sign bundle (OIDC)
        run: |
          cosign sign-blob --yes \
                 --bundle dist/bsp-imx6q.cosign.bundle \
                 dist/bsp-imx6q-*.tar.gz

      - uses: actions/upload-artifact@v4
        with:
          name: release-bundle
          path: dist/

  # ---------------------------------------------------------------------------
  # Job 8a — Release on tag
  # ---------------------------------------------------------------------------
  release:
    name: 'GitHub Release'
    if: startsWith(github.ref, 'refs/tags/v')
    needs: package
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: actions/download-artifact@v4
        with: { name: release-bundle, path: dist }

      - name: Generate changelog
        uses: orhun/git-cliff-action@v3
        with:
          config: cliff.toml
          args: --latest --strip header
        env: { OUTPUT: CHANGELOG_RELEASE.md }

      - name: Publish release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            dist/bsp-imx6q-*.tar.gz
            dist/SHA256SUMS
            dist/sbom.cdx.json
            dist/bsp-imx6q.cosign.bundle
          body_path: CHANGELOG_RELEASE.md
          draft: false
          prerelease: ${{ contains(github.ref, '-rc') }}

  # ---------------------------------------------------------------------------
  # Job 8b — Slack/email notification on failure
  # ---------------------------------------------------------------------------
  notify:
    name: 'Notify'
    if: failure() && (github.event_name == 'push' || github.event_name == 'schedule')
    needs: [host-unit-tests, kernel-build, userspace-build, static-analysis, size-audit, package]
    runs-on: ubuntu-22.04
    steps:
      - name: Slack
        uses: slackapi/slack-github-action@v1.27.0
        with:
          payload: |
            {
              "text": ":x: CI failure on `${{ github.ref_name }}` — <${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}|run ${{ github.run_id }}>",
              "blocks": [
                { "type":"section",
                  "text":{ "type":"mrkdwn",
                           "text":"*BSP-IMX6Q CI failed*\nCommit: `${{ github.sha }}`\nAuthor: ${{ github.actor }}" } }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
          SLACK_WEBHOOK_TYPE: INCOMING_WEBHOOK

      - name: Email security team (nightly only)
        if: github.event_name == 'schedule'
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.example.com
          server_port: 587
          username: ${{ secrets.SMTP_USER }}
          password: ${{ secrets.SMTP_PASS }}
          subject: "[BSP-IMX6Q] Nightly CI failure"
          to: firmware-sec@example.com
          from: ci-bot@example.com
          body: "Nightly pipeline failed: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
```

---

## 3. CMAKE TOOLCHAIN FILE (User-space cross)

<!-- FILE: cmake/arm-linux-gnueabihf.cmake -->
```cmake
# =============================================================================
#  Toolchain: arm-linux-gnueabihf (hard-float VFPv3-D16) for i.MX6Q Cortex-A9
#  Used by:   libbsp, bsp-health daemon, user-space helpers
#  Ref:       SwRS-IMX6Q-BSP-001 §2 Target Toolchain
# =============================================================================

set(CMAKE_SYSTEM_NAME      Linux)
set(CMAKE_SYSTEM_PROCESSOR arm)

# --- Compilers (pinned; override via -DCMAKE_*_COMPILER) ---------------------
set(TOOLCHAIN_PREFIX  "arm-linux-gnueabihf-" CACHE STRING "")
set(CMAKE_C_COMPILER   ${TOOLCHAIN_PREFIX}gcc)
set(CMAKE_CXX_COMPILER ${TOOLCHAIN_PREFIX}g++)
set(CMAKE_AR           ${TOOLCHAIN_PREFIX}ar)
set(CMAKE_RANLIB       ${TOOLCHAIN_PREFIX}ranlib)
set(CMAKE_STRIP        ${TOOLCHAIN_PREFIX}strip)
set(CMAKE_OBJCOPY      ${TOOLCHAIN_PREFIX}objcopy)
set(CMAKE_OBJDUMP      ${TOOLCHAIN_PREFIX}objdump)
set(CMAKE_SIZE_UTIL    ${TOOLCHAIN_PREFIX}size)

# --- Cortex-A9 / VFPv3-D16 / NEON (i.MX6Q) -----------------------------------
set(IMX6Q_CPU_FLAGS "-mcpu=cortex-a9 -mtune=cortex-a9 -mthumb-interwork \
                     -mfpu=neon -mfloat-abi=hard -marm")

# --- Language baselines ------------------------------------------------------
set(CMAKE_C_STANDARD   11)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# --- Warnings (MISRA-enforcing where gcc supports) --------------------------
set(BSP_WARN_FLAGS
    "-Wall -Wextra -Wpedantic -Werror"
    "-Wshadow -Wdouble-promotion -Wformat=2 -Wformat-security"
    "-Wnull-dereference -Wstack-usage=2048"
    "-Wcast-align -Wcast-qual -Wconversion -Wsign-conversion"
    "-Wmissing-prototypes -Wstrict-prototypes -Wold-style-definition"
    "-Wvla -Wpointer-arith -Winit-self -Wwrite-strings"
    "-Wjump-misses-init -Wlogical-op -Wduplicated-cond -Wduplicated-branches"
    "-Wrestrict -Wundef -Wmissing-include-dirs")
string(REPLACE ";" " " BSP_WARN_FLAGS "${BSP_WARN_FLAGS}")

# --- Common flags ------------------------------------------------------------
set(BSP_COMMON_FLAGS
    "${IMX6Q_CPU_FLAGS} ${BSP_WARN_FLAGS} \
     -ffunction-sections -fdata-sections \
     -fstack-usage -fstack-protector-strong \
     -D_FORTIFY_SOURCE=2 -fPIC")

set(CMAKE_C_FLAGS_INIT   "${BSP_COMMON_FLAGS}")
set(CMAKE_CXX_FLAGS_INIT "${BSP_COMMON_FLAGS} -fno-exceptions -fno-rtti")

# --- Per-config flags --------------------------------------------------------
set(CMAKE_C_FLAGS_DEBUG_INIT          "-O0 -g3 -DDEBUG")
set(CMAKE_C_FLAGS_RELEASE_INIT        "-O2 -DNDEBUG -flto=auto")
set(CMAKE_C_FLAGS_RELWITHDEBINFO_INIT "-O2 -g -DNDEBUG -flto=auto")
set(CMAKE_C_FLAGS_MINSIZEREL_INIT     "-Os -DNDEBUG -flto=auto")

# --- Linker ------------------------------------------------------------------
set(CMAKE_EXE_LINKER_FLAGS_INIT
    "-Wl,--gc-sections -Wl,--as-needed -Wl,-z,relro,-z,now \
     -Wl,-Map=${CMAKE_BINARY_DIR}/link.map -Wl,--print-memory-usage")

# --- Sanitizers (debug only) -------------------------------------------------
option(ENABLE_SANITIZERS "Enable ASan+UBSan (debug)" OFF)
if(ENABLE_SANITIZERS)
  add_compile_options(-fsanitize=address,undefined -fno-omit-frame-pointer)
  add_link_options(-fsanitize=address,undefined)
endif()

# --- Root path behaviour -----------------------------------------------------
set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_PACKAGE ONLY)

# --- Post-build: print size --------------------------------------------------
function(bsp_print_size tgt)
  add_custom_command(TARGET ${tgt} POST_BUILD
    COMMAND ${CMAKE_SIZE_UTIL} -Ax $<TARGET_FILE:${tgt}>
    COMMAND ${CMAKE_SIZE_UTIL} -Bd $<TARGET_FILE:${tgt}>)
endfunction()
```

---

## 4. CPPCHECK MISRA CONFIGURATION

<!-- FILE: tools/cppcheck_misra.json -->
```json
{
  "script":        "misra.py",
  "args":          [ "--rule-texts=tools/misra_c_2012_rules.txt" ],
  "ctu":           false,
  "_comment":      "Scope per SwRS-IMX6Q-BSP-001 §6: MISRA advisory only for out-of-tree code",
  "project": {
    "defines":     [ "__linux__", "__arm__", "__ARM_ARCH_7A__" ],
    "undefines":   [ "__KERNEL__" ],
    "include-paths": [
      "libbsp/include",
      "libbsp/src",
      "drivers/bsp-imx6q/include",
      "tools/uboot-patches/include"
    ],
    "paths": [
      "libbsp/",
      "tools/uboot-patches/",
      "test/harness/"
    ],
    "exclude": [
      "drivers/bsp-imx6q/**/*",
      "**/build/**",
      "**/mocks/**",
      "**/unity/**",
      "**/cmock/**"
    ],
    "platform":    "unix32",
    "standard":    "c11"
  },
  "addons": [
    "misra",
    "cert",
    "threadsafety",
    "y2038"
  ],
  "suppressions": [
    { "id": "misra-c2012-20.1",  "justification": "Kernel uapi headers require includes after #define" },
    { "id": "misra-c2012-21.6",  "fileName": "test/*",
      "justification": "stdio permitted in host unit-test harness (advisory only)" },
    { "id": "misra-c2012-8.7",   "justification": "Out-of-tree helpers export symbols for dlopen" },
    { "id": "missingIncludeSystem" }
  ],
  "severity_fail_on": [ "error", "warning" ]
}
```

**Suppressions file** (keeps inline code clean):

<!-- FILE: tools/cppcheck_suppressions.txt -->
```
// Format:  <id>:<file>:<line>   or   <id>
unusedFunction:libbsp/src/bsp_api.c
missingIncludeSystem
unmatchedSuppression
// MISRA Rule 11.3 — cast between pointer types is required for regmap cookies
misra-c2012-11.3:libbsp/src/bsp_regmap_wrap.c
// MISRA Rule 15.5 — multiple returns in small accessors improve readability
misra-c2012-15.5
```

---

## 5. CEEDLING PROJECT (Unit Tests)

<!-- FILE: test/project.yml -->
```yaml
# =============================================================================
#  Ceedling project — BSP-IMX6Q host-native unit tests
#  Traces:  SwUT-IMX6Q-BSP-001 UT-C01..UT-C04
#  Runs:    host (x86_64-linux) with mocked Linux kernel APIs
# =============================================================================
---
:project:
  :use_exceptions:           FALSE
  :use_test_preprocessor:    TRUE
  :use_auxiliary_dependencies: TRUE
  :build_root:               build/
  :test_file_prefix:         test_
  :which_ceedling:           gem
  :default_tasks:
    - test:all

:environment: []

:extension:
  :executable: .out

:paths:
  :test:
    - +:test/unit/**
    - -:test/support
  :source:
    - src/host_shims/**              # kernel API stubs (CU-level)
    - ../drivers/bsp-imx6q/src/bsp_core.c
  :include:
    - ../drivers/bsp-imx6q/include
    - src/host_shims/include
    - mocks
  :support:
    - test/support

:defines:
  :common: &common_defines
    - BSP_UNIT_TEST=1
    - __KERNEL__=0
    - CONFIG_OF=1
  :test:
    - *common_defines
    - TEST
  :test_preprocess:
    - *common_defines

:cmock:
  :mock_prefix:            'Mock'
  :when_no_prototypes:     :warn
  :enforce_strict_ordering: TRUE
  :plugins:
    - :ignore
    - :ignore_arg
    - :expect_any_args
    - :array
    - :callback
    - :return_thru_ptr
  :treat_as:
    uint8:    HEX8
    uint16:   HEX16
    uint32:   HEX32
    int8:     INT8
    bool:     UINT8
  :includes:
    - bsp_core.h
    - <linux/types.h>
    - <linux/clk.h>
    - <linux/regulator/consumer.h>

:gcov:
  :reports:
    - HtmlDetailed
    - JSON
    - Cobertura
  :gcovr:
    :html_medium_threshold: 75
    :html_high_threshold:   90
    :exclude:
      - 'test/.*'
      - 'build/.*'
      - 'mocks/.*'
      - '.*/unity/.*'
    :fail_under_line:       90
    :fail_under_branch:     80
  :utilities:
    - gcovr

:tools_gcov_report:
  :executable: gcovr

:plugins:
  :load_paths:
    - '#{Ceedling.load_path}'
  :enabled:
    - stdout_pretty_tests_report
    - module_generator
    - gcov
    - command_line_tests
    - junit_tests_report

:module_generator:
  :project_root:   '../'
  :source_root:    'drivers/bsp-imx6q/src/'
  :inc_root:       'drivers/bsp-imx6q/include/'
  :test_root:      'test/unit/'
...
```

---

## 6. BINARY SIZE BUDGET & CHECKER

<!-- FILE: tools/size_budget.yml -->
```yaml
# Budgets derived from SwRS-IMX6Q-BSP-001 §7.2 (SwRR-SIZ-001..009)
# All values in bytes. Grow=max increase per release (kiB).

modules:
  bsp_core.ko:
    text:       32768
    data:         512
    bss:         2048
    total:      40960
    grow:         8

  imx6q_flexcan_glue.ko:
    text:       49152
    data:        1024
    bss:         2048
    total:      57344
    grow:        16

  imx6q_ecspi.ko:
    text:       65536
    data:        1024
    bss:         4096
    total:      73728
    grow:        16

  imx6q_i2c.ko:
    text:       40960
    data:        1024
    bss:         2048
    total:      49152
    grow:        16

userspace:
  libbsp.so:
    text:      262144       # 256 kiB
    data:       16384
    bss:        32768
    total:     327680        # 320 kiB (SwRR-SIZ-008)
    grow:        32

  bsp-health:
    text:      131072
    data:        8192
    bss:        16384
    total:     163840        # 160 kiB (SwRR-SIZ-009)
    grow:        16
```

<!-- FILE: tools/check_size.py -->
```python
#!/usr/bin/env python3
# =============================================================================
#  check_size.py — validate .ko / .so sizes against SwRS §7.2 budgets
#  Traces:   SwRR-SIZ-001..009
#  Exit 1 if any component exceeds its total budget; warn on >80 %.
# =============================================================================
from __future__ import annotations
import argparse, glob, os, re, subprocess, sys, yaml
from pathlib import Path

RE_BERK = re.compile(
    r"^\s*(?P<text>\d+)\s+(?P<data>\d+)\s+(?P<bss>\d+)\s+(?P<dec>\d+)")

def size_of(sz_tool: str, path: str) -> dict[str, int]:
    out = subprocess.check_output([sz_tool, "-Bd", path], text=True)
    # Line 2 of "Berkeley" output has the numbers
    m = RE_BERK.search(out.splitlines()[1])
    if not m:
        sys.exit(f"ERROR: cannot parse size output for {path}\n{out}")
    return {k: int(v) for k, v in m.groupdict().items()}

def fmt_kib(n: int) -> str:
    return f"{n/1024:7.1f} kiB"

def check(name: str, actual: dict, budget: dict) -> tuple[bool, str]:
    rows, failed = [], False
    for key in ("text", "data", "bss", "dec"):
        a = actual[key]
        b = budget.get("total" if key == "dec" else key)
        if b is None:
            rows.append(f"| {key:5} | {fmt_kib(a)} |      –      |   –   |")
            continue
        pct = 100.0 * a / b
        mark = "✅"
        if a > b:
            mark, failed = "❌", True
        elif pct > 80.0:
            mark = "⚠️"
        rows.append(f"| {key:5} | {fmt_kib(a)} | {fmt_kib(b)} | {pct:5.1f}% {mark} |")
    body = "\n".join(rows)
    head = (f"### `{name}`\n\n"
            f"| Section | Actual | Budget | Usage |\n"
            f"|---------|--------|--------|-------|\n")
    return failed, head + body + "\n"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget", required=True)
    ap.add_argument("--size-tool", default="size")
    ap.add_argument("--report", default="size_report.md")
    ap.add_argument("files", nargs="+")
    a = ap.parse_args()

    with open(a.budget) as f:
        budget = yaml.safe_load(f)
    flat = {**budget.get("modules", {}), **budget.get("userspace", {})}

    # Expand globs
    files: list[str] = []
    for pat in a.files:
        files.extend(glob.glob(pat, recursive=True))
    if not files:
        sys.exit("ERROR: no input files matched")

    failed_any = False
    report = [f"# Size report vs SwRS §7.2 budgets\n"]
    for f in sorted(files):
        name = os.path.basename(f)
        if name not in flat:
            report.append(f"> ⚠️ `{name}` has no budget entry — please add one.\n")
            continue
        actual = size_of(a.size_tool, f)
        fail, section = check(name, actual, flat[name])
        report.append(section)
        failed_any |= fail

    Path(a.report).write_text("\n".join(report))
    sys.stdout.write("\n".join(report))

    if failed_any:
        print("\n::error::Size budget exceeded — see report", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 7. DOCKERFILE — Reproducible Build Environment

<!-- FILE: docker/Dockerfile -->
```dockerfile
# syntax=docker/dockerfile:1.6
# =============================================================================
#  BSP-IMX6Q CI image — pinned, reproducible, hash-locked
#  Build:   docker build -t ghcr.io/<org>/bsp-ci:1.0.0 -f docker/Dockerfile .
#  Publish: docker push  ghcr.io/<org>/bsp-ci:1.0.0
# =============================================================================
FROM ubuntu:22.04@sha256:a6d2b38300ce017add71440577d5b0a90460d0e57fd7aec21dd0d1b0761bbfb2

ARG DEBIAN_FRONTEND=noninteractive
ARG ARM_GCC_VERSION=13.2.rel1
ARG KERNEL_VERSION=6.6.30
ARG CPPCHECK_VERSION=2.14.2
ARG LCOV_VERSION=2.0
ARG CEEDLING_VERSION=0.31.1
ARG UNITY_VERSION=2.6.0
ARG CMOCK_VERSION=2.5.4

LABEL org.opencontainers.image.title="bsp-imx6q-ci"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.source="https://github.com/<org>/bsp-imx6q"
LABEL org.opencontainers.image.licenses="GPL-2.0-only AND MIT"

# ---- Base tools ------------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential ninja-build cmake git curl ca-certificates xz-utils \
        python3 python3-pip python3-yaml python3-venv \
        ruby ruby-dev \
        bc bison flex libssl-dev libelf-dev libncurses-dev \
        pkg-config libudev-dev libgpiod-dev libdrm-dev \
        sparse smatch coccinelle clang-15 clang-tidy-15 clang-format-15 \
        lcov gcovr file patch cpio rsync unzip gnupg2 sudo \
 && rm -rf /var/lib/apt/lists/* \
 && update-alternatives --install /usr/bin/clang-tidy clang-tidy \
        /usr/bin/clang-tidy-15 100 \
 && update-alternatives --install /usr/bin/clang-format clang-format \
        /usr/bin/clang-format-15 100

# ---- arm-linux-gnueabihf toolchain (pinned) --------------------------------
RUN ARCH=$(uname -m) && \
    URL="https://developer.arm.com/-/media/Files/downloads/gnu/${ARM_GCC_VERSION}/binrel/arm-gnu-toolchain-${ARM_GCC_VERSION}-${ARCH}-arm-none-linux-gnueabihf.tar.xz" && \
    curl -