# Sandmod v0.1.0a6

Alpha release introducing bulk quarantine and subscription-aware cleanup for Insurgency: Sandstorm mod installations.

### Added

- Support for quarantining multiple mods in a single command, with dry-run previews and explicit confirmation.
- `subscriptions --cleanup` command to identify and selectively quarantine locally installed mods absent from the authenticated account's subscriptions.
- `subscriptions --cleanup --dry-run` to preview selected cleanup operations without modifying files.
- Interactive candidate selection with validation of selected entries.

### Improvements

- Reuse existing quarantine validation, locking, and recovery safeguards for bulk operations.
- Validate selected installations before executing quarantine operations.
- Report completed operations and stop execution when a bulk quarantine fails.
- Exclude missing, quarantined, and unknown installations from subscription-aware cleanup candidates.
- Expand automated tests for bulk execution, cancellation, invalid selections, partial failures, and CLI dispatch.

### Notes

- Bulk quarantine is not atomic. Previously completed operations remain quarantined if a later operation fails.
- Cleanup uses reversible filesystem quarantine. No permanent deletion is performed.
- Mod.io subscriptions and SDK `state.json` metadata remain unchanged.
- Unsubscribed installations may still be required by servers or map rotations and should be reviewed before quarantine.
- Existing single-mod quarantine, restore, and installation behavior remains unchanged.

### Known limitations

- Permanent uninstallation, destructive purge, and subscription modification are not yet implemented.
- Quarantined mods may be redownloaded by Sandstorm when required or subscribed.
- A graphical interface is planned but not yet available.
- Cross-platform compatibility testing remains ongoing.


# Sandmod v0.1.0a5

Alpha release introducing authenticated mod.io subscription discovery and local installation comparison.

### Added

- `subscriptions` command to retrieve and list mods subscribed to by an authenticated mod.io account.
- `subscriptions --compare` to compare account subscriptions against locally tracked mod installations.
- Optional mod.io Personal Access Token (PAT) configuration during `init`.
- Authenticated mod.io API requests with paginated subscription retrieval.
- Subscription comparison reporting present, missing, quarantined, unknown, and untracked local installations.

### Improvements

- Reuse existing credential storage mechanisms for API keys and PATs.
- Handle Windows Credential Manager size limitations with an optional plaintext `.env` fallback.
- Detect incomplete or inconsistent subscription API responses rather than returning partial results.
- Reorganize CLI command registration and dispatch for maintainability.
- Update development reset tooling to clear PAT credentials.
- Expand automated test coverage for authentication, credential persistence, pagination, and subscription comparison.

### Notes

- Subscription discovery is read-only. No mods are installed, removed, quarantined, subscribed, or unsubscribed during comparison.
- Subscription membership reflects the account associated with the configured PAT, which may differ from the account used by Sandstorm's SDK.
- Locally installed mods without matching subscriptions are identified for review, not automatically considered safe to remove.
- Existing mod installation, update, quarantine, and restore behavior remains unchanged.

### Known limitations

- Subscription management, bulk cleanup, and permanent uninstallation are not yet implemented.
- Large mod.io PATs may exceed Windows Credential Manager storage limits and require the optional plaintext `.env` fallback.
- Cross-platform compatibility testing remains ongoing.


# Sandmod v0.1.0a4

Maintenance release following the initial public alpha.

### Fixed
- Include license and documentation in portable release archives.
- Handle missing/null modfile metadata in the `status` command.
- Correct README configuration-path documentation.

### Maintenance
- Remove redundant installation-status checks.
- Clean up obsolete commented-out implementation code.

### Notes
- No changes to mod installation, quarantine, or restore behavior.
- Subscription management and bulk cleanup remain planned features.

# Sandmod v0.1.0a3

Pre-release update to Sandmod, a cross-platform CLI for managing Insurgency: Sandstorm mod installations.

### Added

- `quarantine` and `restore` commands with dry-run support.
- Quarantine manifests for reversible local mod removal.
- Quarantine-aware reporting in `list`, `status`, and `check`.
- Version-specific compatibility issue registry.
- `issues` command for viewing known problems.
- Compatibility warnings for affected installed mod versions.
- SAW-targeted Linux build using a Debian 12 environment.

### Improvements

- Reuse existing installation locking and path-validation safeguards.
- Prevent restoration from overwriting redownloaded mod installations.
- Preserve mod.io SDK metadata during quarantine operations.
- Expanded automated test coverage.

### Known limitations

- Subscription management and permanent uninstall are not implemented.
- Quarantined mods may be downloaded again by Sandstorm.
- SDK installation records may remain present after quarantine.
- A GUI is not yet available.
- Runtime compatibility across Windows/Linux systems is still being evaluated.

### Compatibility findings

**Mud Village (448415), version 1.9**

Observed reproducible map-loading crashes affecting Hydro and Assault on November 15, 2026.

Quarantining Mud Village on the affected client resolved both reproduced crashes. The underlying asset conflict has not been conclusively identified.

### Testing and feedback

This is alpha software. Back up important mod installations before modifying them.

Please include the operating system, command, relevant output, and reproduction steps when reporting a problem.

# Sandmod v0.1.0a1

Initial alpha release of Sandmod, a command-line utility for managing Insurgency: Sandstorm mods through mod.io.

### Included
- Interactive configuration and mod.io authentication
- Local mod listing and inspection
- Remote version checking
- Verified mod downloads and archive extraction
- Staged installation updates with rollback and recovery safeguards
- Windows and Linux executables

### Known limitations
- Updates existing registered mods only
- No bulk updates, fresh installation, or GUI
- Stop the game/server before modifying installations
- Windows and Linux compatibility testing is ongoing

**Alpha software:** Back up your installations before testing. Please report reproducible failures with the platform, command, and relevant error output.
