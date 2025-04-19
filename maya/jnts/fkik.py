import pymel.core as pm

from core import matrix
from core import utils
from core import blend_colors
from rigs import stretch


# TODO: currently, the base joint is receiving transform values when the offset should be maintained

def make_fkik_chains(jnts=None, bc=True, primary=None):
    # get list of joints if none are provided
    if jnts is None:
        if not pm.ls(sl=1):
            return pm.error("please select base joints of chains")
        jnts = [jnt for jnt in pm.ls(sl=1) if jnt.type() == "joint"]
        if not jnts:
            return pm.error("make sure you select joints")
    fkikData = {}
    for jnt in jnts:
        pm.select(jnt, r=1)
        fkik = Build(bc=bc, primary=primary)
        fkikData[jnt.name()] = fkik
    return fkikData


# TODO: controls_obj should be dropped in here as well. The object-oriented nature of this will allow
#  data to be queried more easily
class Build(object):
    def __init__(self, driver_obj=None, fk=True, ik=True, bc=False, primary=None):
        self.driver = driver_obj
        if self.driver is not None:
            self.name = self.driver.name
            self.driverJoints = self.driver.driver_joints
        else:
            self.name = utils.get_info_from_joint(pm.ls(sl=1)[0], name=1)
            self.driverJoints = utils.get_joints_in_chain(pm.ls(sl=1)[0])
        self.fk = fk
        self.ik = ik
        self.fkJointsGrp = utils.make_group(f"{self.name}_FK_jnt_grp", parent=utils.make_group("FK_jnt_grp"))
        self.ikJointsGrp = utils.make_group(f"{self.name}_IK_jnt_grp", parent=utils.make_group("IK_jnt_grp"))
        pm.xform(self.fkJointsGrp, t=pm.xform(self.driverJoints[0], q=1, ws=1, rp=1))
        pm.xform(self.ikJointsGrp, t=pm.xform(self.driverJoints[0], q=1, ws=1, rp=1))
        if self.driver is not None:
            if not pm.listRelatives("FK_jnt_grp", p=1):
                pm.parent("FK_jnt_grp", self.driver.main_joints_grp)
            if not pm.listRelatives("IK_jnt_grp", p=1):
                pm.parent("IK_jnt_grp", self.driver.main_joints_grp)
        self.fkJoints = self.get_chain(chain_type="FK")
        self.ikJoints = self.get_chain(chain_type="IK")
        if bc:
            self.blends = self.get_blends(mtrx=False)
        else:
            if primary is None:
                self.blends = self.get_blends(mtrx=True)
            else:
                self.primary = primary
                self.make_matrix_constraints()

        # TODO: setup IK system
        # TODO: determine when to use a spline
        # TODO: setup stretch
        self.ikHandleList = None
        self.ikPoleVectorLocList = None
        self.fkPoleVectorProxyList = None

    def check_chain_type(self, chain_type="FK"):
        if not self.fk and chain_type == "FK":
            return False
        if not self.ik and chain_type == "IK":
            return False
        return True

    def get_blends(self, mtrx=True):
        if not self.fk and not self.ik:
            return None
        blends = []
        for i, jnt in enumerate(self.driverJoints):
            drivers = []
            if self.fk:
                drivers.append(self.fkJoints[i])
            if self.ik:
                drivers.append(self.ikJoints[i])
            if mtrx:
                blend = matrix.make_blend(drivers, jnt, decompose=True)
            else:
                blend = blend_colors.get_blend_colors(drivers, jnt)
            blends.extend(blend)
        return blends

    def get_chain(self, chain_type="FK"):
        if not self.check_chain_type(chain_type):
            return None
        # Set chain's naming convention
        name = f"{self.name}_base_{chain_type}_jnt"
        if not pm.ls(name):
            return self.make_chain(chain_type)
        return utils.get_joints_in_chain(pm.PyNode(name))

    def make_chain(self, chain_type="FK"):
        if chain_type == "FK":
            color = 30
            parent = self.fkJointsGrp
        else:
            color = 29
            parent = self.ikJointsGrp
        newChain = utils.duplicate_chain(utils.get_joints_in_chain(self.driverJoints[0]), chain_type, parent)
        for jnt in newChain:
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(color)
        return newChain

    def make_matrix_constraints(self):
        for grp in [self.fkJointsGrp, self.ikJointsGrp] + pm.listRelatives(self.driverJoints[0], p=1):
            child = pm.listRelatives(grp, c=1)[0]
            pm.parent(child, pm.listRelatives(grp, p=1)[0])
            pm.makeIdentity(grp, a=1)
            pm.parent(child, grp)
        srcJnts = self.ikJoints
        tgtJnts = self.fkJoints
        if not self.primary == "IK":
            srcJnts = self.fkJoints
            tgtJnts = self.ikJoints
        for i, jnt in enumerate(srcJnts):
            tgt_const = matrix.parent_constraint(jnt, tgtJnts[i])
            drive_const = matrix.parent_constraint(tgtJnts[i], self.driverJoints[i])
            tgt_const.useTranslate.set(0)
            drive_const.useTranslate.set(0)






