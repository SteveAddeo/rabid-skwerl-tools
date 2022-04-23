import pymel.core as pm


class Build:
    def __init__(self, prime_obj, ctls_obj, joint_chain):
        self.primeObj = prime_obj
        self.ctlsObj = ctls_obj
        self.jointChain = joint_chain