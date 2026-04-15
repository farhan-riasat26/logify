# logify

Custom logging package for Python 3.12+ built on `picologging`, `loguru`, `structlog`, and `python-json-logger`. Ships a preconfigured `log` object plus a `configure()` entrypoint and graceful `shutdown()`.

## Requirements

- Python `>=3.12`
- [`uv`](https://docs.astral.sh/uv/) (or `pip` with Git support)
- Access to the private GitHub repository

## Install from a private GitHub repo with `uv`

Replace `farhan-riasat26/logify` with the actual path (e.g. `my-org/logify`) and `REF` with a branch, tag, or commit SHA (e.g. `main`, `v0.1.0`).

### 1. Authenticate to GitHub

Pick **one** of the methods below. `uv` uses whichever Git transport you configure.

#### Option A — SSH (recommended for local dev)

Make sure `ssh -T git@github.com` succeeds, then use an SSH URL:

```bash
uv add "logify @ git+ssh://git@github.com/farhan-riasat26/logify.git@REF"
```

#### Option B — Personal Access Token (HTTPS)

Create a fine-grained PAT with **Contents: Read** on the repo, then export it:

```bash
export GH_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx
uv add "logify @ git+https://${GH_TOKEN}@github.com/farhan-riasat26/logify.git@REF"
```

> Avoid committing the token. In CI, inject it via a secret (`${{ secrets.GH_TOKEN }}`).

#### Option C — `gh` CLI credential helper

If you already run `gh auth login`, configure Git to use it:

```bash
gh auth setup-git
uv add "logify @ git+https://github.com/farhan-riasat26/logify.git@REF"
```

### 2. Alternative install commands

```bash
# Install into the active project (adds to pyproject.toml + lockfile)
uv add "logify @ git+https://github.com/farhan-riasat26/logify.git@main"

# Install into the active venv without touching pyproject.toml
uv pip install "git+https://github.com/farhan-riasat26/logify.git@main"

# Install a specific tag
uv add "logify @ git+https://github.com/farhan-riasat26/logify.git@v0.1.0"

# Install a specific commit
uv add "logify @ git+https://github.com/farhan-riasat26/logify.git@<commit-sha>"

# Install as a tool
uv tool install "git+https://github.com/farhan-riasat26/logify.git@main"
```

### 3. Declaring it in `pyproject.toml`

```toml
[project]
dependencies = [
    "logify @ git+https://github.com/farhan-riasat26/logify.git@main",
]
```

Or with `[tool.uv.sources]` (recommended — keeps the version spec clean):

```toml
[project]
dependencies = ["logify"]

[tool.uv.sources]
logify = { git = "https://github.com/farhan-riasat26/logify.git", rev = "main" }
```

Then run:

```bash
uv sync
```

## Usage

```python
from logger import log, configure, shutdown

configure()  # optional — loads logger/config.json by default

log.info("service started", extra={"component": "api"})

# call on process exit if queue_handler is enabled
shutdown()
```

## CI example (GitHub Actions)

```yaml
- uses: astral-sh/setup-uv@v3
- name: Install dependencies
  env:
    GH_TOKEN: ${{ secrets.GH_TOKEN }}
  run: |
    git config --global url."https://${GH_TOKEN}@github.com/".insteadOf "https://github.com/"
    uv sync
```

## Troubleshooting

- **`fatal: Authentication failed`** — PAT is missing the `Contents: Read` scope or the repo hasn't been granted access.
- **`Package 'logify' not found`** — the ref doesn't exist; check branch/tag name.
- **Stale cached build** — clear with `uv cache clean logify` and reinstall.