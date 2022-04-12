import pymel.core as pm
from core import matrix


def freeze_transforms(nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    for node in nodes:
        if not pm.nodeType(node) == "transform":
            if not pm.nodeType(pm.listRelatives(node, p=1)[0]) == "transform":
                continue
            else:
                pm.makeIdentity(pm.listRelatives(node, p=1), a=1)
        else:
            pm.makeIdentity(node, a=1)
    return nodes


def make_offset_groups(name=None):
    if name is None:
        name = "offset"
    offsetGrps = []
    if not pm.ls(sl=1):
        pm.warning("Nothing Selected")
        return None
    for node in pm.ls(sl=1):
        if not pm.nodeType(node) == "transform":
            continue
        parent = pm.listRelatives(node, p=1)
        grp = pm.group(em=1, n="{}_{}_grp".format(str(node), name))
        matrix.worldspace_to_matrix(grp, node)
        if parent:
            pm.parent(grp, parent[0])
        pm.parent(node, grp)
        offsetGrps.append(grp)
    return offsetGrps


def parent_crv():
    # TODO: transforms aren't freezing properly for child nodes.
    #  It's odd because the code runs properly when freeze_transforms() function is
    #  performed separately beforehand but not when run concurrently in the same function
    nodes = freeze_transforms(pm.ls(sl=1))
    if not pm.nodeType(nodes[-1]) == "transform":
        if pm.nodeType(nodes[-1], p=1) == "transform":
            nodes[-1] = pm.listRelatives(nodes[-1], p=1)[0]
        else:
            pm.error("Make sure last object selected is a transform node")
    print(nodes)
    print(nodes[:-1])
    print(nodes[-1], pm.getAttr("{}.scaleX".format(nodes[-1])))
    for node in nodes[:-1]:
        if not pm.nodeType(node) == "nurbsCurve":
            if pm.nodeType(pm.listRelatives(node, c=1)[0]) == "nurbsCurve":
                node = pm.listRelatives(node, c=1)
            else:
                continue
        parent = pm.listRelatives(node, p=1)[0]
        print(node[0], parent, pm.getAttr("{}.scaleX".format(pm.listRelatives(node, p=1)[0])))
        pm.parent(node[0], nodes[-1], r=1, s=1)
        pm.delete(parent)
    pm.select(nodes[-1])
