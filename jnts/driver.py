import pymel.core as pm
import maya.api.OpenMaya as om
from core import constants
from core import utils
from jnts import twist


class Build(object):
    # TODO: Orient base to world needs more testing
    def __init__(self, guides_obj, spline=False, orientation="xyz", orient_tip=True,
                 orient_base_to_world=True, orient_chain_to_world=False, make_twist=False):
        self.guides = guides_obj
        self.spline = spline
        self.name = self.guides.name
        self.orientation = orientation
        self.orientTip = orient_tip
        self.orientBase = orient_base_to_world
        self.orientToWorld = orient_chain_to_world
        self.rigGrp = utils.make_group("rig_grp_DO_NOT_TOUCH")
        self.mainJointsGrp = utils.make_group("jnt_grp", parent=self.rigGrp)
        self.mainUtilsGrp = utils.make_group("utils_grp", parent=self.rigGrp)
        self.driverJointsGrp = utils.make_group(f"{self.name}_drv_jnt_grp", parent=self.mainJointsGrp)
        self.aimVector = self.get_vector_from_axis(self.orientation[0].capitalize())
        self.upVector = self.get_vector_from_axis(self.orientation[1].capitalize())
        self.tertiaryVector = self.get_vector_from_axis(self.orientation[2].capitalize())
        self.driverJoints = self.make_driver_chain()
        self.upLoc = self.make_up_loc()
        self.crv = utils.make_curve_from_chain(self.driverJoints[0])
        self.crvInfo = pm.PyNode(f"{self.crv.name()}_info")
        self.longAxis = self.get_long_axis()
        self.check_rotation(self.driverJoints)
        if make_twist:
            self.twistObj = twist.Build(self.driverJoints[0], self.upVector)

    def check_rotation(self, joints=None, long_axis=None):
        if joints is None:
            joints = self.driverJoints
        if long_axis is None:
            long_axis = self.longAxis
        for i, jnt in enumerate(joints[1:-1], 1):
            prevJnt = joints[i - 1]
            # Get the World Space Matrix of the joints
            jntWS = pm.xform(jnt, q=1, m=1, ws=1)
            prevJntWS = pm.xform(prevJnt, q=1, m=1, ws=1)
            # Get Axis Direction (matrix)
            mtxRange = constants.get_axis_matrix_range(self.orientation[-1])
            jntAxis = om.MVector(jntWS[mtxRange[0]:mtxRange[1]])
            prevJntAxis = om.MVector(prevJntWS[mtxRange[0]:mtxRange[1]])
            # Determine which vector to "look" at the axis from
            if long_axis == "Z":
                axisV = constants.get_axis_vector("X")
            else:
                axisV = constants.get_axis_vector("Z")
            # Get Axis direction based on axis vector (range -1.0 - 1.0)
            jntAxisDir = jntAxis * om.MVector(axisV[0], axisV[1], axisV[2])
            prevJntAxisDir = prevJntAxis * om.MVector(axisV[0], axisV[1], axisV[2])
            # Are axes looking up (is it positive according to the axis vector)?
            jntUp = constants.is_positive(jntAxisDir)
            prevJntUp = constants.is_positive(prevJntAxisDir)
            if not jntUp == prevJntUp:
                self.fix_rotation(jnt, joints[i - 1], joints[i + 1])

    def check_rotation_order(self, node):
        if not self.orientation == (str(node.getRotationOrder()).lower()):
            pm.xform(node, roo=self.orientation, p=1)
        return node

    def fix_rotation(self, joint, prev_jnt, next_jnt):
        rotList = [0, 0, 0]
        rotAmnt = 180
        rotList[constants.get_axis_index(self.orientation[0])] = rotAmnt
        pm.parent(joint, w=1)
        if pm.listRelatives(joint, c=1):
            pm.parent(next_jnt, w=1)
        pm.xform(joint, ro=rotList, os=1)
        pm.makeIdentity(joint, a=1)
        pm.parent(joint, prev_jnt)
        if not pm.listRelatives(next_jnt, p=1):
            pm.parent(next_jnt, joint)

    def get_long_axis(self, joint=None):
        """
        Gets the general world space direction a joint is pointing towards. Often joints do not align
        with a singular axis in world space; this method determines which direction the joint most closely
        aligns with
        :param joint: joint being queried
        """
        if joint is None:
            joint = self.driverJoints[0]
        aimWM = pm.xform(joint, q=1, m=1, ws=1)
        mtrxRange = constants.get_axis_matrix_range(self.orientation[0])
        aimMtrx = om.MVector(aimWM[mtrxRange[0]:mtrxRange[1]])
        aimUpX = abs(aimMtrx * om.MVector(1, 0, 0))
        aimUpY = abs(aimMtrx * om.MVector(0, 1, 0))
        aimUpZ = abs(aimMtrx * om.MVector(0, 0, 1))
        aimValue = max([aimUpX, aimUpY, aimUpZ])
        if aimValue == aimUpX:
            return "X"
        elif aimValue == aimUpY:
            return "Y"
        else:
            return "Z"

    def get_vector_from_axis(self, axis="X"):
        vector = constants.get_axis_vector(axis)
        if self.guides.mirror:
            vector = [-v for v in vector]
        return vector

    def make_driver_chain(self):
        # Double check to make sure driver chain doesn't exist
        if pm.listRelatives(self.driverJointsGrp, c=1):
            pm.delete(pm.listRelatives(self.driverJointsGrp, ad=1))
            pm.delete(f"{self.name}_crv")
        # Clear Selection
        pm.select(cl=1)
        # Create a joint for each guide
        jntList = []
        for guide in self.guides.allGuides:
            jntName = guide.name().replace("_guide", "_drv_jnt")
            jntPos = pm.xform(guide, q=1, ws=1, rp=1)
            jntRad = self.guides.scale * .1
            print(jntName, jntPos, self.orientation, jntRad)
            jnt = pm.joint(n=jntName, p=jntPos, roo=self.orientation, rad=jntRad)
            pm.setAttr("{}.overrideEnabled".format(jntName), 1)
            pm.setAttr("{}.overrideColor".format(jntName), 1)
            jntList.append(jnt)
        # Set proper rotation and orientation for the guides
        longAxis = self.get_long_axis(jntList[0])
        self.orient_joints_in_chain(jntList)
        self.check_rotation(jntList, longAxis)
        return jntList

    def make_up_loc(self):
        if pm.ls(f"{self.name}_up_loc"):
            return pm.PyNode(f"{self.name}_up_loc")
        loc = pm.spaceLocator(n=f"{self.name}_up_loc")
        pt = pm.pointConstraint(self.driverJoints[0], loc)
        ornt = pm.orientConstraint(self.driverJoints[0], loc)
        pm.delete(pt, ornt)
        pm.move(loc, [-v * (self.guides.scale * .2) for v in self.tertiaryVector], r=1, os=1)
        return loc

    def orient_joint(self, joint, aim_obj, up_obj=None, local=False, neg=False):
        up = self.upVector
        if local:
            up = [v * -1 for v in self.tertiaryVector]
        if neg:
            up = [v * -1 for v in up]
        if up_obj is None:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimVector, u=up, wut="vector")
        else:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimVector, u=up, wut="object", wuo=up_obj)
        pm.delete(aimConst)
        pm.makeIdentity(joint, a=1)

    def orient_base_joint(self, joint=None, jnt_list=None):
        if joint is None:
            joint = self.driverJoints[0]
        if jnt_list is None:
            jnt_list = self.driverJoints
        if self.orientToWorld:
            self.orient_joint(joint, jnt_list[1])
        if self.orientBase:
            self.orient_joint(joint, jnt_list[1], local=True)
        else:
            self.orient_joint(joint, jnt_list[1], jnt_list[2])

    def orient_mid_joints(self, joint, i, jnt_list=None):
        if jnt_list is None:
            jnt_list = self.driverJoints
        # Center Chains align to World Up
        if self.orientToWorld:
            self.orient_joint(joint, jnt_list[i + 1])
        else:
            self.orient_joint(joint, jnt_list[i + 1], jnt_list[i - 1])
        pm.parent(joint, jnt_list[i - 1])

    def orient_tip_joint(self, joint, prev_jnt=None):
        if pm.listRelatives(joint, c=1):
            pm.warning("{} is not a tip joint because it has a child")
            return
        if prev_jnt is None:
            prev_jnt = self.driverJoints[-2]
        if pm.listRelatives(joint, p=1):
            pm.parent(joint, w=1)
        # Orient tip to World or local
        if not self.orientTip:
            pm.xform(joint, ws=1, ro=(0, 0, 0))
            pm.makeIdentity(joint, a=1)
        pm.parent(joint, prev_jnt)

    def orient_joints_in_chain(self, joints=None):
        if joints is None:
            joints = self.driverJoints
        # Unparent all joints before orienting
        for jnt in joints:
            if pm.listRelatives(jnt, p=1):
                pm.parent(jnt, w=1)
                self.check_rotation_order(jnt)
        # Orient Joints
        for i, jnt in enumerate(joints):
            # Set orientation for the Base Joint
            if i == 0:
                self.orient_base_joint(jnt, jnt_list=joints)
            # Set orientation for the Tip Joint
            elif i == len(joints) - 1:
                self.orient_tip_joint(jnt, joints[i - 1])
            # Set orientation for all joints in between
            else:
                self.orient_mid_joints(jnt, i, jnt_list=joints)
        if self.orientTip:
            utils.reset_transforms(joints[-1], t=False, r=False, s=False, m=False, o=True)
        pm.xform(self.driverJointsGrp, t=pm.xform(joints[0], q=1, ws=1, rp=1))
        pm.parent(joints[0], self.driverJointsGrp)
