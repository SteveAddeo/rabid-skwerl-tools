import pymel.core as pm

from core import constants
from core import utils


SOLVERS = {"rotatePlane": "ikRPsolver",
           "singleChain": "ikSCsolver",
           "spline": "ikSplineSolver",
           "spring": "ikSpringSolver"}


def make_handle(start, end, name=None, solver="rotatePlane", spline_crv=None):
    if name is None:
        name = start.name().replace("_jnt", "_hndl")
    solver = SOLVERS[solver]
    if solver == "ikSplineSolver":
        if spline_crv is not None:
            hndl = pm.ikHandle(n=name, sj=start, ee=end, sol=solver, c=spline_crv, ccv=0, pcv=0)
        else:
            pm.warning(f"{name} needs a spline curve to build a spline IK setup")
            return None
    else:
        hndl = pm.ikHandle(n=name, sj=start, ee=end, sol=solver)
    for a in constants.AXES:
        eval(f"hndl[0].poleVector{a}.set(0)")
    return hndl


class Build:
    def __init__(self, driver_obj, jnts, handle_name=None, ctls_obj=None, spline=False):
        self.driver = driver_obj
        self.joints = jnts
        self.handleName = self.get_name(handle_name)
        self.ctlsObj = ctls_obj
        self.spline = spline
        self.utilGrp = utils.make_group("util_grp")
        self.mainHandlesGrp = utils.make_group("hndl_grp", parent=self.utilGrp)
        self.handlesGrp = utils.make_group(f"{self.driver.name}_hndl_grp", parent=self.mainHandlesGrp)
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
        return self.joints[0].name().replace("_jnt", "_IK_hndl")

    def get_pole_vectors(self):
        return "poleVectors"

    def make_ik_system(self):
        if len(self.joints) == 2:
            hndlList = [pm.ikHandle(n=self.handleName, sj=self.joints[0], ee=self.joints[-1])[0]]
            if self.ctlsObj is None:
                for axis in constants.AXES:
                    pm.setAttr(f"{hndlList[0]}.poleVector{axis}", 0)
        elif len(self.joints) == 3 and not self.spline:
            pass
        elif len(self.joints) == 4 and not self.spline:
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
        offsetAmnt = self.driver.guidesObj.scale * .05
        pm.setAttr("{}.translateX".format(dup), offsetAmnt)
        return dup