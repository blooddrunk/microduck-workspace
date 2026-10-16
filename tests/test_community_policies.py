"""Small CPU fixtures exercise acceptance failures without downloaded weights."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import evaluate_community_policies as evaluation

AVAILABLE=all(importlib.util.find_spec(n) is not None for n in ('numpy','onnx','onnxruntime'))


@unittest.skipUnless(AVAILABLE,'run with the isolated ONNX CPU environment')
class CommunityChecks(unittest.TestCase):
    def graph(self,path,constant=False,width=61):
        import numpy as np
        import onnx
        from onnx import helper as h,numpy_helper as n,TensorProto as T
        weights=np.random.default_rng(10).normal(size=(width,14)).astype(np.float32)
        if constant:weights[:]=0
        values=[n.from_array(np.zeros((1,width),np.float32),'mean'),
                n.from_array(np.ones((1,width),np.float32),'std'),n.from_array(weights,'w')]
        nodes=[h.make_node('Sub',['obs','mean'],['centered']),
               h.make_node('Div',['centered','std'],['normalized']),
               h.make_node('MatMul',['normalized','w'],['actions'])]
        graph=h.make_graph(nodes,'fixture',[h.make_tensor_value_info('obs',T.FLOAT,[1,width])],
                           [h.make_tensor_value_info('actions',T.FLOAT,[1,14])],values)
        model=h.make_model(graph,opset_imports=[h.make_opsetid('',17)]);model.ir_version=9
        onnx.save(model,path)

    def test_valid_normalized_sensitive_graph(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'good.onnx';self.graph(p)
            result=evaluation.onnx_check(p)
            self.assertEqual(result['status'],'PASS')
            self.assertTrue(result['embedded_normalization'])
            self.assertEqual(set(result['normalizer_constants']),{'mean','std'})

    def test_constant_graph_is_not_behavioral_sensitivity_pass(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'constant.onnx';self.graph(p,constant=True)
            result=evaluation.onnx_check(p)
            self.assertEqual(result['status'],'FAIL');self.assertTrue(result['finite'])
            self.assertFalse(result['output_changes'])

    def test_wrong_width_rejected_before_inference(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'wrong.onnx';self.graph(p,width=60)
            result=evaluation.onnx_check(p)
            self.assertEqual(result['status'],'FAIL')
            self.assertFalse(result['contract_61_to_14_float32'])

    def test_changed_source_rejected_before_model_load(self):
        with tempfile.TemporaryDirectory() as d:
            source=Path(d)/'sources';source.mkdir()
            inventory={}
            for key,(repo,sha,names) in evaluation.SOURCES.items():
                inventory[key]={'repository':repo,'commit':sha,'files':{}}
                p=source/key/names[0];p.parent.mkdir(parents=True);p.write_bytes(b'corrupt')
                inventory[key]['files'][names[0]]={'sha256':'0'*64}
            (source/'inventory.json').write_text(json.dumps(inventory))
            result=evaluation.check(source,Path(d)/'output')
            self.assertEqual(result['status'],'FAIL')
            for model in result['models'].values():
                self.assertIn('Source changed',model['error']);self.assertNotIn('onnx',model)

if __name__=='__main__':unittest.main()
