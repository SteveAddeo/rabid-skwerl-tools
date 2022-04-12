import pymel.core as pm
import maya.api.OpenMaya as api
from core import constants


def get_name_from_joint(joint):
    if "_prime_jnt" in str(joint):
        return str(joint).replace("_primary_jnt", "")
    if "_jnt" in str(joint):
        return str(joint).replace("_jnt", "")
    return str(joint)


def get_parent_and_children(joint):
    if pm.listRelatives(joint, p=1):
        parent = pm.listRelatives(joint, p=1)[0]
    else:
        parent = None
    if pm.listRelatives(joint, c=1):
        children = pm.listRelatives(joint, c=1)
    else:
        children = None
    return [parent, children]


def get_type_from_joint(joint):
    return str(joint).split("_")[-2]


def list_joints_in_chain(joint):
    jnts = [jnt for jnt in reversed(pm.listRelatives(joint, ad=1))]
    jnts.insert(0, joint)
    return jnts


class Build(object):
    def __init__(self, guides_obj, orientation="xyz", invert=False, orient_tip=True, orient_chain_to_world=False):
        self.guidesObj = guides_obj
        self.name = self.guidesObj.name
        self.guides = self.guidesObj.allGuides
        self.orientation = orientation
        self.invert = invert
        self.orientTip = orient_tip
        self.orientToWorld = orient_chain_to_world
        self.mainJointsGrp = self.get_joints_grp("jnts_grp")
        self.subJointsGrp = self.get_joints_grp("{}_jnts_grp".format(self.name), parent=self.mainJointsGrp)
        self.primaryJointsGrp = self.get_joints_grp("{}_prime_jnts_grp".format(self.name), parent=self.subJointsGrp)
        self.aimAxis = self.get_vector_from_axis(self.orientation[0].capitalize())
        self.upAxis = self.get_vector_from_axis(self.orientation[1].capitalize())
        self.tertiaryAxis = self.get_vector_from_axis(self.orientation[2].capitalize())
        self.primaryJoints = self.get_primary_joints()
        self.longAxis = self.get_long_axis()
        self.check_rotation(self.primaryJoints)

    def check_rotation(self, joints=None, long_axis=None):
        if joints is None:
            joints = self.primaryJoints
        if long_axis is None:
            long_axis = self.longAxis
        for i, jnt in enumerate(joints[1:-1], 1):
            prevJnt = joints[i - 1]
            # Get the World Space Matrix of the joints
            jntWS = pm.xform(jnt, q=1, m=1, ws=1)
            prevJntWS = pm.xform(prevJnt, q=1, m=1, ws=1)
            # Get Axis Direction (matrix)
            mtxRange = constants.get_axis_matrix_range(self.orientation[-1])
            jntAxis = api.MVector(jntWS[mtxRange[0]:mtxRange[1]])
            prevJntAxis = api.MVector(prevJntWS[mtxRange[0]:mtxRange[1]])
            # Determine which vector to "look" at the axis from
            if long_axis == "Z":
                axisV = constants.get_axis_vector("X")
            else:
                axisV = constants.get_axis_vector("Z")
            # Get Axis direction based on axis vector (range -1.0 - 1.0)
            jntAxisDir = jntAxis * api.MVector(axisV[0], axisV[1], axisV[2])
            prevJntAxisDir = prevJntAxis * api.MVector(axisV[0], axisV[1], axisV[2])
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

    def get_primary_joints(self):
        if pm.listRelatives(self.primaryJointsGrp, c=1):
            jnts = [jnt for jnt in reversed(pm.listRelatives(self.primaryJointsGrp, ad=1))]
        else:
            jnts = self.make_primary_chain()
        longAxis = self.get_long_axis(jnts[0])
        self.orient_joints_in_chain(jnts)
        self.check_rotation(jnts, longAxis)
        return jnts

    def get_joints_grp(self, grp_name, parent=None):
        if pm.ls(grp_name):
            return pm.ls(grp_name)[0]
        grp = pm.group(em=1, n=grp_name)
        if parent is not None:
            pm.parent(grp, parent)
        return grp

    def get_long_axis(self, joint=None):
        if joint is None:
            joint = self.primaryJoints[0]
        aimWM = pm.xform(joint, q=1, m=1, ws=1)
        mtrxRange = constants.get_axis_matrix_range(self.orientation[0])
        aimMtrx = api.MVector(aimWM[mtrxRange[0]:mtrxRange[1]])
        aimUpX = abs(aimMtrx * api.MVector(1, 0, 0))
        aimUpY = abs(aimMtrx * api.MVector(0, 1, 0))
        aimUpZ = abs(aimMtrx * api.MVector(0, 0, 1))
        aimValue = max([aimUpX, aimUpY, aimUpZ])
        if aimValue == aimUpX:
            return "X"
        elif aimValue == aimUpY:
            return "Y"
        else:
            return "Z"

    def get_vector_from_axis(self, axis="X"):
        n = 1
        if self.invert:
            n = -1
        if axis == "Y":
            vector = [0, n, 0]
        elif axis == "Z":
            vector = [0, 0, n]
        else:
            vector = [n, 0, 0]
        return vector

    def make_primary_chain(self):
        # Double check to make sure primary chain doesn't exist
        if pm.listRelatives(self.primaryJointsGrp, c=1):
            return pm.warning("Joint chain for {} already exists".format(self.name))
        # Clear Selection
        pm.select(cl=1)
        # Create a joint for each guide
        jntList = []
        for guide in self.guides:
            jntName = str(guide).replace("_guide", "_prime_jnt")
            jntPos = pm.xform(guide, q=1, ws=1, rp=1)
            jntRad = self.guidesObj.scale * .1
            jnt = pm.joint(n=jntName, p=jntPos, roo=self.orientation, rad=jntRad)
            jntList.append(jnt)
        return jntList

    def orient_joint(self, joint, aim_obj, up_obj=None):
        if up_obj is None:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="vector")
        else:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="object", wuo=up_obj)
        pm.delete(aimConst)
        pm.makeIdentity(joint, a=1)

    def orient_base_joint(self, joint=None, jnt_list=None):
        if joint is None:
            joint = self.primaryJoints[0]
        if jnt_list is None:
            jnt_list = self.primaryJoints
        if self.orientToWorld:
            self.orient_joint(joint, jnt_list[1])
        else:
            self.orient_joint(joint, jnt_list[1], jnt_list[2])

    def orient_mid_joints(self, joint, i, jnt_list=None):
        if jnt_list is None:
            jnt_list = self.primaryJoints
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
            prev_jnt = self.primaryJoints[-2]
        if pm.listRelatives(joint, p=1):
            pm.parent(joint, w=1)
        # Orient tip to World or local
        if self.orientTip:
            pm.parent(joint, prev_jnt)
            for axis in constants.AXES:
                pm.setAttr("foo_tip_prime_jnt.jointOrient{}".format(axis), 0)
        else:
            pm.xform(joint, ws=1, ro=(0, 0, 0))
            pm.makeIdentity(joint, a=1)
            pm.parent(joint, prev_jnt)

    def orient_joints_in_chain(self, joints=None):
        if joints is None:
            joints = self.primaryJoints
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
        pm.parent(joints[0], self.primaryJointsGrp)





