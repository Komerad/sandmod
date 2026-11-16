
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
