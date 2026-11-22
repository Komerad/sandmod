# Sandmod

A lightweight, cross-platform command-line tool for managing **Insurgency: Sandstorm** mods distributed through [mod.io](https://mod.io).

Sandmod provides a way to inspect locally installed mods, compare their versions against active mod.io releases, and safely update existing installations without relying on the game's built-in update process.


**Downloads:** [GitHub Releases](https://github.com/Komerad/sandmod/releases)

Sandmod is currently in alpha. Prebuilt executables are available for Windows, Linux, and Debian 12-based SAW environments.


### Features

- **Local inspection:** List installed mods, inspect metadata, and identify missing or quarantined installations.
- **Update checking:** Compare locally recorded mod versions against active mod.io releases.
- **Subscription visibility:** List an authenticated mod.io account's subscriptions and compare them against locally tracked installations.
- **Download validation:** Download, verify, and extract mod archives without installing them.
- **Safe updates:** Stage replacements before updating an existing installation, with rollback and recovery safeguards.
- **Quarantine and restore:** Temporarily remove a mod from active storage and restore it without changing mod.io SDK metadata.
- **Known compatibility issues:** Identify version-specific problems reported during testing.
- **Cross-platform builds:** Windows, Linux, and a Debian 12-based build intended for SAW servers.

### Current limitations

Sandmod is an early CLI alpha, not a replacement for the game's mod.io client.

- Updates support existing, registered installations only.
- Subscription discovery is read-only. Subscribing, unsubscribing, bulk cleanup, and permanent uninstallation are not yet implemented.
- Quarantine does not unsubscribe a mod or edit mod.io's `state.json`. The game may redownload quarantined content.
- Update checks compare recorded release metadata; they do not verify the integrity of every installed file.
- Stop the game and any servers sharing the mod storage before modifying installations.
- A graphical interface is planned but not available.
- Portable builds still require testing across different systems.


## Requirements

To run Sandmod from source, you'll need:

- Python 3.11 or newer
- An existing Insurgency: Sandstorm mod.io installation
- A mod.io API key
- Windows or Linux

Sandmod uses the following Python dependencies, managed through `requirements.txt`:

- `requests` — mod.io API requests and downloads
- `keyring` — operating-system credential storage
- `python-dotenv` — optional local credential fallback

Prebuilt executables will not require a separate Python installation.

## Getting Started

### 1. Install dependencies

Clone the Sandmod repository and navigate into its directory.

```bash
python -m pip install -r requirements.txt
```

On systems where Python is invoked as `python3`, substitute that command accordingly.

### 2. Initialize Sandmod

Run the interactive setup:

```bash
python -m sandmod init
```

The setup process will ask for:

- **Platform:** `windows`, `linux`, `windowsserver`, or `linuxserver`
- **Game ID:** Defaults to `254` for Insurgency: Sandstorm
- **Storage root:** The directory containing your mod.io game storage
- **mod.io API key:** Obtain one at https://mod.io/me/access
- **mod.io Personal Access Token (optional):** A read-only PAT enables authenticated subscription discovery and comparison. Obtain one at https://mod.io/me/access.

The storage root must point to an existing installation. Sandmod checks for the expected `state.json` file before accepting the configuration.

For example, a Windows installation might use:

```text
C:\Users\Public\mod.io
```

Sandmod then looks for the state file at:

```text
C:\Users\Public\mod.io\254\metadata\state.json
```

Successful setup creates sandmod.toml beside the application: in the repository root when running from source, or beside the executable when using a portable build.

Sandmod uses two separate mod.io credentials:

- **API key (`MODIO_API_KEY`):** Used for public mod metadata, downloads, and update checks.
- **Personal Access Token (`MODIO_ACCESS_TOKEN`):** Optional, used to retrieve subscriptions for the authenticated mod.io account.

Credentials are retrieved from environment variables, the operating system's credential store, or a local `.env` file, in that order.

During `init`, Sandmod validates existing credentials and optionally offers to configure a PAT. If the operating system's credential store cannot save a credential, Sandmod offers a plaintext `.env` fallback with explicit confirmation.

Windows Credential Manager has a credential size limit that may prevent storing large mod.io PATs. The `.env` fallback allows these tokens to be used without modifying them.

Keep credential files private and do not distribute them with Sandmod.

### 3. Verify your installation

List the mods registered in your local installation:

```bash
python -m sandmod list
```

Check for available updates:

```bash
python -m sandmod check --all
```

You can now inspect individual mods, stage downloads, and perform updates using the commands described below.

## Commands

All commands can be run with `python -m sandmod` from the project directory.

| Command | Description |
|---|---|
| `init` | Configure Sandmod and mod.io credentials |
| `list` | List locally registered mods |
| `status <mod_id>` | Show local installation details |
| `remote <mod_id>` | Show the active mod.io release |
| `check <mod_id>` | Check an individual mod for updates |
| `check --all` | Check all locally registered mods |
| `stage <mod_id>` | Download, validate, and extract a release without installing |
| `update <mod_id>` | Update an existing mod installation |
| `update <mod_id> --force` | Reinstall even when the recorded release is current |
| `quarantine <mod_id>` | Move a mod out of active storage, preserving recovery metadata |
| `quarantine <mod_id> --dry-run` | Preview quarantine without changing files |
| `restore <mod_id>` | Restore a previously quarantined installation |
| `restore <mod_id> --dry-run` | Preview restoration |
| `issues [mod_id]` | Show recorded version-specific compatibility problems |
| `subscriptions` | List mods subscribed to by the authenticated PAT account |
| `subscriptions --compare` | Compare subscriptions against locally tracked installations |


### Subscription visibility

Sandmod can retrieve subscriptions for a mod.io account using an optional Personal Access Token (PAT).

List the account's subscriptions:

```bash
python -m sandmod subscriptions
```

Compare subscriptions against locally tracked installations:

```bash
python -m sandmod subscriptions --compare
```

The comparison displays each mod's subscription membership and local installation status, including present, missing, quarantined, unknown, and not-tracked installations.

Mods present locally but absent from the subscription list are shown first to help identify cleanup candidates.

**Important considerations:**

- Subscriptions belong to the account associated with the PAT, which may differ from the account used by Sandstorm's SDK.
- A mod that is not subscribed may still be required by a server, map rotation, or another installation.
- Subscription comparison does not download, remove, quarantine, subscribe, or unsubscribe any mods.
- Sandmod does not modify `state.json` during subscription discovery.

A PAT is not required for normal installation inspection, update checking, or quarantine operations.


### Updating a mod

```bash
python -m sandmod check --all
python -m sandmod update 123456
```

Replace `123456` with the mod.io mod ID.

Sandmod downloads and verifies the replacement before requesting confirmation to install it.

**Important:** Stop the game and any servers using the same mod storage before confirming an update.

The `stage` command is useful for testing downloads and archive validation independently. It removes its temporary files afterward and does not change the installation.


### Quarantine and restore

Quarantine temporarily removes a mod from active storage without deleting its files or changing mod.io SDK metadata.

Preview the operation first:

```bash
python -m sandmod quarantine 448415 --dry-run
```

Quarantine the installation:

```bash
python -m sandmod quarantine 448415
```

Restore it later:

```bash
python -m sandmod restore 448415
```

Sandmod records the original installation location and refuses to overwrite an existing destination during restoration.

**Important:** Quarantine does not unsubscribe a mod. Sandstorm may download it again if the mod is still required or subscribed. Both operations require confirmation, and the game or server must be stopped.

### Known compatibility issues

Sandmod includes a small registry of observed compatibility problems.

```bash
python -m sandmod issues
python -m sandmod issues 448415
```

Known issues are matched by mod ID and version. They are informational warnings, not automatic blacklists.

### Portable executables

GitHub Releases provides separate builds for Windows, Linux, and SAW-compatible Linux environments.

For example, with the Windows executable:

```powershell
.\sandmod.exe --version
.\sandmod.exe init
.\sandmod.exe list
```

Portable executables do not require a separate Python installation.


## License

Copyright (C) 2026 Komerad

Sandmod is free software licensed under the **GNU General Public License, version 3.0 only (GPL-3.0-only)**.

You are free to use, study, modify, and redistribute Sandmod under the terms of the GPL. Modified versions distributed to others must also comply with the GPL, including its source-code requirements.

See [LICENSE](LICENSE) for the full terms.

Sandmod is an independent community project and is not affiliated with or endorsed by New World Interactive, Focus Entertainment, or mod.io.
