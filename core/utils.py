import os
import json
import pymel.core as pm
from core import constants
from core import matrix


ENVPATH = os.environ["MAYA_APP_DIR"]
SETUPPATH = os.path.join(ENVPATH, pm.about(v=1), "scripts")
RSTPATH = os.path.join(ENVPATH, pm.about(v=1), "prefs", "scripts")


def get_data_from_json(file_path):
    with open(file_path) as file:
        data = json.load(file)
    return data


def get_parent_and_children(node):
    if pm.listRelatives(node, p=1):
        parent = pm.listRelatives(node, p=1)[0]
    else:
        parent = None
    if pm.listRelatives(node, c=1):
        children = pm.listRelatives(node, c=1)
    else:
        children = None
    return [parent, children]


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


def make_offset_groups(nodes=None, name=None):
    if name is None:
        name = "offset"
    offsetGrps = []
    if nodes is None:
        nodes = pm.ls(sl=1)
    if not nodes:
        pm.warning("Nothing Selected")
        return None
    for node in nodes:
        if pm.nodeType(node) == "nurbsCurve":
            continue
        parent = pm.listRelatives(node, p=1)
        grp = pm.group(em=1, n="{}_{}_grp".format(str(node), name))
        matrix.worldspace_to_matrix(grp, node)
        if parent:
            pm.parent(grp, parent[0])
        pm.parent(node, grp)
        offsetGrps.append(grp)
    return offsetGrps


def parent_crv(name=None, nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    if not nodes:
        pm.error("Nothing Selected")
    # Create an empty group to act as the parents for your curves
    transform = pm.group(n=name, em=1)
    # Get the name of the curve
    if name is None:
        name = str(nodes[-1])
    # Get position and pivot data
    mtrx = nodes[-1].getMatrix()
    piv = pm.xform(nodes[-1], q=1, rp=1)
    pm.xform(transform, piv=piv)
    # Parent each curveShape to the new transform node
    for curves in nodes:
        if not pm.nodeType(curves) == "nurbsCurve":
            curves = curves.getShapes()
        parent = pm.listRelatives(curves, p=1)
        if type(curves) == list:
            for curve in curves:
                pm.parent(curve, transform, r=1, s=1)
        if parent:
            pm.delete(parent)
    # Freeze transforms (requires an extra step for Maya versions over 2020)
    if int(pm.about(v=1)) >= 2020:
        # This stores the transforms in the offset parent matrix
        pm.setAttr("{}.offsetParentMatrix".format(str(transform)), mtrx)
        pm.xform(transform, ws=1, m=mtrx)
    pm.makeIdentity(transform, a=1, n=2)
    pm.select(transform)
    return transform


def reset_transforms(node, t=True, r=True, s=True):
    for axis in constants.AXES:
        if t:
            pm.setAttr("{}.translate{}".format(node, axis), 0)
        if r:
            pm.setAttr("{}.rotate{}".format(node, axis), 0)
        if s:
            pm.setAttr("{}.scale{}".format(node, axis), 1)


def write_data_to_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)


