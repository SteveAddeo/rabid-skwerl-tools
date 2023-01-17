import pymel.core as pm

from core import utils
from rigs import ik


class Build(object):
    def __init__(self, driver_obj):
        self.driverObj = driver_obj
        self.followJointGrp = utils.make_group(f"{self.driverObj.name}_flw_jnt_grp", parent=utils.make_group(
            "flw_jnt_grp", parent=utils.make_group("jnt_grp")))
        self.followHndlGrp = utils.make_group(f"{self.driverObj.name}_hndl_grp", parent=utils.make_group(
            "hndl_grp", parent=utils.make_group("utils_grp")))
        pm.xform(self.followJointGrp, t=pm.xform(self.driverObj.driverJoints[0], q=1, ws=1, rp=1))
        pm.xform(self.followHndlGrp, t=pm.xform(self.driverObj.driverJoints[0], q=1, ws=1, rp=1))
        self.followJoints = self.make_follow_jnts()

    def make_follow_jnts(self):
        """
        Make the joints of your follow rig
        :return: list: follow joints
        """
        jnts = [self.driverObj.driverJoints[0], self.driverObj.driverJoints[-1]]
        flwJnts = utils.duplicate_chain(jnts, "flw", self.followJointGrp)
        pm.parent(flwJnts[-1], w=1)
        flwJnts[0].overrideColor.set(10)
        flwJnts[1].overrideColor.set(10)
        # Orient base joint
        aim = pm.aimConstraint(flwJnts[-1], flwJnts[0], aim=self.driverObj.aimVector,
                               u=self.driverObj.upVector, wut="object", wuo=self.driverObj.upLoc)
        pm.delete(aim)
        pm.makeIdentity(flwJnts[0], a=1)
        # Parent and orient tip joint
        pm.parent(flwJnts[-1], flwJnts[0])
        utils.reset_transforms(flwJnts[-1], t=False)
        # Create IK setup
        hndl = ik.make_handle(flwJnts[0], flwJnts[-1], f"{self.driverObj.name}_flw_hndl", "singleChain")[0]
        pm.parent(hndl, self.followHndlGrp)
        pm.pointConstraint(self.driverObj.driverJoints[-1], hndl)
        pm.parent(self.driverObj.upLoc, flwJnts[0])
        return flwJnts
