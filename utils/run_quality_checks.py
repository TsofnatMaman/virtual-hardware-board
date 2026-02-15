#!/usr/bin/env python
"""Local quality checks and tests runner with auto-fix capabilities.

This script runs the same quality checks and tests as the CI/CD pipeline,
with optional automatic fixes for formatting and import ordering.

Usage:
    python run_quality_checks.py                    # Run all checks (no fixes)
    python run_quality_checks.py --fix              # Run all checks + auto fixes
    python run_quality_checks.py --fix --skip lint  # Fix but skip linting
    python run_quality_checks.py --verbose          # Detailed output
"""

import argparse
import subprocess  # nosec B404
import sys

# Directories to check
SIMULATOR_DIR = "simulator"
TESTS_DIR = "tests"
DIRS_TO_CHECK = [SIMULATOR_DIR, TESTS_DIR]


class CheckRunner:
    """Runs quality checks and tests with optional auto-fixes."""

    def __init__(self, fix: bool = False, verbose: bool = False, skip_checks: list[str] = None):
        self.fix = fix
        self.verbose = verbose
        self.skip_checks = skip_checks or []
        self.failed_checks = []
        self.passed_checks = []

    def _run(
        self,
        name: str,
        run_live,
        run_captured,
        show_output: bool = True,
    ) -> bool:
        """Run a command and record its result."""
        if name.lower() in self.skip_checks:
            print(f"[SKIP] {name}")
            return True

        print(f"\n{'=' * 70}")
        print(f"Running: {name}")
        print(f"{'=' * 70}")

        try:
            if self.verbose or show_output:
                result = run_live()
            else:
                result = run_captured()
                if result.returncode != 0:
                    print(result.stdout)
                    print(result.stderr)

            success = result.returncode == 0
            if success:
                print(f"[OK] {name} passed!")
                self.passed_checks.append(name)
            else:
                print(f"[FAIL] {name} failed!")
                self.failed_checks.append(name)

            return success

        except FileNotFoundError as e:
            print(f"[FAIL] Error: {e}")
            print("   Make sure all tools are installed: pip install -r requirements-dev.txt")
            self.failed_checks.append(name)
            return False

    def check_black_formatting(self) -> bool:
        """Check and optionally fix code formatting with Black."""
        if self.fix:
            name = "Black Formatting (auto-fix enabled)"
            return self._run(
                name,
                lambda: subprocess.run(
                    ["black", "simulator", "tests"], check=False, shell=False  # nosec B603
                ),
                lambda: subprocess.run(
                    ["black", "simulator", "tests"],
                    check=False,
                    shell=False,  # nosec B603
                    capture_output=True,
                    text=True,
                ),
            )

        name = "Black Formatting Check"
        return self._run(
            name,
            lambda: subprocess.run(
                ["black", "--check", "simulator", "tests"], check=False, shell=False  # nosec B603
            ),
            lambda: subprocess.run(
                ["black", "--check", "simulator", "tests"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
        )

    def check_isort_imports(self) -> bool:
        """Check and optionally fix import ordering with isort."""
        if self.fix:
            name = "isort Import Ordering (auto-fix enabled)"
            return self._run(
                name,
                lambda: subprocess.run(
                    ["isort", "simulator", "tests"], check=False, shell=False  # nosec B603
                ),
                lambda: subprocess.run(
                    ["isort", "simulator", "tests"],
                    check=False,
                    shell=False,  # nosec B603
                    capture_output=True,
                    text=True,
                ),
            )

        name = "isort Import Ordering Check"
        return self._run(
            name,
            lambda: subprocess.run(
                ["isort", "--check-only", "simulator", "tests"],
                check=False,
                shell=False,  # nosec B603
            ),
            lambda: subprocess.run(
                ["isort", "--check-only", "simulator", "tests"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
        )

    def check_pylint(self) -> bool:
        """Check code quality with Pylint."""
        name = "Pylint Code Quality Check"
        return self._run(
            name,
            lambda: subprocess.run(
                ["pylint", "simulator"], check=False, shell=False  # nosec B603
            ),
            lambda: subprocess.run(
                ["pylint", "simulator"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
        )

    def check_mypy(self) -> bool:
        """Check type hints with Mypy."""
        name = "Mypy Type Checking"
        return self._run(
            name,
            lambda: subprocess.run(
                ["mypy", "simulator"], check=False, shell=False  # nosec B603
            ),
            lambda: subprocess.run(
                ["mypy", "simulator"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
        )

    def check_vulture(self) -> bool:
        """Check for dead code with Vulture."""
        name = "Vulture Dead Code Check"
        return self._run(
            name,
            lambda: subprocess.run(
                ["vulture", ".", "--exclude", "tests", "--min-confidence", "90"],
                check=False,
                shell=False,  # nosec B603
            ),
            lambda: subprocess.run(
                ["vulture", ".", "--exclude", "tests", "--min-confidence", "90"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
        )

    def check_radon_complexity(self) -> bool:
        """Check code complexity with Radon."""
        name = "Radon Code Complexity Check"
        return self._run(
            name,
            lambda: subprocess.run(
                ["radon", "cc", "simulator", "-a"], check=False, shell=False  # nosec B603
            ),
            lambda: subprocess.run(
                ["radon", "cc", "simulator", "-a"],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
            show_output=True,
        )

    def run_tests(self) -> bool:
        """Run pytest with coverage."""
        name = "Pytest + Coverage"
        return self._run(
            name,
            lambda: subprocess.run(
                [
                    "pytest",
                    "--cov=simulator",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                    "simulator",
                    "tests",
                ],
                check=False,
                shell=False,  # nosec B603
            ),
            lambda: subprocess.run(
                [
                    "pytest",
                    "--cov=simulator",
                    "--cov-report=term-missing",
                    "--cov-report=xml",
                    "simulator",
                    "tests",
                ],
                check=False,
                shell=False,  # nosec B603
                capture_output=True,
                text=True,
            ),
            show_output=True,
        )

    def print_summary(self) -> None:
        """Print summary of check results."""
        print(f"\n{'=' * 70}")
        print("SUMMARY")
        print(f"{'=' * 70}")

        if self.passed_checks:
            print(f"\nPassed ({len(self.passed_checks)}):")
            for check in self.passed_checks:
                print(f"   - {check}")

        if self.failed_checks:
            print(f"\nFailed ({len(self.failed_checks)}):")
            for check in self.failed_checks:
                print(f"   - {check}")
        else:
            print("\nAll checks passed!")

        print(f"\n{'=' * 70}")

    def run_all(self) -> int:
        """Run all checks in order.

        Returns:
            0 if all checks passed, non-zero otherwise
        """
        fix_text = "with auto-fixes" if self.fix else "without fixes"
        print(f"\nStarting quality checks {fix_text}...\n")

        # Run checks in order
        checks = [
            ("formatting", self.check_black_formatting),
            ("imports", self.check_isort_imports),
            ("lint", self.check_pylint),
            ("type", self.check_mypy),
            ("deadcode", self.check_vulture),
            ("complexity", self.check_radon_complexity),
            ("tests", self.run_tests),
        ]

        for _check_name, check_func in checks:
            check_func()

        self.print_summary()

        return 0 if not self.failed_checks else 1


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run local quality checks and tests with optional auto-fixes",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_quality_checks.py              # Run all checks
  python run_quality_checks.py --fix        # Run + auto-fix formatting/imports
  python run_quality_checks.py --skip deadcode  # Skip dead code check
  python run_quality_checks.py --fix --verbose  # Auto-fix with detailed output
        """,
    )

    parser.add_argument(
        "--fix",
        "--apply",
        action="store_true",
        dest="fix",
        help="Automatically fix issues (formatting, imports) where possible",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show detailed output from all commands",
    )

    parser.add_argument(
        "--skip",
        nargs="+",
        default=[],
        help="Skip specific checks (formatting, imports, lint, type, deadcode, complexity, tests)",
    )

    args = parser.parse_args()

    runner = CheckRunner(
        fix=args.fix,
        verbose=args.verbose,
        skip_checks=args.skip,
    )

    return runner.run_all()


if __name__ == "__main__":
    sys.exit(main())
