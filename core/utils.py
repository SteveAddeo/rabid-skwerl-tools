import os
import json
import pymel.core as pm
from core import constants
import maya.api.OpenMaya as om


ENVPATH = os.environ["MAYA_APP_DIR"]
SETUPPATH = os.path.join(ENVPATH, pm.about(v=1), "scripts")
RSTPATH = os.path.join(ENVPATH, pm.about(v=1), "prefs", "scripts")


#############
# Deformer
#############
def set_sine_unlock_end(hndl):
    """
    Sets up a sine deformer so that the end isn't locked in place
    :param hndl: the sine deformer being manipulated
    """
    if not hndl.scaleY.get() == hndl.scaleX.get():
        return
    hndl.scaleY.set(2 * hndl.scaleY.get())
    hndl.translateX.set(2 * hndl.translateX.get())


def set_sine_lock_end(hndl):
    """
    Sets up a sine deformer so that the end is locked in place
    :param hndl: the sine deformer being manipulated
    """
    if hndl.scaleY.get() == hndl.scaleX.get():
        return
    hndl.scaleY.set(0.5 * hndl.scaleY.get())
    hndl.translateX.set(0.5 * hndl.translateX.get())


#############
# Nodes
#############

def check_nodes(nodes=None):
    """
    Checks to see if a list of nodes is given and, if not, assign selected nodes. If the
    given variable is a string, the function will return PyNodes in their place
    :param nodes: List: nodes being checked
    :return: List: nodes being checked and seleced nodes if None
    :raises: Error if nothing selected
    """
    if nodes is None:
        if not pm.ls(sl=0):
            pm.warning("Nothing selected.")
            return None
        nodes = pm.ls(sl=1)
    for i, node in enumerate(nodes):
        if type(node) == "string":
            nodes[i] = pm.PyNode(node)
    return nodes


def check_hypergraph_node(name, node_type, shading=True):
    """
    Checks to see if a shading node exists and creates one if it doesn't
    :param name: str: the name of the node being checked
    :param node_type: str: the type of shader node being checked (ex: multiplyDoubleLinear)
    :param shading: bool: if the node being created is a shading node
    :return: PyNode: the shading node being checked
    """
    if pm.ls(name):
        return pm.PyNode(name)
    if not shading:
        return pm.createNode(node_type, n=name)
    return pm.shadingNode(node_type, n=name, au=1)


def check_locator(name):
    """
    Checks to see if a locator exists in a scene and creates one if it doesnt
    :param name: str: name of the locator being checked
    :return: PyNode: the locator being checked
    """
    if pm.ls(name):
        return pm.PyNode(name)
    return pm.spaceLocator(n=name)


def invert_attribute(target_attr):
    """
    Creates a node that multiplies the source attribute value by -1 to invert the number. Can be used for both
    singular and vector attribute formats
    :param target_attr: PyNode.attr: the destination attribute
    :return: the multiply node created
    """
    if not pm.listConnections(target_attr, p=1):
        pm.warning(f"{target_attr} has no incoming connections")
        return None
    source = pm.listConnections(target_attr, p=1)[0]
    if "unitConversion" in source.name():
        conversion = pm.PyNode(source.name().split('.')[0])
        source = pm.listConnections(conversion.input, p=1)[0]
        pm.disconnectAttr(conversion.output, target_attr)
        pm.delete(conversion)
    multName = f"{'_'.join(source.name().split('.'))}_to_{'_'.join(target_attr.split('.'))}_invert_mult"
    if "double" in source.type():
        # Single attributes can use a Multiply Double Linear node with input 2 set to -1
        mult = check_hypergraph_node(multName, "multDoubleLinear")
        mult.input2.set(-1)
    else:
        # Vector formats require a Multiply Divide node with input 2 axes set to -1
        mult = check_hypergraph_node(multName, "multiplyDivide")
        for axis in constants.AXES:
            eval(f"mult.input2{axis}.set(-1)")
    # Connect the attributes (may throw a warning since you're forcing a connection)
    pm.connectAttr(source, mult.input1, f=1)
    pm.connectAttr(mult.output, target_attr, f=1)
    return mult


