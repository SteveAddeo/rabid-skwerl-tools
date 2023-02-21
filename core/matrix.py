import pymel.core as pm
import maya.api.OpenMaya as om

from core import constants
from core import utils


def constrain(driver, driven, frozen=False, offset=False, reset=False):
    if frozen: # TODO: Check for frozen transforms and apply
        pm.move(driven, list(pm.dt.Vector()), rpr=1)
        # pm.makeIdentity(driven, a=1)
    pm.connectAttr(driver.worldMatrix[0], driven.offsetParentMatrix, f=1)
    if reset:
        utils.reset_transforms([driven], m=False)
    if offset:
        offset = offset_driven(driver, driven)
        return offset
    return None


def decompose_constraint(target, pick=False):
    if pick:
        source_attr = "inputMatrix"
    else:
        source_attr = "offsetParentMatrix"
    if pm.listConnections(eval(f"target.{source_attr}"))[0] == "composeMatrix":
        comp = pm.listConnections(eval(f"target.{source_attr}"))[0]
        dec = pm.PyNode(comp.name().replace("_comp", "_dec"))
        return dec, comp
    source = pm.listConnections(eval(f"target.{source_attr}"), p=1)[0]
    name = "_".join(source.name().split(".")[0].split("_")[:-1])
    dec = utils.check_hypergraph_node(f"{name}_dec", "decomposeMatrix", shading=False)
    comp = utils.check_hypergraph_node(f"{name}_comp", "composeMatrix", shading=False)
    pm.connectAttr(source, dec.inputMatrix)
    for attr in constants.TRNSFRMATTRS:
        pm.connectAttr(eval(f"dec.output{attr.capitalize()}"), eval(f"comp.input{attr.capitalize()}"), f=1)
    pm.connectAttr(comp.outputMatrix, eval(f"target.{source_attr}"), f=1)
    return dec, comp


def make_pick(driver, driven):
    pick_name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["pick"])
    pick = utils.check_hypergraph_node(pick_name, "pickMatrix", shading=False)
    source = pm.listConnections(driven.offsetParentMatrix, p=1)[0]
    pm.connectAttr(source, pick.inputMatrix, f=1)
    pm.connectAttr(pick.outputMatrix, driven.offsetParentMatrix, f=1)
    return pick


def make_constraint(driver, driven, translate=False, rotate=False, scale=False, shear=False,
                    frozen=False, offset=False, reset=False):
    constrain(driver, driven, frozen=frozen, reset=reset)
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
        offset_constraint(pick, pick=True)
    return pick


def offset_constraint(target, pick=False):
    dec = decompose_constraint(target, pick)
    offsets = []
    for attr in constants.TRNSFRMATTRS:
        suffix = constants.get_attr_suffix(attr)
        offset = utils.check_hypergraph_node(dec[0].name().replace("_dec", f"{suffix}_offset"), "plusMinusAverage")
        offset_val = eval(f"dec.output{attr.capitalize()}.get()")
        if attr == "scale":
            offset_val = offset_val + 1
        offset.input3D[1].set(offset_val)
        offset.operation.set(2)
        pm.connectAttr(eval(f"dec[0].output{attr.capitalize()}"), offset.input3D[0], f=1)
        pm.connectAttr(offset.output3D, eval(f"dec[1].input{attr.capitalize()}"), f=1)
        offsets.append(offset)
    return dec, offsets


def offset_driven(driver, driven):
    mult_name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["mult"])
    mult = utils.check_hypergraph_node(mult_name, "multMatrix")
    parent = utils.get_parent_and_children(driven)[0]
    driven_mtrx = om.MMatrix(driven.worldMatrix.get())
    driver_imtrx = om.MMatrix(driver.worldInverseMatrix.get())
    mult.matrixIn[0].set(driven_mtrx * driver_imtrx)
    pm.connectAttr(driver.worldMatrix[0], mult.matrixIn[1], f=1)
    if parent is not None:
        pm.connectAttr(parent.inverseMatrix[0], mult.matrixIn[2], f=1)
    pm.connectAttr(mult.matrixSum, driven.offsetParentMatrix, f=1)
    return mult


def orient_constraint(driver, driven, offset=False, reset=False):
    pick = make_constraint(driver, driven, rotate=True, offset=offset, reset=reset)
    return pick


def parent_constraint(driver, driven, frozen=False, offset=False, reset=False):
    constrain(driver, driven, offset, reset)
    pick = make_constraint(driver, driven, translate=True, rotate=True, scale=True, shear=True,
                           frozen=frozen, offset=offset, reset=reset)
    return pick


def point_constraint(driver, driven, frozen=False, offset=False, reset=False):
    pick = make_constraint(driver, driven, frozen=frozen, translate=True, offset=offset, reset=reset)
    return pick


def scale_constraint(driver, driven, offset=False, reset=False):
    pick = make_constraint(driver, driven, scale=True, offset=offset, reset=reset)
    return pick


def shear_constraint(driver, driven, offset=False, reset=False):
    pick = make_constraint(driver, driven, shear=True, offset=offset, reset=reset)
    return pick


def worldspace_to_matrix(source, target):
    if int(pm.about(v=1)) >= 2020:
        mtrx = pm.xform(source, q=1, ws=1, m=1)
        pm.setAttr(f"{target}.offsetParentMatrix", mtrx)
        return mtrx
    else:
        pm.matchTransform(target, source)

