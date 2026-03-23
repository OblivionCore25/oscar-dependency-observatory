# OSCAR Method Observatory — Implementation Plan

**Version:** 1.0
**Date:** March 22, 2026
**Author:** Fabian Gonzalez
**Based on:** Method-Level Observatory Analysis Tool — Deep Research Report v1.0

---

## Overview

This document is the concrete engineering plan to build the **OSCAR Method Observatory** — a method-level static analysis module that extends the existing OSCAR package dependency system into the internal structure of Python codebases.

The plan covers three sequential phases:

- **Phase 1 (MVP):** AST-based call graph, basic metrics, JSON storage, FastAPI integration — approximately 2–3 weeks
- **Phase 2 (Accuracy):** Cross-module resolution, type annotation exploitation, advanced metrics, SQLite — approximately 3–4 weeks
- **Phase 3 (Hybrid):** Runtime tracing, temporal snapshots, diff analysis — approximately 4–6 weeks

Each phase is independently shippable and builds on the previous one without requiring rewrites.

---

## Part 1 — Project Structure

The method observatory lives as a new top-level module inside the existing OSCAR `backend/` directory. It does not require a separate service in Phase 1.

```
backend/
├── app/
│   ├── main.py                        # existing — add method_observatory router here
│   ├── config.py                      # existing — add METHOD_DATA_DIRECTORY setting
│   │
│   ├── method_observatory/            # ← new module, entire implementation lives here
│   │   ├── __init__.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── method_node.py         # MethodNode, ClassNode, ModuleNode Pydantic models
│   │   │   ├── call_edge.py           # CallEdge, ImportEdge, InheritanceEdge Pydantic models
│   │   │   └── analysis_result.py    # AnalysisResult, AnalysisSummary Pydantic models
│   │   │
│   │   ├── ingestion/
│   │   │   ├── __init__.py
│   │   │   ├── project_scanner.py     # Walk directory, discover .py files, filter noise
│   │   │   └── source_reader.py       # Read file contents, handle encoding, track paths
│   │   │
│   │   ├── analysis/
│   │   │   ├── __init__.py
│   │   │   ├── ast_visitor.py         # Core AST NodeVisitor — extracts all entities
│   │   │   ├── scope_tracker.py       # Symbol table and scope management during AST walk
│   │   │   ├── call_resolver.py       # Resolves call targets: direct, self, import-based
│   │   │   ├── complexity.py          # Cyclomatic complexity calculator
│   │   │   └── graph_builder.py       # Assembles NetworkX DiGraph from extracted entities
│   │   │
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   ├── basic_metrics.py       # Fan-in, fan-out, bottleneck, orphan, leaf detection
│   │   │   └── graph_metrics.py       # Betweenness, PageRank, communities (Phase 2+)
│   │   │
│   │   ├── storage/
│   │   │   ├── __init__.py
│   │   │   └── json_storage.py        # Load/save analysis results as JSON (MVP pattern)
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── router.py              # FastAPI router — all /methods/* endpoints
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       └── analysis_service.py    # Orchestrates ingestion → analysis → storage pipeline
│   │
│   └── ... (existing OSCAR modules unchanged)
│
data/
├── npm/                               # existing OSCAR data
├── pypi/                              # existing OSCAR data
└── method_observatory/                # ← new data directory
    └── {project_slug}/
        ├── methods.json               # all MethodNode records
        ├── classes.json               # all ClassNode records
        ├── modules.json               # all ModuleNode records
        ├── calls.json                 # all CallEdge records
        ├── imports.json               # all ImportEdge records
        ├── metrics.json               # per-method metric records
        └── analysis_meta.json         # analysis metadata (timestamp, file count, LOC, etc.)
```

---

## Part 2 — Data Models

All models use Pydantic v2. They mirror OSCAR's existing `Package`, `Version`, and `DependencyEdge` patterns in naming and structure.

### 2.1 `models/method_node.py`

```python
from __future__ import annotations
from enum import Enum
from pydantic import BaseModel, Field


class MethodKind(str, Enum):
    FUNCTION = "function"          # module-level def
    METHOD = "method"              # instance method
    CLASS_METHOD = "classmethod"   # @classmethod
    STATIC_METHOD = "staticmethod" # @staticmethod
    PROPERTY = "property"          # @property
    ASYNC_FUNCTION = "async_function"
    ASYNC_METHOD = "async_method"
    LAMBDA = "lambda"              # inline lambda (limited support)


class MethodNode(BaseModel):
    # Identity
    id: str = Field(
        description="Stable unique identifier. Format: 'module.path:ClassName.method' "
                    "or 'module.path:function_name'. Example: 'app.services.user:UserService.get_user'"
    )
    name: str                      # Short name: "get_user"
    qualified_name: str            # Full name: "UserService.get_user"
    kind: MethodKind

    # Location
    file_path: str                 # Relative to project root: "app/services/user.py"
    line_start: int
    line_end: int
    module: str                    # Dotted module path: "app.services.user"
    class_name: str | None = None  # Enclosing class name, if method

    # Signature
    parameters: list[str] = []     # Parameter names (excluding self/cls)
    return_annotation: str | None = None
    decorators: list[str] = []     # Decorator names as strings
    is_async: bool = False
    docstring: str | None = None   # First line only

    # Size
    loc: int = 0                   # Lines of code in body (non-blank, non-comment)
    complexity: int = 1            # Cyclomatic complexity (min 1)

    class Config:
        use_enum_values = True


class ClassNode(BaseModel):
    id: str                        # "module.path:ClassName"
    name: str
    module: str
    file_path: str
    line_start: int
    line_end: int
    bases: list[str] = []          # Parent class names as strings
    decorator_list: list[str] = []
    method_ids: list[str] = []     # IDs of all methods in this class
    docstring: str | None = None


class ModuleNode(BaseModel):
    id: str                        # Dotted path: "app.services.user"
    file_path: str                 # "app/services/user.py"
    package: str | None = None     # Immediate package: "app.services"
    class_ids: list[str] = []
    function_ids: list[str] = []   # Top-level (non-method) function IDs
    star_imports: list[str] = []   # Modules imported with *; signals analysis gap
```

### 2.2 `models/call_edge.py`

```python
from enum import Enum
from pydantic import BaseModel, Field


class CallType(str, Enum):
    DIRECT = "direct"              # func() — resolved to known definition
    SELF_CALL = "self_call"        # self.method() — resolved within same class
    SUPER_CALL = "super_call"      # super().method()
    CONSTRUCTOR = "constructor"    # ClassName() — resolved to __init__
    MODULE_CALL = "module_call"    # module.func() — resolved via import
    NAME_MATCH = "name_match"      # obj.method() — target matched by name only, type unknown
    UNRESOLVED = "unresolved"      # call target could not be determined at all


class CallEdge(BaseModel):
    source_id: str                 # Caller method ID
    target_id: str                 # Callee method ID (or "external:module.func" for unknowns)
    call_type: CallType
    line: int                      # Line number of call site in source file
    confidence: float = Field(
        ge=0.0, le=1.0,
        description="1.0=statically certain, 0.7=self-call, 0.5=name-matched, 0.0=unresolved"
    )
    is_conditional: bool = False   # Call site is inside an if/try/except block
    argument_count: int = 0

    class Config:
        use_enum_values = True


class ImportEdge(BaseModel):
    source_module: str             # Importing module ID
    target_module: str             # Imported module ID (or best-effort for external)
    imported_names: list[str]      # Specific names, or ["*"] for star import
    alias: str | None = None       # "import numpy as np" → alias="np"
    is_relative: bool = False
    is_external: bool = False      # True if target is a third-party/stdlib package


class InheritanceEdge(BaseModel):
    child_class_id: str
    parent_class_name: str         # String name (may not resolve to a ClassNode if external)
    parent_class_id: str | None    # Resolved ID if parent is within project
    mro_position: int = 0
```

### 2.3 `models/analysis_result.py`

