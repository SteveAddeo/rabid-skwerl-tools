import pymel.core as pm
import maya.api.OpenMaya as api
import constants
import guides


def get_name_from_joint(joint):
    if "_primary_jnt" in str(joint):
        return str(joint).replace("_primary_jnt", "")
    if "_jnt" in str(joint):
        return str(joint).replace("_jnt", "")
    return str(joint)


def list_joints_in_chain(joint):
    jnts = [jnt for jnt in reversed(pm.listRelatives(joint, ad=1))]
    jnts.insert(0, joint)
    return jnts


# TODO: fix axis flipping that happens with hock joints when orienting.
class Build(object):
    def __init__(self, guides_grp, orientation="xyz", invert=False, orient_tip=True, orient_chain_to_world=False):
        self.guidesObj = guides.make_object_from_group(guides_grp)
        self.name = self.guidesObj.name
        self.guides = self.guidesObj.allGuides
        self.orientation = orientation
        self.invert = invert
        self.orientTip = orient_tip
        self.orientToWorld = orient_chain_to_world
        self.mainJointsGrp = self.get_joints_grp("jnts_grp")
        self.subJointsGrp = self.get_joints_grp("{}_jnts_grp".format(self.name), parent=self.mainJointsGrp)
        self.primaryJointsGrp = self.get_joints_grp("{}_primary_jnts_grp".format(self.name), parent=self.subJointsGrp)
        self.aimAxis = self.get_vector_from_axis(self.orientation[0].capitalize())
        self.upAxis = self.get_vector_from_axis(self.orientation[1].capitalize())
        self.tertiaryAxis = self.get_vector_from_axis(self.orientation[2].capitalize())
        self.primaryJoints = self.get_primary_joints()
        self.orient_joints_in_chain()

    def check_rotation(self, joints=None):
        if joints is None:
            joints = self.primaryJoints[1:-1]
        for i, jnt in enumerate(joints[1:-1], 1):
            prevJnt = joints[i - 1]
            # Get the Worldspace Matrix of the joints
            jntWS = pm.xform(jnt, q=1, m=1, ws=1)
            prevJntWS = pm.xform(prevJnt, q=1, m=1, ws=1)
            # Get Axis Direction (matrix)
            mtxRange = constants.get_axis_matrix_range(self.orientation[-1])
            jntAxis = api.MVector(jntWS[mtxRange[0]:mtxRange[1]])
            prevJntAxis = api.MVector(prevJntWS[mtxRange[0]:mtxRange[1]])
            # Get Axis direction (range -1.0 - 1.0)
            axisV = constants.get_axis_vector(self.orientation[-1])
            jntAxisDir = jntAxis * api.MVector(axisV[0], axisV[1], axisV[2])
            prevJntAxisDir = prevJntAxis * api.MVector(axisV[0], axisV[1], axisV[2])
            # Are axes looking up (is it positive)?
            jntUp = constants.is_positive(jntAxisDir)
            prevJntUp = constants.is_positive(prevJntAxisDir)
            if not jntUp == prevJntUp:
                if jntUp and (jntUp - prevJntUp) > .5:
                    self.fix_rotation(jnt, joints[i - 1], joints[i + 1])
                if prevJntUp and (prevJntUp - jntUp) > .5:
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
        if pm.listRelatives(next_jnt, c=1):
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
        return jnts

    def get_joints_grp(self, grp_name, parent=None):
        if pm.ls(grp_name):
            return pm.ls(grp_name)[0]
        grp = pm.group(em=1, n=grp_name)
        if parent is not None:
            pm.parent(grp, parent)
        return grp

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
            jntName = str(guide).replace("_guide", "_primary_jnt")
            jntPos = pm.xform(guide, q=1, ws=1, rp=1)
            jnt = pm.joint(n=jntName, p=jntPos, roo=self.orientation)
            jntList.append(jnt)
        return jntList

    def orient_joint(self, joint, aim_obj, up_obj=None):
        if up_obj is None:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="vector")
        else:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="object", wuo=up_obj)
        pm.delete(aimConst)
        pm.makeIdentity(joint, apply=True)

    def orient_base_joint(self, joint):
        if self.orientToWorld:
            self.orient_joint(joint, self.primaryJoints[1])
        else:
            self.orient_joint(joint, self.primaryJoints[1], self.primaryJoints[2])

    def orient_mid_joints(self, joint, i):
        # Center Chains align to World Up
        if self.orientToWorld:
            self.orient_joint(joint, self.primaryJoints[i + 1])
        else:
            self.orient_joint(joint, self.primaryJoints[i + 1], self.primaryJoints[i - 1])
        pm.parent(joint, self.primaryJoints[i - 1])

    def orient_tip_joint(self, joint, i):
        # Orient tip to World or local
        if self.orientTip:
            pm.parent(joint, self.primaryJoints[i - 1])
            for v in constants.AXES:
                pm.setAttr("{}.jointOrient{}".format(joint, v), 0)
        else:
            for v in constants.AXES:
                pm.setAttr("{}.jointOrient{}".format(joint, v), 0)
            pm.parent(joint, self.primaryJoints[i - 1])

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
                self.orient_base_joint(jnt)
            # Set orientation for the Tip Joint
            elif i == len(joints) - 1:
                self.orient_tip_joint(jnt, i)
            # Set orientation for all joints in between
            else:
                self.orient_mid_joints(jnt, i)
        pm.parent(joints[0], self.primaryJointsGrp)
        self.check_rotation(joints)





