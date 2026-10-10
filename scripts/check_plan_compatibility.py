"""Compare Viewer progress with an explicitly supplied Scoville Plan selector."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan-root', required=True, type=Path, help='Exact package containing scripts/select_context.py')
    parser.add_argument('--fixture-root', required=True, type=Path, help='Plan development/tests/fixtures/valid-profile')
    args = parser.parse_args()
    selector = args.plan_root.resolve() / 'scripts/select_context.py'
    fixture = args.fixture_root.resolve()
    viewer = Path(__file__).resolve().parents[1] / 'src/lib/step-progress.ts'
    if not selector.is_file() or not (fixture / 'docs/plans/0001-validate-profile.md').is_file():
        parser.error('Supply the actual Plan package and its valid-profile fixture with --plan-root and --fixture-root')
    cases = [["todo"], [None, "in_progress"],
             ["done", "in_progress", "in_progress", None, "in_progress"],
             ["done", None, "todo"], ["done", "cancelled"], [None, None]]
    node = "const {stepPosition}=await import(process.argv[1]); let input=''; for await(const chunk of process.stdin) input+=chunk; console.log(JSON.stringify(stepPosition(JSON.parse(input))));"
    with tempfile.TemporaryDirectory(prefix='scoville-plan-compatibility-') as temporary:
        project = Path(temporary) / 'project'
        shutil.copytree(fixture, project)
        plan = project / 'docs/plans/0001-validate-profile.md'
        original = plan.read_text(encoding='utf-8')
        for statuses in cases:
            lines = [f'[status: {status}] Action {i}.' if status else f'Legacy action {i}.'
                     for i, status in enumerate(statuses, 1)]
            text = original.replace('1. Read the canonical files.\n2. Check the local record shapes.',
                '\n'.join(f'{i}. {line}' for i, line in enumerate(lines, 1)))
            if text == original:
                parser.error('The supplied fixture has different Steps; use the matching valid-profile fixture')
            plan.write_text(text, encoding='utf-8', newline='\n')
            before = plan.read_bytes()
            result = subprocess.run([sys.executable, '-X', 'utf8', str(selector), '--root', str(project), '--position'],
                                    check=True, capture_output=True, text=True, encoding='utf-8')
            position = json.loads(result.stdout)
            if plan.read_bytes() != before:
                raise ValueError('The Plan selector modified its input')
            item = {'status': 'in_progress', 'steps': lines,
                    'step_statuses': [{'number': i, 'status': status} for i, status in enumerate(statuses, 1)]}
            result = subprocess.run(['node', '--experimental-strip-types', '--input-type=module', '-e', node, viewer.as_uri()],
                                    input=json.dumps(item), check=True, capture_output=True, text=True, encoding='utf-8')
            observed = json.loads(result.stdout)
            expected = {'numbers': position['current_steps'] or ([position['next_step']] if position['next_step'] else []),
                        'untracked': position['untracked_steps'], 'reason': position['reason']}
            if any(observed[key] != value for key, value in expected.items()):
                raise ValueError(f'Viewer and Plan disagree for statuses {statuses}: {observed} versus {expected}')
    print(json.dumps({'valid': True, 'cases': len(cases), 'plan_package': str(args.plan_root.resolve()),
                      'viewer_source': str(viewer)}))


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'COMPATIBILITY FAILED: {error}', file=sys.stderr)
        if isinstance(error, subprocess.CalledProcessError):
            print(error.stdout or '', file=sys.stderr)
            print(error.stderr or '', file=sys.stderr)
        raise SystemExit(1)
