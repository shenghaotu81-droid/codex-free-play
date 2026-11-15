import copy
import dataclasses
import json
from pathlib import Path
import tempfile
import subprocess
import sys
import unittest
import cv2
import numpy as np
from exchange_sim.world import World,load_config
from exchange_sim.policies import Command,SensorPacket,FollowPolicy
from exchange_sim.protocol import crc,encode_speed,decode_speed,decode_packet,encode_velocity_feedback
from exchange_sim.runtime import PROJECT,make_world,save_run,local_output

cv2.setNumThreads(1)


def config(**overrides):
    c=load_config({'camera':{'noise_sigma':0},'arm':{'grasp_failure_probability':0}})
    for key,value in overrides.items():
        if isinstance(value,dict): c[key].update(value)
        else: c[key]=value
    return load_config(c)


def run(c,**kwargs):
    world=make_world(c,**kwargs)
    try:
        while world.step(): pass
    finally: world.close()
    return world


class ReleasePolicy:
    def step(self,s): return Command(release=True)


class ProtocolTests(unittest.TestCase):
    def test_independent_crc_check_vectors(self):
        # Protocol uses reflected 0x31 with init FF, not MAXIM's init 00.
        self.assertEqual(crc(b'123456789',8),0x0b)
        self.assertEqual(crc(b'123456789',16),0x6f91)

    def test_round_trip_corruption_and_disable(self):
        frame=encode_speed(.5,-.25,1.,True,259,70.)
        self.assertEqual(len(frame),24)
        self.assertEqual(frame[:4],bytes.fromhex('a50f0003'))
        self.assertEqual(decode_speed(frame),(.5,-.25,1.))
        self.assertEqual(decode_speed(encode_speed(9,9,9,False,0,0)),(0,0,0))
        corrupt=bytearray(frame); corrupt[7]^=1
        with self.assertRaisesRegex(ValueError,'CRC'): decode_speed(corrupt)

    def test_protocol_document_wire_examples(self):
        sample=bytes.fromhex('a5 0f 00 00 9c 01 00 00 00 00 3f 00 00 00 00 9a 99 99 3e 16 d2 04 67 0b')
        values=decode_speed(sample)
        self.assertAlmostEqual(values[0],.5);self.assertAlmostEqual(values[2],.3)
        self.assertEqual(encode_velocity_feedback(.5,0,.3,0),bytes.fromhex('a5 06 00 00 12 15 00 88 13 00 00 2c 01 d9 e9'))


class ConfigTests(unittest.TestCase):
    def test_partial_merge_and_invalid_scenarios(self):
        self.assertEqual(load_config({'arm':{'release_delay_s':.25}})['arm']['release_delay_s'],.25)
        for overrides in ({'unknown':1},{'dt_s':0},{'seed':-1},{'camera':{'blur_px':2}},
                          {'camera':{'noise_sigma':float('nan')}},{'link':{'loss_probability':1.1}},
                          {'arm':{'inventory':[1,1]}},{'camera':[]},{'camera':{'width':-1}}):
            with self.subTest(overrides=overrides),self.assertRaises(ValueError):load_config(overrides)

    def test_outputs_stay_in_project(self):
        with self.assertRaises(ValueError): local_output(PROJECT.parent/'escape')


