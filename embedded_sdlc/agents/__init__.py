from .system_requirements import run as run_system_requirements
from .system_architecture  import run as run_system_architecture
from .hw_sw_interface      import run as run_hw_sw_interface
from .sw_requirements      import run as run_sw_requirements
from .sw_architecture      import run as run_sw_architecture
from .detailed_design      import run as run_detailed_design
from .implementation       import run as run_implementation
from .static_analysis      import run as run_static_analysis
from .safety_analysis      import run as run_safety_analysis
from .unit_tests           import run as run_unit_tests
from .integration_tests    import run as run_integration_tests
from .sw_qualification     import run as run_sw_qualification
from .hw_sw_integration    import run as run_hw_sw_integration
from .system_validation    import run as run_system_validation
from .ci_pipeline          import run as run_ci_pipeline
from .design_review        import run as run_design_review

AGENTS = {
    "system_requirements": run_system_requirements,
    "system_architecture": run_system_architecture,
    "hw_sw_interface":     run_hw_sw_interface,
    "sw_requirements":     run_sw_requirements,
    "sw_architecture":     run_sw_architecture,
    "detailed_design":     run_detailed_design,
    "implementation":      run_implementation,
    "static_analysis":     run_static_analysis,
    "safety_analysis":     run_safety_analysis,
    "unit_tests":          run_unit_tests,
    "integration_tests":   run_integration_tests,
    "sw_qualification":    run_sw_qualification,
    "hw_sw_integration":   run_hw_sw_integration,
    "system_validation":   run_system_validation,
    "ci_pipeline":         run_ci_pipeline,
    "design_review":       run_design_review,
}