def make_distance(name, start, end):
    """
    Creates a Distance Between node for a given start and end node.
    :param name: str: name of the distance between setup
    :param start: PyNode: The base node at the start of the measurement
    :param end: PyNode: The tip node at the end of the measurement
    :return: PyNode: the distance between node that was created
    """
    baseLoc = check_locator(f"{name}_base_loc")
    tipLoc = check_locator(f"{name}_tip_loc")
    dist = check_hypergraph_node(f"{name}_dist", "distanceBetween")
    pm.xform(baseLoc, t=pm.xform(start, q=1, ws=1, rp=1))
    pm.xform(tipLoc, t=pm.xform(end, q=1, ws=1, rp=1))
    pm.parent(baseLoc, start)
    pm.parent(tipLoc, end)
    pm.connectAttr(baseLoc.worldMatrix[0], dist.inMatrix1, f=1)
    pm.connectAttr(tipLoc.worldMatrix[0], dist.inMatrix2, f=1)
    return dist


#############
# Outliner
#############

def get_parent_and_children(node):
    """
    Returns a list of a given node's parent and list of children in the outliner
    :param node: PyNode: Node being queiries
    :return: list: The parent and child of the queried node
    """
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
    """
    Looks for or creates then returns a group with a given name, parents it to a defined parent and adds
    defined children to its hierarchy
    :param name: str: the name of the new group
    :param child: PyNode or list: children of the group being created
    :param parent: PyNode: parent of the group being created
    :return: the new group that was created
    """
    if pm.ls(name):
        grp = pm.PyNode(name)
    else:
        grp = pm.group(n=name, em=1)
    if child is not None:
        pm.parent(child, grp)
    if parent is not None:
        pm.parent(grp, parent)
    return grp


def make_offset_groups(nodes=None, name=None, freeze=True, reset=True):
    """
    Creates an offset group
    :param nodes:
    :param name:
    :param freeze:
    :param reset:
    :return:
    """
    offsetGrps = []
    nodes = check_nodes(nodes)
    if nodes is None:
        return None
    for node in nodes:
        if node.type() == "nurbsCurve":
            continue
        if name is None:
            name = f"{node.name()}_grp"
        grp = make_group(name)
        # TODO: this only changes position. Needs to update rotation too
        pm.xform(grp, t=pm.xform(node, q=1, ws=1, rp=1))
        if pm.listRelatives(node, p=1):
            pm.parent(grp, pm.listRelatives(node, p=1)[0])
        if freeze:
            transfer_transforms_to_offset([grp])
        pm.parent(node, grp)
        if reset:
            reset_transforms([node])
        offsetGrps.append(grp)
    return offsetGrps


def parent_crv(name=None, nodes=None):
    """
    Parents curve shapes to a node allowing the curve to directly control it
    :param name: str: name of the returned transform node
    :param nodes: list: curve shape nodes being parented
    :return: transform node curves are parented to
    """
    # TODO: this needs testing
    nodes = check_nodes(nodes)
    if nodes is None:
        return None
    # Get the name of the curve
    if name is None:
        name = nodes[-1].name()
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
    """
    Returns the unit length of a joint chain (not the number of chains)
    :param joint: PyNode: the base joint for the defined chain
    :param aim: str: the aim axis of the given joint
    :return: float: the length of the joint chaoin
    """
    jnts = get_joints_in_chain(joint)[1:]
    chainLen = 0
    for jnt in jnts:
        jntLen = pm.getAttr(f"{jnt}.translate{aim}")
        chainLen = chainLen + jntLen
    return chainLen


def get_info_from_joint(joint, name=False, num=False, side=False, task=False):
    """
    Returns returns specified information from a given joint
    :param joint: PyNode: the joint being queried
    :param name: bool: returns the name of the defined joint
    :param num: bool: returns the number of joints in the chain with defined joint as base
    :param side: bool: returns the side the defined joint exists on
    :param task: bool: returns the name of the task the defined joint is assigned to (ex: driver)
    :return: the data specified
    """
    if name:
        return "_".join(joint.name().split("_")[:2])
    if num:
        return len(get_joints_in_chain(joint))
    if side:
        return joint.name().split("_")[0]
    if task:
        return joint.name().split("_")[-2]


