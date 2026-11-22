import argparse
import sys
from json import JSONDecodeError
from tomllib import TOMLDecodeError

from .. import __version__
from ..config import get_config_path, load_config
from ..credentials import get_access_token, get_api_key
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

    for _register_func in __COMMAND_REGISTRARS:
        _register_func(commands)

    __register_version(parser)

    args = parser.parse_args()

    # Init needs to happen before config loads
    if args.command == "init":
        return sandmod_commands.init(args.reconfigure, args.reauth)

    # Issues doesn't require config
    if args.command == "issues":
        return sandmod_commands.issues(args.mod_id)

    modio_config, game_config = load_config()

    # Decision Maker
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
        case "quarantine":
            return sandmod_commands.quarantine(
                modio_config.game_id,
                game_config.storage_root,
                args.mod_id,
                dry_run=args.dry_run,
            )

        case "restore":
            return sandmod_commands.restore(
                modio_config.game_id,
                game_config.storage_root,
                args.mod_id,
                dry_run=args.dry_run,
            )
        case "subscriptions":
            access_token = __require_access_token(parser)
            return sandmod_commands.subscriptions(
                access_token,
                modio_config.game_id,
                game_config.storage_root if args.compare else None,
            )
    return 0


def __require_api_key(parser: argparse.ArgumentParser) -> str:
    api_key = get_api_key(get_config_path().parent)
    if not api_key:
        parser.error("No mod.io API key configured. " "Run 'sandmod init' or set MODIO_API_KEY.")
    return api_key


def __require_access_token(parser: argparse.ArgumentParser) -> str:
    access_token = get_access_token(get_config_path().parent)
    if not access_token:
        parser.error("No mod.io Personal Access Token configured. " "Set MODIO_ACCESS_TOKEN to use subscriptions.")
    return access_token


def __register_init(commands):
    init = commands.add_parser(
        "init",
        help="Configure sandmod for use",
    )
    init.add_argument("--reconfigure", action="store_true", help="Reconfigure existing settings")
    init.add_argument("--reauth", action="store_true", help="Reconfigure existing credentials")


def __register_status(commands):
    status = commands.add_parser(
        "status",
        help="View local info about a mod",
    )
    status.add_argument("mod_id", type=int)


def __register_remote(commands):
    remote = commands.add_parser(
        "remote",
        help="Check remote info (modio) about a mod",
    )
    remote.add_argument("mod_id", type=int)


def __register_check(commands):
    check = commands.add_parser(
        "check",
        help="Check local mods against remote (modio)",
    )
    check.add_argument("mod_id", type=int, nargs="?")
    check.add_argument("--all", action="store_true")


def __register_stage(commands):
    stage = commands.add_parser(
        "stage",
        help="Download and validate a mod without installing it",
    )
    stage.add_argument("mod_id", type=int)


def __register_update(commands):
    update = commands.add_parser(
        "update",
        help="Update a local mod",
    )
    update.add_argument("mod_id", type=int)
    update.add_argument("--force", action="store_true")


def __register_quarantine(commands):
    quarantine = commands.add_parser(
        "quarantine",
        help="Temporarily move an installed mod out of active storage",
    )
    quarantine.add_argument("mod_id", type=int)
    quarantine.add_argument("--dry-run", action="store_true")


def __register_restore(commands):
    restore = commands.add_parser(
        "restore",
        help="Restore a previously quarantined mod",
    )
    restore.add_argument("mod_id", type=int)
    restore.add_argument("--dry-run", action="store_true")


def __register_issues(commands):
    issues = commands.add_parser(
        "issues",
        help="Show recorded mod compatibility issues",
    )
    issues.add_argument("mod_id", type=int, nargs="?")


def __register_list(commands):
    commands.add_parser(
        "list",
        help="List info about all locally installed mods. (Summary)",
    )


def __register_subscriptions(commands):
    subscriptions = commands.add_parser(
        "subscriptions",
        help="List subscriptions for the authenticated mod.io account",
    )
    subscriptions.add_argument(
        "--compare",
        action="store_true",
        help="Compare subscriptions against locally tracked mods",
    )


def __register_version(parser: argparse.ArgumentParser):
    parser.add_argument(
        "--version",
        action="version",
        version=f"sandmod {__version__}",
    )


__COMMAND_REGISTRARS = [
    __register_check,
    __register_init,
    __register_issues,
    __register_list,
    __register_quarantine,
    __register_restore,
    __register_remote,
    __register_stage,
    __register_status,
    __register_subscriptions,
    __register_update,
]
