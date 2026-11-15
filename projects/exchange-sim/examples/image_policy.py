"""Replace the entire image-to-command algorithm, bypassing built-in perception.

Run from the project: python3 -m exchange_sim --headless --vision none \
    --policy examples.image_policy --mode fixed
"""
from exchange_sim.vision import BaselineVision
from exchange_sim.policies import FollowPolicy
from dataclasses import replace


class ImagePolicy:
    def __init__(self,settings):
        self.vision=BaselineVision(settings['camera'])
        self.controller=FollowPolicy(settings)
        self.last_frame=None; self.observation=None

    def step(self,sensors):
        if sensors.image is not None and sensors.frame_id!=self.last_frame:
            self.observation=self.vision.process(sensors.image,sensors.frame_id,sensors.image_captured_at)
            if self.observation is not None:
                self.observation['captured_at']=sensors.image_captured_at
            self.last_frame=sensors.frame_id
        return self.controller.step(replace(sensors,observation=self.observation))


def make_policy(settings):
    return ImagePolicy(settings)