def get_joints_in_chain(joint):
    """
    Returns the a list of joints in the chain of a defined base joint
    :param joint: PyNode: the base joint of the chain
    :return: list: the joints in the chain
    """
    jnts = [jnt for jnt in reversed(pm.listRelatives(joint, ad=1)) if jnt.type() == "joint"]
    jnts.insert(0, joint)
    return jnts


def get_joint_type(joint):
    """
    Returns the type of joint given (ex: base_IK)
    :param joint: PyNode: joint being queried
    :return: str: the joint type
    """
    jointType = joint.name().split("_")[-2]
    subTypes = ["base", "mid", "tip"]
    if jointType in subTypes:
        jointType = "_".join([joint.name().split("_")[-3], jointType])
    return jointType


def make_curve_from_chain(joint, name=None, cubic=True, bind=None):
    """
    Makes a curve with control points at the location of each joint in a given chain
    :param joint: PyNode: The base joint of the chain the curve is being made out of
    :param name: str: The name of the curve being created
    :param cubic: bool: whether we want the curve degree to be Cubic or Linear
    :param bind: list: list of joints to bind the curve to
    :return: PyNode: the curve that was created
    """
    # Name the curve
    if name is None:
        name = joint.name().replace("_jnt", "_crv")
    # Check if curve exists
    if pm.ls(name):
        return pm.PyNode(name)
    # Get joints and their World Space positions
    jnts = get_joints_in_chain(joint)
    pts = [pm.xform(jnt, q=1, ws=1, rp=1) for jnt in jnts]
    # Build the curve
    deg = 3
    if not len(jnts) > 4 or not cubic:
        deg = 1
    crv = pm.curve(n=name, d=deg, p=pts)
    # Set the pivot point to the curve's base
    pm.xform(crv, p=1, rp=pts[0])
    pm.delete(crv, ch=1)
    crv.inheritsTransform.set(0)
    # Group the curve
    grp = make_group(f"{name}_grp", child=crv, parent=make_group("crv_grp", parent=make_group("utils_grp")))
    pm.xform(grp, t=pm.xform(joint, q=1, ws=1, rp=1))
    if bind is not None:
        skin_to_joints(bind, crv)
    # Create a curve info node
    info = check_hypergraph_node(f"{name}_info", "curveInfo")
    pm.connectAttr(crv.worldSpace[0], info.inputCurve)
    return crv


def duplicate_chain(jnts, chain_type, dup_parent):
    """
    Creates a duplicate of a given joint chain with transforms preserved and parented to a new group
    :param jnts: list: joints being duplicated
    :param chain_type: str: the name of the type of chain that will replace the original joint type (typically 'drv')
    :param dup_parent: The group to parent duplicate chain to
    :return: list: The duplicated joints that were created
    """
    dupJnts = []
    for jnt in jnts:
        parent = get_parent_and_children(jnt)[0]
        children = get_parent_and_children(jnt)[1]
        # Unparent the joint and any children it may have
        if parent is not None:
            pm.parent(jnt, w=1)
        if children is not None:
            pm.parent(children, w=1)
        # Duplicate joint
        try:
            dupName = jnt.name().replace(get_joint_type(jnt), chain_type)
        except IndexError:
            dupName = "_".join([jnt.name(), chain_type])
        dup = pm.duplicate(jnt, n=dupName)[0]
        # Set duplicate joint's radius based on chain type
        if chain_type == "FK":
            dupRad = jnt.radius.get() * 0.65
        elif chain_type == "IK":
            dupRad = jnt.radius.get() * 1.6
        elif chain_type == "twst":
            dupRad = jnt.radius.get() * 2.0
        else:
            dupRad = jnt.radius.get() * 0.4
        dup.radius.set(dupRad)
        # Re-parent joints
        if parent is not None:
            pm.parent(jnt, parent)
        if children is not None:
            pm.parent(children, jnt)
        if dupJnts:
            pm.parent(dup, dupJnts[-1])
        else:
            pm.parent(dup, dup_parent)
        dupJnts.append(dup)
    return dupJnts


