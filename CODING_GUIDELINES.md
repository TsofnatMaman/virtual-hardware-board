# Coding guidelines

The code of this project must be **generic, easy to extend, modular, clean, minimal,
predictable and simple**. Each rule below says what to do, why, and which gate
enforces it (`python -m quality.run --list`; details in
[docs/quality-gates.md](docs/quality-gates.md)). Rules marked *review* cannot be
checked by a tool; they are checked by the person reviewing the change.

When in doubt: **delete code instead of adding it.** The best change is the one that
makes the next change smaller.

## Principles

1. **Generic.** Write for the family, not the instance. A board, a peripheral or a GUI
   component is described by *data* (`config.yaml`, `simulator_gui/boards/*.yaml`) and
   implemented by *one* class that reads it. Behaviour that differs between boards goes
   in configuration; only genuinely different logic gets its own class. *(review)*
2. **Extend by adding, not by editing.** New board, component, debug command or gate = new
   module + one registration (`register_board`, `ComponentRegistry`, `quality/registry.py`).
   If adding a feature forces edits in unrelated places, the structure is wrong. *(review)*
3. **Modular.** One responsibility per module; dependencies point down the layers below;
   no cycles. Enforced: `layers`.
4. **Minimal.** No speculative options, no unused parameters, no commented-out code,
   no "just in case" abstractions. Enforced: `dead-code`.
5. **Predictable.** Same problem, same shape: every board package looks alike, every gate is
   `check(tree) -> list[Finding]`, every CLI flag has one name. Things live where a newcomer
   would look first. *(review)*
6. **Simple.** Prefer boring constructs: early returns, small functions, table-driven
   dispatch, plain data. Cleverness needs a comment explaining why plain code does not work.
   Enforced: `size`.

## Structure

The packages form layers; a module may import only from the layers below it
(`quality/gates/layers.py` is the single source of this table).

| Layer | Package | May import |
|---|---|---|
| shared kernel | `simulator.core.exceptions`, `simulator.core.gpio_enums` | nothing |
| utils | `simulator.utils` | shared |
| interfaces | `simulator.interfaces` (contracts only: ABCs, protocols, dataclasses) | utils, shared |
| core | `simulator.core` (CPU, memory, registry, builders; knows no board) | interfaces, utils, shared |
| boards | `simulator.tm4c`, `simulator.stm32`, `simulator.stm32c031` | core and below; a variant may use its base family (`stm32c031` → `stm32`), never another board |
| debug | `simulator.debug` (session, GDB and JSON servers) | core and below, `simulator` |
| api | `simulator` (`__init__`: registers boards, public API) | everything under `simulator` |
| gui | `simulator_gui` | api, debug, core and below |
| tools, examples | `tools/`, `examples/` | api, debug, gui |

* Type-only imports (`if TYPE_CHECKING:`) are not dependencies; runtime upward imports are.
  If an interface needs a core type only for annotations, import it under `TYPE_CHECKING`.
* Optional heavy dependencies (the GUI) are imported lazily with `importlib` at the edge
  (`simulator/debug/server.py`), never at module level of a lower layer.
* Python lives only in `simulator`, `simulator_gui`, `tools`, `examples`, `quality`, `tests`
  (`gate-scope`): a directory outside that list would escape every gate.
* Documentation names real files: Markdown links and `` `repo/paths` `` must resolve
  (`docs-links`). Build outputs may be mentioned, never committed.
* The repository holds source, not products: no build outputs, no submodule pointers
  without `.gitmodules`, no stray binaries, no files over 512 KiB (`repo-hygiene`;
  allowed exceptions are listed with a reason in `quality/limits.py`).

## Named values

No magic numbers, no magic strings.

* A number is fine when it is `0`, `1`, `2`, sits in a **named definition** (module- or
  class-level assignment, `UPPER_CASE` by convention) or is a default argument.
  Everything else gets a name where it is first needed.
* Hardware addresses, masks, offsets and pin maps live in YAML configuration, not in code.
  Protocol values (packet markers, command ids, register bits) are named constants at the
  top of the module that implements the protocol, or in an `Enum`.
* A string written inline **three times** becomes a constant, an `Enum` member or a
  `Literal` type. Dunders (`"__main__"`) are exempt.
* Shared defaults have one home: debug server host and port are in
  `simulator/debug/defaults.py`; example firmware paths in `examples/__init__.py`;
  every limit a gate uses in `quality/limits.py`.

Enforced: `magic-values`.

## Small and simple

| Limit | Value |
|---|---|
| Lines per function | 50 |
| Parameters per function | 7 |
| Cyclomatic complexity per function | 10 |
| Lines per file | 500 |

* Split by *reason to change*, not by size alone: when a function needs a comment to
  separate its phases, those phases are functions.
* Replace `if/elif` chains over a key with a dictionary of handlers
  (`DebugSession.handle_request`, `GdbRemoteServer._handle_packet`).
* Return early; avoid nesting deeper than three levels.
* The same limits apply to C firmware: `main` stays short, hardware access goes through
  named register macros in the board header.

Enforced: `size`. Existing violations are listed in `quality/baselines/size.json` and may
only shrink (see *Ratchets*).

