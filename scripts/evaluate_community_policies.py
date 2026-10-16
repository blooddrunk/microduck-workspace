#!/usr/bin/env python3
"""Pinned, hardware-free community ONNX checks and native qiaosiyi CPU replay.

prepare downloads only listed files at immutable commits into a NEW directory.
check needs numpy/onnx/onnxruntime only. replay needs the existing HD1910 fork
venv and never installs dependencies, imports a hardware SDK or starts training.
A PASS is scoped to the named check; no output constitutes hardware acceptance.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import time
import traceback
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
A_PREFIX = 'microduck-hd1910/firmware/policies/walk/'
B_PREFIX = 'models/hd1910-walking-iter-2000/'
SOURCES = {
    'kissqy': ('kissqy/Microduck-kissqy', 'f02e875e73b88bf8ec7d5bbb34d0b461ac83b010',
               [A_PREFIX+x for x in ('policy.onnx','manifest.json','deployment-contract.json',
                'training-config.json','training-request.json','README.en.md')] +
               ['microduck-hd1910/firmware/policies/LICENSE']),
    'qiaosiyi': ('qiaosiyi/microduck_rl_hd1910', '77286a243c849e04483c7cc8ff4c5f8bae4eea16',
                 [B_PREFIX+x for x in ('policy.onnx','README.md','release.json','verification.json',
                   'cpu_validation.json','source_hashes.json','hd1910_profile.json','LICENSE')]),
    'xgo': ('LuwuDynamics/xgoduck_runtime_arduino','9dc36787bc61b102c2da0f97c9c758e639e90ab8',
            ['python/'+x for x in ('xgoduck_walk.onnx','policy.py','rl_core.py','requirements.txt')]+['README.md']),
}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, data):
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False)+'\n')


def fresh(path):
    if path.exists() and any(path.iterdir()):
        raise ValueError(f'Refusing to overwrite nonempty directory: {path}')
    path.mkdir(parents=True, exist_ok=True)


def prepare(output):
    fresh(output)
    inventory = {}
    for key, (repo, sha, names) in SOURCES.items():
        inventory[key] = {'repository':repo,'commit':sha,'files':{}}
        for name in names:
            url=f'https://raw.githubusercontent.com/{repo}/{sha}/{name}'
            p=output/key/name;p.parent.mkdir(parents=True,exist_ok=True)
            with urllib.request.urlopen(url, timeout=60) as response:
                data=response.read(16*1024*1024+1)
            if len(data)>16*1024*1024:raise ValueError('File exceeds 16 MiB download cap')
            p.write_bytes(data)
            inventory[key]['files'][name]={'sha256':digest(p),'bytes':p.stat().st_size,'url':url}
        write(output/'inventory.json',inventory)
    return inventory


def prepare_native(output):
    """Export Git objects without changing either existing checkout."""
    fresh(output)
    sources=[('official-rl','8d0db74916a4f833d1d9b95d6a1d7f4d13b9d5ec','kissqy-engine',[]),
             ('kissqy-runtime',SOURCES['kissqy'][1],'kissqy',
              ['microduck-hd1910/training-console/training'])]
    provenance=[]
    for name,sha,dest,paths in sources:
        archive=subprocess.check_output(['git','-C',str(ROOT/'.upstreams'/name),'archive',sha,*paths])
        target=output/dest;target.mkdir()
        with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
            stream.extractall(target,filter='data')
        provenance.append({'repository':name,'commit':sha,'archive_sha256':hashlib.sha256(archive).hexdigest()})
    write(output/'native-inventory.json',{'sources':provenance,'files':{
        str(p.relative_to(output)):digest(p) for p in sorted(output.rglob('*')) if p.is_file()}})


def samples():
    import numpy as np
    # Raw body-frame observations: upright gravity; q-HOME=0; no second normalizer.
    upright=np.zeros((1,61),dtype=np.float32);upright[0,5]=-1
    cases={'upright':upright}
    for label, index, value in [('forward',48,.1),('turn',50,.2),('gyro',1,.1),
                                ('joint_offset',8,.03),('joint_velocity',22,.1),
                                ('previous_action',36,.03)]:
        obs=upright.copy();obs[0,index]=value;cases[label]=obs
    obs=upright.copy();obs[0,3:6]=[.05,0,-(1-.05**2)**.5];cases['tilt']=obs
    return cases


def onnx_check(path):
    import numpy as np
    import onnx
    from onnx import numpy_helper
    import onnxruntime as ort
    model=onnx.load(path);onnx.checker.check_model(model)
    options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
    s=ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
    ins,outs=s.get_inputs(),s.get_outputs()
    contract=(len(ins)==len(outs)==1 and ins[0].shape==[1,61] and outs[0].shape==[1,14]
              and ins[0].type==outs[0].type=='tensor(float)')
    result={'status':'FAIL','checker':'PASS','contract_61_to_14_float32':contract,
            'providers':s.get_providers(),'inputs':[(x.name,x.shape,x.type) for x in ins],
            'outputs':[(x.name,x.shape,x.type) for x in outs]}
    if not contract:return result
    values={k:s.run(None,{ins[0].name:v})[0] for k,v in samples().items()}
    result['cases']={k:{'finite':bool(np.isfinite(v).all()),'output':v.tolist(),
                          'max_delta_from_upright':float(np.max(np.abs(v-values['upright'])))}
                     for k,v in values.items()}
    for _ in range(20):s.run(None,{ins[0].name:samples()['upright']})
    obs=samples()['upright'];times=[]
    for _ in range(200):
        start=time.perf_counter_ns();s.run(None,{ins[0].name:obs});times.append((time.perf_counter_ns()-start)/1e6)
    result['latency_ms']={'runs':200,'warmup':20,'threads':1,'median':float(np.median(times)),
                          'p95':float(np.percentile(times,95)),'max':max(times)}
    # Record the actual data path before the first neural layer, not just metadata.
    affine=[]
    for n in model.graph.node:
        if n.op_type in ('Gemm','MatMul'):break
        affine.append({'op':n.op_type,'inputs':list(n.input),'outputs':list(n.output)})
    result['graph_prefix']=affine
    constants={x.name:numpy_helper.to_array(x) for x in model.graph.initializer}
    for n in model.graph.node:
        if n.op_type=='Constant':
            for a in n.attribute:
                if a.name=='value':constants[n.output[0]]=numpy_helper.to_array(a.t)
    prefix_constants={name for node in affine for name in node['inputs'] if name in constants}
    result['normalizer_constants']={name:{'shape':list(v.shape),'min':float(v.min()),'max':float(v.max()),
        'sha256':hashlib.sha256(v.tobytes()).hexdigest()} for name,v in constants.items()
        if v.size and name in prefix_constants}
    result['embedded_normalization']=bool(len(affine)==2 and
        [n['op'] for n in affine]==['Sub','Div'] and affine[0]['inputs'][0]==ins[0].name and
        affine[1]['inputs'][0]==affine[0]['outputs'][0] and
        constants.get(affine[0]['inputs'][1],np.empty(0)).shape==(1,61) and
        constants.get(affine[1]['inputs'][1],np.empty(0)).shape==(1,61) and
        np.all(constants[affine[1]['inputs'][1]]>0))
    result['metadata']={x.key:x.value for x in model.metadata_props}
    result['finite']=all(x['finite'] for x in result['cases'].values())
    result['output_changes']=all(v['max_delta_from_upright']>1e-7 for k,v in result['cases'].items() if k!='upright')
    result['status']='PASS' if result['finite'] and result['output_changes'] and result['embedded_normalization'] else 'FAIL'
    return result


def check(source,output):
    fresh(output)
    inventory=json.loads((source/'inventory.json').read_text())
    import numpy, onnx, onnxruntime
    report={'schema':1,'created_utc':datetime.now(timezone.utc).isoformat(),
            'environment':{'python':sys.version.split()[0],'numpy':numpy.__version__,
                           'onnx':onnx.__version__,'onnxruntime':onnxruntime.__version__},
            'scope':'ONNX CPU only; simulation and hardware separate', 'models':{}}
    for key, (repo,sha,names) in SOURCES.items():
        record={'repository':repo,'commit':sha,'files':{},'status':'FAIL'}
        report['models'][key]=record
        try:
            if inventory[key]['commit']!=sha or inventory[key]['repository']!=repo:raise ValueError('Source identity mismatch')
            for name in names:
                p=source/key/name
                actual={'sha256':digest(p),'bytes':p.stat().st_size}
                if actual['sha256']!=inventory[key]['files'][name]['sha256']:raise ValueError(f'Source changed: {name}')
                record['files'][name]=actual
            policy=next(name for name in names if name.endswith('.onnx'))
            if key=='kissqy':
                manifest=json.loads((source/key/A_PREFIX/'manifest.json').read_text())
                if digest(source/key/policy)!=manifest['onnx_sha256']:raise ValueError('Publisher ONNX digest mismatch')
            if key=='qiaosiyi':
                release=json.loads((source/key/B_PREFIX/'release.json').read_text())
                if digest(source/key/policy)!=release['onnx_sha256']:raise ValueError('Publisher ONNX digest mismatch')
            record['onnx']=onnx_check(source/key/policy);record['status']=record['onnx']['status']
            if key=='xgo':
                sys.path.insert(0,str(source/key/'python'))
                from policy import Policy
                from rl_core import DEFAULT_DEG
                native=Policy();ok,msg=native.load(source/key/policy)
                if not ok:raise ValueError(msg)
                action=native.infer([0,0,-1],[0,0,0],DEFAULT_DEG,[0]*15)
                import numpy as np
                record['native_adapter']={'status':'PASS' if np.isfinite(action).all() else 'FAIL',
                                           'action':action.tolist(),'no_transport_imported':True}
                record['status']=record['native_adapter']['status'] if record['status']=='PASS' else 'FAIL'
        except Exception as exc:
            record['error']=f'{type(exc).__name__}: {exc}';record['traceback']=traceback.format_exc()
        write(output/'report.json',report)
    report['status']='PASS' if all(v['status']=='PASS' for v in report['models'].values()) else 'FAIL'
    write(output/'report.json',report)
    return report


def replay_qia(source,output,seconds):
    import numpy as np
    import mujoco
    import mjlab.tasks
    from mjlab_microduck.actuator.hd1910 import load_cpu_model
    repo=ROOT/'.upstreams/hd1910-rl'
    actual=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    if actual!=SOURCES['qiaosiyi'][1]:raise ValueError('qiaosiyi checkout SHA mismatch')
    dirty=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
    if dirty:raise ValueError('qiaosiyi checkout dirty')
    path=source/'qiaosiyi'/B_PREFIX/'policy.onnx'
    release=json.loads((source/'qiaosiyi'/B_PREFIX/'release.json').read_text())
    if digest(path)!=release['onnx_sha256']:raise ValueError('Policy digest mismatch')
    spec=importlib.util.spec_from_file_location('native_infer',repo/'scripts/infer_policy.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    os.chdir(repo)
    results=[]
    for label,cmd in [('zero',[0,0,0]),('forward',[.1,0,0]),('turn',[0,0,.2])]:
        m,d,c=load_cpu_model('src/mjlab_microduck/robot/microduck/scene.xml')
        if not np.any(m.geom_type==mujoco.mjtGeom.mjGEOM_PLANE):raise ValueError('Missing floor')
        policy=module.PolicyInference(m,d,walking_onnx_path=str(path),bam_ctrl=c,
                                     new_cmd_obs=True,use_projected_gravity=True)
        policy.set_vel_cmd(*cmd)
        d.qpos[:3]=[0,0,.125];d.qpos[3:7]=[1,0,0,0];d.qpos[c.qids]=policy.default_pose
        mujoco.mj_forward(m,d);c.reset(d.qpos)
        rows=[];stop=None;fall=None
        for i in range(round(seconds/.02)):
            start=time.perf_counter_ns();action=policy.infer();latency=(time.perf_counter_ns()-start)/1e6
            if not np.isfinite(action).all():stop='nonfinite_action';break
            policy.apply_action(action)
            target=c.q_target.copy()
            for _ in range(4):
                c.update();mujoco.mj_step(m,d)
                if not np.isfinite(d.qpos).all() or not np.isfinite(d.qvel).all():stop='nonfinite_state';break
                tilt=float(np.degrees(np.arccos(np.clip(1-2*(d.qpos[4]**2+d.qpos[5]**2),-1,1))))
                if tilt>55 or d.qpos[2]<.06:fall=float(d.time);stop='fall';break
            mujoco.mj_forward(m,d)
            q=d.qpos[c.qids];ranges=m.jnt_range[c.joint_ids];limited=m.jnt_limited[c.joint_ids].astype(bool)
            excess=np.maximum(ranges[:,0]-q,q-ranges[:,1]);target_excess=np.maximum(ranges[:,0]-target,target-ranges[:,1])
            quat=d.xquat[policy.trunk_base_id];vx=policy.quat_rotate_inverse(quat,d.qvel[:3])[0]
            rows.append({'time_s':float(d.time),'tilt_deg':tilt,'z_m':float(d.qpos[2]),
                'vx_body_m_s':float(vx),'yaw_rate_rad_s':float(d.qvel[5]),'inference_ms':latency,
                'joint_limit_excess_rad':float(max(0,excess[limited].max())),
                'target_limit_excess_rad':float(max(0,target_excess[limited].max())),
                'worst_target_joint':m.joint(int(c.joint_ids[np.argmax(np.where(limited,target_excess,-np.inf))])).name,
                'warning_count':int(sum(x.number for x in d.warning))})
            if stop:break
        write(output/f'{label}-trajectory.json',rows)
        warning=max((x['warning_count'] for x in rows),default=0)
        joint=max((x['joint_limit_excess_rad'] for x in rows),default=0)
        target_limit=max((x['target_limit_excess_rad'] for x in rows),default=0)
        vx_rmse=float(np.sqrt(np.mean([(x['vx_body_m_s']-cmd[0])**2 for x in rows]))) if rows else None
        yaw_rmse=float(np.sqrt(np.mean([(x['yaw_rate_rad_s']-cmd[2])**2 for x in rows]))) if rows else None
        # Explicit quick-screen thresholds, not established gait acceptance criteria.
        passed=(not stop and warning==0 and joint<=.01 and target_limit<=.01 and
                vx_rmse is not None and vx_rmse<=.1 and yaw_rmse<=.2)
        results.append({'scenario':label,'command':cmd,'status':'PASS' if passed else 'FAIL',
            'requested_s':seconds,'completed_s':float(d.time),'fall_time_s':fall,'stop_reason':stop,
            'max_tilt_deg':max((x['tilt_deg'] for x in rows),default=None),
            'vx_rmse_m_s':vx_rmse,'yaw_rmse_rad_s':yaw_rmse,
            'max_joint_limit_excess_rad':joint,'max_target_limit_excess_rad':target_limit,
            'warning_count':warning,'inference_p95_ms':float(np.percentile([x['inference_ms'] for x in rows],95)) if rows else None})
    return {'status':'PASS' if all(x['status']=='PASS' for x in results) else 'FAIL',
        'scope':'native provisional PD CPU; deterministic HOME start; fixed 7.4V/4 physics-step delay; no DR',
        'thresholds':{'fall_tilt_deg':55,'fall_root_z_m':.06,'joint_or_target_excess_rad':.01,
                      'vx_rmse_m_s':.1,'yaw_rmse_rad_s':.2,'warnings':0},
        'source':actual,'native_files':{n:digest(repo/n) for n in ['scripts/infer_policy.py',
            'src/mjlab_microduck/actuator/hd1910.py','src/mjlab_microduck/actuator/hd1910_profile.json']},
        'scenarios':results,'hardware':'NOT_RUN'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=['prepare','prepare-kissqy-native','check','replay-qiaosiyi'])
    p.add_argument('--sources',type=Path);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=10)
    args=p.parse_args();output=args.output.resolve();source=args.sources.resolve() if args.sources else None
    if args.mode not in ('prepare','prepare-kissqy-native') and source is None:p.error('--sources is required')
    if not 2<=args.seconds<=30:p.error('--seconds must be 2..30')
    if args.mode=='prepare':prepare(output);return 0
    if args.mode=='prepare-kissqy-native':prepare_native(output);return 0
    if args.mode=='check':result=check(source,output)
    else:
        fresh(output)
        try:result=replay_qia(source,output,args.seconds)
        except Exception as exc:
            result={'status':'NOT_RUN' if isinstance(exc,(ImportError,FileNotFoundError)) else 'FAIL',
                    'reason':f'{type(exc).__name__}: {exc}','traceback':traceback.format_exc()}
        write(output/'report.json',result)
    print(json.dumps({'output':str(output),'status':result.get('status'),
                      'models':{k:v['status'] for k,v in result.get('models',{}).items()}}))
    return int(result.get('status') in ('FAIL','NOT_RUN') or any(v['status']=='FAIL' for v in result.get('models',{}).values()))

if __name__=='__main__':sys.exit(main())
