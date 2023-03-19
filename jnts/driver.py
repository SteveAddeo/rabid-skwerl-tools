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
        """
        Builds the driver skeleton that will be the primary driver of the entire rig
        :param guides_obj: obj: The locator guides that set the world space position of te driver joints
        :param spline: bool: if the skeleton will be driven by an IK spline
        :param orientation: str: The aim, up, tertiary axis order of the chain used to set rotation order
        :param orient_tip: bool: whether or not to orient the tip joint along the same axis as its parent
        :param orient_base_to_world: bool: whether or not the base joint up will point to world up
        :param orient_chain_to_world: bool: whether or not to orient a chain to the world
        :param make_twist: bool: weather or not to add a twist joint at the base of the chain
        :param make_follow: weather or not to create a set of follow joints
        """
        self.guides = guides_obj
        self.spline = spline
        self.name = self.guides.name
        self.orientation = orientation
        self.orient_tip = orient_tip
        self.orient_base = orient_base_to_world
        self.orient_to_world = orient_chain_to_world
        self.rig_grp = utils.make_group("rig_grp_DO_NOT_TOUCH")
        self.main_joints_grp = utils.make_group("jnt_grp", parent=self.rig_grp)
        self.main_utils_grp = utils.make_group("utils_grp", parent=self.rig_grp)
        self.driver_joints_grp = utils.make_group(f"{self.name}_drv_jnt_grp",
                                                  parent=utils.make_group("drv_jnt_grp", parent=self.main_joints_grp))
        self.aim_vector = constants.get_axis_vector(self.orientation[0].capitalize(), invert=self.guides.mirror)
        self.up_vector = constants.get_axis_vector(self.orientation[1].capitalize())
        self.tertiary_vector = constants.get_axis_vector(self.orientation[2].capitalize(), invert=self.guides.mirror)
        self.driver_joints = self.make_driver_chain()
        self.long_axis = self.get_long_axis()
        self.check_rotation()
        self.up_loc = self.make_up_loc()
        self.crv_name = f"{utils.get_info_from_joint(self.driver_joints[0], name=True)}_crv"
        self.crv = utils.make_curve_from_chain(self.driver_joints[0], name=self.crv_name, bind=self.driver_joints)
        self.crv_info = pm.PyNode(f"{self.crv.name()}_info")
        if make_twist:
            self.twist_obj = twist.Build(self.driver_joints[0])
        if make_follow:
            self.followObj = follow.Build(self.driver_joints, self.aim_vector, self.up_vector, self.up_loc)
        pm.select(cl=1)

    def check_rotation(self):
        """
        Checks the rotation of joints along the chain to see if they align with the overall chain.
        """
        for i, jnt in enumerate(self.driver_joints[1:-1], 1):
            prev_jnt = self.driver_joints[i - 1]
            # Get the World Space Matrix of the joints
            jnt_ws = pm.xform(jnt, q=1, m=1, ws=1)
            prevJntWS = pm.xform(prev_jnt, q=1, m=1, ws=1)
            # Get Axis Direction (matrix)
            mtx_range = constants.get_axis_matrix_range(self.orientation[-1])
            jnt_axis = om.MVector(jnt_ws[mtx_range[0]:mtx_range[1]])
            prev_jnt_axis = om.MVector(prevJntWS[mtx_range[0]:mtx_range[1]])
            # Determine which vector to "look" at the axis from
            if self.long_axis == "Z":
                axis_v = constants.get_axis_vector("X")
            else:
                axis_v = constants.get_axis_vector("Z")
            # Get Axis direction based on axis vector (range -1.0 - 1.0)
            jnt_axis_dir = jnt_axis * om.MVector(axis_v[0], axis_v[1], axis_v[2])
            prev_jnt_axis_dir = prev_jnt_axis * om.MVector(axis_v[0], axis_v[1], axis_v[2])
            # Are axes looking up (is it positive according to the axis vector)?
            jnt_up = constants.is_positive(jnt_axis_dir)
            prevJntUp = constants.is_positive(prev_jnt_axis_dir)
            if not jnt_up == prevJntUp:
                self.fix_rotation(jnt, self.driver_joints[i - 1], self.driver_joints[i + 1])
            self.check_mirror()
            self.check_twist()

    def check_mirror(self):
        """
        There's a weird quirk where chains in a straight line don't mirror properly; this corrects that
        """
        guide_vectors = [[round(v, 3) for v in pm.xform(guide, q=1, ws=1, rp=1)] for guide in self.guides.allGuides][:3]
        for joint in [joint for joint in self.driver_joints
                      if constants.is_straight_line(guide_vectors) and self.guides.mirror]:
            if joint != self.driver_joints[-1]:
                children = pm.listRelatives(joint, c=1)
                pm.parent(children, w=1)
                eval(f"joint.rotate{str(joint.getRotationOrder())[0]}.set(180)")
                pm.makeIdentity(joint, a=1)
                pm.parent(children, joint)
            elif self.orient_tip:
                utils.reset_transforms([joint], t=False, r=False, s=False, m=False, o=True)
            else:
                orient.tip_joint(joint, self.driver_joints[-2], to_joint=False)

    def check_rotation_order(self, node):
        """
        Checks to make sure the rotation order of a given node is the same as the class orientation and
        fixes it if not
        :param node: PyNode: the node being checked
        :return: PyNode: the same node that's fixed (if needed)
        """
        if not self.orientation == (str(node.getRotationOrder()).lower()):
            pm.xform(node, roo=self.orientation, p=1)
        return node

    def check_twist(self):
        """
        Checks the joint orientation to make sure there isn't a 180 degree offset
        """
        for joint in self.driver_joints:
            joint_orient = joint.jointOrient.get()
            if abs(round(joint_orient[constants.get_axis_index(str(joint.getRotationOrder())[0])], 3)) == 180:
                if joint != self.driver_joints[-1]:
                    joint_orient[constants.get_axis_index(str(joint.getRotationOrder())[0])] = 0
                    children = pm.listRelatives(joint, c=1)
                    pm.parent(children, w=1)
                    joint.jointOrient.set(joint_orient)
                    pm.parent(children, joint)
                elif self.orient_tip:
                    utils.reset_transforms([joint], t=False, r=False, s=False, m=False, o=True)
                else:
                    orient.tip_joint(joint, self.driver_joints[-2], to_joint=False)

    def fix_rotation(self, joint, prev_jnt, next_jnt):
        """
        Corrects rotation issues along the chain
        :param joint: PyNode: the joint being fixed
        :param prev_jnt: PyNode: the parent joint of the joint being fixed
        :param next_jnt: PyNode: the child joint of the joint being fixed
        """
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
            joint = self.driver_joints[0]
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
        """
        Build the joint chain that will act as the driver for this section of the rig
        :return: list: the joints that were created
        """
        # Double check to make sure driver chain doesn't exist
        if pm.listRelatives(self.driver_joints_grp, c=1):
            pm.delete(pm.listRelatives(self.driver_joints_grp, ad=1))
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
        orient.joints_in_chain(jntList, orient_tip=self.orient_tip, group=self.driver_joints_grp,
                               base_to_world=self.orient_base, chain_to_world=self.orient_to_world,
                               neg=self.guides.invert, mirror=self.guides.mirror)
        return jntList

    def make_up_loc(self):
        """
        Creates an up locator for this portion of the rig that will be used to constrain Twist joints and IK chains
        :return: PyNode: the up locator that was created
        """
        if pm.ls(f"{self.name}_up_loc"):
            return pm.PyNode(f"{self.name}_up_loc")
        loc = pm.spaceLocator(n=f"{self.name}_up_loc")
        pt = pm.pointConstraint(self.driver_joints[0], loc)
        ornt = pm.orientConstraint(self.driver_joints[0], loc)
        pm.delete(pt, ornt)
        pm.move(loc, [-v * (self.guides.scale * .2) for v in self.tertiary_vector], r=1, os=1)
        return loc