```python
from datetime import datetime
from pydantic import BaseModel
from .method_node import MethodNode, ClassNode, ModuleNode
from .call_edge import CallEdge, ImportEdge, InheritanceEdge


class MethodMetrics(BaseModel):
    method_id: str
    fan_in: int = 0                # Callers within project
    fan_out: int = 0               # Callees within project
    fan_out_external: int = 0      # Calls to external code
    bottleneck_score: float = 0.0  # fan_in × fan_out (or fan_in if fan_out=0)
    is_leaf: bool = False          # fan_out == 0
    is_orphan: bool = False        # fan_in == 0 and not an entry point
    complexity: int = 1
    loc: int = 0
    # Phase 2+ fields (None until computed)
    betweenness_centrality: float | None = None
    pagerank: float | None = None
    community_id: int | None = None
    blast_radius: int | None = None


class AnalysisMeta(BaseModel):
    project_slug: str
    project_path: str
    analyzed_at: datetime
    oscar_version: str = "0.1.0"
    file_count: int
    total_loc: int
    method_count: int
    class_count: int
    module_count: int
    edge_count: int
    unresolved_call_count: int
    analysis_approach: str = "ast_static"
    # Completeness estimate: resolved_calls / total_calls
    resolution_rate: float = 0.0


class AnalysisResult(BaseModel):
    meta: AnalysisMeta
    methods: list[MethodNode]
    classes: list[ClassNode]
    modules: list[ModuleNode]
    calls: list[CallEdge]
    imports: list[ImportEdge]
    inheritance: list[InheritanceEdge]
    metrics: list[MethodMetrics]
```

---

## Part 3 — Phase 1 Implementation (MVP)

### 3.1 Ingestion Layer

#### `ingestion/project_scanner.py`

Responsibility: Given a root directory path, discover all Python source files that belong to the project (excluding virtual environments, test directories if requested, `__pycache__`, etc.).

```python
import os
from dataclasses import dataclass, field
from pathlib import Path


# Directories to always skip
DEFAULT_EXCLUDE_DIRS = {
    "__pycache__", ".venv", "venv", "env", ".env",
    "node_modules", ".git", ".tox", "dist", "build",
    "*.egg-info", ".mypy_cache", ".pytest_cache",
}

@dataclass
class ScanConfig:
    root_path: Path
    exclude_dirs: set[str] = field(default_factory=lambda: DEFAULT_EXCLUDE_DIRS.copy())
    exclude_tests: bool = False        # If True, skip test_*.py and tests/ directories
    max_file_size_kb: int = 500        # Skip files larger than this (likely generated code)


@dataclass
class SourceFile:
    path: Path
    relative_path: str                 # Relative to project root
    module_path: str                   # Dotted module path: "app.services.user"
    size_bytes: int


def scan_project(config: ScanConfig) -> list[SourceFile]:
    """Walk the project directory and return all .py files to analyze."""
    ...

def path_to_module(file_path: Path, root: Path) -> str:
    """Convert a file path to a dotted Python module path.

    Example: /project/app/services/user.py → app.services.user
    Handles __init__.py → parent package name.
    """
    ...
```

**Key logic for `path_to_module`:** Strip the root prefix, replace `/` with `.`, remove `.py`. If the file is `__init__.py`, use the parent directory name as the module (e.g., `app/services/__init__.py` → `app.services`).

#### `ingestion/source_reader.py`

```python
@dataclass
class ParsedSource:
    source_file: SourceFile
    source_code: str
    ast_tree: ast.Module | None        # None if parsing failed
    parse_error: str | None = None     # Error message if parsing failed


def read_and_parse(source_file: SourceFile) -> ParsedSource:
    """Read source file and parse to AST. Never raises — errors are captured."""
    ...
```

**Key detail:** Always wrap `ast.parse()` in a try/except. Store the error and continue analysis of other files. A project with one broken file should not fail the entire analysis.

---

### 3.2 Analysis Layer

#### `analysis/scope_tracker.py`

The scope tracker maintains a stack of scopes as the AST visitor descends through the tree. Each scope records names defined at that level, enabling resolution of which function `func()` refers to.

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Scope:
    kind: str                          # "module" | "class" | "function"
    name: str                          # Name of the scope owner
    bindings: dict[str, str] = field(default_factory=dict)
    # bindings: local name → resolved qualified name
    # e.g., {"np": "numpy", "UserService": "app.services.user:UserService"}


class ScopeTracker:
    def __init__(self):
        self._stack: list[Scope] = []

    def push(self, kind: str, name: str) -> None:
        """Enter a new scope (module, class, or function)."""
        ...

    def pop(self) -> Scope:
        """Exit the current scope."""
        ...

    def current(self) -> Scope | None:
        """Return the innermost scope."""
        ...

    def current_class(self) -> str | None:
        """Return the name of the enclosing class, if any."""
        ...

    def current_function(self) -> str | None:
        """Return the name of the enclosing function, if any."""
        ...

    def bind(self, local_name: str, resolved_name: str) -> None:
        """Record a name binding in the current scope."""
        ...

    def resolve(self, name: str) -> str | None:
        """Look up a name from innermost to outermost scope."""
        ...

    def record_import(self, local_name: str, module: str, original_name: str | None = None) -> None:
        """Record an import alias: 'import numpy as np' or 'from mod import func'."""
        ...
```

#### `analysis/ast_visitor.py`

This is the core of the entire system. A single-pass `ast.NodeVisitor` that extracts all entities and call sites from one parsed file.

```python
import ast
from dataclasses import dataclass, field
from ..models.method_node import MethodNode, ClassNode, ModuleNode, MethodKind
from ..models.call_edge import CallEdge, ImportEdge, InheritanceEdge, CallType
from .scope_tracker import ScopeTracker
from .complexity import compute_complexity


@dataclass
class FileExtractionResult:
    """All entities extracted from a single source file."""
    module: ModuleNode
    methods: list[MethodNode] = field(default_factory=list)
    classes: list[ClassNode] = field(default_factory=list)
    raw_calls: list[dict] = field(default_factory=list)    # Pre-resolution call data
    imports: list[ImportEdge] = field(default_factory=list)
    inheritance: list[InheritanceEdge] = field(default_factory=list)


