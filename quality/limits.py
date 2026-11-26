"""Every threshold and policy list the gates use. Change a rule here, nowhere else."""

SOURCE_DIRS = ("simulator", "simulator_gui", "tools", "examples", "quality")
TEST_DIRS = ("tests",)
PYTHON_DIRS = SOURCE_DIRS + TEST_DIRS

# Clean-code limits (CODING_GUIDELINES.md, "Small and simple").
MAX_FUNCTION_LINES = 50
MAX_PARAMS = 7
MAX_COMPLEXITY = 10
MAX_FILE_LINES = 500
MIN_REPEATED_STRING_LEN = 4
MIN_STRING_REPEATS = 3
ALLOWED_NUMBERS = (0, 1, 2)  # -1 is UnaryOp(1)

# Tests: line coverage of the packages below must not drop under this percentage.
COVERAGE_FLOOR = 95
COVERED_PACKAGES = ("simulator", "simulator_gui", "quality")

# Repository hygiene.
MAX_FILE_BYTES = 512 * 1024
FORBIDDEN_TRACKED = (
    "*.elf", "*.map", "*.o", "*.a", "*.so", "*.dll", "*.exe", "*.pyc", "*.pyo",
    "coverage.xml", ".coverage", "*.egg-info/*", "build/*", "*/build/*", "dist/*", ".venv/*",
)  # fmt: skip
ALLOWED_BINARIES = {  # tracked *.bin: path -> why
    "firmware/led_blink/tm4c/firmware.bin": "prebuilt example used by the quick start",
    "firmware/led_blink/stm32/firmware.bin": "prebuilt example used by the quick start",
}
# Documentation: only paths under these roots are checked when written as `code`.
DOC_SUFFIXES = (".md",)
DOC_IGNORED_PREFIXES = ("build/", "tests/integration/__")
