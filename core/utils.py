import os
import json
import pymel.core as pm
from core import constants
from core import matrix


ENVPATH = os.environ["MAYA_APP_DIR"]
SETUPPATH = os.path.join(ENVPATH, pm.about(v=1), "scripts")
RSTPATH = os.path.join(ENVPATH, pm.about(v=1), "prefs", "scripts")


#############
# Deformer
#############
def set_sine_unlock_end(hndl):
    if not hndl.scaleY.get() == hndl.scaleX.get():
        return
    hndl.scaleY.set(2 * hndl.scaleY.get())
    hndl.translateX.set(2 * hndl.translateX.get())


def set_sine_lock_end(hndl):
    if hndl.scaleY.get() == hndl.scaleX.get():
        return
    hndl.scaleY.set(0.5 * hndl.scaleY.get())
    hndl.translateX.set(0.5 * hndl.translateX.get())


#############
# Outliner
#############

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


def make_group(name, child=None, parent=None):
    if pm.ls(name):
        grp = pm.PyNode(name)
    else:
        grp = pm.group(n=name, em=1)
    if child is not None:
        pm.parent(child, grp)
    if parent is not None:
        pm.parent(grp, parent)
    return grp


def make_offset_groups(nodes=None):
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
        grp = pm.group(em=1, n=f"{str(node)}_grp")
        pm.parent(grp, node)
        reset_transforms(grp)
        if parent:
            pm.parent(grp, parent[0])
        else:
            pm.parent(grp, w=1)
        pm.parent(node, grp)
        offsetGrps.append(grp)
    return offsetGrps


def parent_crv(name=None, nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    if not nodes:
        pm.error("Nothing Selected")
    # Get the name of the curve
    if name is None:
        name = str(nodes[-1])
    # Create an empty group to act as the parents for your curves
    transform = pm.group(n=name, em=1)
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


#############
# Skeleton
#############

def get_length_of_chain(joint, aim="X"):
    jnts = get_joints_in_chain(joint)[1:]
    chainLen = 0
    for jnt in jnts:
        jntLen = pm.getAttr(f"{jnt}.translate{aim}")
        chainLen = chainLen + jntLen
    return chainLen


def get_info_from_joint(joint, name=False, num=False, side=False, task=False):
    if name:
        return joint.name().split("_")[1]
    if num:
        return len(get_joints_in_chain(joint))
    if side:
        return joint.name().split("_")[0]
    if task:
        return joint.name().split("_")[-2]


def get_joints_in_chain(joint):
    jnts = [jnt for jnt in reversed(pm.listRelatives(joint, ad=1))]
    jnts.insert(0, joint)
    return jnts


def make_curve_from_chain(joint, name=None):
    # Name the curve
    if name is None:
        name = f"{get_info_from_joint(joint, name=True)}_crv"
    # Check if curve exists
    if pm.ls(name):
        return pm.ls(name)[0]
    # Get joints and their World Space positions
    jnts = get_joints_in_chain(joint)
    pts = [pm.xform(jnt, q=1, ws=1, rp=1) for jnt in jnts]
    # Build the curve
    crv = pm.curve(n=name, d=3, p=pts)
    # Set the pivot point to the curve's base
    pm.xform(crv, p=1, rp=pts[0])
    pm.delete(crv, ch=1)
    crv.inheritsTransform.set(0)
    info = pm.shadingNode("curveInfo", n=f"{name}_info", au=1)
    pm.connectAttr(crv.worldSpace[0], info.inputCurve)
    return crv


#############
# Text Data
#############

def get_data_from_json(file_path):
    with open(file_path) as file:
        data = json.load(file)
    return data


def write_data_to_json(file_path, data):
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)


#############
# Transforms
#############

def freeze_transforms(nodes=None):
    if nodes is None:
        nodes = pm.ls(sl=1)
    for node in nodes:
        if not pm.nodeType(node) == "transform":
            if pm.listRelatives(node, p=1) and not pm.nodeType(pm.listRelatives(node, p=1)[0]) == "transform":
                continue
            else:
                pm.makeIdentity(pm.listRelatives(node, p=1)[0], a=1)
        else:
            pm.makeIdentity(node, a=1)
    return nodes


def reset_transforms(node, t=True, r=True, s=True, o=True):
    # TODO: Check for connections
    for axis in constants.AXES:
        if t and node.type != "joint":
            pm.setAttr(f"{node.name()}.translate{axis}", 0)
        if r:
            pm.setAttr(f"{node.name()}.rotate{axis}", 0)
        if s:
            pm.setAttr(f"{node.name()}.scale{axis}", 1)
        if o:
            node.offsetParentMatrix.set(constants.FROZENMTRX)
        if node.type() == "joint":
            pm.setAttr(f"{node.name()}.jointOrient{axis}", 0)


def toggle_inherits_transform(nodes):
    for node in nodes:
        if node.inheritsTransform.get():
            node.inheritsTransform.set(1)
        else:
            node.inheritsTransform.set(0)