## No duplication

* The third copy is a bug: extract it. The second copy needs a reason.
* Behaviour shared by several boards moves **up** a layer (base class, builder in
  `simulator/core/builders.py`) and is parametrised by the board configuration.
* Tests share setup through fixtures (`tests/**/conftest.py`), not copy-paste.

Enforced: `duplication` (pylint duplicate-code, 8 lines). **Known debt:** the three board
classes repeat their wiring (see `quality/baselines/duplication.json`); the next
refactor is one configurable board class.

## Clean code

* Names say what a thing *is* or *does*; no abbreviations a newcomer cannot guess.
  Every module starts with a docstring stating its one responsibility; public functions
  and classes get a one-line docstring when the name alone is not enough.
* Fully typed signatures in new code. Use `Literal`/`Enum`/`dataclass` instead of strings
  and tuples. Validate external data (YAML, packets) at the boundary, once.
* Catch the exception you handle (`except ImportError`), never `except Exception` to hide
  a problem; do not return error codes where an exception is clearer.
* `pathlib` for paths, f-strings for formatting, `subprocess` with argument lists and no shell.
* Libraries do not `print`; command-line entry points do.
* Comments explain **why**, not what. Dead and commented-out code is deleted (git remembers).

Enforced: `lint` (pylint), `format` and `import-order` (black 24, isort; use
`python -m black`, not a stray global binary).

## Honest suppressions

* A suppression names the rule it silences (`# noqa: E501`, `# type: ignore[attr-defined]`,
  `# pylint: disable=name`); a bare one is rejected (`suppressions-named`).
* Every suppression is debt: the number per file may not grow (`suppressions-budget`).
  Prefer fixing the cause — a typed variable, a narrower exception — over silencing it.
* Tests are exempt from the budget (assertions trigger security-tool noise by design).

## Typed

mypy passes without errors on `simulator`, `simulator_gui` and `quality` (`types`).
Third-party packages without stubs are declared once in `pyproject.toml`
(`[[tool.mypy.overrides]]`), not suppressed line by line.

## Minimal

Unused code is removed, not kept "for later" (`dead-code`, vulture at 90 % confidence).

## Style

`python -m black` and `python -m isort` decide formatting; there is nothing to discuss.
`python -m quality.run --fix` applies them (`format`, `import-order`).

## Security

* No credentials in the repository; configuration secrets come from the environment
  (`secrets`).
* Medium and high severity findings of bandit fail the build (`bandit`).
* Dependencies are audited on a schedule, because that depends on the outside world and
  must not block an unrelated commit (`dependency-audit`).

## Tested

* Every behaviour change comes with a test that fails without it. Bugs get a regression test
  first.
* Pyramid: unit tests next to what they check (`tests/core`, `tests/debug`, …); integration
  tests build real firmware and drive a real `gdb` (`tests/integration`); GUI tests run with
  Qt's `offscreen` platform (`tests/gui`).
* Every gate has a negative test (a planted violation must fail it) and a clean test
  (`tests/quality`).
* Line coverage of `simulator`, `simulator_gui` and `quality` stays at or above 95 % (`tests`).
* A missing optional tool skips tests locally; in CI `REQUIRE_FULL_TEST_ENV=1` turns that
  into a failure, so nothing is skipped silently.

## Extension recipes

Adding any of these must be a small, local change. Tests fail when a step is forgotten.

* **A board**: `simulator/<board>/` (one class + `config.yaml`) registered with
  `register_board`; `simulator_gui/boards/<board>.yaml` with a background image of the
  same size as `canvas`; `firmware/boards/<board>/`; the C template (`board/`, `Makefile`
  branch, `build` task, debug configuration). `tests/integration/test_vscode_and_board_consistency.py`
  lists what is missing.
* **A GUI component**: one class pair in `simulator_gui/components/`, one line in
  `simulator_gui/registry.py`.
* **A debug-server command**: one handler method and one dictionary entry in
  `DebugSession.handle_request` or `GdbRemoteServer._handle_packet`.
* **A gate**: `quality/gates/<name>.py` with `check(tree) -> list[Finding]`, one `Gate(...)` in
  `quality/registry.py`, a rule heading in this file, a row in `docs/quality-gates.md`,
  tests in `tests/quality/`.

## Ratchets and known debt

Old code that breaks a rule is recorded in `quality/baselines/<gate>.json` as *debt per
file or function*. The rule is a ratchet:

* debt may **only go down**; new code starts at zero;
* `python -m quality.run --write-baselines` lowers a baseline after you pay debt and refuses
  to raise it; CI also rejects a pull request that edits a baseline upwards
  (`--growth-check`) and, with `--strict`, one that forgot to lower it;
* when a baseline reaches zero, delete its file and make the gate absolute.

Largest items today: the board wiring duplication, `tools/cmsis_dap_proxy/proxy.py`
(work in progress for Keil), numeric constants in the debug and board modules.

## C firmware

`-Wall -Wextra` always, `-Werror` in the integration tests; register access only through
named macros in `firmware/boards/*/` headers; delays and pin numbers are named constants.
The C template builds without optimisation (`-O0`) so variables and functions stay
visible in the debugger.
