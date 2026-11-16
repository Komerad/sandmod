import requests


class ModIOError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code


def _get_base_url(game_id):
    return f"https://g-{game_id}.modapi.io/v1"


def _get(
    game_id: int,
    endpoint: str,
    api_key: str,
    platform: str,
    params: dict | None = None,
) -> dict:
    try:
        response = requests.get(
            f"{_get_base_url(game_id)}{endpoint}",
            params={"api_key": api_key, **(params or {})},
            headers={
                "Accept": "application/json",
                "X-Modio-Platform": platform,
            },
            timeout=(5, 30),
        )
    except requests.RequestException:
        raise ModIOError("Could not connect to mod.io") from None

    if not response.ok:
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            message = "mod.io rate limit reached"

            if retry_after:
                message += f". Retry after: {retry_after}"

        elif response.status_code == 403:
            message = "mod.io returned 403 forbidden. The item may be hidden or inaccessible"

        elif response.status_code == 404:
            message = "mod.io returned 404 not found. Verify the mod_id is correct"

        else:
            message = f"mod.io returned HTTP {response.status_code}"

        raise ModIOError(
            message,
            status_code=response.status_code,
        )

    try:
        return response.json()
    except ValueError:
        raise ModIOError("mod.io returned invalid JSON") from None


def validate_api_key(
    game_id: int,
    api_key: str,
    platform: str,
) -> None:
    _get(
        game_id,
        f"/games/{game_id}",
        api_key,
        platform,
    )


def get_mod(
    game_id: int,
    mod_id: int,
    api_key: str,
    platform: str = "windows",
) -> dict:
    """Retrieve a mod and its active platform-specific release."""
    return _get(
        game_id,
        f"/games/{game_id}/mods/{mod_id}",
        api_key,
        platform,
    )


def get_modfiles(
    game_id: int,
    mod_id: int,
    api_key: str,
    platform: str = "windows",
) -> list[dict]:
    """Retrieve published modfiles for the selected platform."""
    files = []
    offset = 0

    while True:
        result = _get(
            game_id,
            f"/games/{game_id}/mods/{mod_id}/files",
            api_key,
            platform,
            params={"_offset": offset, "_limit": 100},
        )

        page = result["data"]
        files.extend(page)
        offset += len(page)

        if not page or offset >= result["result_total"]:
            break

    return files


def get_mods(
    game_id: int,
    mod_ids: list[int],
    api_key: str,
    platform: str,
) -> dict[int, dict]:
    """Retrieve current mod metadata, indexed by mod ID."""

    mods = {}

    for start in range(0, len(mod_ids), 100):
        batch = mod_ids[start : start + 100]
        offset = 0

        while True:
            response = _get(
                game_id,
                f"/games/{game_id}/mods",
                api_key,
                platform,
                params={
                    "id-in": ",".join(str(mod_id) for mod_id in batch),
                    "_limit": 100,
                    "_offset": offset,
                },
            )

            page = response["data"]

            for mod in page:
                mods[mod["id"]] = mod

            offset += len(page)

            if not page or offset >= response["result_total"]:
                break

    return mods
