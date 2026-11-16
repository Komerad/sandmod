import argparse
import sys
from json import JSONDecodeError
from tomllib import TOMLDecodeError

from .. import __version__
from ..config import get_config_path, load_config
from ..credentials import get_api_key
from ..download import StageError
from ..install import InstallError
from ..modio import ModIOError
from . import commands as sandmod_commands


def main() -> int:
    try:
        return _run()

    except (ModIOError, StageError, InstallError) as exc:
        print(f"Sandmod: {exc}", file=sys.stderr)

    except (FileNotFoundError, PermissionError) as exc:
        print(f"Sandmod: filesystem error: {exc}", file=sys.stderr)

    except (JSONDecodeError, TOMLDecodeError) as exc:
        print(f"Sandmod: invalid state or configuration: {exc}", file=sys.stderr)

    return 1


def _run() -> int:
    parser = argparse.ArgumentParser(prog="sandmod")

    commands = parser.add_subparsers(
        dest="command",
        required=True,
    )

    init = commands.add_parser(
        "init",
        help="Configure sandmod for use",
    )
    init.add_argument("--reconfigure", action="store_true", help="Reconfigure existing settings")
    init.add_argument("--reauth", action="store_true", help="Reconfigure existing credentials")

    status = commands.add_parser(
        "status",
        help="View local info about a mod",
    )
    status.add_argument("mod_id", type=int)

    remote = commands.add_parser(
        "remote",
        help="Check remote info (modio) about a mod",
    )
    remote.add_argument("mod_id", type=int)

    check = commands.add_parser(
        "check",
        help="Check local mods against remote (modio)",
    )
    check.add_argument("mod_id", type=int, nargs="?")
    check.add_argument("--all", action="store_true")

    stage = commands.add_parser(
        "stage",
        help="Download and validate a mod without installing it",
    )
    stage.add_argument("mod_id", type=int)

    update = commands.add_parser(
        "update",
        help="Update a local mod",
    )
    update.add_argument("mod_id", type=int)
    update.add_argument("--force", action="store_true")

    commands.add_parser(
        "list",
        help="List info about all locally installed mods. (Summary)",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"sandmod {__version__}",
    )

    args = parser.parse_args()

    if args.command == "init":
        return sandmod_commands.init(args.reconfigure, args.reauth)

    modio_config, game_config = load_config()

    match args.command:
        case "status":
            return sandmod_commands.status(modio_config.game_id, game_config.storage_root, args.mod_id)
        case "remote":
            api_key = __require_api_key(parser)
            return sandmod_commands.remote(api_key, modio_config.game_id, modio_config.platform, args.mod_id)
        case "check":
            api_key = __require_api_key(parser)
            if not args.mod_id and not args.all:
                parser.error("Either mod_id or --all is required")
            return sandmod_commands.check(
                api_key, modio_config.game_id, modio_config.platform, game_config.storage_root, args.mod_id, args.all
            )
        case "list":
            return sandmod_commands.list(
                modio_config.game_id,
                game_config.storage_root,
            )
        case "stage":
            api_key = __require_api_key(parser)
            return sandmod_commands.stage(
                api_key,
                modio_config.game_id,
                modio_config.platform,
                game_config.storage_root,
                args.mod_id,
            )
        case "update":
            api_key = __require_api_key(parser)
            return sandmod_commands.update(
                api_key,
                modio_config.game_id,
                modio_config.platform,
                game_config.storage_root,
                args.mod_id,
                force=args.force,
            )
    return 0


def __require_api_key(parser: argparse.ArgumentParser) -> str:
    api_key = get_api_key(get_config_path().parent)

    if not api_key:
        parser.error("No mod.io API key configured. " "Run 'sandmod init' or set MODIO_API_KEY.")

    return api_key