class ClosedLoopTests(unittest.TestCase):
    def test_full_minute_fixed_target_depletes_inventory_and_scores(self):
        w=run(config(target={'mode':'fixed'}),vision='baseline')
        self.assertEqual(w.frame,1800)
        self.assertEqual(w.time,60)
        self.assertEqual((w.hits,w.misses,sum(w.inventory)),(12,0,0))
        self.assertEqual(w.arm_state,'EMPTY')
        self.assertEqual(sum(e['event']=='released' for e in w.events),12)

    def test_repeatable_images_and_environment_independent_of_policy(self):
        c=config(duration_s=3,target={'mode':'random'},camera={'noise_sigma':2})
        a=run(c,vision='baseline'); b=run(c,vision='baseline')
        self.assertEqual(a.summary(),b.summary()); self.assertEqual(a.log,b.log)
        self.assertEqual(a.events,b.events); np.testing.assert_array_equal(a.image,b.image)
        empty=config(duration_s=3,target={'mode':'random'},arm={'inventory':[0,0,0]})
        np.testing.assert_array_equal(a.targets,World(empty).targets)

    def test_blind_algorithm_cannot_get_hits_from_truth(self):
        w=run(config(duration_s=5,camera={'dropout_probability':1}),vision='baseline')
        self.assertEqual(w.hits+w.misses,0); self.assertTrue(w.carry)
        self.assertEqual(w.available_frames,0)
        self.assertEqual(w.car[0],0)

    def test_link_loss_prevents_action_and_triggers_watchdog(self):
        w=make_world(config(duration_s=1,link={'loss_probability':1}),vision='none')
        w.command=np.array([.2,0,0]); w.last_rx=0
        try:
            while w.step(): pass
            self.assertEqual(w.watchdogs,1)
            self.assertTrue(np.all(w.command==0))
            self.assertEqual(w.hits+w.misses,0)
        finally:w.close()

    def test_external_wire_command_is_used_and_bad_crc_is_dropped(self):
        class WirePolicy:
            def step(self,s):
                self.feedback=s.wire_feedback
                frame=encode_speed(.1,0,0,True,0,s.time)
                if s.time>.1:frame=frame[:-1]+bytes([frame[-1]^1])
                return Command(speed_frame=frame)
        w=World(config(duration_s=.5,link={'latency_s':0}),policy_factory=lambda _:WirePolicy())
        try:
            while w.step():pass
            self.assertGreater(w.rejected_frames,0)
            self.assertEqual(w.watchdogs,1)
            self.assertEqual(decode_packet(w.policy.feedback[0])[0],0x15)
            self.assertTrue(np.all(w.command==0))
        finally:w.close()

    def test_release_ack_is_not_a_hit_and_delay_changes_actual_impact(self):
        def toss(delay):
            c=config(duration_s=1,dt_s=.01,target={'mode':'uniform'},link={'latency_s':0},
                     arm={'inventory':[1,0,0],'pick_s':0,'lift_s':0,'release_delay_s':delay,
                          'drop_height_m':0,'scatter_sigma_m':0})
            w=World(c,policy_factory=lambda _:ReleasePolicy())
            try:
                while w.step():pass
            finally:w.close()
            return w
        immediate=toss(0); delayed=toss(.2)
        self.assertEqual((immediate.hits,immediate.misses),(1,0))
        self.assertEqual((delayed.hits,delayed.misses),(0,1))
        self.assertEqual(sum(e['event']=='release_requested' for e in delayed.events),1)

    def test_flights_crossing_deadline_remain_unscored(self):
        c=config(duration_s=.12,dt_s=.01,target={'mode':'fixed'},link={'latency_s':0},
                 arm={'inventory':[1,0,0],'pick_s':0,'lift_s':0,'release_delay_s':0,'drop_height_m':1})
        w=World(c,policy_factory=lambda _:ReleasePolicy())
        try:
            while w.step(): pass
            self.assertEqual(w.hits+w.misses,0); self.assertEqual(len(w.flying),1)
            self.assertEqual(sum(w.inventory)+int(w.carry)+len(w.flying)+w.hits+w.misses,1)
        finally:w.close()

    def test_raw_image_plugin_can_replace_complete_algorithm(self):
        w=run(config(duration_s=5,target={'mode':'fixed'}),vision='none',policy='examples.image_policy')
        self.assertGreaterEqual(w.hits,2)
        self.assertEqual(w.available_frames,0) # built-in perception is really bypassed

    def test_policy_interface_excludes_future_motion_and_seed(self):
        observed={}
        def factory(settings): observed.update(settings); return ReleasePolicy()
        w=World(config(duration_s=.1),policy_factory=factory)
        w.close()
        self.assertNotIn('seed',observed)
        self.assertNotIn('mode',observed['target'])
        self.assertNotIn('half_travel_m',observed['target'])
        names={f.name for f in dataclasses.fields(SensorPacket)}
        self.assertNotIn('target_x',names); self.assertIn('image',names)

    def test_coasting_is_not_permission_to_release(self):
        c=config();settings={k:copy.deepcopy(c[k]) for k in ('camera','arm','algorithm','link','target')}
        p=FollowPolicy(settings)
        obs={'x':0,'y':.052,'depth':.55,'vx':0,'vz':0,'captured_at':0,'measurement_at':0,'measured':False}
        for i in range(12):
            out=p.step(SensorPacket(i/30,obs,(0,0,0),'READY',(1,),True))
            self.assertFalse(out.release)
        self.assertEqual(out,Command())

    def test_save_run_is_replayable_and_refuses_overwrite(self):
        root=PROJECT/'.local/tests';root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            w=run(config(duration_s=.2),vision='baseline')
            output=save_run(w,Path(temporary)/'run')
            self.assertEqual(json.loads((output/'summary.json').read_text()),w.summary())
            self.assertEqual(load_config(output/'config.json'),w.c)
            self.assertTrue((output/'snapshot.png').is_file())
            with self.assertRaises(FileExistsError): save_run(w,output)

    def test_comparison_cli_pairs_scenes_and_writes_both_reports(self):
        root=PROJECT/'.local/tests';root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            output=Path(temporary)/'paired'
            result=subprocess.run([sys.executable,'scripts/compare.py','--vision','none','--duration','.1',
                                   '--seeds','7','--modes','fixed','--output',str(output)],
                                  cwd=PROJECT,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            rows=json.loads((output/'comparison.json').read_text())
            self.assertEqual(len(rows),2)
            self.assertEqual(rows[0]['scene_sha256'],rows[1]['scene_sha256'])
            self.assertTrue((output/'comparison.md').exists())


@unittest.skipUnless((PROJECT/'.local/campus-bridge.json').exists(),'optional pinned C++ bridge is not built')
class CampusIntegrationTests(unittest.TestCase):
    def test_actual_detector_pose_tracker_closed_loop_and_blackout(self):
        w=run(config(duration_s=6,target={'mode':'fixed'}),vision='campus')
        self.assertGreater(w.measured_frames,150)
        self.assertGreaterEqual(w.hits,2)
        blind=run(config(duration_s=2,camera={'dropout_probability':1}),vision='campus')
        self.assertEqual(blind.available_frames,0); self.assertEqual(blind.hits,0)


if __name__=='__main__':unittest.main()
