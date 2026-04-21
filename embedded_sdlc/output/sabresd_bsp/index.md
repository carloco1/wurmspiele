# Embedded SDLC — V-Model Artefacts

**Project:** Develop a complete Linux kernel BSP driver package for the NXP i.MX6 Quad SABRE Smart Device Board (SabreSD). Cover ALL on-board interfaces: FlexCAN (CAN bus), eCSPI (SPI), I2C (PMIC/touch/audio codec SGTL5000), UART (debug + Bluetooth), USB OTG (2x), Gigabit Ethernet (FEC/ENET), uSDHC (SD/eMMC), HDMI-TX (Synopsys DesignWare), MIPI-CSI camera input, MIPI-DSI display output, PCIe, GPIO expander, PWM, IIO ADC, EPDC (E-ink), and Audio SSI/SAI. Implement platform_driver/device_tree bindings, regmap, pinctrl, clock and regulator integration for each subsystem. Target kernel 6.6 LTS, Yocto Scarthgap layer, arm-linux-gnueabihf toolchain.

**Total pipeline time:** 1519s


```
   DEVELOPMENT (left)                    VERIFICATION (right)
   ─────────────────────────────────     ──────────────────────────────────
   1  System Requirements          ───►  14  System Validation
      2  System Architecture       ──►  13  HW/SW Integration Tests
         3  HW/SW Interface        ─►   12  SW Qualification Tests
            4  SW Requirements     ►    11  Integration Tests
               5  SW Architecture  ┐    10  Unit Tests
                  6  Detailed Design│
                  7  Implementation ┘
                     ↓ cross-cutting ↓
                  8  Static Analysis  (MISRA / CERT-C)
                  9  Safety Analysis  (FMEA / FTA)
                     ↓ infrastructure ↓
                 15  CI/CD Pipeline
                 16  Design Review  ──  Go / No-Go
```


## Artefacts

| Stage | Artefact | Time |
|-------|---------|------|
|  1/16  System Requirements Specification | [system_requirements.md](system_requirements.md) | 0.0s |
|  2/16  System Architecture Design | [system_architecture.md](system_architecture.md) | 0.0s |
|  3/16  HW/SW Interface Definition | [hw_sw_interface.md](hw_sw_interface.md) | 0.0s |
|  4/16  Software Requirements Specification | [sw_requirements.md](sw_requirements.md) | 0.0s |
|  5/16  Software Architecture Design | [sw_architecture.md](sw_architecture.md) | 0.0s |
|  6/16  Detailed Design | [detailed_design.md](detailed_design.md) | 0.0s |
|  7/16  Implementation (Code Generation) | [implementation.md](implementation.md) | 0.0s |
|  8/16  Static Analysis  [MISRA / CERT-C] | [static_analysis.md](static_analysis.md) | 0.0s |
|  9/16  Safety Analysis  [FMEA / FTA] | [safety_analysis.md](safety_analysis.md) | 228.5s |
| 10/16  Unit Tests  ↔  Detailed Design | [unit_tests.md](unit_tests.md) | 144.7s |
| 11/16  Integration Tests  ↔  SW Architecture | [integration_tests.md](integration_tests.md) | 180.8s |
| 12/16  SW Qualification Tests  ↔  SW Requirements | [sw_qualification.md](sw_qualification.md) | 152.0s |
| 13/16  HW/SW Integration Tests  ↔  HSI | [hw_sw_integration.md](hw_sw_integration.md) | 258.4s |
| 14/16  System Validation  ↔  System Requirements | [system_validation.md](system_validation.md) | 232.1s |
| 15/16  CI/CD Pipeline Configuration | [ci_pipeline.md](ci_pipeline.md) | 188.2s |
| 16/16  Design Review & Go/No-Go | [design_review.md](design_review.md) | 134.6s |
