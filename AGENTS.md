# Viewer source and builds

This repository is the only maintained Plan Viewer source. The Scoville Suite
owns Skills and Plan helpers; do not copy the application back into it.

Native builds run only in this repository's GitHub Actions for Windows x64,
Linux x64, macOS Apple Silicon and macOS Intel. Do not install Rust or compile
native bundles locally. Frontend and Python checks may run locally.

Preserve Plan format version 1, read-only project access and users' XML project
lists. Change no dependency or application behavior merely for publication.
Release downloads must pass scripts/verify_release.py before and after upload.
