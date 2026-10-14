#!/usr/bin/env python3
"""Offline HD1910 CSV/JSON validation. Never imports a servo SDK or opens devices."""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from evidence import Bundle, timestamp

FIELDS = ('physical_label joint_name current_id planned_id firmware mode baud position_raw voltage_v '
          'temperature_c voltage_min_v voltage_max_v temperature_max_c mechanical_reference '
          'encoder_zero_raw training_home_rad direction joint_min_rad joint_max_rad '
          'registers_raw evidence_ref').split()
UNKNOWN = (None, '', 'UNKNOWN', 'BLOCKED')


def load(path):
    if path.suffix.lower() == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError('Missing or duplicate CSV columns')
            rows = list(reader)
            if any(None in row or any(value is None for value in row.values()) for row in rows):
                raise ValueError('CSV row width differs from header')
            return rows
    if path.suffix.lower() == '.json':
        data = json.loads(path.read_text(encoding='utf-8'))
        if not isinstance(data, list):
            raise ValueError('JSON must be an array of servo objects')
        return data
    raise ValueError('Input must be CSV or JSON')


def number(value, integer=False):
    if isinstance(value, bool):
        raise ValueError('Boolean is not a measurement')
    if integer:
        # Reject 1.5 and JSON float IDs; CSV integer strings are accepted.
        if not isinstance(value, (int, str)) or (isinstance(value, str) and not value.strip().lstrip('-').isdigit()):
            raise ValueError('Expected integer')
        return int(value)
    result = float(value)
    if not math.isfinite(result):
        raise ValueError('Non-finite number')
    return result


