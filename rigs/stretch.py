import pymel.core as pm
from core import utils


class Build(object):
    # TODO: end joint looks like it has double transforms when rotating around the Z axis
    # TODO: only works for spline curve rigs like necks and tails. Needs to be able to work with
    #  distance-based rigs like arms and legs
    def __init__(self, stretch_jnts, curve, skin_jnts=None, vol=True):
        """
        Builds a stretch rig for a given set of joints and sets up scale functionality on skinned joints to
        preserve volume if specified.
        :param stretch_jnts: list: joints the stretch is being applied to
        :param curve: PyNode: Curve who's relative length is driving the scale operations
        :param skin_jnts: list: if the joints being skinned are separate from the stretch joints
        :param vol: bool: whether or not to preserve the volume of a given node
        """
        self.name = "_".join(stretch_jnts[0].split("_")[:-1])
        self.stretchJoints = stretch_jnts
        self.curveInfo = utils.check_hypergraph_node(f"{curve.name()}_info", "curveInfo")
        self.skinJoints = skin_jnts
        self.vol = vol
        self.roo = str(self.stretchJoints[0].getRotationOrder())
        # self.ikCtl = ctls_obj.ikMain
        # Create Stretch Nodes
        self.stretchVal = utils.check_hypergraph_node(f"{self.name}_stretch_val", "multiplyDivide")
        self.squashVal = utils.check_hypergraph_node(f"{self.name}_squash_val", "multiplyDivide")
        self.localMult = utils.check_hypergraph_node(f"local_scale_mult", "multDoubleLinear")
        self.scaleMult = utils.check_hypergraph_node(f"{self.name}_scale_mult", "multDoubleLinear")
        self.squashDiv = utils.check_hypergraph_node(f"{self.name}_squash_div", "multiplyDivide")
        self.stretchMult = utils.check_hypergraph_node(f"{self.name}_stretch_scale_mult", "multDoubleLinear")
        self.arcLength = self.curveInfo.arcLength.get()
        # TODO: stretch switch needs to be set up
        self.ikStretchSwitch = None
        # Set Attribute Values
        for i in range(2):
            if not eval(f"self.localMult.input{i + 1}.get()"):
                eval(f"self.localMult.input{i + 1}.set(1)")
        self.scaleMult.input1.set(self.arcLength)
        self.stretchVal.operation.set(2)
        self.squashVal.operation.set(3)
        self.squashVal.input2X.set(0.5)
        self.squashDiv.operation.set(2)
        self.squashDiv.input1X.set(1)
        # Connect Nodes
        pm.connectAttr(self.localMult.output, self.scaleMult.input2, f=1)
        pm.connectAttr(self.curveInfo.arcLength, self.stretchVal.input1X, f=1)
        pm.connectAttr(self.scaleMult.output, self.stretchVal.input2X, f=1)
        pm.connectAttr(self.stretchVal.outputX, self.squashVal.input1X, f=1)
        pm.connectAttr(self.squashVal.outputX, self.squashDiv.input2X, f=1)
        pm.connectAttr(self.squashDiv.outputX, self.stretchMult.input1, f=1)
        pm.connectAttr(self.scaleMult.input2, self.stretchMult.input2, f=1)
        for strJnt in self.stretchJoints[:-1]:
            pm.connectAttr(self.stretchVal.outputX, eval(f"strJnt.scale{self.roo[0].upper()}"), f=1)
        self.set_skin_scale()

    def make_ik_stretch(self):
        """
        Creates a stretch setup based on distance from the primary IK control and the base IK joint
        rather than one based of the length of a spline curve
        :return:
        """
        # TODO: this section is still under construction. Doesn't currently run in the class
        # Create IK stretch
        localMult = utils.check_hypergraph_node(f"local_scale_mult", "multDoubleLinear")
        ikScaleMult = utils.check_hypergraph_node(f"{self.name}_IK_scale_mult", "multDoubleLinear")
        ikStretchVal = utils.check_hypergraph_node(f"{self.name}_IK_stretch_val", "multiplyDivide")
        cond = utils.check_hypergraph_node(f"{self.name}_IK_str_cond", "condition")
        chainLen = utils.get_length_of_chain(self.stretchJoints[0], self.driver.aimVector)
        dist = utils.make_distance(name=f"{utils.get_info_from_joint(self.stretchJoints[0], name=True)}_IK",
                                   start=self.stretchJoints[0], end=self.ikCtl)
        # Set Attribute Values
        ikScaleMult.input1.set(chainLen)
        ikStretchVal.operation.set(2)
        cond.secondTerm.set(1)
        cond.operation.set(2)
        # Connect Nodes
        pm.connectAttr(self.localMult.output, ikScaleMult.input2, f=1)
        pm.connectAttr(dist.distance, ikStretchVal.input1X, f=1)
        pm.connectAttr(ikStretchVal.outputX, cond.firstTerm, f=1)
        pm.connectAttr(ikStretchVal.outputX, cond.colorIfTrueR, f=1)
        pm.connectAttr(ikStretchVal.outputX, self.ikStretchSwitch.colorIfTrueR, f=1)
        # connect locators to dist node

    def set_ik_jnt_scale(self):
        """
        Sets up a switch to turn the IK Stretch on and off
        """
        # TODO: I'm not sure this method is necessary and could just be part of the make_ik_stretch() method
        # Create nodes
        self.ikStretchSwitch = pm.shadingNode("condition", n=f"{self.name}_stretch_sw", au=1)
        ikJnts = utils.get_joints_in_chain(pm.PyNode(f"{self.name}_base_IK_jnt"))
        # Make connections
        pm.connectAttr(self.stretchVal.outputX, self.ikStretchSwitch.colorIfTrueR, f=1)
        for jnt in ikJnts:
            pm.connectAttr(self.ikStretchSwitch.outColorR, eval(f"jnt.scale{self.roo[0].upper()}"), f=1)
        """if not self.ik.spline:
            self.make_ik_stretch()"""

    def set_skin_scale(self):
        """
        Sets the scale value for the skin joints so that they are able to stretch with the stretch joints as
        well as preserve volume if specified
        """
        if self.skinJoints is not None:
            for sknJnt in self.skinJoints:
                pm.connectAttr(self.scaleMult.input2, eval(f"sknJnt.scale{self.roo[0].upper()}"), f=1)
                if self.vol:
                    pm.connectAttr(self.stretchMult.output, eval(f"sknJnt.scale{self.roo[1].upper()}"), f=1)
                    pm.connectAttr(self.stretchMult.output, eval(f"sknJnt.scale{self.roo[2].upper()}"), f=1)
        else:
            for strJnt in [jnt for jnt in self.stretchJoints if self.vol]:
                pm.connectAttr(self.stretchMult.output, eval(f"strJnt.scale{self.roo[1].upper()}"), f=1)
                pm.connectAttr(self.stretchMult.output, eval(f"strJnt.scale{self.roo[2].upper()}"), f=1)


