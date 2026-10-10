import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('viewer_gate', Path(__file__).resolve().parents[1] / 'scripts/verify_release.py')
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


class ViewerReleaseGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        viewer = self.root / gate.VIEWER
        native = viewer / 'src-tauri'
        native.mkdir(parents=True)
        for path, content in {
            viewer / 'package.json': {'version': '1.4.0'},
            viewer / 'package-lock.json': {'version': '1.4.0', 'packages': {'': {'version': '1.4.0'}}},
            native / 'tauri.conf.json': {'version': '1.4.0'},
        }.items():
            path.write_text(json.dumps(content))
        (native / 'Cargo.toml').write_text('[package]\nversion = "1.4.0"\n')
        (native / 'Cargo.lock').write_text('[[package]]\nname = "scoville-plan-viewer"\nversion = "1.4.0"\n')
        self.assets = self.root / 'assets'
        self.assets.mkdir()
        self.names = [f'scoville-plan-viewer-v1.4.0-{suffix}' for suffix in gate.SUFFIXES]
        for name in self.names:
            (self.assets / name).write_bytes(name.encode())
        sums = ''.join(f'{hashlib.sha256(name.encode()).hexdigest()}  {name}\n' for name in self.names)
        (self.assets / 'SHA256SUMS.txt').write_text(sums)
        (self.assets / 'BUILD.json').write_text('{}')

    def test_complete_current_inventory_passes(self):
        version, names, sums = gate.local_assets(self.root, self.assets)
        self.assertEqual(version, '1.4.0')
        self.assertEqual(names, set(self.names))
        self.assertEqual(len(sums), 11)

    def test_utf8_metadata_with_non_ascii_content(self):
        path = self.root / gate.VIEWER / 'package.json'
        path.write_text(json.dumps({'version': '1.4.0', 'description': 'Menü 日本語'}, ensure_ascii=False),
                        encoding='utf-8')
        cargo = self.root / gate.VIEWER / 'src-tauri/Cargo.toml'
        cargo.write_text('[package]\nversion = "1.4.0"\n# Menü 日本語\n', encoding='utf-8')
        self.assertEqual('1.4.0', gate.local_assets(self.root, self.assets)[0])

    def test_mutated_binary_is_rejected(self):
        (self.assets / self.names[0]).write_bytes(b'wrong source build')
        with self.assertRaisesRegex(ValueError, 'checksum-mismatched'):
            gate.local_assets(self.root, self.assets)

    def test_mixed_version_owner_is_rejected(self):
        (self.root / gate.VIEWER / 'src-tauri/Cargo.toml').write_text('[package]\nversion = "1.3.3"\n')
        with self.assertRaisesRegex(ValueError, 'version owners must agree'):
            gate.local_assets(self.root, self.assets)

    def test_extra_old_binary_is_rejected(self):
        (self.assets / 'scoville-plan-viewer-v1.3.3-windows-x64.exe').write_bytes(b'old')
        with self.assertRaisesRegex(ValueError, 'extra='):
            gate.local_assets(self.root, self.assets)

    def test_duplicate_checksum_is_rejected(self):
        path = self.assets / 'SHA256SUMS.txt'
        path.write_text(path.read_text() + path.read_text().splitlines()[0] + '\n')
        with self.assertRaisesRegex(ValueError, 'unique basenames'):
            gate.local_assets(self.root, self.assets)

    def test_wrong_or_duplicate_destinations_are_rejected_before_network(self):
        from unittest.mock import patch
        for targets in (['benjaminstelzer/scoville-plan=v1.4.0'],
                        ['benjaminstelzer/scoville-suite=v1.4.0'],
                        ['benjaminstelzer/scoville-suite-for-codex=v1.4.0'],
                        ['benjaminstelzer/scoville-plan-viewer=v1.4.0'] * 2,
                        ['benjaminstelzer/scoville-plan-viewer=broken']):
            with self.subTest(targets=targets), patch.object(gate, 'api') as api:
                with self.assertRaisesRegex(ValueError, 'exactly one'):
                    gate.verify(self.root, self.assets, targets)
                api.assert_not_called()

    def attachment(self):
        path = self.assets / self.names[0]
        return path, {'name': path.name, 'state': 'uploaded',
                      'size': path.stat().st_size, 'digest': 'sha256:' + gate.digest(path)}

    def test_uploaded_metadata_matches_approved_file(self):
        path, asset = self.attachment()
        gate.verify_attachment(asset, path)

    def test_wrong_uploaded_digest_is_rejected(self):
        path, asset = self.attachment()
        asset['digest'] = 'sha256:' + '0' * 64
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            gate.verify_attachment(asset, path)

    def test_missing_uploaded_digest_is_rejected(self):
        path, asset = self.attachment()
        asset.pop('digest')
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            gate.verify_attachment(asset, path)

    def test_incomplete_upload_is_rejected(self):
        path, asset = self.attachment()
        asset['state'] = 'starter'
        with self.assertRaisesRegex(ValueError, 'metadata differs'):
            gate.verify_attachment(asset, path)

    def test_wrong_version_tag_is_rejected_before_network(self):
        with patch.object(gate, 'api') as api:
            with self.assertRaisesRegex(ValueError, 'tag must equal'):
                gate.verify(self.root, self.assets, ['benjaminstelzer/scoville-plan-viewer=v1.3.0'])
            api.assert_not_called()

    def verify_provenance(self, defect=None):
        build = {'version': '1.4.0', 'platforms': list(gate.PLATFORMS), 'source_commit': 'a' * 40,
                 'workflow_run': 'https://github.com/benjaminstelzer/scoville-plan-viewer/actions/runs/123'}
        if defect == 'old_owner': build['workflow_run'] = build['workflow_run'].replace('scoville-plan-viewer/', 'scoville-suite/')
        (self.assets / 'BUILD.json').write_text(json.dumps(build))
        jobs = ['Linux x64', 'Windows x64', 'macOS Apple Silicon', 'macOS Intel', 'Checksums', 'Plan compatibility']
        def api(route):
            if route.endswith('/actions/runs/123'):
                return {'status': 'completed', 'conclusion': 'success', 'head_sha': 'a' * 40,
                        'path': gate.WORKFLOW, 'html_url': build['workflow_run']}
            if '/jobs?' in route:
                return {'jobs': [{'name': name, 'conclusion': 'success'} for name in jobs if not (defect == 'missing_job' and name == 'Plan compatibility')]}
            if '/git/trees/' in route:
                return {'truncated': defect == 'truncated', 'tree': [
                    {'type': 'blob', 'path': 'src/main.ts', 'sha': 'b' * 40}]}
            if '/releases/tags/' in route:
                assets = [{'name': p.name, 'state': 'uploaded', 'size': p.stat().st_size,
                           'digest': 'sha256:' + gate.digest(p)} for p in self.assets.iterdir() if p.name != 'BUILD.json']
                if defect == 'extra_upload': assets.append({'name': 'skill.zip'})
                return {'assets': assets}
            raise AssertionError(route)
        def command(*args):
            if args[0] == 'git' and 'ls-files' in args: return b'src/main.ts\nREADME.md\n'
            if args[0] == 'git' and 'hash-object' in args: return ('c' * 40 if defect == 'changed_input' else 'b' * 40).encode()
            if args[:3] == ('gh', 'run', 'download'):
                destination = Path(args[args.index('--dir') + 1])
                destination.mkdir()
                for path in self.assets.iterdir():
                    if path.name != 'BUILD.json': (destination / path.name).write_bytes(path.read_bytes())
                return b''
            raise AssertionError(args)
        with patch.object(gate, 'api', side_effect=api), patch.object(gate, 'command', side_effect=command):
            return gate.verify(self.root, self.assets, ['benjaminstelzer/scoville-plan-viewer=v1.4.0'])

    def test_independent_source_jobs_artifacts_and_upload_pass(self):
        self.assertEqual(self.verify_provenance()['source_files_verified'], 1)

    def test_provenance_rejects_old_owner_missing_job_partial_tree_drift_and_extra_upload(self):
        for defect in ('old_owner', 'missing_job', 'truncated', 'changed_input', 'extra_upload'):
            with self.subTest(defect=defect), self.assertRaises(ValueError): self.verify_provenance(defect)


if __name__ == '__main__':
    unittest.main()
