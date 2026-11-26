# Quality gates

A *gate* is an automated check that must pass before code is accepted. The rules they
enforce are in [CODING_GUIDELINES.md](../CODING_GUIDELINES.md); this page says **what each
gate checks, where it runs and what to do when it fails**.

```bash
python -m quality.run --list                   # all gates, their stage and rule
python -m quality.run --stage pre-commit       # the fast ones (a few seconds)
python -m quality.run                          # everything CI runs (includes the tests)
python -m quality.run --only layers,size -v    # selected gates, every finding
python -m quality.run --fix                    # let the formatters repair their findings
python -m quality.run --write-baselines        # lower a ratchet after paying debt
```

## Where each gate runs

| Stage | When | Budget | Why here |
|---|---|---|---|
| `pre-commit` | every commit, locally (`pre-commit install`) | seconds | cheap, deterministic, catch the mistake while the change is still in your head |
| `ci` | every pull request and push to `main` | minutes | needs the whole toolchain: compilers, `gdb`, Qt, the test suite |
| `scheduled` | weekly (`.github/workflows/scheduled-audit.yml`) | minutes | depends on the outside world (new vulnerabilities) and must not block an unrelated change |

The registry (`quality/registry.py`) is the only list of gates. The local runner, the
pre-commit hook and both workflows read it, so they cannot drift apart.

## The gates

| Gate | Rule | Stage | What it checks |
|---|---|---|---|
| `format` | Style | pre-commit, ci | black formatting of every Python directory (`--fix` repairs) |
| `import-order` | Style | pre-commit, ci | isort ordering (`--fix` repairs) |
| `layers` | Structure | pre-commit, ci | imports follow the layer table; no import cycles |
| `gate-scope` | Structure | pre-commit, ci | every tracked `.py` file is in a directory the gates check |
| `docs-links` | Structure | pre-commit, ci | Markdown links and `` `repo/paths` `` in documentation exist |
| `repo-hygiene` | Structure | pre-commit, ci | no submodule pointers, build outputs, unlisted binaries or huge files |
| `magic-values` | Named values | pre-commit, ci | inline numbers and strings repeated three times (ratchet) |
| `size` | Small and simple | pre-commit, ci | function length, parameters, complexity, file length (ratchet) |
| `suppressions-named` | Honest suppressions | pre-commit, ci | no bare `# noqa` / `# type: ignore` |
| `suppressions-budget` | Honest suppressions | pre-commit, ci | number of suppressions per file (ratchet) |
| `secrets` | Security | pre-commit, ci | tokens, private keys and hard-coded secrets |
| `duplication` | No duplication | ci | copy-pasted blocks across modules, pylint duplicate-code (ratchet) |
| `bandit` | Security | ci | medium and high severity security findings |
| `lint` | Clean code | ci | pylint |
| `types` | Typed | ci | mypy |
| `dead-code` | Minimal | ci | vulture, unused code at 90 % confidence |
| `tests` | Tested | ci | pytest with the coverage floor (95 %) |
| `dependency-audit` | Security | scheduled, advisory | known vulnerabilities in the declared dependencies |

## Why these gates, and why here

The project is a **layered, config-driven simulator with a plug-in board registry**, a
**Qt GUI**, two **debug protocol servers** and **C firmware** that is built and debugged
with real tools. The gates follow its actual risks:

* **Architecture erosion** is the main long-term risk of a plug-in design (a board that
  imports another board, the core that knows a chip). `layers` checks it statically
  and cheaply, on every commit. The board consistency tests
  (`tests/integration/test_vscode_and_board_consistency.py`) cover the other half: adding
  a board touches ten files.
* **Silent blind spots.** The GUI, tools and examples were outside every lint gate until
  `gate-scope` made "this directory is checked" a rule. New directories are caught the day
  they appear.
* **Copy-paste between boards** is the natural failure mode of "one more board". `duplication`
  keeps it from growing; the existing board duplication is the first item of the debt list.
* **Constants scattered through protocol code** (packet markers, register bits) make the
  debugger servers hard to change; `magic-values` stops new ones and `size` keeps the
  functions that use them small.
* **Generated and binary files** in a repository that builds firmware (`.elf`, `.map`,
  prebuilt `.bin`) are the usual accident; `repo-hygiene` found a broken submodule
  pointer on its first run.
* **Real behaviour** is what users see, so the `tests` gate includes integration tests that
  compile firmware with `-Werror` and drive a real `gdb` against the simulator; a coverage
  floor stops silent erosion.
* **Credentials**: CI uploads coverage with a project token, so `secrets` runs on every commit.

### Considered and not added

| Idea | Decision |
|---|---|
| Mutation testing | Too slow for the value; the negative tests of every gate and the integration tests already pin behaviour. Revisit for `simulator/core`. |
| `mypy --strict` everywhere | Too much churn for the Qt code; instead every new module must pass the normal mypy gate and new code is fully annotated (review). |
| Lock file with pinned dependencies | A simulator library should work with current releases; the scheduled audit watches for breakage. Revisit when a release process exists. |
| Commit-message / branch-name linting | No team process needs it yet. |
| Per-pull-request diff coverage | The global floor plus ratchets already prevent new untested debt; adds a tool and a failure mode. |
| Spell checking | Low value for code; documentation links are checked instead. |

## Ratchets

`magic-values`, `size`, `suppressions-budget` and `duplication` start from the debt that
existed when they were introduced (`quality/baselines/*.json`, one number per file or
function). The baseline can only shrink:

1. Pay debt (name a constant, split a function) — the gate still passes.
2. Lower the baseline: `python -m quality.run --only <gate> --write-baselines`. It refuses to
   raise a number; `--allow-growth` exists only to create a brand-new baseline.
3. CI runs with `--strict` (a baseline that could be lower fails, so paid debt cannot creep
   back) and `--growth-check --base origin/main` (a pull request may not raise any baseline).
4. When a baseline is empty, delete the file and the `ratchet=True` flag: the gate is now
   absolute.

## Adding a gate

1. `quality/gates/<name>.py`: a module docstring stating the rule and
   `check(tree) -> list[Finding]` (use `tree.python(...)`, `tree.read(...)`; give findings a
   `key` and `value` if the gate is a ratchet). External tools need no module — put the
   command in the registry.
2. One `Gate(...)` entry in `quality/registry.py`, with the stage it belongs to: *pre-commit* only if it
   takes a couple of seconds and has no false positives.
3. A heading for its rule in `CODING_GUIDELINES.md` and a row in the table above.
4. Tests in `tests/quality/`: one planted violation that fails and one clean tree that passes.
   `tests/quality/test_registry_and_runner.py` fails if any of these steps is missing.
