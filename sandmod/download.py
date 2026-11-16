import hashlib
import shutil
import stat
from pathlib import Path, PurePosixPath
from zipfile import BadZipFile, ZipFile

import requests


class StageError(RuntimeError):
    pass


def _invalid_windows_name(name: str) -> bool:
    if not name or name.endswith((" ", ".")):
        return True

    invalid_chars = '<>:"\\|?*'

    if any(ord(char) < 32 or char in invalid_chars for char in name):
        return True

    device = name.split(".", 1)[0].rstrip(" ").upper()

    if device in {"CON", "PRN", "AUX", "NUL"}:
        return True

    if len(device) == 4 and device[:3] in {"COM", "LPT"} and device[3] in "123456789":
        return True

    return False


def download_modfile(
    url: str,
    destination: Path,
    expected_md5: str,
    expected_size: int,
) -> None:
    """Download an archive and verify its size and MD5."""

    digest = hashlib.md5(usedforsecurity=False)
    downloaded = 0
    created = False
    complete = False

    try:
        with requests.get(
            url,
            stream=True,
            timeout=(10, 60),
        ) as response:
            if response.status_code != 200:
                raise StageError(f"Download returned HTTP {response.status_code}")

            with destination.open("xb") as output:
                created = True

                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if not chunk:
                        continue

                    downloaded += len(chunk)

                    if downloaded > expected_size:
                        raise StageError("Download exceeds expected file size")

                    output.write(chunk)
                    digest.update(chunk)

        if downloaded != expected_size:
            raise StageError(f"Download incomplete: " f"{downloaded}/{expected_size} bytes")

        if digest.hexdigest().lower() != expected_md5.lower():
            raise StageError("Download checksum does not match mod.io")

        complete = True

    except requests.RequestException:
        # The download URL might contain a temporary signature.
        raise StageError("Network error while downloading modfile") from None

    finally:
        if created and not complete:
            destination.unlink(missing_ok=True)


def extract_modfile(
    archive: Path,
    staging: Path,
    expected_uncompressed_size: int,
) -> int:
    """Extract a verified archive into a new staging directory."""

    staging.mkdir()
    count = 0

    try:
        with ZipFile(archive) as zip_file:
            entries = []
            total_size = 0

            # Inspect everything before extracting anything.
            for info in zip_file.infolist():
                name = info.filename
                rel_path = PurePosixPath(name)
                parts = rel_path.parts

                if not parts and info.is_dir():
                    continue

                if (
                    not parts
                    or rel_path.is_absolute()
                    or ".." in parts
                    or any(_invalid_windows_name(part) for part in parts)
                    or stat.S_ISLNK(info.external_attr >> 16)
                ):
                    raise StageError(f"Unsafe archive entry: {name!r}")

                if not info.is_dir():
                    total_size += info.file_size

                    if total_size > expected_uncompressed_size:
                        raise StageError("Archive exceeds published " "uncompressed size")

                entries.append((info, parts))

            # Everything looks acceptable. Extract.
            for info, parts in entries:
                target = staging.joinpath(*parts)

                if info.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue

                target.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                with zip_file.open(info) as source:
                    with target.open("xb") as output:
                        shutil.copyfileobj(
                            source,
                            output,
                            length=1024 * 1024,
                        )

                count += 1

    except StageError:
        raise
    except (
        BadZipFile,
        RuntimeError,
        EOFError,
        NotImplementedError,
    ):
        raise StageError("Invalid or unsupported ZIP archive") from None

    if count == 0:
        raise StageError("Archive contains no files")

    return count
