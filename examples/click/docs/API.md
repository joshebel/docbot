# API Reference

## `src/click/__init__.py`

- `__getattr__(name) -> object` — Module-level attribute access that lazily imports and returns public symbols from submodules.

## `src/click/_compat.py`

- `is_ascii_encoding(encoding) -> bool` — Checks if a given encoding is ASCII.
- `get_best_encoding(stream) -> str` — Returns the default stream encoding if not found.
- `_NonClosingTextIOWrapper` — A `TextIOWrapper` variant that does not close the underlying buffer on `close()`.
- `_FixupStream` — Wraps a stream to provide missing `io` interface methods like `read1`, `readable`, `writable`, and `seekable`.
- `get_binary_stdin() -> t.BinaryIO` — Returns the binary standard input stream.
- `get_binary_stdout() -> t.BinaryIO` — Returns the binary standard output stream.
- `get_binary_stderr() -> t.BinaryIO` — Returns the binary standard error stream.
- `get_text_stdin(encoding, errors) -> t.TextIO` — Returns a text-mode standard input stream with the specified encoding and error handling.
- `get_text_stdout(encoding, errors) -> t.TextIO` — Returns a text-mode standard output stream with the specified encoding and error handling.
- `get_text_stderr(encoding, errors) -> t.TextIO` — Returns a text-mode standard error stream with the specified encoding and error handling.
- `open_stream(filename, mode, encoding, errors, atomic) -> tuple[t.IO[t.Any], bool]` — Opens a stream for reading or writing, handling special cases like atomic writes.
- `_AtomicFile` — A file wrapper that writes to a temporary file and renames it on close to ensure atomicity.
- `strip_ansi(value) -> str` — Removes ANSI escape sequences from a string.
- `should_strip_ansi(stream, color) -> bool` — Determines whether ANSI codes should be stripped from output based on stream properties and color settings.
- `term_len(x) -> int` — Returns the visible length of a string, ignoring ANSI escape sequences.
- `isatty(stream) -> bool` — Checks if a stream is a TTY, handling edge cases for Windows and Jupyter.

## `src/click/_termui_impl.py`

- `ProgressBar` — An iterable context manager that displays a progress bar in the terminal, supporting ETA, percentage, and custom formatting.
- `_PagerWriter` — Wraps a pager's output stream to strip ANSI styling when colors are disabled.
- `get_pager_file(color) -> t.Generator[t.TextIO, None, None]` — Context manager that yields a file-like object for paging output, handling ANSI stripping based on color settings.
- `Editor` — Manages opening files or text in the user's preferred editor, handling environment variables and save requirements.
- `open_url(url, wait, locate) -> int` — Opens a URL or file in the default application, optionally waiting for it to close or locating it in the file manager.

## `src/click/_textwrap.py`

- `TextWrapper` — A `textwrap.TextWrapper` variant that measures widths by visible characters, ignoring ANSI escape sequences.

## `src/click/_utils.py`

- `Sentinel` — An enum used to define sentinel values, such as `UNSET`, that are distinct from `None` and other defaults.

## `src/click/_winconsole.py`

- `_WindowsConsoleRawIOBase` — Base class for Windows console raw I/O streams.
- `_WindowsConsoleReader` — A raw I/O stream for reading from the Windows console.
- `_WindowsConsoleWriter` — A raw I/O stream for writing to the Windows console.
- `ConsoleStream` — A wrapper for Windows console streams that provides text and byte stream access.

## `src/click/core.py`

- `batch(iterable, batch_size) -> list[tuple[V, ...]]` — Splits an iterable into batches of a specified size.
- `augment_usage_errors(ctx, param)` — Context manager that attaches extra information to usage error exceptions.
- `iter_params_for_processing(invocation_order, declaration_order) -> list[Parameter]` — Returns all declared parameters in the order they should be processed.
- `ParameterSource` — An `IntEnum` indicating the source of a parameter value (e.g., command line, environment variable, default).
- `Context` — Holds state relevant to the current command execution, including parameters, objects, and resource management.
- `Command` — The basic building block of command line interfaces, representing a single command with parameters and a callback.
- `Group` — A command that nests other commands (or more groups), providing a way to organize subcommands.
- `CommandCollection` — A `Group` that looks up subcommands on other groups, allowing commands to be shared across multiple groups.
- `Parameter` — An abstract base class for command line parameters, defining common behavior for options and arguments.
- `Option` — A parameter that is usually optional and can be specified with a flag or value on the command line.
- `Argument` — A positional parameter to a command, generally required unless specified otherwise.

## `src/click/decorators.py`

