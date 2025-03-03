"""Generate the CLI reference in Markdown."""

import getpass
import re

import cappa
from cappa.base import collect
from cappa.help import generate_arg_groups

from insiders._internal.cli import CommandMain, CommandBacklog, CommandIndex, CommandProject, CommandSponsors


def _repl_config(match: re.Match) -> str:
    config_key = match.group(1).strip("`")
    config_attr = config_key.replace("-", "_").replace(".", "_")
    return f"[`{config_key}`][insiders._internal.config.Config.{config_attr}]"


def _render_parser(command: cappa.Command, title: str, heading_level: int = 1, *, recursive: bool = True) -> str:
    result = [f"{'#' * heading_level} **`{title}`**\n"]
    if command.help:
        result.append(f"> {command.help}\n")
    if command.description:
        result.append(f"{command.description}\n")

    for (name, _), args in sorted(generate_arg_groups(command)):
        if name.lower() != "subcommands":
            result.append(f"{name.title()} | Description | Default")
            result.append("--- | --- | ---")
        for arg in args:
            if isinstance(arg, cappa.Subcommand):
                for option in arg.options.values():
                    title = option.real_name()
                    if recursive:
                        result.append(_render_parser(option, title, heading_level + 1, recursive=True))
                continue

            line = ""
            if name.lower() != "arguments":
                opts = [f"`{opt}`" for opt in arg.names()]
                line += f"`{arg.field_name}`" if not opts else ", ".join(opts)

            line += f" `{arg.value_name.upper()}`" if isinstance(arg.value_name, str) and arg.num_args else ""
            line += f" | {arg.help} | "
            default = arg.show_default.format_default(  # type: ignore[union-attr]
                arg.default,  # type: ignore[arg-type]
                default_format="{default}",
            )
            if default:
                default = re.sub(r"(`(backlog|index|project|sponsors)\.[^`]+`)", _repl_config, default)
                line += default
            result.append(line)
        result.append("")

    return re.sub(rf"\b{re.escape(getpass.getuser())}\b", "user", "\n".join(result))


def render_cli(command: str, *, recursive: bool = True) -> str:
    dataclass = {
        "insiders": CommandMain,
        "backlog": CommandBacklog,
        "index": CommandIndex,
        "project": CommandProject,
        "sponsors": CommandSponsors,
    }[command]
    cappa_command: cappa.Command = collect(dataclass, help=False, completion=False)
    return _render_parser(cappa_command, command, recursive=recursive)
