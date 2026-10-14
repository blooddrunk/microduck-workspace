#!/usr/bin/env python3
"""Read-only JSON/TOML calibration review; never opens a bus or generates targets."""
import argparse
import hashlib
import json
import math
from pathlib import Path

NAMES = ['left_hip_yaw','left_hip_roll','left_hip_pitch','left_knee','left_ankle',
         'neck_pitch','head_pitch','head_yaw','head_roll','mouth',
         'right_hip_yaw','right_hip_roll','right_hip_pitch','right_knee','right_ankle']
IDS = [20,21,22,23,24,30,31,32,33,34,10,11,12,13,14]
HOME = [0,-.0873,-.4579,-.0049,.453,.3491,.3491,0,0,0,0,.0873,.4579,.0049,-.453]

def finite(x):
    return type(x) in (int,float) and math.isfinite(x)

def review(data, provenance, expected_robot, file_hash):
    issues=[]
    if not isinstance(data,dict) or not isinstance(provenance,dict):
        return {'status':'FAIL','issues':['configuration/provenance must be objects']}
    if not expected_robot or expected_robot in ('UNKNOWN','duck-10e4'):
        issues.append('local robot identity required; bundled duck-10e4 is not this robot')
    if provenance.get('robot_id')!=expected_robot or provenance.get('calibration_sha256')!=file_hash:
        issues.append('provenance robot/hash mismatch')
    if provenance.get('source')!='local-readback' or not isinstance(provenance.get('evidence_ref'),str) or not provenance.get('evidence_ref','').strip():
        issues.append('own readback evidence required')
    if data.get('motion_enabled') is not False:
        issues.append('preparation requires motion_enabled=false')
    mount=data.get('imu_mount_quat')
    if not isinstance(mount,list) or len(mount)!=4 or not all(finite(x) for x in mount) or abs(sum(x*x for x in mount)-1)>1e-6:
        issues.append('mount must be unit [w,x,y,z]')
    joints=data.get('joints')
    if not isinstance(joints,list) or len(joints)!=15:
        issues.append('15 joints required'); joints=[]
    for i,j in enumerate(joints):
        if not isinstance(j,dict):
            issues.append(f'joint {i}: object required');continue
        if j.get('name')!=NAMES[i] or type(j.get('id')) is not int or j.get('id')!=IDS[i]:
            issues.append(f'joint {i}: canonical name/ID mismatch')
        z,d=j.get('zero_raw'),j.get('direction')
        if type(z) is not int or not 0<=z<=4095 or type(d) is not int or d not in (-1,1):
            issues.append(f'joint {i}: zero/direction invalid');continue
        lo,hi=j.get('min_rad'),j.get('max_rad')
        if j.get('calibrated') is not True or not finite(lo) or not finite(hi) or not lo<hi or not lo<=HOME[i]<=hi:
            issues.append(f'joint {i}: calibration/limits/HOME unverified');continue
        if any(not 0<=round(z+q*d*4096/(2*math.pi))<=4095 for q in (lo,hi)):
            issues.append(f'joint {i}: encoder boundary crossed')
    return {'status':'BLOCKED' if issues else 'PASS','issues':issues,
            'scope':'offline preparation consistency; provenance is a claim requiring human evidence review',
            'hardware_acceptance':'NOT_EXECUTED','motion_authorized':False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('calibration',type=Path);p.add_argument('--provenance',type=Path,required=True)
    p.add_argument('--robot-id',required=True)
    a=p.parse_args()
    try:
        raw=a.calibration.read_bytes()
        if a.calibration.suffix=='.toml':
            import tomllib # Python 3.11+ only for TOML; JSON works on 3.10.
            data=tomllib.loads(raw.decode())
        else: data=json.loads(raw)
        result=review(data,json.loads(a.provenance.read_text()),a.robot_id,hashlib.sha256(raw).hexdigest())
    except (OSError,ValueError,TypeError,ImportError) as e:
        result={'status':'FAIL','issues':[str(e)]}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return {'PASS':0,'BLOCKED':2,'FAIL':1}[result['status']]
if __name__=='__main__': raise SystemExit(main())
