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


def _request_json(
    game_id: int,
    endpoint: str,
    params: dict,
    headers: dict,
) -> dict:
    try:
        response = requests.get(
            f"{_get_base_url(game_id)}{endpoint}",
            params=params,
            headers=headers,
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


def _get(
    game_id: int,
    endpoint: str,
    api_key: str,
    platform: str,
    params: dict | None = None,
) -> dict:
    return _request_json(
        game_id,
        endpoint,
        params={"api_key": api_key, **(params or {})},
        headers={
            "Accept": "application/json",
            "X-Modio-Platform": platform,
        },
    )


def _get_authenticated(
    game_id: int,
    endpoint: str,
    access_token: str,
    params: dict | None = None,
) -> dict:
    return _request_json(
        game_id,
        endpoint,
        params=params or {},
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
        },
    )


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


def validate_access_token(game_id: int, access_token: str) -> None:
    """Verify that a PAT can access the account's subscriptions."""
    _get_authenticated(
        game_id,
        "/me/subscribed",
        access_token,
        params={
            "game_id": game_id,
            "_limit": 1,
        },
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


def get_subscribed_mods(
    game_id: int,
    access_token: str,
) -> dict[int, dict]:
    """Retrieve all subscriptions for the authenticated user and game."""
    mods = {}
    offset = 0
    expected_total = None

    while True:
        result = _get_authenticated(
            game_id,
            "/me/subscribed",
            access_token,
            params={
                "game_id": game_id,
                "_limit": 100,
                "_offset": offset,
            },
        )

        if not isinstance(result, dict):
            raise ModIOError("mod.io returned invalid subscription data")

        page = result.get("data")
        total = result.get("result_total")

        if (
            not isinstance(page, list)
            or not isinstance(total, int)
            or total < 0
            or result.get("result_offset") != offset
            or result.get("result_count") != len(page)
        ):
            raise ModIOError("mod.io returned invalid subscription pagination data")

        if expected_total is None:
            expected_total = total
        elif total != expected_total:
            raise ModIOError("mod.io subscriptions changed during pagination; retry")

        if not page and offset < total:
            raise ModIOError("mod.io returned an incomplete subscription list")

        for mod in page:
            if not isinstance(mod, dict) or not isinstance(mod.get("id"), int) or mod.get("game_id") != game_id:
                raise ModIOError("mod.io returned invalid subscribed mod data")

            mods[mod["id"]] = mod

        offset += len(page)

        if offset >= total:
            if offset != total or len(mods) != total:
                raise ModIOError("mod.io returned inconsistent subscription results")

            return mods
