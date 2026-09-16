<div align="center"><img src="https://raw.githubusercontent.com/pallets/click/refs/heads/stable/docs/_static/click-name.svg" alt="" height="150"></div>

# Click

Click is a Python package for creating composable command line interfaces with minimal boilerplate. It provides decorators for declaring commands, options, and arguments, automatic help-page generation, and a rich set of built-in parameter types, terminal utilities, and testing helpers. It is highly configurable but ships with sensible defaults, aiming to make writing CLI tools quick and fun while preventing frustration from unimplementable CLI APIs.

## Features

- **Composable commands and groups** — nest commands to arbitrary depth; groups can chain subcommands and pass results through a `result_callback`.
- **Automatic help pages** — usage lines, option/argument listings, and descriptions are generated from docstrings and parameter metadata.
- **Rich parameter types** — built-in types for `int`, `float`, `bool`, `UUID`, `datetime`, file paths, file handles, choices, and ranges, plus a `ParamType` base class for custom types.
- **Terminal UI helpers** — progress bars, prompts, confirmations, colored output, pagers, editor launching, and screen clearing.
- **Shell completion** — built-in completion for Bash, Zsh, Fish, and PowerShell, with a `shell_complete` hook for custom completions.
- **Testing utilities** — `CliRunner` isolates a command in a controlled environment and captures stdout, stderr, and return values.
- **Environment variable support** — options can read defaults from environment variables, with automatic prefixing for nested groups.
- **Lazy loading** — subcommands can be loaded at runtime, keeping startup fast for large CLIs.

## Installation

Install from PyPI:

```bash
pip install click
```

The package requires Python 3.10 or later.

## Usage

### A simple command

```python
import click

@click.command()
@click.option("--count", default=1, help="Number of greetings.")
@click.option("--name", prompt="Your name", help="The person to greet.")
def hello(count, name):
    """Simple program that greets NAME for a total of COUNT times."""
    for _ in range(count):
        click.echo(f"Hello, {name}!")

if __name__ == "__main__":
    hello()
```

```
$ python hello.py --count=3
Your name: Click
Hello, Click!
Hello, Click!
Hello, Click!
```

### Groups and subcommands

```python
import click

@click.group()
def cli():
    """Naval Fate!"""

@cli.command()
@click.argument("name")
def ship(name):
    """Create a new ship."""
    click.echo(f"Creating new ship {name!r}")

@cli.command()
@click.argument("x", type=int)
@click.argument("y", type=int)
def mine(x, y):
    """Place a mine."""
    click.echo(f"Setting mine at {x}, {y}")

if __name__ == "__main__":
    cli()
```

```
$ python naval.py ship frigate
Creating new ship 'frigate'
$ python naval.py mine 5 10
Setting mine at 5, 10
```

### Progress bar

```python
import click

@click.command()
def process():
    with click.progressbar(range(100), label="Processing") as bar:
        for item in bar:
            do_work(item)
```

### Testing with CliRunner

```python
from click.testing import CliRunner

def test_hello():
    runner = CliRunner()
    result = runner.invoke(hello, ["--count", "2", "--name", "World"])
    assert result.exit_code == 0
    assert "Hello, World!" in result.output
```

## Configuration

Click does not require a configuration file. Behavior is controlled through:

- **`context_settings`** on `@click.command` or `@click.group` — pass a dictionary of `Context` constructor arguments (e.g. `auto_envvar_prefix`, `token_normalize_func`, `max_content_width`).
- **Environment variables** — options with an `envvar` parameter, or automatic env-var lookup when `auto_envvar_prefix` is set on the context.
- **`default_map`** on `Context` — a mapping of parameter names to default values that overrides parameter-level defaults.

## Project Layout

```
src/click/          # Package source
  core.py           # Command, Group, Context, Parameter, Option, Argument
  decorators.py     # @command, @group, @option, @argument, etc.
  types.py          # ParamType subclasses (INT, FLOAT, Path, File, …)
  termui.py         # prompt, confirm, progressbar, style, echo_via_pager
  testing.py        # CliRunner, Result
  shell_completion.py
  exceptions.py
  formatting.py
  utils.py
  _compat.py        # Platform-specific stream and encoding helpers
  _termui_impl.py   # ProgressBar, Editor, pager internals
  _winconsole.py    # Windows console stream wrappers
  _textwrap.py      # ANSI-aware text wrapping
  _utils.py         # Sentinel enum
tests/              # Test suite
examples/           # Runnable example CLIs (naval, aliases, imagepipe, …)
docs/               # Sphinx documentation source
```

## Development

Set up a development environment with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Run the test suite:

```bash
uv run pytest
```

Run pre-commit hooks (Ruff, uv lock, codespell):

```bash
uv run pre-commit run --all-files
```

Build the documentation:

```bash
uv run sphinx-build docs/ docs/_build/html
```

## License

[BSD-3-Clause](LICENSE.txt)

## Donate

The Pallets organization develops and supports Click and other popular packages. In order to grow the community of contributors and users, and allow the maintainers to devote more time to the projects, [please donate today][].

[please donate today]: https://palletsprojects.com/donate

## Contributing

See our [detailed contributing documentation][contrib] for many ways to contribute, including reporting issues, requesting features, asking or answering questions, and making PRs.

[contrib]: https://palletsprojects.com/contributing/
