import pymel.core as pm
from core import constants
import primary


def duplicate_chain(jnt_chain, chain_type, dup_parent):
    dupJnts = []
    for jnt in jnt_chain:
        parent = primary.get_parent_and_children(jnt)[0]
        children = primary.get_parent_and_children(jnt)[1]
        # Unparent the joint and any children it may have
        if parent is not None:
            pm.parent(jnt, w=1)
        if children is not None:
            pm.parent(children, w=1)
        # Duplicate joint
        dupName = str(jnt).replace(primary.get_type_from_joint(jnt), chain_type)
        dup = pm.duplicate(jnt, n=dupName)[0]
        # Set duplicate joint's radius based on chain type
        if chain_type == "FK":
            dupRad = pm.getAttr("{}.radius".format(jnt)) * .65
        elif chain_type == "IK":
            dupRad = pm.getAttr("{}.radius".format(jnt)) * 1.6
        else:
            dupRad = pm.getAttr("{}.radius".format(jnt))
        pm.setAttr("{}.radius".format(dup), dupRad)
        if parent is not None:
            pm.parent(jnt, parent)
        if children is not None:
            pm.parent(children, jnt)
        if dupJnts:
            pm.parent(dup, dupJnts[-1])
        else:
            pm.parent(dup, dup_parent)
        dupJnts.append(dup)
    return dupJnts


class BlendColors(object):
    def __init__(self, name=None, drivers=None, driven=None, const_type="parent"):
        self.name = name
        self.drivers = drivers
        self.driven = driven
        self.constType = const_type
        if self.drivers is None or self.driven is None:
            self.get_driver_driven()
        if self.name is None:
            self.name = primary.get_name_from_joint(self.driven)
        self.blendColors = self.get_blend_colors()

    def check_connections(self, bc_nodes):
        for node in bc_nodes:
            if str(node).split("_")[-2] == "pos":
                attr = "translate"
            elif str(node).split("_")[-2] == "rot":
                attr = "rotate"
            else:
                attr = "scale"
            print(node, attr)
            print(self.drivers[0], type(self.drivers[0]))
            if not pm.isConnected("{}.{}".format(self.drivers[0], attr), "{}.color1".format(node)):
                print("{}.{} not connected".format(str(self.drivers[0]), attr))
                pm.connectAttr("{}.{}".format(self.drivers[0], attr), "{}.color1".format(node))
            if len(self.drivers) > 1:
                if not pm.isConnected("{}.{}".format(self.drivers[1], attr), "{}.color2".format(node)):
                    pm.connectAttr("{}.{}".format(self.drivers[1], attr), "{}.color2".format(node))
            if not pm.isConnected("{}.output".format(node), "{}.{}".format(str(self.driven), attr)):
                pm.connectAttr("{}.output".format(node), "{}.{}".format(self.driven, attr))

    def get_blend_colors(self):
        bcNodeList = []
        for attr in constants.get_constrain_attrs(self.constType):
            # Create a Blend Colors node (if one doesn't already exist)
            bcName = "{}{}_bc".format(self.name, attr)
            if pm.ls(bcName):
                bcNodeList.append(pm.ls(bcName)[0])
                continue
            bcNode = pm.createNode("blendColors", n=bcName)
            # Make sure both color(transform) values are set to 0
            pm.setAttr("{}.color1".format(bcName), 0, 0, 0)
            pm.setAttr("{}.color2".format(bcName), 0, 0, 0)
            # Add node to list of blend colors
            bcNodeList.append(bcNode)
        self.check_connections(bcNodeList)
        return bcNodeList

    def get_driver_driven(self):
        # Check to make sure at least two objects are selected
        if not len(pm.ls(sl=1)) >= 2:
            return pm.error("Please select your driver objects and a driven object")
        # Get driven object
        self.driven = [pm.ls(sl=1)[-1]]
        # Get driver objects (max 2)
        drivers = [node for node in pm.ls(sl=1) if node not in self.driven]
        if len(drivers) > 2:
            pm.warning("more than two drivers were selected; only the first two are used")
        self.drivers = drivers[0:2]