class ASTVisitor(ast.NodeVisitor):
    """
    Single-pass visitor over one Python module's AST.
    Extracts: method definitions, class definitions, call sites, imports.
    Does NOT resolve cross-file calls — that is done in CallResolver.
    """

    def __init__(self, module_id: str, file_path: str, relative_path: str):
        self.module_id = module_id
        self.file_path = file_path
        self.relative_path = relative_path
        self.scope = ScopeTracker()
        self.result = FileExtractionResult(
            module=ModuleNode(id=module_id, file_path=relative_path)
        )
        # Stack of class contexts for nested class support
        self._class_stack: list[str] = []
        # Stack of function contexts (qualified names)
        self._function_stack: list[str] = []

    # ------------------------------------------------------------------ #
    #  Entry Point                                                         #
    # ------------------------------------------------------------------ #

    def extract(self, tree: ast.Module) -> FileExtractionResult:
        self.scope.push("module", self.module_id)
        self.visit(tree)
        self.scope.pop()
        return self.result

    # ------------------------------------------------------------------ #
    #  Import Handling                                                     #
    # ------------------------------------------------------------------ #

    def visit_Import(self, node: ast.Import) -> None:
        """Handle: import foo, import foo.bar as baz"""
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            self.scope.record_import(local_name, alias.name)
            self.result.imports.append(ImportEdge(
                source_module=self.module_id,
                target_module=alias.name,
                imported_names=[alias.name],
                alias=alias.asname,
                is_external=self._is_external_module(alias.name),
            ))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Handle: from foo import bar, from . import baz"""
        module = node.module or ""
        is_relative = node.level > 0
        imported_names = [alias.name for alias in node.names]

        # Record each imported name in scope
        for alias in node.names:
            local_name = alias.asname or alias.name
            full_qualified = f"{module}.{alias.name}" if module else alias.name
            self.scope.record_import(local_name, full_qualified)

        is_star = imported_names == ["*"]
        if is_star:
            self.result.module.star_imports.append(module)

        self.result.imports.append(ImportEdge(
            source_module=self.module_id,
            target_module=module,
            imported_names=imported_names,
            is_relative=is_relative,
            is_external=self._is_external_module(module),
        ))
        self.generic_visit(node)

    # ------------------------------------------------------------------ #
    #  Class Definitions                                                   #
    # ------------------------------------------------------------------ #

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_id = f"{self.module_id}:{node.name}"
        decorators = [self._decorator_name(d) for d in node.decorator_list]

        # Extract base class names (best-effort string representation)
        bases = [ast.unparse(b) for b in node.bases]

        class_node = ClassNode(
            id=class_id,
            name=node.name,
            module=self.module_id,
            file_path=self.relative_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            bases=bases,
            decorator_list=decorators,
            docstring=self._extract_docstring(node),
        )
        self.result.classes.append(class_node)
        self.result.module.class_ids.append(class_id)

        # Add inheritance edges for each base
        for base_name in bases:
            self.result.inheritance.append(InheritanceEdge(
                child_class_id=class_id,
                parent_class_name=base_name,
                parent_class_id=None,   # resolved later in Phase 2
            ))

        # Bind the class name in the current module scope
        self.scope.bind(node.name, class_id)

        # Descend into class body with class context
        self._class_stack.append(node.name)
        self.scope.push("class", node.name)
        self.generic_visit(node)
        self.scope.pop()
        self._class_stack.pop()

        # Populate method_ids on the class node
        class_node.method_ids = [
            m.id for m in self.result.methods
            if m.class_name == node.name and m.module == self.module_id
        ]

    # ------------------------------------------------------------------ #
    #  Function / Method Definitions                                       #
    # ------------------------------------------------------------------ #

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._handle_function(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._handle_function(node, is_async=True)

    def _handle_function(self, node, is_async: bool) -> None:
        enclosing_class = self._class_stack[-1] if self._class_stack else None

        # Compute qualified name and ID
        if enclosing_class:
            qualified_name = f"{enclosing_class}.{node.name}"
            method_id = f"{self.module_id}:{qualified_name}"
        else:
            qualified_name = node.name
            method_id = f"{self.module_id}:{node.name}"

        decorators = [self._decorator_name(d) for d in node.decorator_list]
        kind = self._determine_kind(decorators, enclosing_class, is_async)

        # Extract parameters (skip self/cls)
        params = self._extract_params(node.args, kind)

        # Return annotation
        return_annotation = None
        if node.returns:
            try:
                return_annotation = ast.unparse(node.returns)
            except Exception:
                pass

        # Compute complexity and LOC
        complexity = compute_complexity(node)
        loc = self._count_loc(node)

        method_node = MethodNode(
            id=method_id,
            name=node.name,
            qualified_name=qualified_name,
            kind=kind,
            file_path=self.relative_path,
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            module=self.module_id,
            class_name=enclosing_class,
            parameters=params,
            return_annotation=return_annotation,
            decorators=decorators,
            is_async=is_async,
            docstring=self._extract_docstring(node),
            loc=loc,
            complexity=complexity,
        )
        self.result.methods.append(method_node)

        # Bind in scope
        self.scope.bind(node.name, method_id)
        if not enclosing_class:
            self.result.module.function_ids.append(method_id)

        # Descend into function body (will encounter Call nodes)
        self._function_stack.append(method_id)
        self.scope.push("function", method_id)
        self.generic_visit(node)
        self.scope.pop()
        self._function_stack.pop()

    # ------------------------------------------------------------------ #
    #  Call Sites                                                          #
    # ------------------------------------------------------------------ #

    def visit_Call(self, node: ast.Call) -> None:
        """Record every call site encountered. Resolution happens later."""
        if not self._function_stack:
            # Top-level call (module initialization); record as module-level
            caller_id = f"{self.module_id}:<module>"
        else:
            caller_id = self._function_stack[-1]

        raw_call = {
            "caller_id": caller_id,
            "line": node.lineno,
            "argument_count": len(node.args) + len(node.keywords),
            "call_expr_type": None,   # "name", "attribute", "other"
            "call_name": None,        # For Name calls: the function name
            "attr_name": None,        # For Attribute calls: the method name
            "receiver_name": None,    # For Attribute calls: the receiver name
            "is_conditional": self._is_in_conditional(),
        }

        func = node.func
        if isinstance(func, ast.Name):
            raw_call["call_expr_type"] = "name"
            raw_call["call_name"] = func.id
        elif isinstance(func, ast.Attribute):
            raw_call["call_expr_type"] = "attribute"
            raw_call["attr_name"] = func.attr
            # Best-effort receiver name extraction
            raw_call["receiver_name"] = self._extract_receiver_name(func.value)
        else:
            raw_call["call_expr_type"] = "other"  # indirect call, lambda, etc.

        self.result.raw_calls.append(raw_call)
        self.generic_visit(node)

    # ------------------------------------------------------------------ #
    #  Helper Methods                                                      #
    # ------------------------------------------------------------------ #

    def _determine_kind(self, decorators: list[str], class_name: str | None, is_async: bool) -> MethodKind:
        if "classmethod" in decorators:
            return MethodKind.CLASS_METHOD
        if "staticmethod" in decorators:
            return MethodKind.STATIC_METHOD
        if "property" in decorators:
            return MethodKind.PROPERTY
        if class_name:
            return MethodKind.ASYNC_METHOD if is_async else MethodKind.METHOD
        return MethodKind.ASYNC_FUNCTION if is_async else MethodKind.FUNCTION

    def _extract_params(self, args: ast.arguments, kind: MethodKind) -> list[str]:
        all_params = [a.arg for a in args.posonlyargs + args.args + args.kwonlyargs]
        if args.vararg:
            all_params.append(f"*{args.vararg.arg}")
        if args.kwarg:
            all_params.append(f"**{args.kwarg.arg}")
        # Remove self / cls
        if kind in (MethodKind.METHOD, MethodKind.ASYNC_METHOD, MethodKind.PROPERTY):
            return all_params[1:]   # drop self
        if kind == MethodKind.CLASS_METHOD:
            return all_params[1:]   # drop cls
        return all_params

    def _extract_docstring(self, node) -> str | None:
        if (node.body and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)):
            first_line = node.body[0].value.value.strip().split("\n")[0]
            return first_line[:200]  # cap at 200 chars
        return None

    def _decorator_name(self, node: ast.expr) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return "<unknown>"

    def _extract_receiver_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return f"{self._extract_receiver_name(node.value)}.{node.attr}"
        return None

    def _is_external_module(self, module: str) -> bool:
        # Heuristic: if the module doesn't start with a local package name, treat as external.
        # This is refined by the CallResolver once the full project module list is known.
        STDLIB_PREFIXES = {"os", "sys", "re", "ast", "json", "pathlib", "typing",
                           "collections", "functools", "itertools", "datetime",
                           "logging", "unittest", "abc", "enum", "dataclasses"}
        root = module.split(".")[0]
        return root in STDLIB_PREFIXES  # Phase 1: stdlib only; Phase 2: all non-project

    def _count_loc(self, node) -> int:
        """Count non-blank, non-comment lines in function body."""
        if not hasattr(node, 'end_lineno') or node.end_lineno is None:
            return 0
        return max(0, (node.end_lineno - node.lineno) - 1)

    def _is_in_conditional(self) -> bool:
        # Simplified: always False in Phase 1.
        # Phase 2: track If/Try/While stack during traversal.
        return False
```

#### `analysis/complexity.py`

```python
import ast


# AST node types that each add 1 to cyclomatic complexity
COMPLEXITY_INCREMENTORS = (
    ast.If, ast.While, ast.For, ast.AsyncFor,
    ast.ExceptHandler, ast.With, ast.AsyncWith,
    ast.Assert, ast.comprehension,
    ast.BoolOp,   # each and/or in a BoolOp adds branches
)


def compute_complexity(func_node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """
    Compute McCabe cyclomatic complexity for a single function.

    Formula: 1 + number of branching points in the function's control flow.
    Minimum value is always 1.

    Notes:
    - Each 'if', 'while', 'for', 'except', 'with' = +1
    - Each 'and'/'or' in a BoolOp = +(num_values - 1)
    - Nested functions are counted separately; their internal complexity
      is NOT included in the enclosing function's score.
    """
    complexity = 1
    for node in ast.walk(func_node):
        # Skip nested function bodies — they are analyzed separately
        if node is not func_node and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if isinstance(node, COMPLEXITY_INCREMENTORS):
            if isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
            else:
                complexity += 1
    return complexity
```

#### `analysis/call_resolver.py`

After all files are parsed, the call resolver performs cross-file call resolution using the collected scope information and import tables.

```python
from ..models.call_edge import CallEdge, CallType
from ..models.method_node import MethodNode, ClassNode


class CallResolver:
    """
    Resolves raw call site records (collected during AST visit) into
    typed CallEdge objects with confidence scores.

    Works across the entire project — receives all methods and modules
    and builds a lookup index before resolving.
    """

    def __init__(
        self,
        all_methods: list[MethodNode],
        all_classes: list[ClassNode],
        import_map: dict[str, dict[str, str]],
        # import_map[module_id][local_name] = resolved_qualified_name
    ):
        # Build fast lookup indexes
        self._method_by_id: dict[str, MethodNode] = {m.id: m for m in all_methods}
        # Index methods by their short name for name-matching fallback
        self._methods_by_name: dict[str, list[MethodNode]] = {}
        for m in all_methods:
            self._methods_by_name.setdefault(m.name, []).append(m)
        self._class_by_id: dict[str, ClassNode] = {c.id: c for c in all_classes}
        self._import_map = import_map

    def resolve(self, raw_call: dict) -> CallEdge | None:
        """
        Attempt to resolve one raw call record into a CallEdge.
        Returns None if the call is to an external (out-of-project) function
        and we choose to drop it rather than create a placeholder.
        """
        caller_id: str = raw_call["caller_id"]
        expr_type: str = raw_call["call_expr_type"]
        line: int = raw_call["line"]
        arg_count: int = raw_call["argument_count"]
        is_conditional: bool = raw_call["is_conditional"]

        if expr_type == "name":
            return self._resolve_name_call(raw_call, caller_id, line, arg_count, is_conditional)
        elif expr_type == "attribute":
            return self._resolve_attribute_call(raw_call, caller_id, line, arg_count, is_conditional)
        else:
            # "other" — indirect call, cannot resolve
            return CallEdge(
                source_id=caller_id,
                target_id="unresolved:indirect",
                call_type=CallType.UNRESOLVED,
                line=line,
                confidence=0.0,
                argument_count=arg_count,
            )

    def _resolve_name_call(self, raw_call, caller_id, line, arg_count, is_conditional) -> CallEdge | None:
        """
        Resolve: func() or imported_func()

        Resolution order:
        1. Look up name in import_map for caller's module → may resolve to a project function
        2. Look up name directly as a method in the same module
        3. Name-match fallback: if unique match, use it with medium confidence
        4. Unresolved
        """
        name: str = raw_call["call_name"]
        caller_module = caller_id.rsplit(":", 1)[0] if ":" in caller_id else caller_id

        # Step 1: Check if imported from another module
        module_imports = self._import_map.get(caller_module, {})
        if name in module_imports:
            resolved = module_imports[name]
            if resolved in self._method_by_id:
                return CallEdge(
                    source_id=caller_id, target_id=resolved,
                    call_type=CallType.MODULE_CALL, line=line,
                    confidence=0.9, argument_count=arg_count,
                    is_conditional=is_conditional,
                )

        # Step 2: Same module direct lookup
        same_module_id = f"{caller_module}:{name}"
        if same_module_id in self._method_by_id:
            return CallEdge(
                source_id=caller_id, target_id=same_module_id,
                call_type=CallType.DIRECT, line=line,
                confidence=1.0, argument_count=arg_count,
                is_conditional=is_conditional,
            )

        # Step 3: Name-match across project
        candidates = self._methods_by_name.get(name, [])
        if len(candidates) == 1:
            return CallEdge(
                source_id=caller_id, target_id=candidates[0].id,
                call_type=CallType.NAME_MATCH, line=line,
                confidence=0.5, argument_count=arg_count,
                is_conditional=is_conditional,
            )

        # Step 4: Unresolved
        return CallEdge(
            source_id=caller_id, target_id=f"unresolved:{name}",
            call_type=CallType.UNRESOLVED, line=line,
            confidence=0.0, argument_count=arg_count,
        )

    def _resolve_attribute_call(self, raw_call, caller_id, line, arg_count, is_conditional) -> CallEdge | None:
        """
        Resolve: obj.method() or self.method() or module.func()

        Resolution order:
        1. self.method() → look up in the caller's own class
        2. super().method() → look up in parent class
        3. ClassName.method() — receiver is a known class name → constructor or classmethod
        4. module.func() — receiver matches an import alias → look up in that module
        5. Name-match fallback on method name alone
        6. Unresolved
        """
        attr_name: str = raw_call["attr_name"]
        receiver: str | None = raw_call["receiver_name"]

        caller_module = caller_id.rsplit(":", 1)[0] if ":" in caller_id else caller_id
        caller_method = self._method_by_id.get(caller_id)
        caller_class = caller_method.class_name if caller_method else None

        # Step 1: self.method() resolution
        if receiver == "self" and caller_class:
            target_id = f"{caller_module}:{caller_class}.{attr_name}"
            if target_id in self._method_by_id:
                return CallEdge(
                    source_id=caller_id, target_id=target_id,
                    call_type=CallType.SELF_CALL, line=line,
                    confidence=0.95, argument_count=arg_count,
                    is_conditional=is_conditional,
                )

        # Step 2: super().method()
        if receiver == "super()" and caller_class:
            # Find parent class and look up method there
            # (full MRO resolution deferred to Phase 2)
            pass

        # Step 3: ClassName() — constructor call
        # receiver is None for Name calls but attr_name may be "__init__"
        # If receiver is a known class name, resolve to __init__
        if receiver:
            class_id = f"{caller_module}:{receiver}"
            if class_id in self._class_by_id:
                init_id = f"{class_id}.__init__"
                target_id = init_id if init_id in self._method_by_id else class_id
                return CallEdge(
                    source_id=caller_id, target_id=target_id,
                    call_type=CallType.CONSTRUCTOR, line=line,
                    confidence=0.9, argument_count=arg_count,
                    is_conditional=is_conditional,
                )

        # Step 4: module.func() via import alias
        if receiver:
            module_imports = self._import_map.get(caller_module, {})
            if receiver in module_imports:
                target_module = module_imports[receiver]
                target_id = f"{target_module}:{attr_name}"
                if target_id in self._method_by_id:
                    return CallEdge(
                        source_id=caller_id, target_id=target_id,
                        call_type=CallType.MODULE_CALL, line=line,
                        confidence=0.85, argument_count=arg_count,
                        is_conditional=is_conditional,
                    )

        # Step 5: Name-match on method name
        candidates = self._methods_by_name.get(attr_name, [])
        if len(candidates) == 1:
            return CallEdge(
                source_id=caller_id, target_id=candidates[0].id,
                call_type=CallType.NAME_MATCH, line=line,
                confidence=0.4, argument_count=arg_count,
                is_conditional=is_conditional,
            )

        # Step 6: Unresolved
        return CallEdge(
            source_id=caller_id,
            target_id=f"unresolved:{receiver}.{attr_name}" if receiver else f"unresolved:{attr_name}",
            call_type=CallType.UNRESOLVED, line=line,
            confidence=0.0, argument_count=arg_count,
        )
```

#### `analysis/graph_builder.py`

```python
import networkx as nx
from ..models.method_node import MethodNode
from ..models.call_edge import CallEdge, CallType


class GraphBuilder:
    """
    Assembles a NetworkX DiGraph from the resolved call edges and method nodes.
    The graph is the in-memory representation used for all metric computation.
    """

    def build(
        self,
        methods: list[MethodNode],
        calls: list[CallEdge],
    ) -> nx.DiGraph:
        G = nx.DiGraph()

        # Add all method nodes with their attributes as node data
        for method in methods:
            G.add_node(method.id, **{
                "name": method.name,
                "module": method.module,
                "class_name": method.class_name,
                "kind": method.kind,
                "file_path": method.file_path,
                "line_start": method.line_start,
                "complexity": method.complexity,
                "loc": method.loc,
            })

        # Add edges from resolved calls
        # Only include edges where both source and target are in the project
        # (i.e., both are in the method node set — skip "unresolved:*" targets)
        project_ids = {m.id for m in methods}
        for call in calls:
            if call.target_id in project_ids and call.source_id in project_ids:
                # If a parallel edge already exists (same source+target, different call site),
                # keep the one with higher confidence; this is a simple graph (not multigraph)
                if G.has_edge(call.source_id, call.target_id):
                    existing = G[call.source_id][call.target_id]
                    if call.confidence > existing.get("confidence", 0):
                        G[call.source_id][call.target_id].update({
                            "call_type": call.call_type,
                            "confidence": call.confidence,
                        })
                else:
                    G.add_edge(call.source_id, call.target_id, **{
                        "call_type": call.call_type,
                        "confidence": call.confidence,
                        "line": call.line,
                    })

        return G
```

---

### 3.3 Metrics Layer

#### `metrics/basic_metrics.py`

```python
import networkx as nx
from ..models.analysis_result import MethodMetrics
from ..models.method_node import MethodNode


# Methods matching these names are treated as "entry points" (not orphans)
ENTRY_POINT_NAMES = {
    "main", "__main__", "__init__", "__new__", "__call__",
    "__enter__", "__exit__", "__iter__", "__next__",
    # FastAPI/Flask route handlers will be detected by decorator in Phase 2
}


def compute_basic_metrics(
    graph: nx.DiGraph,
    methods: list[MethodNode],
    all_calls_including_external: list,  # includes unresolved calls per method
) -> list[MethodMetrics]:
    """
    Compute fan-in, fan-out, bottleneck score, leaf, and orphan flags
    for every method node in the graph.
    """
    # Count external calls per method (calls that left the project boundary)
    external_count: dict[str, int] = {}
    for call in all_calls_including_external:
        if call.target_id.startswith("unresolved:") or call.call_type == "unresolved":
            external_count[call.source_id] = external_count.get(call.source_id, 0) + 1

    results = []
    for method in methods:
        node_id = method.id

        if node_id not in graph:
            # Method exists but has no edges (neither caller nor callee found in project)
            results.append(MethodMetrics(
                method_id=node_id,
                fan_in=0, fan_out=0,
                fan_out_external=external_count.get(node_id, 0),
                bottleneck_score=0.0,
                is_leaf=True,
                is_orphan=method.name not in ENTRY_POINT_NAMES,
                complexity=method.complexity,
                loc=method.loc,
            ))
            continue

        fan_in = graph.in_degree(node_id)
        fan_out = graph.out_degree(node_id)
        fan_out_external = external_count.get(node_id, 0)

        # Bottleneck score: mirrors OSCAR's formula
        if fan_out > 0:
            bottleneck_score = float(fan_in * fan_out)
        else:
            bottleneck_score = float(fan_in)

        is_leaf = (fan_out == 0 and fan_out_external == 0)
        is_orphan = (fan_in == 0 and method.name not in ENTRY_POINT_NAMES)

        results.append(MethodMetrics(
            method_id=node_id,
            fan_in=fan_in,
            fan_out=fan_out,
            fan_out_external=fan_out_external,
            bottleneck_score=bottleneck_score,
            is_leaf=is_leaf,
            is_orphan=is_orphan,
            complexity=method.complexity,
            loc=method.loc,
        ))

    return results
```

---

### 3.4 Services Layer

#### `services/analysis_service.py`

The service orchestrates the full pipeline from a project path to a stored `AnalysisResult`.

```python
import ast
from datetime import datetime, timezone
from pathlib import Path
from ..ingestion.project_scanner import ScanConfig, scan_project
from ..ingestion.source_reader import read_and_parse
from ..analysis.ast_visitor import ASTVisitor
from ..analysis.call_resolver import CallResolver
from ..analysis.graph_builder import GraphBuilder
from ..metrics.basic_metrics import compute_basic_metrics
from ..models.analysis_result import AnalysisResult, AnalysisMeta
from ..storage.json_storage import JsonStorage


class AnalysisService:

    def __init__(self, data_directory: Path, oscar_version: str = "0.1.0"):
        self.data_directory = data_directory
        self.oscar_version = oscar_version
        self.storage = JsonStorage(data_directory)

    def analyze(self, project_path: str, project_slug: str, exclude_tests: bool = False) -> AnalysisResult:
        """
        Full pipeline: scan → parse → extract → resolve → metrics → store → return.
        """
        root = Path(project_path).resolve()

        # ── 1. Scan ──────────────────────────────────────────────────
        config = ScanConfig(root_path=root, exclude_tests=exclude_tests)
        source_files = scan_project(config)

        # ── 2. Parse all files ───────────────────────────────────────
        parsed_sources = [read_and_parse(f) for f in source_files]

        # ── 3. Extract entities file-by-file ─────────────────────────
        all_methods, all_classes, all_modules = [], [], []
        all_raw_calls, all_imports, all_inheritance = [], [], []
        import_map: dict[str, dict[str, str]] = {}  # module_id → {local → resolved}

        for parsed in parsed_sources:
            if parsed.ast_tree is None:
                continue  # skip unparseable files
            visitor = ASTVisitor(
                module_id=parsed.source_file.module_path,
                file_path=parsed.source_file.relative_path,
                relative_path=parsed.source_file.relative_path,
            )
            result = visitor.extract(parsed.ast_tree)

            all_methods.extend(result.methods)
            all_classes.extend(result.classes)
            all_modules.append(result.module)
            all_raw_calls.extend(result.raw_calls)
            all_imports.extend(result.imports)
            all_inheritance.extend(result.inheritance)

            # Build import map for this module
            # Populated from scope_tracker's recorded_imports
            import_map[result.module.id] = visitor.scope.get_all_imports()

        # ── 4. Resolve calls ─────────────────────────────────────────
        resolver = CallResolver(
            all_methods=all_methods,
            all_classes=all_classes,
            import_map=import_map,
        )
        resolved_calls = [resolver.resolve(rc) for rc in all_raw_calls]
        resolved_calls = [c for c in resolved_calls if c is not None]

        # ── 5. Build graph ───────────────────────────────────────────
        graph_builder = GraphBuilder()
        graph = graph_builder.build(all_methods, resolved_calls)

        # ── 6. Compute metrics ───────────────────────────────────────
        metrics = compute_basic_metrics(graph, all_methods, resolved_calls)

        # ── 7. Compute analysis metadata ─────────────────────────────
        unresolved_count = sum(1 for c in resolved_calls if c.call_type == "unresolved")
        total_calls = len(resolved_calls)
        resolution_rate = (
            (total_calls - unresolved_count) / total_calls if total_calls > 0 else 1.0
        )
        total_loc = sum(f.size_bytes for f in source_files) // 50  # rough estimate

        meta = AnalysisMeta(
            project_slug=project_slug,
            project_path=str(root),
            analyzed_at=datetime.now(timezone.utc),
            oscar_version=self.oscar_version,
            file_count=len(parsed_sources),
            total_loc=total_loc,
            method_count=len(all_methods),
            class_count=len(all_classes),
            module_count=len(all_modules),
            edge_count=sum(1 for c in resolved_calls if not c.target_id.startswith("unresolved:")),
            unresolved_call_count=unresolved_count,
            resolution_rate=round(resolution_rate, 4),
        )

        # ── 8. Assemble result ───────────────────────────────────────
        result = AnalysisResult(
            meta=meta,
            methods=all_methods,
            classes=all_classes,
            modules=all_modules,
            calls=resolved_calls,
            imports=all_imports,
            inheritance=all_inheritance,
            metrics=metrics,
        )

        # ── 9. Persist ───────────────────────────────────────────────
        self.storage.save(project_slug, result)

        return result

    def load(self, project_slug: str) -> AnalysisResult | None:
        return self.storage.load(project_slug)

    def list_projects(self) -> list[str]:
        return self.storage.list_projects()
```

---

### 3.5 Storage Layer

#### `storage/json_storage.py`

```python
import json
from pathlib import Path
from ..models.analysis_result import AnalysisResult


class JsonStorage:
    """
    Flat-file JSON storage for analysis results.
    Mirrors OSCAR's existing data/ directory structure pattern.

    Layout:
        data/method_observatory/{project_slug}/
            analysis_meta.json
            methods.json
            classes.json
            modules.json
            calls.json
            imports.json
            inheritance.json
            metrics.json
    """

    def __init__(self, data_directory: Path):
        self.root = data_directory / "method_observatory"
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, project_slug: str, result: AnalysisResult) -> None:
        project_dir = self.root / project_slug
        project_dir.mkdir(parents=True, exist_ok=True)

        self._write(project_dir / "analysis_meta.json", result.meta.model_dump(mode="json"))
        self._write(project_dir / "methods.json", [m.model_dump(mode="json") for m in result.methods])
        self._write(project_dir / "classes.json", [c.model_dump(mode="json") for c in result.classes])
        self._write(project_dir / "modules.json", [m.model_dump(mode="json") for m in result.modules])
        self._write(project_dir / "calls.json", [c.model_dump(mode="json") for c in result.calls])
        self._write(project_dir / "imports.json", [i.model_dump(mode="json") for i in result.imports])
        self._write(project_dir / "inheritance.json", [i.model_dump(mode="json") for i in result.inheritance])
        self._write(project_dir / "metrics.json", [m.model_dump(mode="json") for m in result.metrics])

    def load(self, project_slug: str) -> AnalysisResult | None:
        project_dir = self.root / project_slug
        if not project_dir.exists():
            return None
        return AnalysisResult(
            meta=self._read_model(project_dir / "analysis_meta.json", "meta"),
            methods=self._read_list(project_dir / "methods.json"),
            classes=self._read_list(project_dir / "classes.json"),
            modules=self._read_list(project_dir / "modules.json"),
            calls=self._read_list(project_dir / "calls.json"),
            imports=self._read_list(project_dir / "imports.json"),
            inheritance=self._read_list(project_dir / "inheritance.json"),
            metrics=self._read_list(project_dir / "metrics.json"),
        )

    def list_projects(self) -> list[str]:
        return [d.name for d in self.root.iterdir() if d.is_dir()]

    def _write(self, path: Path, data) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)

    def _read_list(self, path: Path) -> list:
        if not path.exists():
            return []
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _read_model(self, path: Path, key: str):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
```

---

### 3.6 API Layer

#### `api/router.py`

```python
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from pathlib import Path
from ..services.analysis_service import AnalysisService
from ..models.analysis_result import AnalysisResult, AnalysisMeta, MethodMetrics

router = APIRouter(prefix="/methods", tags=["Method Observatory"])


# ── Request/Response schemas ──────────────────────────────────────────────── #

class AnalyzeRequest(BaseModel):
    project_path: str              # Absolute path on the analysis server's filesystem
    project_slug: str              # Short identifier used in storage and URLs
    exclude_tests: bool = False


class AnalyzeSummaryResponse(BaseModel):
    project_slug: str
    meta: AnalysisMeta
    top_risk: list[MethodMetrics]  # Top 10 by bottleneck score


class MethodDetailResponse(BaseModel):
    method: dict                   # Full MethodNode serialized
    metrics: MethodMetrics
    callers: list[dict]            # List of {method_node, edge_info}
    callees: list[dict]            # List of {method_node, edge_info}


# ── Endpoints ─────────────────────────────────────────────────────────────── #

@router.post("/analyze", response_model=AnalyzeSummaryResponse)
async def analyze_project(request: AnalyzeRequest, service: AnalysisService = Depends(get_service)):
    """
    Trigger analysis of a Python project directory.
    Runs the full ingestion → AST parsing → call resolution → metrics pipeline.
    Returns a summary with top-risk methods on completion.

    Note: For large projects (>50K LOC), this should be made async with a job queue (Phase 2).
    """
    try:
        result = service.analyze(
            project_path=request.project_path,
            project_slug=request.project_slug,
            exclude_tests=request.exclude_tests,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    top_risk = sorted(result.metrics, key=lambda m: m.bottleneck_score, reverse=True)[:10]
    return AnalyzeSummaryResponse(
        project_slug=request.project_slug,
        meta=result.meta,
        top_risk=top_risk,
    )


@router.get("/projects", response_model=list[str])
async def list_projects(service: AnalysisService = Depends(get_service)):
    """List all previously analyzed projects."""
    return service.list_projects()


@router.get("/{project_slug}", response_model=AnalysisMeta)
async def get_project_meta(project_slug: str, service: AnalysisService = Depends(get_service)):
    """Return analysis metadata for a project (summary statistics)."""
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")
    return result.meta


@router.get("/{project_slug}/top-risk", response_model=list[MethodMetrics])
async def get_top_risk(
    project_slug: str,
    limit: int = Query(default=10, ge=1, le=100),
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods ranked by bottleneck score (fan_in × fan_out).
    Mirrors OSCAR's /analytics/top-risk endpoint at the method level.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")
    ranked = sorted(result.metrics, key=lambda m: m.bottleneck_score, reverse=True)
    return ranked[:limit]


@router.get("/{project_slug}/orphans", response_model=list[dict])
async def get_orphans(
    project_slug: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods with fan_in=0 (never called within the project).
    Candidates for dead code removal.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    orphans = [m for m in result.metrics if m.is_orphan]
    return [{"method": method_map[m.method_id].model_dump(), "metrics": m.model_dump()}
            for m in orphans if m.method_id in method_map]


@router.get("/{project_slug}/method/{method_id:path}", response_model=MethodDetailResponse)
async def get_method_detail(
    project_slug: str,
    method_id: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return full detail for one method: its node data, metrics, and immediate callers/callees.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    metrics_map = {m.method_id: m for m in result.metrics}

    if method_id not in method_map:
        raise HTTPException(status_code=404, detail=f"Method '{method_id}' not found")

    method = method_map[method_id]
    metrics = metrics_map.get(method_id)

    # Collect callers (edges where target == method_id)
    callers = []
    for call in result.calls:
        if call.target_id == method_id and call.source_id in method_map:
            callers.append({
                "method": method_map[call.source_id].model_dump(),
                "edge": call.model_dump(),
            })

    # Collect callees (edges where source == method_id)
    callees = []
    for call in result.calls:
        if call.source_id == method_id and call.target_id in method_map:
            callees.append({
                "method": method_map[call.target_id].model_dump(),
                "edge": call.model_dump(),
            })

    return MethodDetailResponse(
        method=method.model_dump(),
        metrics=metrics,
        callers=callers,
        callees=callees,
    )


@router.get("/{project_slug}/graph", response_model=dict)
async def export_graph(
    project_slug: str,
    format: str = Query(default="json", enum=["json", "csv"]),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    service: AnalysisService = Depends(get_service),
):
    """
    Export the full method call graph for downstream analysis (Gephi, NetworkX, etc.).
    Mirrors OSCAR's /export/{ecosystem}/graph endpoint.

    JSON format: { "project": "...", "nodes": [...], "edges": [...] }
    CSV format: source,target,call_type,confidence
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    metrics_map = {m.method_id: m for m in result.metrics}

    filtered_calls = [
        c for c in result.calls
        if c.confidence >= min_confidence
        and not c.target_id.startswith("unresolved:")
        and c.source_id in method_map
        and c.target_id in method_map
    ]

    if format == "csv":
        from fastapi.responses import PlainTextResponse
        lines = ["source,target,call_type,confidence"]
        for call in filtered_calls:
            lines.append(f"{call.source_id},{call.target_id},{call.call_type},{call.confidence}")
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    nodes = [
        {**method_map[mid].model_dump(), **metrics_map[mid].model_dump()}
        for mid in method_map
        if mid in metrics_map
    ]
    edges = [c.model_dump() for c in filtered_calls]

    return {
        "project": project_slug,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


# ── Dependency injection ──────────────────────────────────────────────────── #

def get_service() -> AnalysisService:
    from app.config import settings
    return AnalysisService(
        data_directory=Path(settings.OSCAR_DATA_DIRECTORY),
        oscar_version=settings.OSCAR_APP_VERSION,
    )
```

#### Register the router in `app/main.py`

Add this to the existing `main.py` (two lines only):

```python
from app.method_observatory.api.router import router as method_router
app.include_router(method_router)
```

---

## Part 4 — Configuration

Add to `app/config.py` alongside existing `OSCAR_*` settings:

```python
# Method Observatory settings
OSCAR_METHOD_DATA_DIRECTORY: str = Field(
    default="data",
    env="OSCAR_DATA_DIRECTORY",  # reuses the same directory, different subpath
)
OSCAR_METHOD_MAX_FILE_SIZE_KB: int = Field(
    default=500,
    description="Skip Python source files larger than this (usually generated code)"
)
OSCAR_METHOD_EXCLUDE_TEST_FILES: bool = Field(
    default=False,
    description="If True, exclude test_*.py files and tests/ directories from analysis"
)
OSCAR_METHOD_MIN_CONFIDENCE: float = Field(
    default=0.0,
    description="Default minimum edge confidence for graph exports"
)
```

---

## Part 5 — Testing Plan

### 5.1 Unit Tests

Location: `backend/tests/method_observatory/`

| Test File | What to Test |
|---|---|
| `test_ast_visitor.py` | Individual visitor methods — parse small snippets and assert correct extraction of methods, classes, imports, call sites |
| `test_complexity.py` | `compute_complexity` against known-complexity functions. E.g., a function with 3 if-statements should return 4 |
| `test_call_resolver.py` | Each resolution path: direct, self, constructor, import-alias, name-match, unresolved |
| `test_graph_builder.py` | Graph node/edge counts for a known fixture project |
| `test_basic_metrics.py` | Fan-in/fan-out/bottleneck for a hand-constructed call graph |
| `test_scope_tracker.py` | Push/pop, bind, resolve, record_import |
| `test_json_storage.py` | Round-trip: save an AnalysisResult, load it, assert equality |

### 5.2 Integration Test: Fixture Project

Create `backend/tests/method_observatory/fixtures/simple_project/` — a minimal Python project with known call structure:

```
fixtures/simple_project/
├── app.py                 # main() calls service.process()
├── service.py             # process() calls repo.get() and validator.check()
├── repository.py          # get() is a leaf function
└── validator.py           # check() is a leaf function
```

Expected graph properties after analysis:
- 5 methods total
- 4 call edges (main→process, process→get, process→check, and one more)
- `process` has fan_in=1, fan_out=2
- `get` and `check` are leaves
- `main` is an orphan (not called by anyone in the project)

### 5.3 Self-Analysis Test

Analyze the OSCAR backend itself with the Method Observatory and verify:
- Analysis completes without crash
- `resolution_rate > 0.5` (more than half of calls resolved)
- `method_count > 10` (enough methods found)
- No method ID collisions

---

## Part 6 — Phase 2 Additions (Accuracy Improvements)

### 6.1 Cross-Module Resolution Enhancement

In Phase 1, `CallResolver` only checks immediate imports. Phase 2 adds project-wide symbol table construction that follows import chains transitively.

**New component:** `analysis/symbol_table.py`

```python
class ProjectSymbolTable:
    """
    Builds a project-wide mapping from fully qualified names to MethodNode IDs.
    Processes all ImportEdge records to follow re-export chains.
    Handles: from package.module import func (with re-exports through __init__.py)
    """
    def build(self, modules: list[ModuleNode], imports: list[ImportEdge], methods: list[MethodNode]) -> dict[str, str]:
        ...
```

### 6.2 Type Annotation Exploitation

Add annotation-based resolution to `CallResolver`: when a parameter is type-annotated (`repo: UserRepository`), record the annotation in the scope and use it to resolve `repo.method()` calls.

**New field in `ScopeTracker`:**

```python
self._type_annotations: dict[str, str] = {}
# Maps: "repo" → "app.repository:UserRepository"
```

**New logic in `_resolve_attribute_call`:**

```python
# After self.method() check, before module alias check:
# If receiver is a typed parameter, look up its class
if receiver and receiver in self.scope._type_annotations:
    class_id = self.scope._type_annotations[receiver]
    target_id = f"{class_id}.{attr_name}"
    if target_id in self._method_by_id:
        return CallEdge(..., call_type=CallType.DIRECT, confidence=0.9)
```

### 6.3 Advanced Metrics

Add to `metrics/graph_metrics.py`:

```python
import networkx as nx

def compute_graph_metrics(graph: nx.DiGraph) -> dict[str, dict]:
    """
    Compute betweenness centrality, PageRank, and community assignments.
    Returns a dict: method_id → {betweenness, pagerank, community_id, blast_radius}
    """
    betweenness = nx.betweenness_centrality(graph, normalized=True)
    pagerank = nx.pagerank(graph, alpha=0.85)

    # Community detection using Louvain
    # Convert directed → undirected for community detection
    undirected = graph.to_undirected()
    communities = nx.community.louvain_communities(undirected, seed=42)
    community_map = {}
    for community_id, community_set in enumerate(communities):
        for node_id in community_set:
            community_map[node_id] = community_id

    # Blast radius: size of transitive closure from each node (BFS)
    blast_radius = {}
    for node in graph.nodes:
        reachable = nx.descendants(graph, node)
        blast_radius[node] = len(reachable)

    return {
        node: {
            "betweenness_centrality": round(betweenness.get(node, 0.0), 6),
            "pagerank": round(pagerank.get(node, 0.0), 6),
            "community_id": community_map.get(node),
            "blast_radius": blast_radius.get(node, 0),
        }
        for node in graph.nodes
    }
```

### 6.4 SQLite Storage

Replace `JsonStorage` with `SqliteStorage` in Phase 2. Schema:

```sql
-- analysis_runs table tracks when each project was analyzed
CREATE TABLE analysis_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    analyzed_at TEXT NOT NULL,
    file_count INTEGER,
    method_count INTEGER,
    edge_count INTEGER,
    resolution_rate REAL,
    analysis_approach TEXT
);

