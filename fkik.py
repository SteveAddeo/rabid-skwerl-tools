import pymel.core as pm
import primary


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

    def get_blend_colors(self):
        bcNodeList = []
        for attr in self.get_constrain_attrs():
            # Create a Blend Colors node (if one doesn't already exist)
            bcName = "{}{}_bc".format(self.name, attr)
            if bcName in pm.ls():
                bcNodeList.append(pm.ls(bcName)[0])
                continue
            bcNode = pm.createNode("blendColors", n=bcName)
            # Make sure both color(transform) values are set to 0
            pm.setAttr("{}.color1".format(bcName), 0, 0, 0)
            pm.setAttr("{}.color2".format(bcName), 0, 0, 0)
            # Add node to list of blend colors
            bcNodeList.append(bcNode)
        return bcNodeList

    def get_constrain_attrs(self):
        if self.constType == "parent":
            attrs = ["_pos", "_rot"]
        elif self.constType == "point":
            attrs = ["_pos"]
        elif self.constType == "orient":
            attrs = ["_rot"]
        elif self.constType == "scale":
            attrs = ["_scl"]
        else:
            attrs = ["_pos", "_rot", "_scl"]
        return attrs

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

    def make_connections(self, bc_nodes):
        for node in bc_nodes:
            if str(node).split("_")[-2] == "pos":
                attr = "translate"
            elif str(node).split("_")[-2] == "rot":
                attr = "rotate"
            else:
                attr = "scale"
            pm.connectAttr("{}.{}".format(self.drivers[0], attr), "{}.color1".format(node))
            if len(self.drivers) > 1:
                pm.connectAttr("{}.{}".format(self.drivers[1], attr), "{}.color2".format(node))
            pm.connectAttr("{}.output".format(node), "{}.{}".format(self.driven, attr))


class Build(object):
    def __init__(self, name=None, primary_joint=None):
        if primary_joint is None:
            primary_joint = self.get_joint_primary()
        if name is None:
            name = primary.get_name_from_joint(primary_joint)
        self.name = name
        self.primaryChain = primary.list_joints_in_chain(primary_joint)
        self.fkChainGrp = self.get_chain_grp(chain_type="FK")
        self.ikChainGrp = self.get_chain_grp(chain_type="IK")
        self.fkChain = self.get_chain(chain_type="FK")
        self.ikChain = self.get_chain(chain_type="IK")
        self.blendColors = self.get_blend_colors()
        # TODO: setup IK system
        self.ikHandleList = None
        self.ikPoleVectorLocList = None
        self.fkPoleVectorProxyList = None

    def get_blend_colors(self):
        bcDict = {}
        for i, jnt in enumerate(self.primaryChain):
            fkik = BlendColors(self.name, [self.fkChain[i], self.ikChain[i]], jnt)
            bcDict[str(jnt)] = fkik.blendColors
        return bcDict

    def get_chain(self, chain_type="FK"):
        # Set chain's naming convention
        if "primary" in str(self.primaryChain):
            name = str(self.primaryChain).replace("primary", chain_type)
        elif "_jnt" in str(self.primaryChain):
            name = str(self.primaryChain).replace("jnt", "{}_jnt".format(chain_type))
        else:
            name = "{}_{}_jnt".format(str(self.primaryChain), chain_type)
        if name not in pm.ls():
            return self.make_chain(name, chain_type)
        return pm.ls(name)[0]

    def get_chain_grp(self, chain_type="FK"):
        grpName = "{}_{}_jnts_grp".format(self.name, chain_type)
        if grpName in pm.ls():
            return pm.ls(grpName)[0]
        grp = pm.group(em=1, n=grpName)
        parent = pm.listRelatives("{}_primary_jnts_grp".format(self.name), p=1)[0]
        pm.parent(grp, parent)
        return grp

    def get_joint_primary(self):
        if "{}_primary_jnts_grp".format(self.name) not in pm.ls():
            return pm.error("{} primary joint chain does not exist".format(self.name))
        return pm.listRelatives("{}_primary_jnts_grp".format(self.name), c=1)[0]

    def make_chain(self, name, chain_type="FK"):
        # Duplicate primary chain to create new chain
        newChain = pm.duplicate(self.primaryChain[0], n=name)
        # Parent chain to the group
        if chain_type == "FK":
            parent = self.fkChainGrp
        else:
            parent = self.ikChainGrp
        pm.parent(newChain, parent)
        return self.rename_joints(primary.list_joints_in_chain(newChain), chain_type)

    def rename_joints(self, joints, chain_type):
        for jnt in joints:
            if "primary" in str(jnt):
                newName = str(jnt).replace("primary", chain_type)
                pm.rename(jnt, newName)
            if "_{}_".format(chain_type) not in str(jnt):
                newName = "{}_{}".format(str(jnt), chain_type)
                pm.rename(jnt, newName)
        return joints


def make_fkik(chains=None):
    fkikDict = {}
    # Get list of joint chains to create FKIK blends
    if chains is None:
        if not pm.ls(sl=1):
            return pm.error("Please select a joint chain")
        chains = pm.ls(sl=1)
    for driver in chains:
        # Make the FK and IK chains
        fkChain = make_chain(driver, "FK")
        ikChain = make_chain(driver, "IK")
        # Make a dict of joints in chain with the value being a list of the corresponding FK and IK joints
        jntsDict = {driver: {"FK": fkChain[-1], "IK": ikChain[-1]}}
        if pm.listRelatives(driver, ad=1):
            for i, child in enumerate(pm.listRelatives(driver, ad=1)):
                jntsDict[child] = {"FK": fkChain[i], "IK": ikChain[i]}
        # Create the blend shapes and connections
        for jnt in jntsDict:
            jntbc = BlendColors(drivers=[jntsDict[jnt]["FK"], jntsDict[jnt]["IK"]], driven=jnt)
            bcNodes = jntbc.make_constraint("parent")
            jntsDict[jnt]["blendColors"] = bcNodes
        # Add jntsDict to fkikDict
        fkikDict[str(driver).split("_")[0]] = jntsDict
    return fkikDict

