# Logging utilities.

from __future__ import annotations

import logging
import subprocess
import sys
import time
from contextlib import closing, contextmanager, redirect_stderr, redirect_stdout
from io import StringIO
from typing import TYPE_CHECKING
from typing import Annotated as An

from loguru import logger
from typing_extensions import Doc

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path
    from typing import Any

    from loguru import Record


def _double_brackets(message: An[str, Doc("The message to transform.")]) -> An[str, Doc("The updated message.")]:
    """Double `{` and `}` in log messages to prevent formatting errors."""
    return message.replace("{", "{{").replace("}", "}}")


def _run(
    *args: An[str | Path, Doc("Command line arguments.")],
    **kwargs: An[Any, Doc("Additional arguments to [subprocess.Popen][].")],
) -> An[str, Doc("The process standard output.")]:
    """Run a subprocess, log its standard output and error, return its output."""
    args_str = _double_brackets(str(args))
    kwargs_str = _double_brackets(str(kwargs))
    _logger.debug(f"Running subprocess with args={args_str}, kwargs={kwargs_str}")
    process = subprocess.Popen(  # noqa: S603
        args,
        **kwargs,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout = []
    while True:
        stdout_line = process.stdout.readline().strip()  # type: ignore[union-attr]
        stderr_line = process.stderr.readline().strip()  # type: ignore[union-attr]
        if stdout_line:
            _logger.debug(f"STDOUT: {_double_brackets(stdout_line)}", pkg=args[0])
            stdout.append(stdout_line)
        if stderr_line:
            _logger.debug(f"STDERR: {_double_brackets(stderr_line)}", pkg=args[0])
        if not stdout_line and not stderr_line:
            break
    process.wait()
    return "\n".join(stdout)


class _TextBuffer(StringIO):
    class _BytesBuffer:
        def __init__(self, text_buffer: _TextBuffer) -> None:
            self._text_buffer = text_buffer

        def flush(self) -> None: ...

        def write(self, value: bytes) -> int:
            return self._text_buffer.write(value.decode())

    def __init__(self, log_func: Callable[[str], None], *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.log_func = log_func
        self.buffer = self._BytesBuffer(self)  # type: ignore[misc,assignment]

    def write(self, message: str) -> int:
        for line in message.splitlines(keepends=False):
            if stripped := line.strip():
                self.log_func(stripped)
        return 0


@contextmanager
def _redirect_output_to_logging(
    stdout_level: An[str, Doc("Log level for standard output.")] = "info",
    stderr_level: An[str, Doc("Log level for standard error.")] = "error",
) -> Iterator[None]:
    """Redirect standard output and error to logging."""
    with (
        closing(_TextBuffer(getattr(logger, stdout_level))) as new_stdout,
        closing(_TextBuffer(getattr(logger, stderr_level))) as new_stderr,
        redirect_stdout(new_stdout),
        redirect_stderr(new_stderr),
    ):
        yield


def _log_captured(
    text: An[str, Doc("The text to split and log.")],
    level: An[str, Doc("The log level to use.")] = "info",
    pkg: An[str | None, Doc("Extra `pkg` log metadata.")] = None,
) -> None:
    """Log captured text."""
    log = getattr(logger, level)
    for line in text.splitlines(keepends=False):
        log(_double_brackets(line), pkg=pkg)


def _tail(log_file: An[str, Doc("The log file to tail.")]) -> None:
    """Tail a log file."""
    with open(log_file) as file:
        try:
            while True:
                line = file.readline()
                if line:
                    print(line, end="")  # noqa: T201
                else:
                    time.sleep(0.5)
        except KeyboardInterrupt:
            return


def _update_record(record: Record) -> None:
    record["pkg"] = record["extra"].get("pkg") or (record["name"] or "").split(".", 1)[0]  # type: ignore[typeddict-unknown-key]


class _InterceptHandler(logging.Handler):
    def __init__(
        self,
        level: int = 0,
        include: tuple[str, ...] = (),
        exclude: tuple[str, ...] = (),
        downgrade: tuple[str, ...] = (),
    ) -> None:
        super().__init__(level)
        self.include = include
        self.exclude = exclude
        self.downgrade = downgrade

    def _main(self, record: logging.LogRecord) -> bool:
        return record.name.split(".", 1)[0] == "insiders"

    def _show(self, record: logging.LogRecord) -> bool:
        return self._main(record) or (self._included(record) and not self._excluded(record))

    def _included(self, record: logging.LogRecord) -> bool:
        return not self.include or (
            record.name in self.include or any(record.name.startswith(f"{included}.") for included in self.include)
        )

    def _excluded(self, record: logging.LogRecord) -> bool:
        return record.name in self.include or any(record.name.startswith(f"{hidden}.") for hidden in self.exclude)

    def _downgraded(self, record: logging.LogRecord) -> bool:
        return not self._main(record) and (
            not self.downgrade
            or (record.name in self.downgrade or any(record.name.startswith(f"{down}.") for down in self.downgrade))
        )

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists.
        try:
            level: str | int = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Prevent too much noise from dependencies.
        if not self._show(record):
            return
        if level == "INFO" and self._downgraded(record):
            level = "DEBUG"

        # Find caller from where originated the logged message.
        frame, depth = sys._getframe(6), 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore[assignment]
            depth += 1

        # Log the message, replacing new lines with spaces.
        message = record.getMessage().replace("\n", " ")
        _logger.opt(depth=depth, exception=record.exc_info).log(level, message)


_intercept_handler = _InterceptHandler()


def _configure_logging(
    level: An[str, Doc("Log level (name).")],
    path: An[str | Path | None, Doc("Log file path.")] = None,
    *,
    include: An[tuple[str, ...], Doc("List of package names for which to show logs.")] = (),
    exclude: An[tuple[str, ...], Doc("List of package names for which to hide logs.")] = (),
    downgrade: An[
        tuple[str, ...],
        Doc(
            """
            List of package names for which to allow log levels greater or equal to INFO level.
            Packages that are downgraded will see all their INFO logs demoted to DEBUG level.
            If unspecified, downgrade every dependency.
            """,
        ),
    ] = (),
) -> None:
    """Configure logging."""
    sink = path or sys.stderr
    log_level = {
        "TRACE": logging.DEBUG - 5,  # 5
        "DEBUG": logging.DEBUG,  # 10
        "INFO": logging.INFO,  # 20
        "SUCCESS": logging.INFO + 5,  # 25
        "WARNING": logging.WARNING,  # 30
        "ERROR": logging.ERROR,  # 40
        "CRITICAL": logging.CRITICAL,  # 50
    }.get(level.upper(), logging.INFO)
    _intercept_handler.include = include
    _intercept_handler.exclude = exclude
    _intercept_handler.downgrade = downgrade
    logging.basicConfig(handlers=[_intercept_handler], level=0, force=True)
    loguru_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | <cyan>{pkg}</cyan> - <level>{message}</level>"
    )
    handler = {"sink": sink, "level": log_level, "format": loguru_format}
    _logger.configure(handlers=[handler])  # type: ignore[list-item]


_logger = logger.patch(_update_record)
