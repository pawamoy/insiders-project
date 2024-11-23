---
hide:
- feedback
---

--8<-- "README.md"

## Usage

```python exec="1" idprefix=""
import cappa
from cappa.base import collect
from cappa.help import generate_arg_groups

from insiders._internal.cli import CommandMain


def render_parser(command: cappa.Command, title: str, heading_level: int = 3) -> str:
    """Render the parser help documents as a string."""

    result = [f"{'#' * heading_level} **`{title}`**\n"]
    if command.help:
        result.append(f"> {command.help}\n")
    if command.description:
        result.append(f"{command.description}\n")

    for (name, _), args in sorted(generate_arg_groups(command)):
        result.append(f"*{name.title()}*\n")
        for arg in args:
            if isinstance(arg, cappa.Subcommand):
                for option in arg.options.values():
                    result.append(
                        render_parser(option, option.real_name(), heading_level + 1)
                    )
                continue

            opts = [f"`{opt}`" for opt in arg.names()]
            if not opts:
                line = f"- `{arg.field_name}`"
            else:
                line = f"- {', '.join(opts)}"

            line += f" `{arg.value_name.upper()}`" if arg.num_args else ""
            line += f": {arg.help}"
            if arg.default is not cappa.Arg.default:
                default = str(arg.default)
                line += f" Default: `{default}`."
            result.append(line)
        result.append("")

    return "\n".join(result)


command = collect(CommandMain, help=False, completion=False)
print(render_parser(command, "insiders"))
```
