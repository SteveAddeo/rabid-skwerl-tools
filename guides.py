import pymel.core as pm
import constants


def get_guides_from_group(group):
    guides = [node for node in reversed(pm.listRelatives(group, ad=1)) if str(node).split("_")[-1] == "guide"]
    if not guides:
        return None
    return guides


def make_object_from_group(group):
    name = str(group).replace("_guides_grp", "")
    chainLength = len(get_guides_from_group(group))
    obj = Build(name, chain_len=chainLength)
    return obj


class Build(object):
    def __init__(self, name, chain_len=3, axis="X", scale=10):
        self.name = name
        self.chainLength = chain_len
        self.axis = axis
        self.scale = self.get_scale(scale)
        self.grp = self.get_guides_grp()
        self.subGrp = self.get_guides_grp(sub_grp=1)
        self.allGuides = self.get_guides()
        self.curve = self.get_guides_curve()

    def get_guides(self):
        if pm.listRelatives(self.subGrp, c=1):
            guides = get_guides_from_group(self.subGrp)
            if len(guides) != self.chainLength:
                pm.delete(pm.listRelatives(self.subGrp, c=1))
                guides = self.make_guides()
        else:
            guides = self.make_guides()
        return guides

    def get_guides_curve(self):
        curve = pm.ls("{}_guides_crv".format(self.name))
        if not curve:
            self.make_guide_curves()
        return curve

    def get_guides_grp(self, sub_grp=0):
        if sub_grp:
            grpName = "{}_guides_grp".format(self.name)
        else:
            grpName = "guides_grp"
        guidesGrp = pm.ls(grpName)
        if not guidesGrp:
            guidesGrp = pm.createNode("transform", n=grpName)
        if sub_grp and not str(pm.listRelatives(guidesGrp, p=1)) == ["guides_grp"]:
            pm.parent(guidesGrp, "guides_grp")
        return guidesGrp

    def get_guide_name(self, i):
        if i == 0:
            guideName = "{}_base_guide".format(self.name)
        elif i == self.chainLength - 1:
            guideName = "{}_tip_guide".format(self.name)
        elif i >= 1 and self.chainLength >= 4:
            guideName = "{}_mid{}_guide".format(self.name, str(i).zfill(2))
        else:
            guideName = "{}_mid_guide".format(self.name)
        return guideName

    def get_scale(self, scale):
        if not self.axis == "X":
            scale = -scale
        return scale

    def make_guides(self):
        guidesList = []
        prevGuide = None
        for i in range(self.chainLength):
            guideName = self.get_guide_name(i)
            # Create and position the locator
            guide = pm.spaceLocator(n=guideName)
            guidesList.append(guide)
            pm.setAttr("{}.translate{}".format(guide, self.axis), i * self.scale)
            # Lock attributes you don't want to be changed so the rig is built properly
            for v in constants.AXES:
                pm.setAttr("{}.rotate{}".format(guide, v), lock=True, keyable=False, channelBox=False)
                if i == 0:
                    pm.setAttr("{}.scale{}".format(guide, v), self.scale / 5)
                pm.setAttr("{}.scale{}".format(guide, v), lock=True, keyable=False, channelBox=False)
            # Parent to the appropriate node
            if i == 0:
                pm.parent(guide, self.subGrp)
            else:
                pm.parent(guide, prevGuide)
            prevGuide = guide
        return guidesList

    def make_guide_curves(self):
        # Get the coordinates for each point of the curve
        ptsPos = [pm.xform(guide, q=1, ws=1, rp=1) for guide in self.allGuides]
        curve = pm.curve(d=1, p=ptsPos, n="{}_guides_crv".format(self.name))
        pm.parent(curve, self.subGrp)
        pm.setAttr("{}.inheritsTransform".format(curve), 0)
        pm.setAttr("{}.template".format(curve), 1)
        # Apply custer handles so the guides can move the curve
        for i, guide in enumerate(self.allGuides):
            cluster = pm.cluster("{}.cv[{}]".format(curve, i), n=guide.replace("_guide", "_clstr"))[1]
            pm.setAttr("{}.visibility".format(cluster), 0)
            pm.parent(cluster, guide)


def get_guide_name(chain_len, i, name):
    if i == 0:
        guideName = "{}_base_guide".format(name)
    elif i == chain_len - 1:
        guideName = "{}_tip_guide".format(name)
    elif i >= 1 and chain_len >= 4:
        guideName = "{}_mid{}_guide".format(name, str(i).zfill(2))
    else:
        guideName = "{}_mid_guide".format(name)
    return guideName


def make_guide_curves(name, group, guides):
    # Get the coordinates for each point of the curve
    ptsPos = [pm.xform(guide, q=1, ws=1, rp=1) for guide in guides]
    crv = pm.curve(d=1, p=ptsPos, n="{}_guides_crv".format(name))
    pm.parent(crv, group)
    pm.setAttr("{}.inheritsTransform".format(crv), 0)
    pm.setAttr("{}.template".format(crv), 1)
    for i, guide in enumerate(guides):
        clstr = pm.cluster("{}.cv[{}]".format(crv, i), n=guide.replace("_guide", "_clstr"))[1]
        pm.setAttr("{}.visibility".format(clstr), 0)
        pm.parent(clstr, guide)


def make_guides(name, chain_len=3, axis="X", scale=10):
    # Check for and create a group to store the guides and a sub group for this chain
    if not pm.ls("guides_grp"):
        pm.createNode("transform", n="guides_grp")
    grp = pm.ls("guides_grp")[0]
    if not pm.ls("{}_guides_grp".format(name)):
        guidesGrp = pm.createNode("transform", n="{}_guides_grp".format(name))
    else:
        guidesGrp = pm.ls("{}_guides_grp".format(name))
    if not pm.listRelatives(guidesGrp) == grp:
        pm.parent(guidesGrp, grp)
    # Create a set of locators that will be used as placeholders for the joints
    guidesList = []
    prevGuide = None
    for i in range(chain_len):
        # Create the proxy name
        guideName = get_guide_name(chain_len, i, name)
        # Create and position the locator
        guide = pm.spaceLocator(n=guideName)
        guidesList.append(guide)
        pm.setAttr("{}.translate{}".format(guide, axis), i * scale)
        # Lock attributes you don't want to be changed so the rig is built properly
        for v in VECTORS:
            pm.setAttr("{}.rotate{}".format(guide, v), lock=True, keyable=False, channelBox=False)
            if i == 0:
                pm.setAttr("{}.scale{}".format(guide, v), scale/5)
            pm.setAttr("{}.scale{}".format(guide, v), lock=True, keyable=False, channelBox=False)
        # Parent to the appropriate node
        if i == 0:
            pm.parent(guide, guidesGrp)
        else:
            pm.parent(guide, prevGuide)
        prevGuide = guide
    make_guide_curves(name, guidesGrp, guidesList)