- `pass_context(f)` — Marks a callback as wanting to receive the current context object as its first argument.
- `pass_obj(f)` — Marks a callback as wanting to receive the current context object's `obj` attribute as its first argument.
- `make_pass_decorator(object_type, ensure)` — Creates a decorator that passes a specific object type from the context to the callback.
- `pass_meta_key(key, doc_description)` — Creates a decorator that passes a key from the context's `meta` dictionary to the callback.
- `command(name, cls, **attrs)` — Creates a new `Command` and uses the decorated function as its callback.
- `group(name, cls, **attrs)` — Creates a new `Group` with a function as callback, allowing subcommands to be attached.
- `argument(*param_decls, cls, **attrs)` — Attaches an argument to the command, with all positional arguments being parameter declarations.
- `option(*param_decls, cls, **attrs)` — Attaches an option to the command, with all positional arguments being parameter declarations.
- `confirmation_option(*param_decls, **kwargs)` — Adds a `--yes` option which shows a prompt before continuing if not passed.
- `password_option(*param_decls, **kwargs)` — Adds a `--password` option which prompts for a password, hiding input.
- `version_option(version, *param_decls, package_name, prog_name, message, **kwargs)` — Adds a `--version` option which immediately prints the version and exits.
- `custom_version_option(callback, *param_decls, **kwargs)` — Adds a `--version` option whose output is produced by a custom callback.
- `help_option(*param_decls, **kwargs)` — Pre-configured `--help` option which immediately prints the help page and exits.

## `src/click/exceptions.py`

- `ClickException` — An exception that Click can handle and show to the user, with a formatted message.
- `UsageError` — An internal exception that signals a usage error, typically resulting in a non-zero exit code.
- `BadParameter` — An exception that formats out a standardized error message for a bad parameter value.
- `MissingParameter` — Raised if a required option or argument was not provided.
- `NoSuchOption` — Raised if Click attempted to handle an option that does not exist.
- `NoSuchCommand` — Raised if Click attempted to handle a command that does not exist.
- `BadOptionUsage` — Raised if an option is generally supplied but the use of the option is invalid.
- `BadArgumentUsage` — Raised if an argument is generally supplied but the use of the argument is invalid.
- `NoArgsIsHelpError` — Raised when a command with no arguments is invoked and help is expected.
- `FileError` — Raised if a file cannot be opened, with a hint about the issue.
- `Abort` — An internal signalling exception that signals Click to abort execution.
- `Exit` — An exception that indicates the application should exit with a specific code.

## `src/click/formatting.py`

- `measure_table(rows) -> tuple[int, ...]` — Measures the width of columns in a table of rows.
- `iter_rows(rows, col_count)` — Iterates over rows, padding them to a consistent column count.
- `wrap_text(text, width, initial_indent, subsequent_indent, preserve_paragraphs) -> str` — A helper function that intelligently wraps text, preserving paragraphs if requested.
- `HelpFormatter` — A class that helps with formatting text-based help pages, managing indentation and sections.
- `join_options(options) -> tuple[str, bool]` — Given a list of option strings, joins them in the most appropriate way for display.

## `src/click/globals.py`

- `get_current_context(silent) -> Context | None` — Returns the current click context, or `None` if not found and `silent` is true.
- `push_context(ctx) -> None` — Pushes a new context to the current stack.
- `pop_context() -> None` — Removes the top level from the context stack.
- `resolve_color_default(color) -> bool | None` — Internal helper to get the default value of the color flag, resolving environment variables.

## `src/click/parser.py`

- `_Option` — Represents an option in the parser, handling its processing and value collection.
- `_Argument` — Represents a positional argument in the parser.
- `_ParsingState` — Holds the state of the parsing process, including remaining arguments.
- `_OptionParser` — The internal class used to parse command line arguments into values.

## `src/click/shell_completion.py`

- `shell_complete(cli, ctx_args, prog_name, complete_var, instruction) -> t.Literal[0, 1]` — Performs shell completion for the given CLI program, returning an exit code.
- `CompletionItem` — Represents a completion value and metadata about the value, such as help text.
- `ShellComplete` — Base class for providing shell completion support, with subclasses for specific shells.
- `BashComplete` — Shell completion for Bash.
- `ZshComplete` — Shell completion for Zsh.
- `FishComplete` — Shell completion for Fish.
- `PowerShellComplete` — Shell completion for PowerShell (Windows PowerShell 5.1+ and pwsh 7+).
- `add_completion_class(cls, name)` — Registers a `ShellComplete` subclass under the given name.
- `get_completion_class(shell)` — Looks up a registered `ShellComplete` subclass by the name of the shell.
- `split_arg_string(string) -> list[str]` — Splits an argument string as with `shlex.split`, but doesn't remove quotes.

