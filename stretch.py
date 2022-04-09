import pymel.core as pm
import primary


class Build(primary.Build):
    def __init__(self, guides_grp, orientation="xyz", invert=False, orient_tip=True, orient_chain_to_world=False):
        primary.Build.__init__(self, guides_grp, orientation, invert, orient_tip, orient_chain_to_world)
        self.stretchJointsGrp = None
        self.stretchJoints = None
