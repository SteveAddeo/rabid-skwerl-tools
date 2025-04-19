import pymel.core as pm

from core import constants
from core import matrix
from core import utils
from rigs import ik


class Build(object):
    def __init__(self, base_jnt):
        self.name = utils.get_info_from_joint(base_jnt, name=True)
        self.base = base_jnt
        self.child = pm.listRelatives(self.base, c=1)[0]
        self.twist_joint_grp = utils.make_group(f"{self.name}_twst_jnt_grp", parent=utils.make_group(
            "twst_jnt_grp", parent=utils.make_group("jnt_grp")))
        self.twist_handle_grp = utils.make_group(f"{utils.get_info_from_joint(base_jnt, name=True)}_hndl_grp",
                                                 parent=utils.make_group("utils_grp"))
        pm.xform(self.twist_joint_grp, t=pm.xform(self.base, q=1, ws=1, rp=1))
        pm.xform(self.twist_handle_grp, t=pm.xform(self.base, q=1, ws=1, rp=1))
        self.twist_joint = utils.duplicate_chain([base_jnt], "twst", self.twist_joint_grp)[0]
        self.up_loc = pm.PyNode(f"{utils.get_info_from_joint(self.base, name=True)}_up_loc")
        self.make_twist()

    def make_twist(self):
        aimV = constants.get_axis_vector(str(self.base.getRotationOrder())[0])
        upV = constants.get_axis_vector(str(self.base.getRotationOrder())[-1])
        aim = pm.aimConstraint(self.child, self.twist_joint, aim=aimV, u=upV, wut="object", wuo=self.up_loc)
        self.twist_joint.overrideEnabled.set(1)
        self.twist_joint.overrideColor.set(18)
        pm.pointConstraint(self.base, self.twist_joint)
        self.make_twist_follow()
        # Check to make sure twist joint has the same orientation of the base joint
        if round(abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180 and round(
                abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twist_joint, aim=[-v for v in aimV],
                             u=[-v for v in upV], wut="object", wuo=self.up_loc)
        if round(abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180 and not round(
                abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twist_joint, aim=aimV,
                             u=[-v for v in upV], wut="object", wuo=self.up_loc)
        if round(abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180 and not \
                round(abs(eval(f"self.twist_joint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twist_joint, aim=[-v for v in aimV],
                             u=upV, wut="object", wuo=self.up_loc)
        pm.scaleConstraint(pm.listRelatives(self.base, p=1)[0], self.twist_joint_grp)

    def make_twist_follow(self):
        flw_jnts = utils.duplicate_chain([self.base, self.child], "twst_flw", self.twist_joint_grp)
        hndl = ik.make_handle(flw_jnts[0], flw_jnts[1],
                              name=f"{utils.get_info_from_joint(self.base, name=True)}_twst_hndl",
                              solver="singleChain")
        flw_jnts[0].overrideColor.set(10)
        flw_jnts[1].overrideColor.set(10)
        pm.parent(hndl[0], self.twist_handle_grp)
        pm.parent(self.up_loc, flw_jnts[0])
        matrix.point_constraint(self.child, hndl[0], frozen=True)
        pm.pointConstraint(self.base, flw_jnts[0])