## `src/click/termui.py`

- `hidden_prompt_func(prompt) -> str` — A prompt function that hides the input, used for password prompts.
- `prompt(text, default, hide_input, confirmation_prompt, type, value_proc, prompt_suffix, show_default, err, show_choices)` — Prompts a user for input, with various options for validation and display.
- `confirm(text, default, abort, prompt_suffix, show_default, err) -> bool` — Prompts for confirmation (yes/no question).
- `get_pager_file(color)` — Context manager that yields a file-like object for paging output.
- `echo_via_pager(text_or_generator, color) -> None` — Shows text via an environment specific pager, handling ANSI colors.
- `progressbar(length, label, hidden, show_eta, show_percent, show_pos, fill_char, empty_char, bar_template, info_sep, width, file, color, update_min_steps)` — Creates an iterable context manager that can be used to display a progress bar.
- `clear() -> None` — Clears the terminal screen.
- `style(text, fg, bg, bold, dim, underline, overline, italic, blink, reverse, strikethrough, reset) -> str` — Styles a text with ANSI styles and returns the new string.
- `unstyle(text) -> str` — Removes ANSI styling information from a string.
- `secho(message, file, nl, err, color, **styles) -> None` — Combines `echo` and `style` into one function, printing styled text.
- `edit(text, editor, env, require_save, extension, filename)` — Edits the given text in the defined editor, returning the edited text.
- `launch(url, wait, locate) -> int` — Launches the given URL (or filename) in the default application.
- `getchar(echo) -> str` — Fetches a single character from the terminal and returns it.
- `raw_terminal()` — Context manager that puts the terminal into raw mode.
- `pause(info, err) -> None` — Stops execution and waits for the user to press any key.

## `src/click/testing.py`

- `EchoingStdin` — A stream that echoes input to an output stream, used for testing prompts.
- `_FDCapture` — Redirects a file descriptor to a temporary file for capture.
- `BytesIOCopy` — Patches `io.BytesIO` to let the written stream be copied to another stream.
- `StreamMixer` — Mixes `<stdout>` and `<stderr>` streams.
- `_NamedTextIOWrapper` — A `TextIOWrapper` with custom `name` and `mode` attributes.
- `make_input_stream(input, charset) -> t.BinaryIO` — Creates a binary input stream from a string or bytes.
- `Result` — Holds the captured result of an invoked CLI script, including output, exit code, and exceptions.
- `CliRunner` — Provides functionality to invoke a Click command line interface in an isolated environment for testing.

## `src/click/types.py`

- `ParamType` — Represents the type of a parameter, validating and converting values.
- `CompositeParamType` — A parameter type that combines multiple types, such as tuples.
- `FuncParamType` — A parameter type that uses a custom function for conversion.
- `UnprocessedParamType` — A parameter type that does not process the value, passing it through unchanged.
- `StringParamType` — A parameter type that converts values to strings.
- `Choice` — A parameter type that allows a value to be checked against a fixed set of choices.
- `DateTime` — A parameter type that converts date strings into `datetime` objects.
- `IntParamType` — A parameter type that converts values to integers.
- `IntRange` — Restricts an `INT` value to a range of accepted values.
- `FloatParamType` — A parameter type that converts values to floats.
- `FloatRange` — Restricts a `FLOAT` value to a range of accepted values.
- `BoolParamType` — A parameter type that converts values to booleans.
- `UUIDParameterType` — A parameter type that converts values to `uuid.UUID` objects.
- `File` — Declares a parameter to be a file for reading or writing.
- `Path` — A parameter type that validates and converts values to file paths.
- `Tuple` — A parameter type that converts values to tuples of specified types.
- `convert_type(ty, default)` — Finds the most appropriate `ParamType` for the given Python type.

## `src/click/utils.py`

- `make_str(value) -> str` — Converts a value into a valid string.
- `_LazyFile` — A lazy file works like a regular file but it does not fully open the file until it is accessed.
- `_KeepOpenFile` — Proxy a file object but keep it open across a `with` block.
- `echo(message, file, nl, err, color) -> None` — Print a message and newline to stdout or a file.
- `open_file(filename, mode, encoding, errors, lazy, atomic) -> t.IO[t.Any]` — Open a file, with extra behavior to handle `'-'` to indicate stdin/stdout.
- `format_filename(filename, shorten) -> str` — Format a filename as a string for display, ensuring it can be displayed correctly.
- `get_app_dir(app_name, roaming, force_posix) -> str` — Returns the config folder for the application.
- `_PacifyFlushWrapper` — A wrapper that catches and suppresses `BrokenPipeError` resulting from flushing.
