import pymel.core as pm

from core import utils
from core import matrix
from rigs import ik


class Build(object):
    def __init__(self, driver_jnts, aim, up, up_loc):
        self.name = utils.get_info_from_joint(driver_jnts[0], name=True)
        self.driverJoints = driver_jnts
        self.aimVector = aim
        self.upVector = up
        self.upLoc = up_loc
        self.followJointGrp = utils.make_group(f"{self.name}_flw_jnt_grp", parent=utils.make_group(
            "flw_jnt_grp", parent=utils.make_group("jnt_grp")))
        self.followHndlGrp = utils.make_group(f"{self.name}_hndl_grp", parent=utils.make_group(
            "hndl_grp", parent=utils.make_group("utils_grp")))
        pm.xform(self.followJointGrp, t=pm.xform(self.driverJoints[0], q=1, ws=1, rp=1))
        pm.xform(self.followHndlGrp, t=pm.xform(self.driverJoints[0], q=1, ws=1, rp=1))
        self.followJoints = self.make_follow_jnts()
        pm.select(cl=1)

    def make_follow_jnts(self):
        """
        Make the joints of your follow rig
        :return: list: follow joints
        """
        jnts = [self.driverJoints[0], self.driverJoints[-1]]
        flwJnts = utils.duplicate_chain(jnts, "flw", self.followJointGrp)
        pm.parent(flwJnts[-1], w=1)
        flwJnts[0].overrideColor.set(10)
        flwJnts[1].overrideColor.set(10)
        # Orient base joint
        aim = pm.aimConstraint(flwJnts[-1], flwJnts[0], aim=self.aimVector,
                               u=self.upVector, wut="object", wuo=self.upLoc)
        pm.delete(aim)
        pm.makeIdentity(flwJnts[0], a=1)
        # Parent and orient tip joint
        pm.parent(flwJnts[-1], flwJnts[0])
        utils.reset_transforms([flwJnts[-1]], t=False)
        # Create IK setup
        hndl = ik.make_handle(flwJnts[0], flwJnts[-1], f"{self.name}_flw_hndl", "singleChain")[0]
        pm.parent(hndl, self.followHndlGrp)
        pm.pointConstraint(self.driverJoints[-1], hndl)
        pm.parent(self.upLoc, flwJnts[0])
        # Setup Constraints
        matrix.point_constraint(self.driverJoints[-1], hndl, frozen=True)
        pm.pointConstraint(self.driverJoints[0], flwJnts[0])
        pm.scaleConstraint(pm.listRelatives(self.driverJoints[0], p=1)[0], self.followJointGrp)
        return flwJnts
