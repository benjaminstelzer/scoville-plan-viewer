# Scoville Plan Viewer

A local, read-only desktop viewer for Scoville Plan format version 1 projects.
It shows the active Plan point, completed and upcoming work, current Decisions,
and superseded Decision history across a saved list of project folders.

## Run the Viewer

Download the executable or installer for your platform from a successful
GitHub Actions `Plan Viewer` run. Native builds run only on GitHub, for
Windows x64, Linux x64, macOS Apple Silicon and macOS Intel. Do not install
Rust or compile the native Viewer locally.

The folder picker accepts a project root containing `PROJECT_INDEX.md`,
`docs/plans`, and `docs/decisions`. The portable project list is stored as
`scoville-plan-viewer.xml` next to the executable. Removing an entry does not
edit its repository. On macOS the file sits beside the `.app` bundle. An
AppImage uses its outer `APPIMAGE` location instead of the read-only runtime
mount. When an installer places the application in a read-only system folder,
the same XML file is stored in the platform user configuration directory.

## Interface system

The interface uses current shadcn-svelte components and tokens with Svelte 5,
Tailwind CSS 4, Bits UI primitives, Inter, and Lucide icons. Local CSS owns only
the viewer layout and the domain-specific Plan and Decision status
visualization.

## Validation

The suite-root and standalone-member GitHub Actions workflows check the
frontend, test the project reader, build all four platform bundles and create
`SHA256SUMS.txt`. Dispatch the workflow on the branch containing the intended
Viewer changes. Download all platform artifacts and verify their checksums
before retaining the build under `skills/temp/release/viewer/`.

These workflows do not publish a release. Platform signing and notarization
are outside this development build. Compilation, tests and packaging do not
verify runtime behavior on each platform.
