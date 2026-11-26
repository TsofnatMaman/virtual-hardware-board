"""Architecture: modules may only import from the layers below them, and never in a cycle.

Type-only imports (under `if TYPE_CHECKING:`) and lazy `importlib` calls are not
dependencies. To allow a new dependency, edit RULES below and say why in the comment.
"""

from __future__ import annotations

import ast

from quality.core import Finding, Tree
from quality.limits import PYTHON_DIRS

# (layer, module prefix); the longest matching prefix wins.
LAYERS = (
    ("shared", "simulator.core.exceptions"),
    ("shared", "simulator.core.gpio_enums"),
    ("sim-utils", "simulator.utils"),
    ("interfaces", "simulator.interfaces"),
    ("core", "simulator.core"),
    ("board:tm4c", "simulator.tm4c"),
    ("board:stm32", "simulator.stm32"),
    ("board:stm32c031", "simulator.stm32c031"),
    ("debug", "simulator.debug"),
    ("api", "simulator"),
    ("gui", "simulator_gui"),
    ("tools", "tools"),
    ("examples", "examples"),
    ("quality", "quality"),
    ("tests", "tests"),
)
_KERNEL = {"shared", "sim-utils", "interfaces"}
_BOARD = _KERNEL | {"core"}
RULES: dict[str, set[str] | None] = {  # layer -> layers it may import (None = anything)
    "shared": set(),
    "sim-utils": {"shared"},
    "interfaces": {"shared", "sim-utils"},
    "core": _KERNEL,
    "board:tm4c": _BOARD,
    "board:stm32": _BOARD,
    "board:stm32c031": _BOARD
    | {"board:stm32"},  # a family variant reuses its base family
    "debug": _BOARD | {"api"},
    "api": None,
    "gui": _BOARD | {"api", "debug"},
    "tools": _BOARD | {"api", "debug", "gui"},
    "examples": {"api", "debug", "gui"},
    "quality": set(),
    "tests": None,
}


def layer_of(module: str) -> str | None:
    best = max(
        (p for _, p in LAYERS if module == p or module.startswith(p + ".")),
        key=len,
        default=None,
    )
    return next((name for name, p in LAYERS if p == best), None)


def module_name(path: str) -> str:
    parts = path.removesuffix(".py").split("/")
    return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)


def _type_checking_nodes(tree: ast.Module) -> set[int]:
    """Ids of every node inside an `if TYPE_CHECKING:` block."""
    guards = [
        g
        for g in ast.walk(tree)
        if isinstance(g, ast.If) and "TYPE_CHECKING" in ast.unparse(g.test)
    ]
    return {id(n) for guard in guards for n in ast.walk(guard)}


def _absolute(node: ast.ImportFrom, module: str, is_package: bool) -> str:
    """The module a `from ... import` refers to, resolving relative imports."""
    if not node.level:
        return node.module or ""
    anchor = module.split(".") if is_package else module.split(".")[:-1]
    kept = anchor[: len(anchor) - node.level + 1]
    return ".".join(kept + ([node.module] if node.module else []))


def _imported(node: ast.AST, module: str, is_package: bool) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        base = _absolute(node, module, is_package)
        return [f"{base}.{alias.name}" if base else alias.name for alias in node.names]
    return []


def runtime_imports(
    tree: ast.Module, module: str, is_package: bool
) -> list[tuple[int, str]]:
    """(line, imported module) for imports that execute at runtime."""
    skipped = _type_checking_nodes(tree)
    return [
        (node.lineno, target)
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom)) and id(node) not in skipped
        for target in _imported(node, module, is_package)
    ]


def graph(tree: Tree) -> dict[str, list[tuple[str, int, str]]]:
    """module -> [(imported module, line, path)] restricted to this repo's own packages."""
    edges: dict[str, list[tuple[str, int, str]]] = {}
    for path in tree.python(PYTHON_DIRS):
        module = module_name(path)
        imports = runtime_imports(
            tree.parse(path), module, path.endswith("__init__.py")
        )
        edges[module] = [(m, line, path) for line, m in imports if layer_of(m)]
    return edges


def cycles(edges: dict[str, list[tuple[str, int, str]]]) -> list[list[str]]:
    """Strongly connected components with more than one module (Tarjan)."""
    index: dict[str, int] = {}
    low: dict[str, int] = {}
    stack: list[str] = []
    found: list[list[str]] = []

    def visit(node: str) -> None:
        index[node] = low[node] = len(index)
        stack.append(node)
        for target in {
            t for t, _, _ in edges.get(node, ()) if t in edges and t != node
        }:
            if target not in index:
                visit(target)
                low[node] = min(low[node], low[target])
            elif target in stack:
                low[node] = min(low[node], index[target])
        if low[node] == index[node]:
            group = [stack.pop()]
            while group[-1] != node:
                group.append(stack.pop())
            if len(group) > 1:
                found.append(sorted(group))

    for module in edges:
        if module not in index:
            visit(module)
    return found


def check(tree: Tree) -> list[Finding]:
    edges = graph(tree)
    findings = []
    for module, imports in edges.items():
        src = layer_of(module)
        allowed = RULES.get(src or "", set())
        for target, line, path in imports:
            dst = layer_of(target)
            if allowed is not None and dst != src and dst not in allowed:
                findings.append(
                    Finding(
                        path,
                        line,
                        f"layer '{src}' must not import '{dst}' ({target})",
                        key=f"{src}->{dst}",
                    )
                )
    findings += [
        Finding(
            group[0].replace(".", "/") + ".py",
            1,
            "import cycle: " + " <-> ".join(group),
        )
        for group in cycles(edges)
    ]
    return findings
