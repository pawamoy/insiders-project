"""Generate the CLI reference in Markdown."""

import getpass
import re

import cappa
import mkdocs_gen_files
from cappa.base import collect
from cappa.help import generate_arg_groups

from insiders._internal.cli import CommandMain

nav = mkdocs_gen_files.Nav()


def _repl_config(match: re.Match) -> str:
    config_key = match.group(1).strip("`")
    config_attr = config_key.replace("-", "_").replace(".", "_")
    return f"[`{config_key}`][insiders._internal.config.Config.{config_attr}]"


def render_parser(command: cappa.Command, title: str, page: str, heading_level: int = 1, layer: int = 1) -> str:
    """Render the parser help documents as a string."""
    result = [f"{'#' * heading_level} **`{title}`**\n"]
    if command.help:
        result.append(f"> {command.help}\n")
    if command.description:
        result.append(f"{command.description}\n")

    for (name, _), args in sorted(generate_arg_groups(command)):
        if name.lower() == "global options" and layer > 1:
            continue
        if name.lower() != "subcommands":
            result.append(f"{name.title()} | Description | Default")
            result.append("--- | --- | ---")
        for arg in args:
            if isinstance(arg, cappa.Subcommand):
                for option in arg.options.values():
                    title = option.real_name()
                    markdown = render_parser(option, title, f"command-{title}.md", heading_level + 1, layer + 1)
                    if layer >= 2:  # noqa: PLR2004
                        result.append(markdown)
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

    markdown = "\n".join(result)

    if layer < 3:  # noqa: PLR2004
        nav[page[:-3]] = page
        markdown = re.sub(rf"\b{re.escape(getpass.getuser())}\b", "user", markdown)
        with mkdocs_gen_files.open(f"cli/{page}", "w") as fd:
            fd.write(markdown)

        mkdocs_gen_files.set_edit_path(f"cli/{page}", "scripts/gen_cli_reference.py")

    return markdown


command = collect(CommandMain, help=False, completion=False)
render_parser(command, "insiders", "index.md")

with mkdocs_gen_files.open("cli/SUMMARY.md", "w") as nav_file:
    nav_file.writelines(nav.build_literate_nav())
