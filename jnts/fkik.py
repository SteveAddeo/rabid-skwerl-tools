import pymel.core as pm

from core import constants
from core import matrix
from core import utils
from rigs import stretch


def make_fkik_chains(jnts=None, bc=True, primary="IK"):
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


class BlendColors(object):
    def __init__(self, name=None, drivers=None, driven=None, const_type="all"):
        self.name = name
        self.drivers = drivers
        self.driven = driven
        if self.drivers is None or self.driven is None:
            self.get_driver_driven()
        if name is None:
            self.name = "_".join(self.driven.name().split("_")[:-2])
        self.constType = const_type
        self.blendColors = self.get_blend_colors()

    def check_connections(self, bc_nodes):
        for node in bc_nodes:
            if str(node).split("_")[-2] == "pos":
                attr = "translate"
            elif str(node).split("_")[-2] == "rot":
                attr = "rotate"
            else:
                attr = "scale"
            if not pm.isConnected(f"{self.drivers[0]}.{attr}", f"{node}.color1"):
                pm.connectAttr(f"{self.drivers[0]}.{attr}", f"{node}.color1")
            if not pm.isConnected(f"{node}.output", f"{self.driven.name()}.{attr}"):
                pm.connectAttr(f"{node}.output", f"{self.driven.name()}.{attr}")
            if len(self.drivers) > 1:
                if not pm.isConnected(f"{self.drivers[1]}.{attr}", f"{node}.color2"):
                    pm.connectAttr(f"{self.drivers[1]}.{attr}", f"{node}.color2")
            else:
                pm.setAttr("{}.blender".format(node), 1)

    def get_blend_colors(self):
        bcNodeList = []
        for attr in constants.get_constrain_attrs(self.constType):
            # Create a Blend Colors node (if one doesn't already exist)
            bcName = f"{self.name}_{attr}_bc"
            if pm.ls(bcName):
                bcNodeList.append(pm.PyNode(bcName))
                continue
            bcNode = pm.createNode("blendColors", n=bcName)
            # Make sure both color(transform) values are set to 0
            bcNode.color1.set(0, 0, 0)
            bcNode.color2.set(0, 0, 0)
            # Add node to list of blend colors
            bcNodeList.append(bcNode)
        self.check_connections(bcNodeList)
        return bcNodeList

    def get_driver_driven(self):
        # Check to make sure at least two objects are selected
        if not len(pm.ls(sl=1)) >= 2:
            return pm.error("Please select your driver objects and a driven object")
        # Get driven object
        self.driven = pm.ls(sl=1)[-1]
        # Get driver objects (max 2)
        drivers = [node for node in pm.ls(sl=1) if node not in self.driven]
        if len(drivers) > 2:
            pm.warning("more than two drivers were selected; only the first two are used")
        self.drivers = drivers[0:2]


# TODO: controls_obj should be dropped in here as well. The object-oriented nature of this will allow
#  data to be queried more easily
class Build(object):
    def __init__(self, driver_obj=None, fk=True, ik=True, bc=True, primary="IK"):
        self.driver = driver_obj
        if self.driver is not None:
            self.name = self.driver.name
            self.driverJoints = self.driver.driverJoints
        else:
            self.name = utils.get_info_from_joint(pm.ls(sl=1)[0], name=1)
            self.driverJoints = utils.get_joints_in_chain(pm.ls(sl=1)[0])
        self.fk = fk
        self.ik = ik
        self.fkJointsGrp = utils.make_group(f"{self.name}_FK_jnt_grp", parent=utils.make_group("FK_jnt_grp"))
        self.ikJointsGrp = utils.make_group(f"{self.name}_IK_jnt_grp", parent=utils.make_group("IK_jnt_grp"))
        if self.driver is not None:
            if not pm.listRelatives("FK_jnt_grp", p=1):
                pm.parent("FK_jnt_grp", self.driver.mainJointsGrp)
            if not pm.listRelatives("IK_jnt_grp", p=1):
                pm.parent("IK_jnt_grp", self.driver.mainJointsGrp)
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
            for i, jnt in enumerate(srcJnts):
                # TODO: this constraint still doesn't successfully reset joints
                matrix.matrix_constraint(jnt, tgtJnts[i])
                matrix.matrix_constraint(tgtJnts[i], self.driverJoints[i])
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
        newChain = utils.duplicate_chain(utils.get_joints_in_chain(self.driverJoints[0]), chain_type, parent)
        for jnt in newChain:
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(color)
        return newChain




