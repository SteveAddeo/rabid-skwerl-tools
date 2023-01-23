import pymel.core as pm
from core import utils


def make_distance(jnts, ctl=None):
    name = utils.get_info_from_joint(jnts[0], name=True)
    baseLoc = pm.spaceLocator(n=f"{name}_IK_base_loc")
    tipLoc = pm.spaceLocator(n=f"{name}_IK_tip_loc")
    dist = pm.shadingNode("distanceBetween", n=f"{name}_dist", au=1)
    pm.xform(baseLoc, t=pm.xform(jnts[0], q=1, ws=1, rp=1))
    pm.xform(tipLoc, t=pm.xform(jnts[-1], q=1, ws=1, rp=1))
    pm.parent(baseLoc, jnts[0])
    if ctl is None:
        pm.parent(tipLoc, jnts[-1])
        pm.warning(f"The IK Stretch for {name} did not include a control. "
                   f"{name}_IK_tip_loc was parented to {jnts[-1].name()}. "
                   f"Remember to manually parent {name}_IK_tip_loc to the main IK control.")
    else:
        pm.parent(tipLoc, ctl)
    pm.connectAttr(baseLoc.worldMatrix[0], dist.inMatrix1)
    pm.connectAttr(tipLoc.worldMatrix[0], dist.inMatrix2)
    return dist


class Build(object):
    # TODO: end joint looks like it has double transforms when rotating around the Z axis
    def __init__(self, stretch_jnts, curve, skin_jnts=None, vol=True):
        self.name = "_".join(stretch_jnts[0].split("_")[:-1])
        self.stretchJoints = stretch_jnts
        self.curveInfo = utils.check_shading_node(f"{curve.name()}_info", "curveInfo")
        self.skinJoints = skin_jnts
        self.vol = vol
        self.roo = str(self.stretchJoints[0].getRotationOrder())
        print(self.roo)
        # self.ikCtl = ctls_obj.ikMain
        # Create Stretch Nodes
        self.stretchVal = utils.check_shading_node(f"{self.name}_stretch_val", "multiplyDivide")
        self.squashVal = utils.check_shading_node(f"{self.name}_squash_val", "multiplyDivide")
        self.localMult = utils.check_shading_node(f"local_scale_mult", "multDoubleLinear")
        self.scaleMult = utils.check_shading_node(f"{self.name}_scale_mult", "multDoubleLinear")
        self.squashDiv = utils.check_shading_node(f"{self.name}_squash_div", "multiplyDivide")
        self.stretchMult = utils.check_shading_node(f"{self.name}_stretch_scale_mult", "multDoubleLinear")
        self.arcLength = self.curveInfo.arcLength.get()
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
        # Create IK stretch
        localMult = utils.check_shading_node(f"local_scale_mult", "multDoubleLinear")
        ikScaleMult = utils.check_shading_node(f"{self.name}_IK_scale_mult", "multDoubleLinear")
        ikStretchVal = utils.check_shading_node(f"{self.name}_IK_stretch_val", "multiplyDivide")
        cond = utils.check_shading_node(f"{self.name}_IK_str_cond", "condition")
        """chainLen = utils.get_length_of_chain(self.stretchJoints[0], self.driver.aimVector)
        dist = make_distance(self.stretchJoints, self.ikCtl)"""
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
        # Create nodes
        self.ikStretchSwitch = pm.shadingNode("condition", n=f"{self.name}_stretch_sw", au=1)
        ikJnts = utils.get_joints_in_chain(pm.PyNode(f"{self.name}_base_IK_jnt"))
        # Make connections
        pm.connectAttr(self.stretchVal.outputX, self.ikStretchSwitch.colorIfTrueR, f=1)
        for jnt in ikJnts:
            pm.connectAttr(self.ikStretchSwitch.outColorR, jnt.scaleX, f=1)
        if not self.ik.spline:
            self.make_ik_stretch()

    def set_skin_scale(self):
        """# Create Nodes
        localMult = utils.check_shading_node(f"local_scale_mult", "multDoubleLinear")
        scaleMult = utils.check_shading_node(f"{self.name}_scale_mult", "multDoubleLinear")
        squashDiv = utils.check_shading_node(f"{self.name}_squash_div", "multiplyDivide")
        stretchMult = utils.check_shading_node(f"{self.name}_stretch_scale_mult", "multDoubleLinear")
        arcLength = self.curveInfo.arcLength.get()
        # Set Attribute Values

        scaleMult.input1.set(arcLength)

        squashDiv.operation.set(2)
        squashDiv.input1X.set(1)
        # Connect Nodes
        pm.connectAttr(localMult.output, scaleMult.input2, f=1)
        pm.connectAttr(self.driver.crvInfo.arcLength, self.stretchVal.input1X, f=1)
        pm.connectAttr(scaleMult.output, self.stretchVal.input2X, f=1)
        pm.connectAttr(self.stretchVal.outputX, self.squashVal.input1X, f=1)
        pm.connectAttr(self.squashVal.outputX, squashDiv.input2X, f=1)
        pm.connectAttr(squashDiv.outputX, stretchMult.input1, f=1)
        pm.connectAttr(scaleMult.input2, stretchMult.input2, f=1)"""
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


