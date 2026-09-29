# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2023, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Default values throughout the project.

from __future__ import annotations

from pathlib import Path
from typing import Annotated as An

from platformdirs import user_cache_dir, user_config_dir, user_data_dir
from typing_extensions import Doc

_APP_NAME = "insiders"
_APP_AUTHOR = _APP_NAME

DEFAULT_PORT: An[int, Doc("The default index port.")] = 31411
DEFAULT_INDEX_URL: An[str, Doc("The default index URL.")] = f"http://localhost:{DEFAULT_PORT}"
DEFAULT_REPO_DIR: An[Path, Doc("The default Git repository (clones) cache directory.")] = Path(
    user_cache_dir(_APP_NAME, _APP_AUTHOR),
)
DEFAULT_DIST_DIR: An[Path, Doc("The default index distributions directory")] = Path(
    user_data_dir(_APP_NAME, _APP_AUTHOR),
)
DEFAULT_CONF_DIR: An[Path, Doc("The default configuration directory.")] = Path(user_config_dir(_APP_NAME))
DEFAULT_CONF_PATH: An[Path, Doc("The default configuration file path.")] = DEFAULT_CONF_DIR / "insiders.toml"
