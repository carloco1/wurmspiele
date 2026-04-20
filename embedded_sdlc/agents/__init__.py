from .requirements import run as run_requirements
from .architect import run as run_architect
from .codegen import run as run_codegen
from .analyzer import run as run_analyzer
from .testgen import run as run_testgen
from .reviewer import run as run_reviewer

AGENTS = {
    "requirements": run_requirements,
    "architecture": run_architect,
    "codegen":      run_codegen,
    "analysis":     run_analyzer,
    "testgen":      run_testgen,
    "review":       run_reviewer,
}
