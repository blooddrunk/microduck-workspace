"""No hardware, network or privileged writes: synthetic data and temporary files only."""
import copy
import json
import tempfile
import unittest
import sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import diagnose_radxa as diag
import evidence
import validate_servos as servos
ROOT = Path(__file__).resolve().parents[1]


class ServoTests(unittest.TestCase):
    def setUp(self):
        self.rows = servos.load(ROOT / 'tests/fixtures/servos_simulated.json')
        self.mapping = servos.load(ROOT / 'tests/fixtures/mapping_simulated.json')

    def result(self):
        return servos.validate(self.rows, self.mapping)['status']

    def test_simulated_consistent_table(self):
        self.assertEqual(self.result(), 'PASS')
        self.assertIn('BLOCKED', servos.validate(self.rows, self.mapping)['hardware_acceptance'])

    def test_unknown_template_remains_blocked(self):
        self.assertEqual(servos.validate(servos.load(ROOT / 'templates/hd1910_inventory.csv'),
            servos.load(ROOT / 'templates/hd1910_mapping.json'))['status'], 'BLOCKED')

    def test_duplicate_fields(self):
        for key in ('current_id', 'planned_id', 'joint_name', 'physical_label'):
            with self.subTest(key=key):
                saved = copy.deepcopy(self.rows)
                self.rows[1][key] = self.rows[0][key]
                self.assertEqual(self.result(), 'FAIL')
                self.rows = saved

    def test_missing_servo_and_mapping(self):
        self.rows.pop()
        self.assertEqual(self.result(), 'FAIL')
        self.mapping.pop()
        self.assertEqual(self.result(), 'FAIL')

    def test_incomplete_field(self):
        del self.rows[0]['encoder_zero_raw']
        self.assertEqual(self.result(), 'FAIL')

    def test_malformed_cli_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'broken.json'; p.write_text('[broken')
            self.assertEqual(servos.main([str(p), '--mapping', str(ROOT / 'tests/fixtures/mapping_simulated.json'),
                '--output', str(Path(tmp) / 'result')]), 1)

    def test_unknown_calibration(self):
        self.rows[0]['mechanical_reference'] = ''
        self.assertEqual(self.result(), 'BLOCKED')

    def test_invalid_values(self):
        cases = {'current_id': [254, -1, True, 1.1, '1.5'], 'direction': [0, 2],
                 'baud': [0], 'voltage_min_v': [-2, 0], 'voltage_v': ['nan', float('inf'), 9],
                 'training_home_rad': [2], 'joint_min_rad': [1],
                 'temperature_c': [60], 'firmware': [False, {}], 'position_raw': [True]}
        for key, invalid in cases.items():
            for val in invalid:
                with self.subTest(key=key, val=val):
                    saved = copy.deepcopy(self.rows)
                    self.rows[0][key] = val
                    self.assertEqual(self.result(), 'FAIL')
                    self.rows = saved

    def test_mapping_disagreement_and_missing_id(self):
        self.rows[0]['planned_id'] = 100
        self.assertEqual(self.result(), 'FAIL')

    def test_policy_mapping(self):
        for val in (14, -1, 'excluded', 1):
            with self.subTest(val=val):
                self.mapping[0]['policy_index'] = val
                self.assertEqual(self.result(), 'FAIL')

    def test_raw_register_failures(self):
        for val in ('broken JSON', [], [{'address': 0}],
                    [dict(address=0, width_bytes=1, value=256, manual_ref='SIMULATED')]):
            with self.subTest(val=val):
                self.rows[0]['registers_raw'] = val
                self.assertEqual(self.result(), 'FAIL')

    def test_csv_json_equivalence_and_bad_row(self):
        import csv
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'input.csv'
            with p.open('w', newline='') as f:
                w = csv.DictWriter(f, fieldnames=servos.FIELDS)
                w.writeheader()
                for r in self.rows:
                    w.writerow({**r, 'registers_raw': json.dumps(r['registers_raw'])})
            self.assertEqual(servos.validate(servos.load(p), self.mapping)['status'], 'PASS')
            p.write_text('a,a\n1,2\n')
            with self.assertRaises(ValueError): servos.load(p)
            p.write_text('a,b\n1\n')
            with self.assertRaises(ValueError): servos.load(p)
            p = Path(tmp) / 'bad.json'; p.write_text('{}')
            with self.assertRaises(ValueError): servos.load(p)


