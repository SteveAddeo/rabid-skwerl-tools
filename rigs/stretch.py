import pymel.core as pm
from core import utils


def make_dist(jnts, ctl=None):
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


# TODO: skin object is any class that creates skin joints (currently only ribbon class does this)
class Build(object):
    def __init__(self, driver_obj, ctls_obj, ik_obj, skin_obj):
        self.driver = driver_obj
        self.ik = ik_obj
        self.name = self.driver.name
        self.ikJoints = self.ik.joints
        self.skinJoints = skin_obj.skinJoints
        self.ikCtl = ctls_obj.ikMain
        self.stretchVal = None
        # TODO: Connect the following nodes to controller attributes
        self.squashVal = None
        self.ikStretchSwitch = None

    def make_ik_stretch(self):
        # Create IK stretch
        ikScaleMult = utils.check_shading_node(f"{self.name}_IK_scale_mult", "multDoubleLinear")
        ikStretchVal = utils.check_shading_node(f"{self.name}_IK_stretch_val", "multiplyDivide")
        cond = utils.check_shading_node(f"{self.name}_IK_str_cond", "condition")
        chainLen = utils.get_length_of_chain(self.ikJoints[0], self.driver.aimVector)
        dist = make_dist(self.ikJoints, self.ikCtl)
        # Set Attribute Values
        ikScaleMult.input1.set(chainLen)
        ikStretchVal.operation.set(2)
        cond.secondTerm.set(1)
        cond.operation.set(2)
        # Connect Nodes
        pm.connectAttr("local_scale_mult.output", ikScaleMult.input2, f=1)
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

    def set_skin_jnt_scale(self):
        # Create Nodes
        self.stretchVal = utils.check_shading_node(f"{self.name}_stretch_val", "multiplyDivide")
        self.squashVal = utils.check_shading_node(f"{self.name}_squash_val", "multiplyDivide")
        scaleMult = utils.check_shading_node(f"{self.name}_scale_mult", "multDoubleLinear")
        squashDiv = utils.check_shading_node(f"{self.name}_squash_div", "multiplyDivide")
        stretchMult = utils.check_shading_node(f"{self.name}_stretch_scale_mult", "multDoubleLinear")
        arcLength = self.driver.crvInfo.arcLength.get()
        # Set Attribute Values
        self.stretchVal.operation.set(2)
        scaleMult.input1.set(arcLength)
        self.squashVal.operation.set(3)
        self.squashVal.input2X.set(0.5)
        squashDiv.operation.set(2)
        squashDiv.input1X.set(1)
        # Connect Nodes
        pm.connectAttr("local_scale_mult.output", scaleMult.input2, f=1)
        pm.connectAttr(self.driver.crvInfo.arcLength, self.stretchVal.input1X, f=1)
        pm.connectAttr(scaleMult.output, self.stretchVal.input2X, f=1)
        pm.connectAttr(self.stretchVal.outputX, self.squashVal.input1X, f=1)
        pm.connectAttr(self.squashVal.outputX, squashDiv.input2X, f=1)
        pm.connectAttr(squashDiv.outputX, stretchMult.input1, f=1)
        pm.connectAttr(scaleMult.input2, stretchMult.input2, f=1)
        for jnt in self.skinJoints:
            pm.connectAttr(scaleMult.input2, jnt.scaleX, f=1)
            pm.connectAttr(stretchMult.output, jnt.scaleY, f=1)
            pm.connectAttr(stretchMult.output, jnt.scaleZ, f=1)


