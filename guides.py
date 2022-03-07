import pymel.core as pm


VECTORS = ["X", "Y", "Z"]


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


