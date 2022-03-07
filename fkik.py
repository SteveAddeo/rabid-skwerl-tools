import pymel.core as pm


class BlendColors(object):
    def __init__(self, drivers=None, driven=None):
        self.drivers = drivers
        self.driven = driven
        if self.drivers is None or self.driven is None:
            self.get_driver_driven()
        self.name = self.get_name()
        self.bcList = []

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

    def get_name(self):
        name = str(self.driven)
        if "_jnt" in name:
            name = name.replace("_jnt", "")
        if "_primary" in name:
            name = name.replace("_primary", "")
        return name

    def make_blend_colors(self, attrs):
        bcNodeList = []
        for attr in attrs:
            # Create a Blend Colors node (if one doesn't already exist)
            bcName = "{}{}_bc".format(self.name, attr)
            bcNode = pm.createNode("blendColors", n=bcName)
            # Make sure both color values are set to
            pm.setAttr("{}.color1".format(bcName), 0, 0, 0)
            pm.setAttr("{}.color2".format(bcName), 0, 0, 0)
            # Add node to list of blend colors
            bcNodeList.append(bcNode)
        self.bcList = bcNodeList
        return bcNodeList

    def make_connections(self, bcnodes):
        for node in bcnodes:
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

    def make_constraint(self, const):
        if const == "parent":
            attrList = ["_pos", "_rot"]
        elif const == "point":
            attrList = ["_pos"]
        elif const == "orient":
            attrList = ["_rot"]
        elif const == "scale":
            attrList = ["_scl"]
        else:
            attrList = ["_pos", "_rot", "_scl"]
        bcNodes = self.make_blend_colors(attrList)
        self.make_connections(bcNodes)
        return bcNodes


def make_chain(orig_chain, chain_type="FK"):
    if "primary" in str(orig_chain):
        name = str(orig_chain).replace("primary", chain_type)
    elif "_jnt" in str(orig_chain):
        name = str(orig_chain).replace("jnt", "{}_jnt".format(chain_type))
    else:
        name = "{}_{}_jnt".format(str(orig_chain), chain_type)
    newChain = pm.duplicate(orig_chain, n=name)
    jnts = pm.listRelatives(newChain, ad=1)
    jnts.append(newChain[0])
    for jnt in jnts:
        if "primary" in str(jnt):
            newName = str(jnt).replace("primary", chain_type)
            pm.rename(jnt, newName)
        if "_{}_".format(chain_type) not in str(jnt):
            newName = "{}_{}".format(str(jnt), chain_type)
            pm.rename(jnt, newName)
    return jnts


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
        fkikDict[driver] = jntsDict
    return fkikDict

