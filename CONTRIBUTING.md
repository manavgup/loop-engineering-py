# Contributing

Thanks for improving backlog-grinder. This repo keeps a small, strict bar so the
harness stays trustworthy. Conventions are adapted (sized down) from
[IBM/mcp-context-forge](https://github.com/IBM/mcp-context-forge).

## Setup

```bash
make install        # editable install with dev extras + pre-commit hooks
```

## Before you open a PR

```bash
make lint           # ruff (lint) + ruff-format + all pre-commit hooks
make test           # unit suite + doctests
make coverage       # coverage, fails under 85%
```

CI runs the same `lint` and `test` checks on every PR and they must be green.

## Branch & PR flow

`main` is protected: **no direct pushes** (enforced for admins too). Work on a
branch, open a PR into `main`, let CI go green, then self-merge (0 approvals
required). No force-pushes or branch deletions on `main`.

Sign your commits with the Developer Certificate of Origin:

```bash
git commit -s       # appends: Signed-off-by: Your Name <you@example.com>
```

## Coding standards

- **Python ≥ 3.9, type hints** on public signatures.
- **Naming:** `snake_case` functions, `PascalCase` classes, `UPPER_CASE` constants.
- **Line length 100**; formatting and import order are owned by `ruff format` /
  `ruff check` — don't hand-fight them.
- **File header** on every module:
  ```python
  # SPDX-License-Identifier: MIT
  """One-line summary of the module.

  Location: backlog_grinder/<module>.py
  Authors: <you>

  Optional longer description.
  """
  ```
- **Docstrings:** Google style on every public function — a one-line imperative
  summary plus `Args:` / `Returns:` / `Raises:` as applicable (`ruff` enforces
  presence via `D1` and argument completeness via `D417`). Add a `>>>` doctest
  `Examples:` block for pure, deterministic functions; never for code that
  touches git, the filesystem, subprocess, time, or randomness.

## Tests

- Every behaviour change ships with a test. The suite is fully synthetic (no
  network, no real model, no real git beyond temp repos).
- Keep coverage ≥ 85%. Doctests are part of `make test`.
