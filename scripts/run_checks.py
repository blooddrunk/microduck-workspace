#!/usr/bin/env python3
"""Run the fixed workspace acceptance suite, preserving local raw logs and metadata."""
import argparse
from evidence import Bundle, ROOT, run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='NEW private local evidence directory')
    args = parser.parse_args(argv)
    bundle = Bundle(args.output, 'Workspace offline tests + remote HEAD comparison; no hardware, simulation or training acceptance')
    commands = [
        ('workspace', ['python3', 'scripts/verify_workspace.py'], 0),
        ('unit_tests', ['python3', '-m', 'unittest', 'discover', '-s', 'tests', '-v'], 0),
        ('upstreams', ['python3', 'scripts/sync_upstreams.py', 'check'], 0),
        ('simulated_table', ['python3', 'scripts/validate_servos.py', 'tests/fixtures/servos_simulated.json',
         '--mapping', 'tests/fixtures/mapping_simulated.json', '--output', str(bundle.path.resolve() / 'simulated')], 0),
        ('unknown_template', ['python3', 'scripts/validate_servos.py', 'templates/hd1910_inventory.csv',
         '--mapping', 'templates/hd1910_mapping.json', '--output', str(bundle.path.resolve() / 'unknown')], 2),
    ]
    import os
    os.chdir(ROOT)
    for name, command, expected in commands:
        result = run(command, timeout=400 if name == 'upstreams' else 60)
        status = 'BLOCKED' if result['error'] or (name == 'upstreams' and result['returncode'] != 0) else (
            'PASS' if result['returncode'] == expected else 'FAIL')
        bundle.add(name, result, status, f'Expected exit {expected}; observed {result["returncode"]}; upstream PASS means query succeeded, not compatibility')
    return bundle.finish()


if __name__ == '__main__':
    raise SystemExit(main())
