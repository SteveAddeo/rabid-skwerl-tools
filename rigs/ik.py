import pymel.core as pm


class Build:
    def __init__(self, prime_obj, ctls_obj, joint_chain, spline=False):
        self.primeObj = prime_obj
        self.ctlsObj = ctls_obj
        self.jntChain = joint_chain
        self.spline = spline
        self.handles = self.get_handles()
        self.poleVectors = self.get_pole_vectors()

    def get_handles(self):
        return "handles"

    def get_pole_vectors(self):
        return "poleVectors"

    def make_ik_system(self):
        if len(self.jntChain) == 2:
            #
            pass
        elif len(self.jntChain) == 3 and not self.spline:
            pass
        elif len(self.jntChain) == 4 and not self.spline:
            pass
        else:
            pass

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