def validate(rows, mapping):
    issues = []
    def issue(status, text):
        issues.append(dict(status=status, reason=text))
    if not isinstance(rows, list) or len(rows) != 15:
        issue('FAIL', 'Expected exactly 15 physical servos')
    if not isinstance(mapping, list) or len(mapping) != 15:
        issue('FAIL', 'Expected exactly 15 agreed mapping entries')
    seen = {key: set() for key in ('physical_label', 'joint_name', 'current_id', 'planned_id')}
    for index, row in enumerate(rows if isinstance(rows, list) else []):
        tag = f'row {index + 1}'
        if not isinstance(row, dict):
            issue('FAIL', f'{tag}: must be object'); continue
        values = {}
        for key in FIELDS:
            if key not in row:
                issue('FAIL', f'{tag}: missing field {key}')
            elif row[key] in UNKNOWN:
                issue('BLOCKED', f'{tag}: unknown {key}')
            else:
                values[key] = row[key]
        for key in ('physical_label', 'joint_name', 'firmware', 'mode', 'mechanical_reference', 'evidence_ref'):
            if key in values and (not isinstance(values[key], str) or not values[key].strip()):
                issue('FAIL', f'{tag}: {key} must be nonempty text'); values.pop(key)
        integers = ('current_id', 'planned_id', 'baud', 'position_raw', 'encoder_zero_raw', 'direction')
        decimals = ('voltage_v', 'temperature_c', 'voltage_min_v', 'voltage_max_v', 'temperature_max_c',
                    'training_home_rad', 'joint_min_rad', 'joint_max_rad')
        for key in integers + decimals:
            if key in values:
                try:
                    values[key] = number(values[key], key in integers)
                except (ValueError, TypeError, OverflowError):
                    issue('FAIL', f'{tag}: invalid {key}'); values.pop(key)
        for key in ('current_id', 'planned_id'):
            if key in values and not 0 <= values[key] <= 253:
                issue('FAIL', f'{tag}: {key} outside unicast range 0..253 (model/firmware may restrict further)')
        if 'voltage_min_v' in values and values['voltage_min_v'] <= 0:
            issue('FAIL', f'{tag}: supply lower bound must be positive')
        if 'baud' in values and values['baud'] <= 0:
            issue('FAIL', f'{tag}: baud must be positive')
        if 'direction' in values and values['direction'] not in (-1, 1):
            issue('FAIL', f'{tag}: direction must be -1 or +1')
        for key, bucket in seen.items():
            if key in values:
                if values[key] in bucket:
                    issue('FAIL', f'{tag}: duplicate {key}={values[key]}')
                bucket.add(values[key])
        for low, value, high in [('joint_min_rad', 'training_home_rad', 'joint_max_rad'),
                                 ('voltage_min_v', 'voltage_v', 'voltage_max_v')]:
            if all(k in values for k in (low, value, high)):
                if values[low] >= values[high] or not values[low] <= values[value] <= values[high]:
                    issue('FAIL', f'{tag}: invalid limits or {value} outside declared range')
        if all(k in values for k in ('temperature_c', 'temperature_max_c')) and values['temperature_c'] >= values['temperature_max_c']:
            issue('FAIL', f'{tag}: temperature at/above declared maximum')
        if 'registers_raw' in values:
            try:
                registers = json.loads(values['registers_raw']) if isinstance(values['registers_raw'], str) else values['registers_raw']
                if not isinstance(registers, list) or not registers:
                    raise ValueError('Empty registers')
                addresses = set()
                for reg in registers:
                    address = number(reg['address'], True)
                    width = number(reg['width_bytes'], True)
                    raw = number(reg['value'], True)
                    if address < 0 or address in addresses or width not in (1, 2, 4) or not 0 <= raw < 256 ** width or not isinstance(reg['manual_ref'], str) or not reg['manual_ref'].strip():
                        raise ValueError('Invalid register metadata')
                    addresses.add(address)
            except (ValueError, TypeError, KeyError, OverflowError):
                issue('FAIL', f'{tag}: registers_raw requires unique addresses, width_bytes, unsigned raw values, manual_ref')
    expected = {k: set() for k in ('physical_label', 'joint_name', 'planned_id', 'policy_index')}
    map_by_label = {}
    for entry in mapping if isinstance(mapping, list) else []:
        if not isinstance(entry, dict):
            issue('FAIL', 'Mapping entry must be object'); continue
        normalized = {}
        for key in expected:
            if key not in entry:
                issue('FAIL', f'Mapping missing {key}'); continue
            val = entry[key]
            if val in UNKNOWN:
                issue('BLOCKED', f'Mapping unknown {key}'); continue
            try:
                if key == 'planned_id' or (key == 'policy_index' and val != 'excluded'):
                    val = number(val, True)
                elif not isinstance(val, str) or not val.strip():
                    raise ValueError('Invalid text')
                if val in expected[key]:
                    issue('FAIL', f'Mapping duplicate {key}={val}')
                expected[key].add(val)
                normalized[key] = val
            except (ValueError, TypeError, OverflowError):
                issue('FAIL', f'Mapping invalid {key}')
        if len(normalized) == 4:
            map_by_label[normalized['physical_label']] = normalized
    if len(map_by_label) == 15:
        if expected['policy_index'] != set(range(14)) | {'excluded'}:
            issue('FAIL', 'Mapping must have policy indices 0..13 once and one excluded actuator')
        for row in rows:
            if not isinstance(row, dict):
                continue
            match = map_by_label.get(row.get('physical_label'))
            if not match:
                issue('FAIL', 'Physical label missing from agreed mapping'); continue
            for key in ('joint_name', 'planned_id'):
                if row.get(key) not in UNKNOWN:
                    try:
                        actual = number(row[key], True) if key == 'planned_id' else row[key]
                        if actual != match[key]:
                            issue('FAIL', f'{row["physical_label"]}: {key} disagrees with mapping')
                    except (ValueError, TypeError):
                        pass  # reported above
        missing = expected['planned_id'] - seen['planned_id']
        if missing:
            issue('FAIL', f'Missing planned IDs: {sorted(missing)}')
    status = 'FAIL' if any(i['status'] == 'FAIL' for i in issues) else 'BLOCKED' if issues else 'PASS'
    return dict(status=status, issues=issues, scope='static data consistency only',
                hardware_acceptance='BLOCKED: no bus readback, electrical measurement or calibration performed')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('--mapping', required=True, type=Path)
    parser.add_argument('--output', required=True, help='NEW private local evidence directory')
    args = parser.parse_args(argv)
    bundle = Bundle(args.output, 'S2 offline static table validation; no hardware access or register writes')
    try:
        result = validate(load(args.input), load(args.mapping))
        hashes = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (args.input, args.mapping)}
    except (OSError, ValueError, TypeError) as exc:
        result = dict(status='FAIL', issues=[dict(status='FAIL', reason=str(exc))])
        hashes = {}
    bundle.add('servo_table', dict(command=bundle.metadata['invocation'], time_utc=timestamp(),
               validation=result, input_sha256=hashes), result['status'], 'See raw validation issues; PASS never qualifies hardware')
    return bundle.finish()


if __name__ == '__main__':
    raise SystemExit(main())
