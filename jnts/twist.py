import pymel.core as pm

from core import constants
from core import utils
from rigs import ik


class Build(object):
    def __init__(self, base_jnt):
        self.name = utils.get_info_from_joint(base_jnt, name=True)
        self.base = base_jnt
        self.child = pm.listRelatives(self.base, c=1)[0]
        self.twistJointGrp = utils.make_group(f"{self.name}_twst_jnt_grp", parent=utils.make_group(
            "twst_jnt_grp", parent=utils.make_group("jnt_grp")))
        self.twistHandleGrp = utils.make_group(f"{utils.get_info_from_joint(base_jnt, name=True)}_hndl_grp",
                                               parent=utils.make_group("utils_grp"))
        pm.xform(self.twistJointGrp, t=pm.xform(self.base, q=1, ws=1, rp=1))
        pm.xform(self.twistHandleGrp, t=pm.xform(self.base, q=1, ws=1, rp=1))
        self.twistJoint = utils.duplicate_chain([base_jnt], "twst", self.twistJointGrp)[0]
        self.upLoc = pm.PyNode(f"{utils.get_info_from_joint(self.base, name=True)}_up_loc")
        self.make_twist()

    def make_twist(self):
        aimV = constants.get_axis_vector(str(self.base.getRotationOrder())[0])
        upV = constants.get_axis_vector(str(self.base.getRotationOrder())[-1])
        aim = pm.aimConstraint(self.child, self.twistJoint, aim=aimV, u=upV, wut="object", wuo=self.upLoc)
        self.make_twist_follow()
        # Check to make sure twist joint has the same orientation of the base joint
        if round(abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180 and round(
                abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twistJoint, aim=[-v for v in aimV],
                             u=[-v for v in upV], wut="object", wuo=self.upLoc)
        if round(abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180 and not round(
                abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twistJoint, aim=aimV,
                             u=[-v for v in upV], wut="object", wuo=self.upLoc)
        if round(abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[-1]}.get()"))) == 180 and not \
                round(abs(eval(f"self.twistJoint.rotate{str(self.base.getRotationOrder())[0]}.get()"))) == 180:
            pm.delete(aim)
            pm.aimConstraint(self.child, self.twistJoint, aim=[-v for v in aimV],
                             u=upV, wut="object", wuo=self.upLoc)

    def make_twist_follow(self):
        flwJnts = utils.duplicate_chain([self.base, self.child], "twst_flw", self.twistJointGrp)
        hndl = ik.make_handle(flwJnts[0], flwJnts[1],
                              name=f"{utils.get_info_from_joint(self.base, name=True)}_twst_hndl",
                              solver="singleChain")
        flwJnts[0].overrideColor.set(10)
        flwJnts[1].overrideColor.set(10)
        pm.pointConstraint(self.child, hndl[0])
        pm.parent(hndl[0], self.twistHandleGrp)
        pm.parent(self.upLoc, flwJnts[0])
