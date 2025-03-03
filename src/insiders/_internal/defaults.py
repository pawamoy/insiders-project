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
