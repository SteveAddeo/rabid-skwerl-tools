import pymel.core as pm

from core import constants
from core import utils
from jnts import primary


def make_handle(start, end, name=None):
    if name is None:
        name = str(start).replace("_jnt", "_hndl")
    hndl = pm.ikHandle(n=name, sj=start, ee=end)
    return hndl


class Build:
    def __init__(self, prime_obj, joint_chain, handle_name=None, ctls_obj=None, spline=False):
        self.primeObj = prime_obj
        self.jntChain = joint_chain
        self.handleName = self.get_name(handle_name)
        self.ctlsObj = ctls_obj
        self.spline = spline
        self.mainRigsGrp = primary.get_grp("rigs_grp")
        self.subRigsGrp = primary.get_grp("{}_rigs_grp".format(self.primeObj.name), parent=self.mainRigsGrp)
        self.handlesGrp = primary.get_grp("{}_IK_hndls_grp".format(self.primeObj.name), parent=self.subRigsGrp)
        self.handles = self.get_handles()
        # self.poleVectors = self.get_pole_vectors()

    def get_handles(self):
        if not utils.get_parent_and_children(self.handlesGrp)[1] or [hndl for hndl in utils.get_parent_and_children(
                self.handlesGrp)[1] if str(hndl) == self.handleName]:
            hndls = self.make_ik_system()
        else:
            hndls = utils.get_parent_and_children(self.handlesGrp)[1]
        return hndls

    def get_name(self, name):
        if name is not None:
            return name
        return str(self.jntChain[0]).replace("_jnt", "_IK_hndl")

    def get_pole_vectors(self):
        return "poleVectors"

    def get_rigs_grp(self):
        if not pm.ls("rigs_grp"):
            pm.group(em=1, n="rigs_grp")
        return pm.ls("rigs_grp")[0]

    def make_ik_system(self):
        if len(self.jntChain) == 2:
            hndlList = [pm.ikHandle(n=self.handleName, sj=self.jntChain[0], ee=self.jntChain[-1])[0]]
            if self.ctlsObj is None:
                for axis in constants.AXES:
                    pm.setAttr("{}.poleVector{}".format(hndlList[0], axis), 0)
        elif len(self.jntChain) == 3 and not self.spline:
            pass
        elif len(self.jntChain) == 4 and not self.spline:
            pass
        else:
            pass
        pm.parent(hndlList, self.handlesGrp)
        return hndlList

    def make_ik_driver(self):
        pass

    def make_ik_end(self, ik_chain):
        jnt = ik_chain[-1]
        dupName = str(jnt).replace("_IK_", "_end_IK_")
        dup = pm.duplicate(jnt, n=dupName)[0]
        pm.parent(dup, jnt)
        offsetAmnt = self.primeObj.guidesObj.scale * .05
        pm.setAttr("{}.translateX".format(dup), offsetAmnt)
        return dup