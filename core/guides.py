import pymel.core as pm
from core import constants
from core import utils


def get_guides_from_group(group):
    guides = [node for node in reversed(pm.listRelatives(group, ad=1)) if node.name.split("_")[-1] == "guide"]
    if not guides:
        return None
    return guides


def make_object_from_group(group):
    name = group.name.replace("_guides_grp", "")
    chainLength = len(get_guides_from_group(group))
    obj = Build(name, chain_len=chainLength)
    return obj


class Build:
    def __init__(self, name, chain_len=3, axis="X", scale=10):
        self.name = name
        self.chainLength = chain_len
        self.axis = axis
        self.scale = scale
        self.mainGuidesGrp = utils.make_group("guides_grp")
        self.guidesGrp = utils.make_group(f"{self.name}_guides_grp", parent=self.mainGuidesGrp)
        self.allGuides = self.get_guides()
        self.curve = self.make_guides_curve()

    def get_guides(self):
        if pm.listRelatives(self.guidesGrp, c=1):
            guides = get_guides_from_group(self.guidesGrp)
            if len(guides) != self.chainLength:
                pm.delete(pm.listRelatives(self.guidesGrp, c=1))
                guides = self.make_guides()
        else:
            guides = self.make_guides()
        return guides

    def get_guide_name(self, i):
        if i == 0:
            guideName = f"{self.name}_base_guide"
        elif i == self.chainLength - 1:
            guideName = f"{self.name}_tip_guide"
        else:
            guideName = f"{self.name}_mid{str(i).zfill(2)}_guide"
        return guideName

    def make_guides(self):
        guidesList = []
        prevGuide = None
        scale = self.scale
        if not self.axis == "X":
            scale = -scale
        for i in range(self.chainLength):
            guideName = self.get_guide_name(i)
            # Create and position the locator
            guide = pm.spaceLocator(n=guideName)
            guidesList.append(guide)
            pm.setAttr(f"{guide}.translate{self.axis}", i * scale)
            # Lock attributes you don't want to be changed so the rig is built properly
            for v in constants.AXES:
                pm.setAttr(f"{guide}.rotate{v}", lock=True, keyable=False, channelBox=False)
                if i == 0:
                    pm.setAttr(f"{guide}.scale{v}", scale / 5)
                pm.setAttr(f"{guide}.scale{v}", lock=True, keyable=False, channelBox=False)
            # Parent to the appropriate node
            if i == 0:
                pm.parent(guide, self.guidesGrp)
            else:
                pm.parent(guide, prevGuide)
            prevGuide = guide
        return guidesList

    def make_guides_curve(self):
        if pm.ls("{}_guides_crv".format(self.name)):
            return pm.PyNode("{}_guides_crv".format(self.name))
        # Get the coordinates for each point of the curve
        ptsPos = [pm.xform(guide, q=1, ws=1, rp=1) for guide in self.allGuides]
        curve = pm.curve(d=1, p=ptsPos, n="{}_guides_crv".format(self.name))
        pm.parent(curve, self.guidesGrp)
        pm.setAttr("{}.inheritsTransform".format(curve), 0)
        pm.setAttr("{}.template".format(curve), 1)
        # Apply custer handles so the guides can move the curve
        for i, guide in enumerate(self.allGuides):
            cluster = pm.cluster("{}.cv[{}]".format(curve, i), n=guide.replace("_guide", "_clstr"))[1]
            pm.setAttr("{}.visibility".format(cluster), 0)
            pm.parent(cluster, guide)
        return curve

