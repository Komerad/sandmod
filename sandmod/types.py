from __future__ import annotations

import typing


class StateDictType(typing.TypedDict):
    Mods: list[ModDictType]
    version: int


class ModDictType(typing.TypedDict):
    ID: int
    NeverRetryCategory: int
    NeverRetryCode: int
    PathOnDisk: str
    Profile: ModProfileType
    SizeOnDisk: int
    State: int
    SubscriptionCount: list[int]


class ModProfileType(typing.TypedDict):
    date_added: int
    date_live: int
    date_updated: int
    description: str
    description_plaintext: str
    id: int
    logo: str
    maturity_option: int
    media: ProfileMediaType
    metadata_blob: str
    metadata_kvp: list
    modfile: dict
    name: str
    profile_url: str
    stats: dict
    status: int
    submitted_by: dict
    summary: str
    tags: list[dict]
    visible: int


class ProfileMediaType(typing.TypedDict):
    images: list[str]
    sketchfab: list[str]
    youtube: list[str]
