import pymel.core as pm
import maya.api.OpenMaya as om

from core import constants
from core import utils
from jnts import follow
from jnts import orient
from jnts import twist


class Build(object):
    # TODO: Orient base to world needs more testing
    def __init__(self, guides_obj, spline=False, orientation="xyz", orient_tip=True,
                 orient_base_to_world=True, orient_chain_to_world=False, make_twist=False, make_follow=False):
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
        self.driverJointsGrp = utils.make_group(f"{self.name}_drv_jnt_grp",
                                                parent=utils.make_group("drv_jnt_grp", parent=self.mainJointsGrp))
        self.aimVector = constants.get_axis_vector(self.orientation[0].capitalize(), invert=self.guides.mirror)
        self.upVector = constants.get_axis_vector(self.orientation[1].capitalize())
        self.tertiaryVector = constants.get_axis_vector(self.orientation[2].capitalize(), invert=self.guides.mirror)
        self.driverJoints = self.make_driver_chain()
        self.longAxis = self.get_long_axis()
        self.check_rotation()
        self.upLoc = self.make_up_loc()
        self.crvName = f"{utils.get_info_from_joint(self.driverJoints[0], name=True)}_crv"
        self.crv = utils.make_curve_from_chain(self.driverJoints[0], name=self.crvName, bind=self.driverJoints)
        self.crvInfo = pm.PyNode(f"{self.crv.name()}_info")
        if make_twist:
            self.twistObj = twist.Build(self.driverJoints[0])
        if make_follow:
            self.followObj = follow.Build(self.driverJoints, self.aimVector, self.upVector, self.upLoc)
        pm.select(cl=1)

    def check_rotation(self):
        for i, jnt in enumerate(self.driverJoints[1:-1], 1):
            prevJnt = self.driverJoints[i - 1]
            # Get the World Space Matrix of the joints
            jntWS = pm.xform(jnt, q=1, m=1, ws=1)
            prevJntWS = pm.xform(prevJnt, q=1, m=1, ws=1)
            # Get Axis Direction (matrix)
            mtxRange = constants.get_axis_matrix_range(self.orientation[-1])
            jntAxis = om.MVector(jntWS[mtxRange[0]:mtxRange[1]])
            prevJntAxis = om.MVector(prevJntWS[mtxRange[0]:mtxRange[1]])
            # Determine which vector to "look" at the axis from
            if self.longAxis == "Z":
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
                self.fix_rotation(jnt, self.driverJoints[i - 1], self.driverJoints[i + 1])
            self.check_mirror()
            self.check_twist()

    def check_mirror(self):
        # There's a weird quirk where chains in a straight line don't mirror properly; this corrects that
        guide_vectors = [[round(v, 3) for v in pm.xform(guide, q=1, ws=1, rp=1)] for guide in self.guides.allGuides][:3]
        for joint in [joint for joint in self.driverJoints
                      if constants.is_straight_line(guide_vectors) and self.guides.mirror]:
            if joint != self.driverJoints[-1]:
                children = pm.listRelatives(joint, c=1)
                pm.parent(children, w=1)
                eval(f"joint.rotate{str(joint.getRotationOrder())[0]}.set(180)")
                pm.makeIdentity(joint, a=1)
                pm.parent(children, joint)
            elif self.orientTip:
                utils.reset_transforms([joint], t=False, r=False, s=False, m=False, o=True)
            else:
                orient.tip_joint(joint, self.driverJoints[-2], to_joint=False)

    def check_rotation_order(self, node):
        if not self.orientation == (str(node.getRotationOrder()).lower()):
            pm.xform(node, roo=self.orientation, p=1)
        return node

    def check_twist(self):
        for joint in self.driverJoints:
            joint_orient = joint.jointOrient.get()
            if abs(round(joint_orient[constants.get_axis_index(str(joint.getRotationOrder())[0])], 3)) == 180:
                if joint != self.driverJoints[-1]:
                    joint_orient[constants.get_axis_index(str(joint.getRotationOrder())[0])] = 0
                    children = pm.listRelatives(joint, c=1)
                    pm.parent(children, w=1)
                    joint.jointOrient.set(joint_orient)
                    pm.parent(children, joint)
                elif self.orientTip:
                    utils.reset_transforms([joint], t=False, r=False, s=False, m=False, o=True)
                else:
                    orient.tip_joint(joint, self.driverJoints[-2], to_joint=False)

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
            jnt = pm.joint(n=jntName, p=jntPos, roo=self.orientation, rad=jntRad)
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(1)
            jntList.append(jnt)
        # Set proper rotation and orientation for the guides
        orient.joints_in_chain(jntList, orient_tip=self.orientTip, group=self.driverJointsGrp,
                               base_to_world=self.orientBase, chain_to_world=self.orientToWorld,
                               neg=self.guides.invert, mirror=self.guides.mirror)
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
