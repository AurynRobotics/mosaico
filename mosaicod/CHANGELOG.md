# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Features

- Added optional Arrow IPC body buffer compression on outbound DoGet streams,
  selected by the `MOSAICOD_FLIGHT_IPC_COMPRESSION` environment variable
  (`none` default, `lz4`, or `zstd`). Column-aware and complementary to the
  gRPC-channel GZIP enabled by `--gzip`. Backward compatible: any Arrow Flight
  client with the matching codec linked decodes transparently.


## [0.3.0] - 2026-30-03

This release introduces a major transition to session-based ingestion, a comprehensive API key management system with hierarchical permissions, and significant security enhancements, including TLS support.

### Features

- Introduced a new session handling architecture to allow sequences updates, including server-side actions, added extensive documentation. 
- Established a formal API key permission hierarchy `Read < Write < Delete < Manage` and added comprehensive documentation.
- Added support for secure TLS connections, allowing for encrypted communication via environment variable configuration.
- Introduced `postgres` feature in `mosaicod-db` to expose postgres compatibility layer.
- Added `api-key` subcommand to `mosaicod` CLI.
- Added environment variables page in documentation, to list all env variables used.
- Splitted `mosaicod-repo` into `mosaicod-db` and `mosaicod-facade`
- Bump of several dependencies.


### Bug Fixes

- Modified Docker compose files to bind PostgreSQL and storage ports to `127.0.0.1` only, preventing external exposure to the internet.
- Resolved caching issues that occurred in DataFusion after a session was aborted.
- Standardized resource identification across the system to use the term *locator* consistently.

### Breaking Changes

- Removed `sequence_abort`


[unreleased]: https://github.com/mosaico-labs/mosaico/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/mosaico-labs/mosaico/compare/v0.2.6...v0.3.0