class DiagnosticTests(unittest.TestCase):
    def test_commands_are_read_only(self):
        allowed = {'uname', 'free', 'lsblk', 'df', 'ip', 'systemctl', 'journalctl', 'dmesg'}
        for command in [*diag.COMMANDS.values(), diag.ROBOTD]:
            self.assertIn(command[0], allowed)
            self.assertFalse({'start', 'stop', 'enable', 'disable', 'restart', 'set', 'add', 'delete'} & set(command))

    def test_command_failures_and_warnings(self):
        for code in (None, 1):
            self.assertEqual(diag.command_status('kernel', dict(returncode=code, stdout=''))[0], 'BLOCKED')
        self.assertEqual(diag.command_status('failed_services', dict(returncode=0, stdout='failed.service'))[0], 'FAIL')
        self.assertEqual(diag.command_status('kernel_log', dict(returncode=0, stdout='error'))[0], 'BLOCKED')
        self.assertEqual(diag.command_status('boot_warnings', dict(returncode=0, stdout='-- No entries --', stderr='insufficient permissions'))[0], 'BLOCKED')
        self.assertEqual(diag.command_status('boot_warnings', dict(returncode=0, stdout='-- No entries --', stderr=''))[0], 'PASS')
        self.assertEqual(diag.command_status('robotd', dict(returncode=0, stdout='LoadState=not-found'))[0], 'BLOCKED')

    def test_occupancy_snapshot_and_no_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp); dev = base / 'dev'; proc = base / 'proc'
            dev.mkdir(); proc.mkdir()
            self.assertEqual(diag.occupancy(dev, proc)['nodes'], [])
            node = dev / 'ttyS2'; node.touch()
            fd = proc / '123' / 'fd'; fd.mkdir(parents=True)
            (fd / '0').symlink_to(node)
            self.assertEqual(diag.occupancy(dev, proc)['open_by_pid'][str(node)], ['123'])

    def test_permission_visibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            dev = Path(tmp) / 'dev'; proc = Path(tmp) / 'proc'
            dev.mkdir(); proc.mkdir(); (proc / '123').mkdir()
            real = Path.iterdir
            def denied(path):
                if path.name == 'fd': raise PermissionError()
                return real(path)
            with patch.object(Path, 'iterdir', denied):
                self.assertEqual(diag.occupancy(dev, proc)['denied'], 1)

    def test_host_run_never_qualifies_hardware(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = dict(command=['MOCK'], time_utc='SIMULATED', returncode=0, stdout='', stderr='', error=None)
            with patch.object(diag, 'run', return_value=result), patch.object(diag, 'occupancy',
                return_value=dict(nodes=['SIMULATED'], denied=0)), patch.object(diag.platform, 'system', return_value='Linux'):
                self.assertEqual(diag.main(['--output', str(Path(tmp)/'bundle'), '--robotd']), 2)
            report = json.loads((Path(tmp)/'bundle/summary.json').read_text())
            self.assertEqual(report['status'], 'BLOCKED')
            self.assertNotIn('stdout', report['checks'][0])


class EvidenceTests(unittest.TestCase):
    def test_missing_command_and_timeout(self):
        self.assertIsNotNone(evidence.run(['/nonexistent/microduck-command'])['error'])
        import subprocess
        with patch.object(evidence.subprocess, 'run', side_effect=subprocess.TimeoutExpired('mock', 1)):
            self.assertEqual(evidence.run(['mock'])['error'], 'TimeoutExpired')

    def test_preserve_previous_bundle_and_privacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'bundle'
            bundle = evidence.Bundle(p, 'SIMULATED')
            bundle.add('mock', {'stdout': 'secret example'}, 'FAIL', 'synthetic failure')
            self.assertEqual(bundle.finish(), 1)
            self.assertEqual(p.stat().st_mode & 0o777, 0o700)
            self.assertEqual((p/'summary.json').stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError): evidence.Bundle(p, 'SIMULATED')
            report = json.loads((p/'summary.json').read_text())
            self.assertNotIn('secret example', json.dumps(report))
            raw = p / report['checks'][0]['raw']
            import hashlib
            self.assertEqual(report['checks'][0]['sha256'], hashlib.sha256(raw.read_bytes()).hexdigest())