-- methods table mirrors MethodNode
CREATE TABLE methods (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    module TEXT NOT NULL,
    class_name TEXT,
    kind TEXT,
    file_path TEXT,
    line_start INTEGER,
    line_end INTEGER,
    complexity INTEGER,
    loc INTEGER,
    project_slug TEXT NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id)
);

-- calls table mirrors CallEdge
CREATE TABLE calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    target_id TEXT NOT NULL,
    call_type TEXT,
    confidence REAL,
    line INTEGER,
    project_slug TEXT NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id)
);

-- metrics table mirrors MethodMetrics
CREATE TABLE method_metrics (
    method_id TEXT PRIMARY KEY,
    fan_in INTEGER,
    fan_out INTEGER,
    bottleneck_score REAL,
    betweenness_centrality REAL,
    pagerank REAL,
    community_id INTEGER,
    blast_radius INTEGER,
    project_slug TEXT NOT NULL,
    run_id INTEGER REFERENCES analysis_runs(id)
);

CREATE INDEX idx_calls_source ON calls(source_id);
CREATE INDEX idx_calls_target ON calls(target_id);
CREATE INDEX idx_methods_module ON methods(module);
CREATE INDEX idx_metrics_bottleneck ON method_metrics(bottleneck_score DESC);
```

---

## Part 7 — Phase 3 Additions (Hybrid Analysis)

### 7.1 Runtime Tracer

**New component:** `analysis/runtime_tracer.py`

```python
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class TraceRecord:
    caller_file: str
    caller_name: str
    callee_file: str
    callee_name: str
    count: int = 0


