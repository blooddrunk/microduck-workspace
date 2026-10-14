import copy
import hashlib
import json
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'scripts'))
import review_calibration as c

class CalibrationReviewTests(unittest.TestCase):
    def setUp(self):
        self.data=dict(motion_enabled=False,imu_mount_quat=[1,0,0,0],joints=[
            dict(name=n,id=id,zero_raw=2048,direction=1,calibrated=True,min_rad=-1,max_rad=1)
            for n,id in zip(c.NAMES,c.IDS)])
        self.prov=dict(robot_id='my-offline-fixture',calibration_sha256='f'*64,source='local-readback',evidence_ref='SYNTHETIC ONLY')
    def check(self,data=None,prov=None):return c.review(data or self.data,prov or self.prov,'my-offline-fixture','f'*64)
    def test_consistency_only(self):
        r=self.check();self.assertEqual(r['status'],'PASS');self.assertFalse(r['motion_authorized'])
    def test_foreign_and_hash(self):
        for key,value in [('robot_id','duck-10e4'),('calibration_sha256','a'*64),('source','bundled'),('evidence_ref','')]:
            p=copy.deepcopy(self.prov);p[key]=value;self.assertEqual(self.check(prov=p)['status'],'BLOCKED')
    def test_unsafe_config(self):
        for key,value in [('zero_raw',True),('zero_raw',4096),('direction',0),('min_rad',float('nan')),('max_rad',5),('calibrated',False),('id',200),('name','mouth')]:
            d=copy.deepcopy(self.data);d['joints'][0][key]=value;self.assertEqual(self.check(data=d)['status'],'BLOCKED')
        d=copy.deepcopy(self.data);d['motion_enabled']=True;self.assertEqual(self.check(data=d)['status'],'BLOCKED')
    def test_bad_mount_shape(self):
        for v in [[0,0,0,0],[float('nan'),0,0,0],[1,0,0],['1',0,0,0]]:
            d=copy.deepcopy(self.data);d['imu_mount_quat']=v;self.assertEqual(self.check(data=d)['status'],'BLOCKED')
    def test_order_and_mouth(self):
        self.assertEqual(c.NAMES[9],'mouth');self.assertEqual(c.IDS[9],34)
        d=copy.deepcopy(self.data);d['joints'][9],d['joints'][10]=d['joints'][10],d['joints'][9]
        self.assertEqual(self.check(data=d)['status'],'BLOCKED')
    def test_pinned_assets(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        manifest=json.loads((root/'hardware/reference/manifest.json').read_text())
        for entry in manifest['files']:
            self.assertEqual(hashlib.sha256((root/entry['path']).read_bytes()).hexdigest(),entry['sha256'])

class CalibrationCliTests(unittest.TestCase):
    def test_cli_toml_and_malformed(self):
        import tempfile, subprocess
        script=pathlib.Path(c.__file__).resolve()
        with tempfile.TemporaryDirectory() as tmp:
            p=pathlib.Path(tmp);cfg=p/'cal.toml';prov=p/'prov.json'
            cfg.write_text('motion_enabled = false\nimu_mount_quat = [1, 0, 0, 0]\n')
            prov.write_text(json.dumps(dict(robot_id='fixture',calibration_sha256=hashlib.sha256(cfg.read_bytes()).hexdigest(),source='local-readback',evidence_ref='synthetic')))
            r=subprocess.run([sys.executable,str(script),str(cfg),'--provenance',str(prov),'--robot-id','fixture'],capture_output=True,text=True)
            self.assertEqual(r.returncode,2 if sys.version_info>=(3,11) else 1)
            cfg.write_text('broken = [')
            r=subprocess.run([sys.executable,str(script),str(cfg),'--provenance',str(prov),'--robot-id','fixture'],capture_output=True,text=True)
            self.assertEqual(r.returncode,1);self.assertEqual(json.loads(r.stdout)['status'],'FAIL')
    def test_reference_mapping(self):
        root=pathlib.Path(__file__).resolve().parents[1]
        rows=json.loads((root/'hardware/hd1910-contract.json').read_text())['joints']
        self.assertEqual([r['joint_name'] for r in rows],c.NAMES)
        self.assertEqual([r['design_id'] for r in rows],c.IDS)
        self.assertEqual([r['default_home_rad'] for r in rows],c.HOME)
        self.assertEqual([r['policy_index'] for r in rows],list(range(9))+['excluded']+list(range(9,14)))
        self.assertTrue(all(r['physical_direction']=='UNKNOWN' for r in rows))
