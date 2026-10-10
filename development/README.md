# Build and release

The application source is at the repository root. Frontend development uses
Node.js 22 and npm. Run `npm ci`, then `npm run check` or `npm run dev`.
Use Python 3.11+ and run `python -B -m unittest discover -s tests` for the release verifier.

Dispatch `.github/workflows/plan-viewer.yml` on the intended committed branch.
It checks the frontend and Rust project reader, builds all four platform bundles
and creates `SHA256SUMS.txt`. Do not install Rust or build native bundles locally.

Download the eleven binaries and checksums from that successful Actions run into
a new, empty folder outside the repository under `skills/temp/release/`
(for example `skills/temp/release/scoville-plan-viewer/`). Add `BUILD.json`
with its `version`, `platforms`, `workflow_run` and exact `source_commit`.

Before upload:

```text
python scripts/verify_release.py --assets-root <staging-folder>
```

Create an annotated tag matching the Viewer version on that exact published
commit. Publish the twelve verified download files, excluding local `BUILD.json`.
After upload:

```text
python scripts/verify_release.py --assets-root <staging-folder> --release benjaminstelzer/scoville-plan-viewer=vX.Y.Z
```

The gate compares version owners, complete binary inventory, checksums, current
build inputs, successful Actions jobs and their artifacts. Uploaded files are
checked by name, state, size and digest without downloading them again.
Preserve previous downloads until a replacement passes. No Skill release is needed.

Actions also compares progress with the public Plan package and fixture at the
explicit revision pinned in the workflow. Update that pin when adopting a new
Plan progress contract. For changes to Plan progress semantics, run the explicit cross-repository check:

```text
python scripts/check_plan_compatibility.py --plan-root <exact-plan-package> --fixture-root <plan-development/tests/fixtures/valid-profile>
```

It compares the Viewer with the supplied real Plan selector. Ordinary isolated
Skill tests do not need a Viewer checkout. Neither project owns a copied implementation
of the other.
