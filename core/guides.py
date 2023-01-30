import pymel.core as pm
from core import constants
from core import utils


SIDES = {"LT": "RT_",
         "RT": "LT_",
         "FT": "BK_",
         "BK": "FT_",
         "TP": "BT_",
         "BT": "TP_"}


def get_guides_from_group(group):
    guides = [node for node in reversed(pm.listRelatives(group, ad=1)) if node.name().split("_")[-1] == "guide"]
    if not guides:
        return None
    return guides


def make_guides_objects():
    """
    Creates a list of Guides Objects from an imported Guides Group that can be used to build a rig
    :return: list: Guides Objects created from group
    """
    if not pm.ls("guides_grp"):
        pm.warning("guides group is not in Maya scene")
    guidesObjList = []
    for group in pm.listRelatives("guides_grp", c=1):
        name = group.name().replace("_guides_grp", "")
        side = name[:2]
        chainLength = len(get_guides_from_group(group))
        mirror = False
        if side in ["RT", "BK", "BT"]:
            mirror = True
        invert = False
        if name.split("_")[1] in ["leg"]:
            invert = True
        guidesObj = Build(name, side=side, chain_len=chainLength, mirror=mirror, invert=invert)
        guidesObjList.append(guidesObj)
    return guidesObjList


class Build(object):
    def __init__(self, name, side, chain_len=3, axis="X", scale=10,
                 invert=False, mirror=False, mirror_axis="X", link=False):
        self.name = f"{side}_{name}"
        self.side = side
        self.chainLength = chain_len
        self.axis = axis
        self.scale = scale
        self.invert = invert
        self.mirror = mirror
        self.mirrorAxis = mirror_axis
        self.mainGuidesGrp = utils.make_group("guides_grp")
        self.guidesGrp = utils.make_group(f"{self.name}_guides_grp", parent=self.mainGuidesGrp)
        self.allGuides = self.get_guides()
        self.curve = self.make_guides_curve()
        if link:
            self.linkGuides = self.link_guides()
        pm.select(cl=1)

    def get_guides(self):
        if pm.listRelatives(self.guidesGrp, c=1):
            guides = get_guides_from_group(self.guidesGrp)
            if len(guides) != self.chainLength:
                pm.delete(pm.listRelatives(self.guidesGrp, c=1))
                guides = self.make_guides()
        else:
            guides = self.make_guides()
        return guides

    def link_guides(self):
        linkGuides = []
        for guide in [guide for guide in self.allGuides
                      if pm.ls(guide.name().replace(f"{self.side}_", SIDES[self.side]))]:
            linkGuide = pm.PyNode(guide.name().replace(f"{self.side}_", SIDES[self.side]))
            linkGuides.append(linkGuide)
            decMtrx = utils.check_hypergraph_node(linkGuide.name().replace("_guide", "_mtrx"), "decomposeMatrix")
            mult = utils.check_hypergraph_node(linkGuide.name().replace("_guide", "_mult"), "multiplyDivide")
            if guide.name().split("_")[-2] == "base":
                eval(f"mult.input2{self.mirrorAxis}.set(-1)")
            else:
                for axis in [axis for axis in constants.AXES if axis != self.mirrorAxis]:
                    eval(f"mult.input2{axis}.set(-1)")
            pm.connectAttr(linkGuide.matrix, decMtrx.inputMatrix, f=1)
            pm.connectAttr(decMtrx.outputTranslate, mult.input1, f=1)
            pm.connectAttr(mult.output, guide.translate, f=1)
        return linkGuides

    def make_guides(self):
        guidesList = []
        prevGuide = None
        scale = self.scale
        if self.mirror and not self.invert:
            scale = -scale
        if self.invert and not self.mirror:
            scale = -scale
        for i in range(self.chainLength):
            span = constants.get_span(i, self.chainLength, base_tip=1)
            guideName = f"{self.name}_{span}_guide"
            # Create and position the locator
            guide = pm.spaceLocator(n=guideName)
            guidesList.append(guide)
            pm.setAttr(f"{guide}.translate{self.axis}", (i * scale) + (0.1 * scale))
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

