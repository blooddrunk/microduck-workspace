#!/usr/bin/env python3
"""Native kissqy CPU replay; no hardware imports, services, viewer, or training.

Requires private source archives of the pinned official engine and kissqy
training directory, plus the pinned downloads from evaluate_community_policies.
Uses the pre-existing HD1910 venv only as a dependency runtime, never its PD model.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--native-sources',type=Path,required=True)
    p.add_argument('--sources',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seconds',type=float,default=10)
    args=p.parse_args()
    if not 2<=args.seconds<=30:p.error('--seconds must be 2..30')
    out=args.output.resolve()
    if out.exists() and any(out.iterdir()):p.error('output must be new')
    out.mkdir(parents=True,exist_ok=True)
    result={'status':'NOT_RUN','hardware':'NOT_RUN','scope':'native kissqy M6/backlash on CPU; no hardware acceptance'}
    env=None
    try:
        b=args.native_sources.resolve();package=args.sources.resolve()/'kissqy/microduck-hd1910/firmware/policies/walk'
        inventory=json.loads((b/'native-inventory.json').read_text())
        expected={'official-rl':'8d0db74916a4f833d1d9b95d6a1d7f4d13b9d5ec',
                  'kissqy-runtime':'f02e875e73b88bf8ec7d5bbb34d0b461ac83b010'}
        if {s['repository']:s['commit'] for s in inventory['sources']}!=expected:
            raise ValueError('Native source pins differ')
        for name,sha in inventory['files'].items():
            if hashlib.sha256((b/name).read_bytes()).hexdigest()!=sha:
                raise ValueError('Native source changed: '+name)
        result['native_source_verification']={'status':'PASS','sources':inventory['sources'],
                                              'files_checked':len(inventory['files'])}
        training=b/'kissqy/microduck-hd1910/training-console'
        sys.path[:0]=[str(b/'kissqy-engine/src'),str(training)]
        import numpy as np
        import torch
        torch.set_num_threads(1)
        import mjlab.tasks,mjlab_microduck.tasks
        from mjlab.tasks.registry import load_env_cfg,load_rl_cfg
        from training.runtime_adapter import apply_recipe,configure_evaluation_events
        from training.recipe import model_details
        from training.sim_protocol import OnnxPolicy
        from mjlab.envs import ManagerBasedRlEnv
        req=json.loads((package/'training-request.json').read_text());req['op']='onnx'
        contract=json.loads((package/'deployment-contract.json').read_text())
        manifest=json.loads((package/'manifest.json').read_text())
        path=package/'policy.onnx'
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['onnx_sha256']:raise ValueError('ONNX digest mismatch')
        cfg=load_env_cfg(req['task'],play=True);agent=load_rl_cfg(req['task']);apply_recipe(cfg,agent,req)
        detail=model_details(cfg)
        actual=detail['actuators'][0];expected=contract['training_physics']['actuators'][0]
        fields=['kp_fw','delay_min_lag','delay_max_lag','vin_range','vin_min','vin_drop_gain_range']
        checks={k:actual[k]==expected[k] for k in fields}
        checks['m6_sha256']=actual['parameter_file']['sha256']==expected['parameter_file']['sha256']
        homes={j['name']:j['home_rad'] for j in detail['joints']}
        checks['home']=all(abs(homes[n]-v)<1e-7 for n,v in zip(contract['runtime_joint_order'],contract['runtime_home_rad']))
        checks['action_scale']=cfg.actions['joint_pos'].scale==contract['trained_action_scale']
        checks['no_filter']=not contract['action_filter']['enabled']
        result['contract_checks']=checks
        result['native_actuator']=actual
        if not all(checks.values()):raise ValueError('Reconstructed native physics differs from deployment contract')
        configure_evaluation_events(cfg,req)
        cfg.scene.num_envs=1;cfg.seed=42;cfg.auto_reset=False
        env=ManagerBasedRlEnv(cfg,device='cpu')
        print('Native CPU environment constructed',flush=True)
        groups=agent.obs_groups['actor'];policy=OnnxPolicy(path,61,14,groups,'cpu')
        result['status']='RUNNING'
        robot=env.scene['robot'];names=robot.joint_names
        ids=[names.index(n) for n in contract['runtime_joint_order']]
        result['scenarios']=[]
        for label,cmd in [('zero',[0,0,0]),('forward',[.1,0,0]),('turn',[0,0,.2])]:
            env.reset(seed=42);policy.reset()
            # Controlled upright HOME start on the native terrain's environment origin.
            state=torch.zeros((1,13));state[:,:3]=env.scene.env_origins;state[:,2]+=.125;state[:,3]=1
            robot.write_root_state_to_sim(state)
            robot.write_joint_state_to_sim(robot.data.default_joint_pos.clone(),torch.zeros_like(robot.data.default_joint_pos))
            env.scene.write_data_to_sim();env.sim.forward();env.scene.update(dt=env.physics_dt)
            obs=env.observation_manager.compute(update_history=True)
            rows=[];reason=None
            for i in range(round(args.seconds/.02)):
                vector=torch.cat([obs[g] for g in groups],dim=-1).cpu().numpy().copy()
                vector[:,48:]=0;vector[:,48:51]=cmd
                start=time.perf_counter_ns();action=policy.infer_array(vector);latency=(time.perf_counter_ns()-start)/1e6
                if not np.isfinite(action).all():reason='nonfinite_action';break
                obs,reward,terminated,truncated,extras=env.step(torch.as_tensor(action,dtype=torch.float32))
                quat=robot.data.root_link_quat_w[0];tilt=float(torch.rad2deg(torch.acos(torch.clamp(1-2*(quat[1]**2+quat[2]**2),-1,1))))
                q=robot.data.joint_pos[0,ids].cpu().numpy();limits=robot.data.default_joint_pos_limits[0,ids].cpu().numpy()
                target=np.asarray(contract['runtime_home_rad'])+action[0]
                joint_excess=float(max(0,np.maximum(limits[:,0]-q,q-limits[:,1]).max()))
                target_excess=float(max(0,np.maximum(limits[:,0]-target,target-limits[:,1]).max()))
                z=float(robot.data.root_link_pos_w[0,2]-env.scene.env_origins[0,2])
                finite=bool(torch.isfinite(env.sim.data.qpos[:]).all() and torch.isfinite(env.sim.data.qvel[:]).all())
                rows.append({'time_s':(i+1)*.02,'tilt_deg':tilt,'root_z_relative_origin_m':z,
                    'vx_body_m_s':float(robot.data.root_link_lin_vel_b[0,0]),
                    'yaw_rate_rad_s':float(robot.data.root_link_ang_vel_b[0,2]),'inference_ms':latency,
                    'joint_limit_excess_rad':joint_excess,'target_limit_excess_rad':target_excess,
                    'finite':finite,'terminated':bool(terminated.any()),'truncated':bool(truncated.any())})
                if not finite:reason='nonfinite_state'
                elif tilt>55 or z<.06:reason='fall'
                elif bool(terminated.any()):reason='native_termination'
                elif bool(truncated.any()):reason='native_timeout'
                if reason:break
            (out/f'{label}-trajectory.json').write_text(json.dumps(rows,indent=2,allow_nan=False)+'\n')
            vx=float(np.sqrt(np.mean([(r['vx_body_m_s']-cmd[0])**2 for r in rows]))) if rows else None
            yaw=float(np.sqrt(np.mean([(r['yaw_rate_rad_s']-cmd[2])**2 for r in rows]))) if rows else None
            je=max((r['joint_limit_excess_rad'] for r in rows),default=0);te=max((r['target_limit_excess_rad'] for r in rows),default=0)
            result['scenarios'].append({'scenario':label,'command':cmd,'requested_s':args.seconds,'completed_s':len(rows)*.02,
                'status':'PASS' if rows and not reason and je<=.01 and te<=.01 and vx<=.1 and yaw<=.2 else 'FAIL',
                'stop_reason':reason,'max_tilt_deg':max((r['tilt_deg'] for r in rows),default=None),
                'vx_rmse_m_s':vx,'yaw_rmse_rad_s':yaw,'max_joint_limit_excess_rad':je,
                'max_target_limit_excess_rad':te,'inference_p95_ms':float(np.percentile([r['inference_ms'] for r in rows],95)) if rows else None})
            (out/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
        result['status']='PASS' if all(s['status']=='PASS' for s in result['scenarios']) else 'FAIL'
        result['conditions']={'seed':42,'terrain':'native Rough generator','auto_reset':False,'pushes':False,
            'commands':'raw ONNX command block overridden each step, head/body zero',
            'randomization':'native startup/randomization retained; not a deterministic PD comparison',
            'thresholds':{'fall_tilt_deg':55,'fall_root_z_relative_origin_m':.06,'joint_or_target_excess_rad':.01,'vx_rmse_m_s':.1,'yaw_rmse_rad_s':.2},
            'warning_count':'NOT_RUN: no per-step warning counter exported by this adapter'}
    except Exception as exc:
        result['reason']=f'{type(exc).__name__}: {exc}';result['traceback']=traceback.format_exc()
        result['status']='FAIL' if env is not None else 'NOT_RUN'
    finally:
        if env is not None:env.close()
    (out/'report.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':result['status'],'reason':result.get('reason')}))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':sys.exit(main())