class RuntimeTracer:
    """
    Instruments Python execution via sys.settrace() to record actual method calls.
    Usage:
        tracer = RuntimeTracer(project_root="/path/to/project")
        tracer.start()
        # ... run tests or code here ...
        tracer.stop()
        records = tracer.get_records()
    """

    def __init__(self, project_root: str):
        self.project_root = project_root
        self._call_counts: dict[tuple, int] = defaultdict(int)
        self._call_stack: list[tuple] = []
        self._lock = threading.Lock()

    def start(self) -> None:
        sys.settrace(self._trace_calls)

    def stop(self) -> list[TraceRecord]:
        sys.settrace(None)
        return self._build_records()

    def _trace_calls(self, frame, event, arg):
        if event != "call":
            return self._trace_calls

        filename = frame.f_code.co_filename
        # Only trace files within the project
        if not filename.startswith(self.project_root):
            return None  # don't trace inside external libraries

        func_name = frame.f_code.co_qualname  # includes ClassName.method_name

        if self._call_stack:
            caller_file, caller_name = self._call_stack[-1]
            with self._lock:
                self._call_counts[(caller_file, caller_name, filename, func_name)] += 1

        self._call_stack.append((filename, func_name))
        return self._trace_calls

    def _build_records(self) -> list[TraceRecord]:
        return [
            TraceRecord(cf, cn, tf, tn, count)
            for (cf, cn, tf, tn), count in self._call_counts.items()
        ]