class FK(object):
    def __init__(self, prime_obj, ctls_obj, joint_chain):
        self.primeObj = prime_obj
        self.ctlsObj = ctls_obj
        self.jointChain = joint_chain


class IK(object):
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


# TODO: controls_obj should be dropped in here as well. The object-oriented nature of this will allow
#  data to be queried more easily
class Build(object):
    def __init__(self, primary_obj, start_jnt=None, chain_len=3, fk=True, ik=True, ik_spline=False):
        if not fk and not ik:
            return
        self.primeObj = primary_obj
        self.startJoint = start_jnt
        if self.startJoint is None:
            self.startJoint = self.primeObj.primaryJoints[0]
        self.chainLen = chain_len
        self.fk = fk
        self.ik = ik
        self.ikSpline = ik_spline
        self.name = self.primeObj.name
        self.primaryChain = self.get_chain_primary()
        self.fkJointsGrp = self.get_chain_grp(chain_type="FK")
        self.ikJointsGrp = self.get_chain_grp(chain_type="IK")
        self.fkChain = self.get_chain(chain_type="FK")
        self.ikChain = self.get_chain(chain_type="IK")
        self.blendColors = self.get_blend_colors()
        # TODO: setup IK system
        self.ikHandleList = None
        self.ikPoleVectorLocList = None
        self.fkPoleVectorProxyList = None

    def check_chain_type(self, chain_type="FK"):
        if not self.fk and chain_type == "FK":
            return False
        if not self.ik and chain_type == "IK":
            return False
        return True

    def get_blend_colors(self):
        if not self.fk and not self.ik:
            return None
        bcDict = {}
        for i, jnt in enumerate(self.primaryChain):
            drivers = []
            if self.fk:
                print("FK driver is {}".format(self.fkChain[i]), type(self.fkChain[i]))
                drivers.append(self.fkChain[i])
            if self.ik:
                print("IK driver is {}".format(self.ikChain[i]), type(self.ikChain[i]))
                drivers.append(self.ikChain[i])
            fkik = BlendColors(drivers=drivers, driven=jnt)
            print("{} built".format(fkik))
            bcDict[str(jnt)] = fkik.blendColors
        return bcDict

    def get_chain(self, chain_type="FK"):
        if not self.check_chain_type(chain_type):
            return None
        # Set chain's naming convention
        name = "{}_{}_jnt".format(self.name, chain_type)
        if not pm.ls(name):
            return self.make_chain(chain_type)
        return primary.list_joints_in_chain(name)

    def get_chain_grp(self, chain_type="FK"):
        if not self.check_chain_type(chain_type):
            return None
        grpName = "{}_{}_jnts_grp".format(self.name, chain_type)
        if pm.ls(grpName):
            return pm.ls(grpName)[0]
        grp = pm.group(em=1, n=grpName)
        parent = self.primeObj.subJointsGrp
        pm.parent(grp, parent)
        return grp

    def get_chain_primary(self):
        jntIndex = self.primeObj.primaryJoints.index(self.startJoint)
        chainEnd = jntIndex + self.chainLen
        return self.primeObj.primaryJoints[jntIndex:chainEnd]

    def get_joint_primary(self):
        if "{}_primary_jnts_grp".format(self.name) not in pm.ls():
            return pm.error("{} primary joint chain does not exist".format(self.name))
        return pm.listRelatives("{}_prime_jnts_grp".format(self.name), c=1)[0]

    def make_chain(self, chain_type="FK"):
        if not self.check_chain_type(chain_type):
            return None
        if chain_type == "FK":
            parent = self.fkJointsGrp
        else:
            parent = self.ikJointsGrp
        newChain = duplicate_chain(self.primaryChain, chain_type, parent)
        return newChain




