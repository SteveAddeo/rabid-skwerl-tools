import pymel.core as pm
import maya.api.OpenMaya as om

from core import constants
from core import utils


def constrain(driver, driven, frozen=False, offset=False, reset=False):
    """
    Uses matrix nodes to constrain a driven object to a driver. The function can account for frozen transforms,
    preserve offsets, and resets transforms if told to.
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param frozen: bool: if the driver node has frozen transforms
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the offset multMatrix node
    """
    # TODO: Check for frozen transforms instead of asking the user to set the attribute
    if frozen:
        pm.move(driven, list(pm.dt.Vector()), rpr=1)
        # pm.makeIdentity(driven, a=1)
    pm.connectAttr(driver.worldMatrix[0], driven.offsetParentMatrix, f=1)
    if reset:
        utils.reset_transforms([driven], m=False)
    if offset:
        # TODO: offset may be preserved by turning off inherit transforms!
        offset = offset_driven(driver, driven)
        return offset
    return None


def decompose_constraint(target, pick=False):
    """
    Creates a decompose matrix to a compose matrix node at the offsetParentMatrix input of a defined
    target node. The function can also work for pickMatrix node but it has to be told to do so.
    :param target: PyNode: the node receiving the offsetParentMatrix data
    :param pick: bool: whether the target node is a pickMatrix node
    :return: PyNode, PyNode: the created decompose and compose matrix nodes
    """
    # Set the source attribute based on pick attribute
    if pick:
        source_attr = "inputMatrix"
    else:
        source_attr = "offsetParentMatrix"
    # Check to see if decompose/compose matrix node pair already exists
    if pm.listConnections(eval(f"target.{source_attr}"))[0] == "composeMatrix":
        comp = pm.listConnections(eval(f"target.{source_attr}"))[0]
        dec = pm.PyNode(comp.name().replace("_comp", "_dec"))
        return dec, comp
    # Set variables and create decompose/compose matrix node pair
    source = pm.listConnections(eval(f"target.{source_attr}"), p=1)[0]
    name = "_".join(source.name().split(".")[0].split("_")[:-1])
    dec = utils.check_hypergraph_node(f"{name}_dec", "decomposeMatrix", shading=False)
    comp = utils.check_hypergraph_node(f"{name}_comp", "composeMatrix", shading=False)
    # Make attribute connections
    pm.connectAttr(source, dec.inputMatrix)
    for attr in constants.TRNSFRMATTRS:
        pm.connectAttr(eval(f"dec.output{attr.capitalize()}"), eval(f"comp.input{attr.capitalize()}"), f=1)
    pm.connectAttr(comp.outputMatrix, eval(f"target.{source_attr}"), f=1)
    return dec, comp


def make_blend(drivers, driven, decompose=False):
    """
    Creates a blendMatrix node between a defined pair of driver/driven nodes. The function can also use a decompose
    matrix node to directly drive the driven transforms rather than its offset parent matrix.
    :param drivers: list: the source nodes driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param decompose: bool: if the driven node needs its transforms to be constrained
    :return: the blendMatrix node that is created.
    """
    # Set variables and create blend node
    blend_name = "_".join(driven.name().split("_")[:-1] + ["blend"])
    if pm.ls(blend_name):
        return pm.PyNode(blend_name)
    blend = utils.check_hypergraph_node(blend_name, "blendMatrix", shading=False)
    # Connect drivers to blend
    driven.inheritsTransform.set(0)
    for i, driver in enumerate(drivers):
        if i:
            blend.target[i-1].targetMatrix.get()
            pm.connectAttr(driver.worldMatrix[0], blend.target[i-1].targetMatrix, f=1)
            continue
        pm.connectAttr(driver.worldMatrix[0], blend.inputMatrix, f=1)
    # Connect blend to driven
    pm.connectAttr(blend.outputMatrix, driven.offsetParentMatrix, f=1)
    utils.reset_transforms([driven], m=False)
    if decompose:
        make_decompose(blend, driven)
    return blend


def make_decompose(driver, driven):
    """
    Creates a decomposeMatrix node between a defined pair of driver/driven nodes.
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :return: the decomposeMatrix node that is created.
    """
    # Set variables and create decompose node
    decompose_name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["dec"])
    decompose = utils.check_hypergraph_node(decompose_name, "decomposeMatrix", shading=False)
    driver_attr = pm.listConnections(driven.offsetParentMatrix, p=1)[0]
    pm.disconnectAttr(driver_attr, driven.offsetParentMatrix)
    # Make connections
    pm.connectAttr(driver_attr, decompose.inputMatrix, f=1)
    for attr in constants.TRNSFRMATTRS:
        pm.connectAttr(eval(f"decompose.output{attr.capitalize()}"), eval(f"driven.{attr}"), f=1)
    return decompose


def make_pick(driver, driven):
    """
    Creates a pickMatrix node between a defined pair of driver/driven nodes
    :param driver: the source node for the matrix data
    :param driven: the target node for the matrix data
    :return: the pickMatrix node that is created.
    """
    # Set variables and create pick node
    pick_name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["pick"])
    pick = utils.check_hypergraph_node(pick_name, "pickMatrix", shading=False)
    source = pm.listConnections(driven.offsetParentMatrix, p=1)[0]
    # Make connections
    pm.connectAttr(source, pick.inputMatrix, f=1)
    pm.connectAttr(pick.outputMatrix, driven.offsetParentMatrix, f=1)
    return pick


