import pymel.core as pm
from core import matrix


def freeze_transforms(nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    for node in nodes:
        print(node, node.getMatrix())
        if not pm.nodeType(node) == "transform":
            if pm.listRelatives(node, p=1) and not pm.nodeType(pm.listRelatives(node, p=1)[0]) == "transform":
                continue
            else:
                pm.makeIdentity(pm.listRelatives(node, p=1)[0], a=1)
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


def parent_crv(nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    if not nodes:
        pm.error("Nothing Selected")
    # Create an empty group to act as the parents for your curves
    transform = pm.group(em=1)
    # Get the name of the curve
    name = str(nodes[-1])
    mtrx = nodes[-1].getMatrix()
    # Parent each curveShape to the new transform node
    for curve in nodes:
        if not pm.nodeType(curve) == "nurbsCurve":
            curve = curve.getShape()
        parent = pm.listRelatives(curve, p=1)[0]
        pm.parent(curve, transform, r=1, s=1)
        pm.delete(parent)
    # Freeze transforms (requires an extra step for Maya versions over 2020)
    if int(pm.about(v=1)) >= 2020:
        # This stores the transforms in the offset parent matrix
        pm.setAttr("{}.offsetParentMatrix".format(str(transform)), mtrx)
        pm.xform(transform, ws=1, m=mtrx)
    pm.makeIdentity(transform, a=1, n=2)
    pm.rename(transform, name)
    pm.select(transform)