```

**Merging dynamic records with static graph:**

```python
def merge_dynamic_traces(
    graph: nx.DiGraph,
    trace_records: list[TraceRecord],
    method_map: dict[str, MethodNode],
) -> nx.DiGraph:
    """
    For each trace record, find the matching static edge and mark it as 'confirmed'.
    For trace records with no static edge, add a new edge with call_type='dynamic'.
    """
    ...
```

---

## Part 8 — Development Timeline

### Phase 1 (MVP) — 13 working days

| Day | Task |
|---|---|
| 1 | Set up `method_observatory/` module structure, `__init__.py` files, add to `app/main.py` |
| 2 | Implement Pydantic models (`MethodNode`, `ClassNode`, `ModuleNode`, `CallEdge`, `AnalysisResult`) |
| 3 | Implement `ScopeTracker` and unit tests |
| 4 | Implement `ASTVisitor` — imports, class definitions |
| 5 | Implement `ASTVisitor` — function/method definitions, complexity |
| 6 | Implement `ASTVisitor` — call site recording; end-to-end extraction test |
| 7 | Implement `CallResolver` — name calls and self calls |
| 8 | Implement `CallResolver` — attribute calls, module calls; unit tests |
| 9 | Implement `GraphBuilder` and `basic_metrics` |
| 10 | Implement `AnalysisService` pipeline orchestration |
| 11 | Implement `JsonStorage` (save + load round-trip) |
| 12 | Implement all FastAPI endpoints; wire into `main.py` |
| 13 | Integration test: analyze fixture project + analyze OSCAR itself; fix any issues |

### Phase 2 (Accuracy) — 17 working days

| Days | Task |
|---|---|
| 1–2 | `ProjectSymbolTable` for cross-module resolution |
| 3–4 | Type annotation exploitation in `CallResolver` |
| 5–6 | Class hierarchy analysis (MRO, parent class resolution) |
| 7–8 | `compute_graph_metrics` (betweenness, PageRank, communities, blast radius) |
| 9–10 | `SqliteStorage` implementation + migration from JSON |
| 11–12 | Incremental analysis (skip unchanged files via mtime) |
| 13–14 | New API endpoints: `/communities`, `/graph/path`, `/method/{id}/blast-radius` |
| 15–16 | Performance profiling; parallelize file parsing with `concurrent.futures` |
| 17 | End-to-end accuracy test against known Python project |

### Phase 3 (Hybrid) — 20 working days

| Days | Task |
|---|---|
| 1–4 | `RuntimeTracer` implementation and safety testing |
| 5–6 | Dynamic trace → static graph merge logic |
| 7–8 | CLI command: `oscar-trace` to instrument test suite execution |
| 9–10 | Temporal snapshot storage (analysis history per project) |
| 11–12 | Diff analysis API: what changed between two analysis runs? |
| 13–15 | Basic frontend integration (extend OSCAR UI with method-level views) |
| 16–17 | PyCG integration as optional high-precision backend |
| 18–20 | Documentation, testing, hardening |

---

## Part 9 — OSCAR Integration Summary

### New API Endpoints Added to OSCAR

| Endpoint | Method | Description | OSCAR Analogue |
|---|---|---|---|
| `/methods/analyze` | POST | Trigger analysis of a project | (new) |
| `/methods/projects` | GET | List analyzed projects | (new) |
| `/methods/{slug}` | GET | Project analysis metadata | `/packages/{eco}/{pkg}/{ver}` |
| `/methods/{slug}/top-risk` | GET | Methods by bottleneck score | `/analytics/top-risk` |
| `/methods/{slug}/orphans` | GET | Methods never called | (new) |
| `/methods/{slug}/method/{id}` | GET | Method detail + callers/callees | `/packages/{eco}/{pkg}/{ver}` |
| `/methods/{slug}/graph` | GET | Full graph export (JSON or CSV) | `/export/{eco}/graph` |

### New Config Variables

```env
OSCAR_METHOD_MAX_FILE_SIZE_KB=500
OSCAR_METHOD_EXCLUDE_TEST_FILES=false
OSCAR_METHOD_MIN_CONFIDENCE=0.0
```

### New Dependencies (add to `requirements.txt`)

```
networkx>=3.2
# radon>=6.0        ← Phase 2: more accurate cyclomatic complexity
# python-igraph>=0.11  ← Phase 2: Leiden community detection
# gitpython>=3.1    ← Phase 3: git integration for temporal analysis
```

Phase 1 has **zero new dependencies** — only Python stdlib and the packages OSCAR already uses (FastAPI, Pydantic).

---

## Part 10 — Known Gaps and Acceptance Criteria

### Acceptance Criteria for Phase 1 Completion

| Criterion | Target |
|---|---|
| Analyzes OSCAR backend itself without crash | ✓ |
| `resolution_rate` on OSCAR backend | ≥ 0.50 |
| `method_count` on OSCAR backend | ≥ 20 |
| `/methods/{slug}/top-risk` returns plausible results | ✓ |
| `/methods/{slug}/graph` CSV importable into NetworkX | ✓ |
| Round-trip: save → load → re-save produces identical JSON | ✓ |
| All unit tests pass | ✓ |
| No new Python dependencies required | ✓ |

### Known Gaps Accepted in Phase 1

| Gap | Reason | Phase Addressed |
|---|---|---|
| `obj.method()` without type annotation unresolved | Requires type inference | Phase 2 |
| `from module import *` creates analysis gap | Fundamentally unresolvable statically | Mitigated in Phase 2 |
| Lambda expressions not modeled as methods | Low priority | Phase 2 |
| Decorator-registered routes (FastAPI `@app.get`) don't appear as callers | Requires decorator semantics | Phase 2 |
| Recursive calls not distinguished from self-calls | Minor accuracy issue | Phase 2 |
| Dynamic calls (`getattr`, `callable()`) unresolved | Requires runtime data | Phase 3 |
| External library internals opaque | Requires source of dependencies | Out of scope |