def make_joint(name, radius=1.0, parent=None, color=1):
    """
    Creates a joint with a given name, radius, and parent node
    :param name: str: the name of the joint
    :param radius: float: the radius of the joint
    :param parent: PyNode: the node the user wants to parent the joint to
    :param color: desired color of the joint
    :return: PyNode: the joint that was created
    """
    joint = pm.joint(n=name, rad=radius)
    joint.overrideEnabled.set(1)
    joint.overrideColor.set(color)
    if parent is not None:
        pm.parent(joint, parent)
    return joint


def skin_to_joints(bind_jnts, obj, name=None):
    """
    Apply a skincluster to a given object with given joints
    :param bind_jnts: list: joints being skinned to
    :param obj: pyMel: object being skinned
    :param name: str: name of skin cluster
    :return: pyMel: the skincluster that was created
    """
    if name is None:
        name = f"{obj.name()}_skinCluster"
    clstr = pm.skinCluster(bind_jnts, obj, n=name, tsb=True, bm=0, sm=0, nw=1)
    return clstr


def split_chain(jnt_chain, jnt_type="split", splits=1):
    """
    Takes a given joint chain and creates a new chain with each span composed of a given number of split joints
    :param jnt_chain: list: The base chain creating the split chain (Typically a driver joint)
    :param jnt_type: str: The name of the joints being created (can also be 'skn')
    :param splits: int: Number of in between joints for each span
    :return: list: All split joints that were created
    """
    # Make sure splits make sense mathematically
    if splits == 0:
        splits = 1
    if splits < 0:
        splits = -1 * splits
    # Create a group to parent the splits to
    grp = make_group(f"{get_info_from_joint(jnt_chain[0], name=True)}_{jnt_type}_jnt_grp",
                     parent=make_group(f"{jnt_type}_jnt_grp", parent=make_group("jnt_grp")))
    allSpltJnts = []
    # Create splits for each joint span
    for i, jnt in enumerate(jnt_chain[:-1]):
        # Create the base of the split chain
        span = constants.get_span(i, len(jnt_chain[:-1]))
        dupJnt = duplicate_chain([jnt], jnt_type, grp)[0]
        pm.rename(dupJnt, dupJnt.name().replace(dupJnt.name().split("_")[-3], f"{span}01"))
        spltJnts = [dupJnt]
        # Create the split joints
        for n in range(splits + 1):
            spltJnt = pm.duplicate(spltJnts[-1], n=spltJnts[-1].name().replace(
                spltJnts[-1].name().split("_")[-3], f"{span}{str(n+2).zfill(2)}"))[0]
            pm.parent(spltJnt, spltJnts[-1])
            aimAxis = str(spltJnt.getRotationOrder())[0]
            eval(f"spltJnt.translate{aimAxis}.set((jnt_chain[i+1].translate{aimAxis}.get() / (splits + 1)))")
            spltJnts.append(spltJnt)
        # set attributes for split joints
        for n, j in enumerate(spltJnts):
            j.overrideEnabled.set(1)
            j.overrideColor.set(9)
            allSpltJnts.append(j)
    return allSpltJnts


#############
# Text Data
#############

def get_data_from_json(file_path):
    """
    Retrieves data from a given json file
    :param file_path: str: the directory path to the json file being read from
    :return: the data retrieved
    """
    with open(file_path) as file:
        data = json.load(file)
    return data


def write_data_to_json(file_path, data):
    """
    Writes given data to a specified json file
    :param file_path: str: the directory path to the json file being written to
    :param data: data being written to the json file
    """
    with open(file_path, "w") as file:
        json.dump(data, file, indent=2)


#############
# Transforms
#############

def is_frozen(node=None):
    # TODO: this function doesn't work
    nodes = check_nodes([node])
    if nodes is None:
        return False
    if nodes[0].getMatrix() == pm.dt.Matrix() and not pm.xform(nodes[0], q=1, ws=1, rp=1) == nodes[0].translate.get():
        return True
    return False


