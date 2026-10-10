#!/usr/bin/env python3
"""Gate Viewer release files against successful Actions jobs and exact sources."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile
import tomllib

VIEWER = '.'
REPOSITORY = 'benjaminstelzer/scoville-plan-viewer'
BUILD_FILES = {'package.json', 'package-lock.json', 'index.html', 'tsconfig.json',
               'vite.config.ts', 'components.json', '.github/workflows/plan-viewer.yml'}

def build_input(path):
    return path in BUILD_FILES or path.startswith(('src/', 'src-tauri/', 'public/'))
WORKFLOW = '.github/workflows/plan-viewer.yml'
PLATFORMS = ('linux-x64', 'windows-x64', 'macos-arm64', 'macos-x64')
SUFFIXES = ('linux-x64', 'linux-x64.AppImage', 'linux-x64.deb', 'linux-x64.rpm',
            'windows-x64.exe', 'windows-x64-setup.exe', 'windows-x64.msi',
            'macos-arm64.app.zip', 'macos-arm64.dmg', 'macos-x64.app.zip', 'macos-x64.dmg')


def command(*args):
    result = subprocess.run(args, capture_output=True)
    if result.returncode:
        raise ValueError(f'{args[0]} failed: ' + result.stderr.decode(errors='replace').strip())
    return result.stdout


def api(route):
    return json.loads(command('gh', 'api', route))


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def local_assets(root, assets):
    viewer = root / VIEWER
    package = json.loads((viewer / 'package.json').read_text(encoding='utf-8'))
    version = package['version']
    lock = json.loads((viewer / 'package-lock.json').read_text(encoding='utf-8'))
    cargo = tomllib.loads((viewer / 'src-tauri/Cargo.toml').read_text(encoding='utf-8'))
    cargo_lock = tomllib.loads((viewer / 'src-tauri/Cargo.lock').read_text(encoding='utf-8'))
    native = [p['version'] for p in cargo_lock['package'] if p['name'] == 'scoville-plan-viewer']
    versions = [lock['version'], lock['packages']['']['version'], cargo['package']['version'],
                json.loads((viewer / 'src-tauri/tauri.conf.json').read_text(encoding='utf-8'))['version'], *native]
    if len(native) != 1 or any(v != version for v in versions):
        raise ValueError('Viewer version owners must agree: package/locks, Cargo and Tauri')
    names = {f'scoville-plan-viewer-v{version}-{suffix}' for suffix in SUFFIXES}
    actual = {p.name for p in assets.iterdir()}
    if actual != names | {'SHA256SUMS.txt', 'BUILD.json'}:
        raise ValueError('Viewer assets must contain exactly the current 11 binaries, SHA256SUMS.txt and BUILD.json; '
                         f'missing={sorted((names | {"SHA256SUMS.txt", "BUILD.json"}) - actual)}, '
                         f'extra={sorted(actual - (names | {"SHA256SUMS.txt", "BUILD.json"}))}')
    sums = {}
    for line in (assets / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-f]{64})  (\S+)', line)
        if not match or match[2] in sums or Path(match[2]).name != match[2]:
            raise ValueError('SHA256SUMS.txt requires unique basenames and lowercase SHA-256 hashes')
        sums[match[2]] = match[1]
    if sums.keys() != names:
        raise ValueError('SHA256SUMS.txt must cover exactly the 11 current binaries')
    for name, expected in sums.items():
        path = assets / name
        if not path.is_file() or not path.stat().st_size or digest(path) != expected:
            raise ValueError('Missing, empty or checksum-mismatched Viewer asset: ' + name)
    return version, names, sums


def verify_attachment(asset, path):
    """Check an uploaded attachment without downloading its bytes again."""
    if (asset.get('name') != path.name or asset.get('state') != 'uploaded'
            or asset.get('size') != path.stat().st_size
            or asset.get('digest') != 'sha256:' + digest(path)):
        raise ValueError('Uploaded attachment metadata differs from approved file: ' + path.name)


def verify(root, assets, releases=()):
    if releases and (len(releases) != 1 or not re.fullmatch(
            re.escape(REPOSITORY) + r'=v\d+\.\d+\.\d+', releases[0])):
        raise ValueError('--release expects exactly one benjaminstelzer/scoville-plan-viewer=vX.Y.Z')
    version, names, sums = local_assets(root, assets)
    if releases and releases[0].split('=')[1] != 'v' + version:
        raise ValueError('--release tag must equal the agreed Viewer version v' + version)
    build = json.loads((assets / 'BUILD.json').read_text(encoding='utf-8'))
    match = re.fullmatch(r'https://github.com/(benjaminstelzer/scoville-plan-viewer)/actions/runs/(\d+)', build['workflow_run'])
    if not match or build['version'] != version or sorted(build['platforms']) != sorted(PLATFORMS):
        raise ValueError('BUILD.json must identify the current version, four platforms and canonical Viewer Actions run')
    repo, run_id = match.groups()
    run = api(f'repos/{repo}/actions/runs/{run_id}')
    if (run['status'] != 'completed' or run['conclusion'] != 'success'
            or run['head_sha'] != build['source_commit'] or run['path'] != WORKFLOW):
        raise ValueError('Actions run must succeed for BUILD.json source_commit and Plan Viewer workflow')
    jobs = api(f'repos/{repo}/actions/runs/{run_id}/jobs?per_page=100')['jobs']
    expected_jobs = {'Linux x64', 'Windows x64', 'macOS Apple Silicon', 'macOS Intel', 'Checksums', 'Plan compatibility'}
    if {j['name'] for j in jobs} != expected_jobs or any(j['conclusion'] != 'success' for j in jobs):
        raise ValueError('All platform, checksum and Plan compatibility jobs must succeed')
    tree = api(f'repos/{repo}/git/trees/{run["head_sha"]}?recursive=1')
    if tree.get('truncated'):
        raise ValueError('GitHub source tree is truncated; cannot establish source identity')
    remote = {e['path']: e['sha'] for e in tree['tree']
              if e['type'] == 'blob' and build_input(e['path'])}
    paths = command('git', '-C', str(root), 'ls-files', '--cached', '--others', '--exclude-standard').decode().splitlines()
    local = {p: command('git', '-C', str(root), 'hash-object', '--path=' + p, p).decode().strip() for p in paths if build_input(p)}
    if local != remote:
        changed = sorted(p for p in local.keys() | remote.keys() if local.get(p) != remote.get(p))
        raise ValueError('Actions source differs from current Viewer/workflow: ' + ', '.join(changed))
    # Compare artifacts themselves, not just their recorded checksums or filenames.
    with tempfile.TemporaryDirectory(prefix='scoville-viewer-gate-') as temp:
        downloaded = Path(temp) / 'actions'
        command('gh', 'run', 'download', run_id, '--repo', repo, '--dir', str(downloaded))
        for name in names | {'SHA256SUMS.txt'}:
            found = list(downloaded.rglob(name))
            if len(found) != 1 or digest(found[0]) != digest(assets / name):
                raise ValueError('Local Viewer file differs from Actions artifact: ' + name)
        for target in releases:
            release_repo, tag = target.split('=')
            release = api(f'repos/{release_repo}/releases/tags/{tag}')
            published = [a['name'] for a in release['assets']]
            if len(published) != 12 or set(published) != names | {'SHA256SUMS.txt'}:
                raise ValueError(target + ' must attach exactly all 12 approved Viewer files directly')
            for attachment in release['assets']:
                if attachment['name'] in published:
                    verify_attachment(attachment, assets / attachment['name'])
    return {'version': version, 'source_commit': run['head_sha'], 'workflow_run': run['html_url'],
            'source_files_verified': len(local), 'assets': {name: sums.get(name, digest(assets / name))
                                                        for name in sorted(names | {'SHA256SUMS.txt'})},
            'releases_verified': list(releases)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--viewer-root', type=Path, default=Path(__file__).resolve().parents[1], help='Canonical Viewer checkout; defaults to this repository')
    parser.add_argument('--assets-root', required=True, type=Path)
    parser.add_argument('--release', action='append', default=[])
    args = parser.parse_args()
    try:
        result = verify(args.viewer_root.resolve(), args.assets_root.resolve(), args.release)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
