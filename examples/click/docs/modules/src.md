# `src` Module

The `src/click` package is the core implementation of the Click command-line interface toolkit. It is organized into public API modules (imported by `click`) and private implementation modules (prefixed with `_`).

## Public Entry Points

`click/__init__.py` re-exports the public surface: decorators (`command`, `group`, `option`, `argument`, `version_option`, `help_option`, `pass_context`, `pass_obj`), core classes (`Command`, `Group`, `Context`, `Option`, `Argument`, `Parameter`), types (`INT`, `FLOAT`, `BOOL`, `Choice`, `Path`, `File`, `Tuple`, `DateTime`, `UUID`), exceptions, and utility functions (`echo`, `prompt`, `confirm`, `progressbar`, `style`, `open_file`).

## Key Components

**`core.py`** — The heart of Click. `Command` handles parsing, help formatting, and invocation. `Group` extends `Command` to nest subcommands, supporting chaining and result callbacks. `Context` holds per-invocation state (params, args, obj, meta) and manages resource cleanup via `with_resource`/`call_on_close`. `Parameter` (abstract) defines the common interface; `Option` and `Argument` implement it. `ParameterSource` (an `IntEnum`) tracks where a value came from (command line, env var, default map, prompt, default).

**`decorators.py`** — Wraps core classes into Python decorators. `command()` and `group()` create command objects from functions. `option()` and `argument()` attach parameters to a function's `__click_params__` list, which `command()` collects at decoration time.

**`types.py`** — `ParamType` is the abstract base for value conversion. Concrete types include `StringParamType`, `IntParamType`, `FloatParamType`, `BoolParamType`, `Choice`, `DateTime`, `File`, `Path`, `Tuple`, and `UUID`. `convert_type()` infers a `ParamType` from a Python type or default value.

**`exceptions.py`** — `ClickException` is the base; `UsageError` and its subclasses (`BadParameter`, `NoSuchOption`, `NoSuchCommand`) carry context for formatted error messages. `Abort` and `Exit` are internal control-flow signals.

**`termui.py` / `_termui_impl.py`** — Terminal interaction: `prompt`, `confirm`, `progressbar`, `style`/`secho`, `echo_via_pager`, `edit`, `launch`, `getchar`, `pause`.

**`shell_completion.py`** — `ShellComplete` base class with `BashComplete`, `ZshComplete`, `FishComplete`, and `PowerShellComplete` subclasses. `shell_complete()` is the entry point called from `Command.main()`.

**`testing.py`** — `CliRunner` provides isolated invocation for tests, capturing stdout/stderr and supporting `capture='sys'` or `capture='fd'` modes.

**`parser.py`** — Internal `_OptionParser` (not exposed publicly) that parses CLI tokens into option/argument values.

**`_compat.py`** — Platform-specific stream handling, ANSI stripping, and encoding detection.

**`_winconsole.py`** — Windows console I/O wrappers.

**`_textwrap.py`** — `TextWrapper` variant that measures visible width (ignoring ANSI codes).

**`_utils.py`** — `Sentinel` enum and the `UNSET` sentinel used to distinguish "no value" from `None`.

## Notable Design Decisions

- **`UNSET` sentinel**: Parameters use an internal `UNSET` value to distinguish "not provided" from an explicit `None`. This is hidden from users via `_hide_unset()` at boundaries.
- **Lazy defaults**: `Option` keeps `default` and `flag_value` as raw values (possibly `UNSET`) at construction time, resolving them lazily in `get_default()` and `flag_activation_value`. This supports feature-switch groups where multiple options share a parameter name.
- **`_FakeSubclassCheck` metaclass**: Deprecated aliases `_BaseCommand` and `_MultiCommand` use this to pass `isinstance` checks against their real base classes.
- **`__getattr__` in `__init__.py` and `core.py`**: Provides deprecation warnings for removed names (`BaseCommand`, `MultiCommand`, `OptionParser`, `__version__`) without importing them eagerly.

## Gotchas

- `Command.main()` with `standalone_mode=True` (default) calls `sys.exit()`; use `standalone_mode=False` to get the return value.
- `Group` with `chain=True` cannot contain optional arguments.
- `Option` with `nargs=-1` is not supported (use `multiple=True` instead).
- The `UNSET` sentinel is an implementation detail; user code should never compare against it directly.
