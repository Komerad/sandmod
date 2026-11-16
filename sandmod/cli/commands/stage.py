from pathlib import Path
from tempfile import TemporaryDirectory

from ...download import (
    StageError,
    download_modfile,
    extract_modfile,
)
from ...game import get_mods_path
from ...modio import get_mod


def sandmod_stage(
    api_key: str,
    game_id: int,
    platform: str,
    storage_root: Path,
    mod_id: int,
) -> int:
    remote = get_mod(
        game_id,
        mod_id,
        api_key,
        platform,
    )

    modfile = remote.get("modfile")

    if not modfile:
        print(f"No active release found for {platform}.")
        return 1

    try:
        url = modfile["download"]["binary_url"]
        md5 = modfile["filehash"]["md5"]
        filesize = modfile["filesize"]
        uncompressed_size = modfile["filesize_uncompressed"]

        if (
            not isinstance(url, str)
            or not isinstance(md5, str)
            or type(filesize) is not int
            or type(uncompressed_size) is not int
            or filesize <= 0
            or uncompressed_size <= 0
        ):
            print("mod.io returned invalid download metadata.")
            return 1

    except (KeyError, TypeError):
        print("Release is missing required download metadata.")
        return 1

    # Keep temporary files on the installation filesystem.
    work_parent = get_mods_path(
        game_id,
        storage_root,
    ).parent

    try:
        with TemporaryDirectory(
            prefix=".sandmod-",
            dir=work_parent,
        ) as temp_dir:
            work_dir = Path(temp_dir)

            archive = work_dir / "download.zip"
            staging = work_dir / "extracted"

            print(f"Staging: {remote['name']}")
            print(f"Version: {modfile['version']}")
            print(f"Download size: {filesize:,} bytes")

            print("\nDownloading...")
            download_modfile(url, archive, md5, filesize)
            print("Download verified.")

            print("\nValidating and extracting...")
            count = extract_modfile(
                archive,
                staging,
                uncompressed_size,
            )

            print("\nArchive contents:")

            for path in staging.rglob("*"):
                if path.is_file():
                    relative_path = path.relative_to(staging)
                    size = path.stat().st_size

                    print(f"  {relative_path} ({size:,} bytes)")

            print(f"Extracted {count} files successfully.")

        # TemporaryDirectory has cleaned up at this point.
        print("\nStaging successful. Temporary files removed.")
        return 0

    except (StageError, OSError) as exc:
        print(f"\nStaging failed: {exc}")
        return 1
