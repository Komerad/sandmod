# Sandmod

A lightweight, cross-platform command-line tool for managing **Insurgency: Sandstorm** mods distributed through [mod.io](https://mod.io).

Sandmod provides a way to inspect locally installed mods, compare their versions against active mod.io releases, and safely update existing installations without relying on the game's built-in update process.

### Features

- **Local inspection:** List installed mods and examine their recorded installation metadata.
- **Update checking:** Compare installed modfile versions against the active releases for a configured platform.
- **Download validation:** Download, verify, and extract mod archives without installing them.
- **Safe updates:** Stage replacement files before updating an existing installation, retaining backups when recovery is necessary.
- **Platform selection:** Support mod.io release selection for Windows, Linux, and their server variants.

### Current limitations

Sandmod is an early CLI alpha with deliberately limited scope.

- Updates are supported for existing, registered mod installations only.
- Fresh mod installation and bulk updating are not implemented.
- The game and any servers sharing the installation must be stopped before updating.
- A graphical interface is not yet available.
- Linux and Windows portable builds require platform-specific validation before being considered verified.

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

The storage root must point to an existing installation. Sandmod checks for the expected `state.json` file before accepting the configuration.

For example, a Windows installation might use:

```text
C:\Users\Public\mod.io
```

Sandmod then looks for the state file at:

```text
C:\Users\Public\mod.io\254\metadata\state.json
```

Successful setup creates `sandmod.toml` in the Sandmod source directory and validates your mod.io credentials.

API keys are stored in your operating system's credential store when available. Alternatively, Sandmod can use the `MODIO_API_KEY` environment variable or, with your permission, a local `.env` file.

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

### Updating a mod

```bash
python -m sandmod check --all
python -m sandmod update 123456
```

Replace `123456` with the mod.io mod ID.

Sandmod downloads and verifies the replacement before requesting confirmation to install it.

**Important:** Stop the game and any servers using the same mod storage before confirming an update.

The `stage` command is useful for testing downloads and archive validation independently. It removes its temporary files afterward and does not change the installation.
