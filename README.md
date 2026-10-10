# Scoville Plan Viewer

Long work leaves its decisions and progress in more than one project. Scoville
Plan Viewer reads those local records and shows what is current, finished or
still open. The application has its own builds and updates, separate from the
Scoville Plan Skill.

## How it works

- Add project folders containing `PROJECT_INDEX.md`, `docs/plans` and `docs/decisions`.
- Browse Plans, Step progress and current or superseded Decisions.
- Refresh the displayed records automatically while the application is active.

## What it enforces

- Projects are read-only. Removing an entry from the Viewer leaves its files alone.
- Release downloads come from four platform builds and include SHA-256 checksums.

## What it costs

- Keep local project paths accessible and use a Viewer that supports your Plan format.

## How it was developed

The Viewer grew alongside Scoville Plan to make repository records easier to
read across sessions. It now lives here so application builds can evolve without
turning every Skill correction into an installer release. Scoville measures
chili heat; the Viewer makes the resulting paperwork easier to digest.

## Compatibility

Reads Scoville Plan `format_version: 1` records, including explicit Step progress.
Builds target Windows x64, Linux x64, macOS Apple Silicon and macOS Intel.

## Install

Download the application or installer for your platform from
[the latest release](https://github.com/benjaminstelzer/scoville-plan-viewer/releases/latest).
Windows provides a portable EXE, MSI and setup EXE. Linux provides a portable
binary, AppImage, DEB and RPM. Each macOS architecture has a zipped app and DMG.
Use `SHA256SUMS.txt` to check the downloaded file.

## Configuration

Portable copies store `scoville-plan-viewer.xml` beside the executable or macOS
app bundle. An AppImage uses its outer location. An installation in a read-only
system folder stores that list in the platform user configuration directory.
Keep your existing XML file when replacing the application.

## Limitations

Platform signing and notarization are not included. Successful builds do not
establish runtime behavior on every supported operating system.

## How to use

Open the Viewer, add a project folder and select a Plan. Its current point,
remaining Steps and Decisions come from the repository records. The Viewer
does not dispatch agents or edit Plans.

## Related projects

- [Scoville Plan Skill](https://github.com/benjaminstelzer/scoville-plan)
- [Scoville Suite](https://github.com/benjaminstelzer/scoville-suite)
- [Scoville Suite for Codex](https://github.com/benjaminstelzer/scoville-suite-for-codex)

## Developer links

See [the build and release guide](development/README.md). Future native builds
use this repository's `Plan Viewer` GitHub Actions workflow.

## License

MIT. See [LICENSE](LICENSE).
