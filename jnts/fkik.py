import pymel.core as pm

from core import constants
from core import matrix
from core import utils
from rigs import stretch


def duplicate_chain(jnt_chain, chain_type, dup_parent):
    dupJnts = []
    for jnt in jnt_chain:
        parent = utils.get_parent_and_children(jnt)[0]
        children = utils.get_parent_and_children(jnt)[1]
        # Unparent the joint and any children it may have
        if parent is not None:
            pm.parent(jnt, w=1)
        if children is not None:
            pm.parent(children, w=1)
        # Duplicate joint
        dupName = jnt.name().replace(utils.get_joint_type(jnt), chain_type)
        dup = pm.duplicate(jnt, n=dupName)[0]
        # Set duplicate joint's radius based on chain type
        if chain_type == "FK":
            dupRad = pm.getAttr("{}.radius".format(jnt)) * .65
        elif chain_type == "IK":
            dupRad = pm.getAttr("{}.radius".format(jnt)) * 1.6
        else:
            dupRad = pm.getAttr("{}.radius".format(jnt))
        pm.setAttr("{}.radius".format(dup), dupRad)
        # Re-parent joints
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
            self.name = utils.get_info_from_joint(self.driven, name=True)
        self.blendColors = self.get_blend_colors()

    def check_connections(self, bc_nodes):
        for node in bc_nodes:
            if str(node).split("_")[-2] == "pos":
                attr = "translate"
            elif str(node).split("_")[-2] == "rot":
                attr = "rotate"
            else:
                attr = "scale"
            if not pm.isConnected("{}.{}".format(self.drivers[0], attr), "{}.color1".format(node)):
                pm.connectAttr("{}.{}".format(self.drivers[0], attr), "{}.color1".format(node))
            if not pm.isConnected("{}.output".format(node), "{}.{}".format(str(self.driven), attr)):
                pm.connectAttr("{}.output".format(node), "{}.{}".format(self.driven, attr))
            if len(self.drivers) > 1:
                if not pm.isConnected("{}.{}".format(self.drivers[1], attr), "{}.color2".format(node)):
                    pm.connectAttr("{}.{}".format(self.drivers[1], attr), "{}.color2".format(node))
            else:
                pm.setAttr("{}.blender".format(node), 1)

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


# TODO: controls_obj should be dropped in here as well. The object-oriented nature of this will allow
#  data to be queried more easily
class Build(object):
    def __init__(self, driver_obj=None, fk=True, ik=True, bc=True, spline=True, primary="IK"):
        if self.driver is not None:
            self.driver = driver_obj
            self.name = self.driver.name
            self.driverJoints = self.driver.driverJoints
        else:
            if not pm.ls(sl=1) or pm.ls(sl=1)[0].type() != "joint":
                pm.warning(f"{pm.ls(sl=1)[0].name()} is not a joint. Please select base joint for your FKIK chain")
                return
            self.name = utils.get_info_from_joint(pm.ls(sl=1)[0], name=1)
            self.driverJoints = utils.get_joints_in_chain(pm.ls(sl=1)[0])
        self.fk = fk
        self.ik = ik
        self.fkJointsGrp = utils.make_group(f"{self.name}_FK_jnt_grp", parent=utils.make_group("FK_jnt_grp"))
        self.ikJointsGrp = utils.make_group(f"{self.name}_IK_jnt_grp", parent=utils.make_group("IK_jnt_grp"))
        self.fkJoints = self.get_chain(chain_type="FK")
        self.ikJoints = self.get_chain(chain_type="IK")
        if bc:
            self.blendColors = self.get_blend_colors()
        else:
            srcJnts = self.ikJoints
            tgtJnts = self.fkJoints
            if not primary == "IK":
                srcJnts = self.fkJoints
                tgtJnts = self.ikJoints
            for i, jnt in srcJnts:
                # TODO: this constraint still doesn't successfully reset joints
                matrix.matrix_constraint(jnt, tgtJnts[i])
                matrix.matrix_constraint(tgtJnts[i], self.driverJoints[i])
        # TODO: setup IK system
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

    def get_blend_colors(self):
        if not self.fk and not self.ik:
            return None
        bcDict = {}
        for i, jnt in enumerate(self.driverJoints):
            drivers = []
            if self.fk:
                drivers.append(self.fkJoints[i])
            if self.ik:
                drivers.append(self.ikJoints[i])
            fkik = BlendColors(drivers=drivers, driven=jnt)
            print("{} built".format(fkik))
            bcDict[jnt.name()] = fkik.blendColors
        return bcDict

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
        newChain = duplicate_chain(self.driverJoints, chain_type, parent)
        for jnt in newChain:
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(color)
        return newChain