def freeze_transforms(nodes=None):
    """
    Freezes the transforms of a given list of nodes
    :param nodes: list: the list of PyNodes whose transforms are being frozen
    :return: list: the same list of PyNodes
    """
    nodes = check_nodes(nodes)
    if nodes is None:
        return None
    for node in nodes:
        if not pm.nodeType(node) == "transform":
            if pm.listRelatives(node, p=1) and not pm.nodeType(pm.listRelatives(node, p=1)[0]) == "transform":
                continue
            else:
                pm.makeIdentity(pm.listRelatives(node, p=1)[0], a=1)
        else:
            pm.makeIdentity(node, a=1)
    return nodes


def reset_transforms(nodes=None, t=True, r=True, s=True, m=True, o=True):
    """
    Resets the transformation values of a given node without preserving transforms
    :param nodes: list: List of PyNodes being edited
    :param t: bool: Reset Translate attribute values
    :param r: bool: Reset Rotate attribute values
    :param s: bool: Reset Scale attribute values
    :param m: bool: Reset Ofset Parent Matrix attribute values
    :param o: bool: Reset Joint Offset attribute values (checks to see if node is a joint)
    """
    nodes = check_nodes(nodes)
    if nodes is None:
        return None
    attrs = ["translate", "rotate", "scale", "jointOrient", "offsetParentMatrix"]
    tansforms = [t, r, s, o, m]
    for node in nodes:
        for attr in [attr for attr in attrs if tansforms[attrs.index(attr)]]:
            for axis in constants.AXES:
                val = 0
                if attr == "scale":
                    val = 1
                try:
                    if attr == "offsetParentMatrix":
                        node.offsetParentMatrix.set(constants.FROZENMTRX)
                        break
                    elif attr == "jointOrient" and node.type() != "joint":
                        continue
                    else:
                        eval(f"node.{attr}{axis}.set({val})")
                except RuntimeError as e:
                    print(e)


def point_constraint_move(source, target):
    """
    Uses a point constrain to move a target node then deletes the consrtraint
    :param source: PyNode: the object being moved to
    :param target: PyNode: the object being moved
    """
    constraint = pm.pointConstraint(source, target)
    pm.delete(constraint)
    try:
        pm.makeIdentity(target, a=1)
    except RuntimeError as e:
        pm.warning(str(e))


def transfer_transforms_to_offset(nodes=None):
    """
    Moves all transform values from the transform attributs to the Offset Parent Matrix attribute
    :param nodes: list: a list of the PyNodes being edited
    """
    nodes = check_nodes(nodes)
    if nodes is None:
        return None
    for node in nodes:
        localMtrx = om.MMatrix(pm.xform(node, q=1, m=1, ws=0))
        offsetMtrx = om.MMatrix(node.offsetParentMatrix.get())
        bakedMtrx = localMtrx * offsetMtrx
        node.offsetParentMatrix.set(bakedMtrx)
        reset_transforms([node], m=False)


def transfer_offset_to_orient(nodes=None):
    """
    Moves any rotation value in the Offset Parent Matrix over to the Joint Orient attribude
    :param nodes: list: a list of the PyNodes being edited
    """
    nodes = check_nodes(nodes)
    if nodes is None:
        return
    for node in nodes:
        if not node.type() == "joint":
            continue
        decompose = pm.createNode("decomposeMatrix", n="tempDM")
        source = pm.listConnections(node.offsetParentMatrix,  p=1, d=0)[0]
        pm.connectAttr(source, decompose.inputMatrix)
        decompose.inputRotateOrder.set(node.rotateOrder.get())
        node.jointOrient.set([-v for v in decompose.outputRotate.get()])
        pm.delete(decompose)


def toggle_inherits_transform(nodes=None):
    """
    Turns the Inherits Transform attribute of a given node off and on
    :param nodes: list: a list of the PyNodes being edited
    """
    nodes = check_nodes(nodes)
    if nodes is None:
        return
    for node in nodes:
        if node.inheritsTransform.get():
            node.inheritsTransform.set(1)
        else:
            node.inheritsTransform.set(0)