def make_constraint(driver, driven, translate=False, rotate=False, scale=False, shear=False,
                    frozen=False, offset=False, reset=False):
    """
    Uses a pickMatrix node to set up a constraint between a defined pair of driver/driven nodes and constrains
    a defined set of tranform attributes. The function can also account for frozen transforms, maintain offsets,
    and reset transforms of the driven node.
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param translate: bool: whether or not to constrain the translate attribute of the driven node
    :param rotate: bool: whether or not to constrain the rotate attribute of the driven node
    :param scale: bool: whether or not to constrain the scale attribute of the driven node
    :param shear: bool: whether or not to constrain the shear attribute of the driven node
    :param frozen: bool: if the driver node has frozen transforms
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    constrain(driver, driven, frozen=frozen, reset=reset)
    # Set pickMatrix constraint attributes
    pick = make_pick(driver, driven)
    if not translate:
        pick.useTranslate.set(0)
    if not rotate:
        pick.useRotate.set(0)
    if not scale:
        pick.useScale.set(0)
    if not shear:
        pick.useShear.set(0)
    if offset:
        # TODO: offset may be preserved by turning off inherit transforms!
        offset_constraint(pick, pick=True)
    return pick


def offset_constraint(target, pick=False):
    """
    Sets up a decompose/compose matrix pair with a set of plusMinusAverage nodes in between that subtract the
    source node's transform data to preserve the offset of the defined target node
    :param target: PyNode: the node receiving the transform data
    :param pick: bool: whether the target node is a pickMatrix node
    :return: tup, list: the created decompose/compose matrix pair and a list of the offset nodes
    """
    # Get the decompose/compose matrix pair
    dec = decompose_constraint(target, pick)
    offsets = []
    for attr in constants.TRNSFRMATTRS:
        # Create the offset node and set the transform variables
        suffix = constants.get_attr_suffix(attr)
        offset = utils.check_hypergraph_node(dec[0].name().replace("_dec", f"{suffix}_offset"), "plusMinusAverage")
        offset_val = eval(f"dec.output{attr.capitalize()}.get()")
        if attr == "scale":
            offset_val = offset_val + 1
        # Make connections
        offset.input3D[1].set(offset_val)
        offset.operation.set(2)
        pm.connectAttr(eval(f"dec[0].output{attr.capitalize()}"), offset.input3D[0], f=1)
        pm.connectAttr(offset.output3D, eval(f"dec[1].input{attr.capitalize()}"), f=1)
        offsets.append(offset)
    return dec, offsets


def offset_driven(driver, driven):
    """
    Creates a multMatrix node to preserve the offset on a defined driver/driven pair
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :return: PyNode: the multMatrix node creating the offset
    """
    # Set the variables and create the multMatrix node controlling the offset
    mult_name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["mult"])
    mult = utils.check_hypergraph_node(mult_name, "multMatrix")
    parent = utils.get_parent_and_children(driven)[0]
    driven_mtrx = om.MMatrix(driven.worldMatrix.get())
    driver_imtrx = om.MMatrix(driver.worldInverseMatrix.get())
    # Set and connect attributes
    mult.matrixIn[0].set(driven_mtrx * driver_imtrx)
    pm.connectAttr(driver.worldMatrix[0], mult.matrixIn[1], f=1)
    if parent is not None:
        pm.connectAttr(parent.inverseMatrix[0], mult.matrixIn[2], f=1)
    pm.connectAttr(mult.matrixSum, driven.offsetParentMatrix, f=1)
    return mult


def orient_constraint(driver, driven, offset=False, reset=False):
    """
    Uses matrix functionality to create a more direct orient constraint
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    pick = make_constraint(driver, driven, rotate=True, offset=offset, reset=reset)
    return pick


def parent_constraint(driver, driven, frozen=False, offset=False, reset=False):
    """
    Uses matrix functionality to create a more direct parent constraint
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param frozen: bool: if the driver node has frozen transforms
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    constrain(driver, driven, offset, reset)
    pick = make_constraint(driver, driven, translate=True, rotate=True, scale=True, shear=True,
                           frozen=frozen, offset=offset, reset=reset)
    return pick


def point_constraint(driver, driven, frozen=False, offset=False, reset=False):
    """
    Uses matrix functionality to create a more direct point constraint
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param frozen: bool: if the driver node has frozen transforms
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    pick = make_constraint(driver, driven, frozen=frozen, translate=True, offset=offset, reset=reset)
    return pick


def scale_constraint(driver, driven, offset=False, reset=False):
    """
    Uses matrix functionality to create a more direct scale constraint
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    pick = make_constraint(driver, driven, scale=True, offset=offset, reset=reset)
    return pick


def shear_constraint(driver, driven, offset=False, reset=False):
    """
    Uses matrix functionality to create a more direct orient constraint
    :param driver: PyNode: the source node driving the driven node
    :param driven: PyNode: the target node being controlled by the driver node
    :param offset: bool: whether or not to preserve the offset of the driven node
    :param reset: bool: whether or not to reset the transforms of the driven node
    :return: PyNode: the pickMatrix node controlling the constraints
    """
    pick = make_constraint(driver, driven, shear=True, offset=offset, reset=reset)
    return pick


def worldspace_to_matrix(source, target):
    """
    Queires the world matrix position of a defined source node and applies it to the offsetParentMatrix of
    a defined target node.
    This is an older function that probably needs to account for frozen transforms in the source node
    :param source: PyNode: the node whose matrix position is being queried
    :param target: PyNode: the node receiving the matrix position data
    """
    if int(pm.about(v=1)) >= 2020:
        target.offsetParentMatrix.set(pm.xform(source, q=1, ws=1, m=1))
    else:
        pm.matchTransform(target, source)

