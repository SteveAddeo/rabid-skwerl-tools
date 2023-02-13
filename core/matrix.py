import pymel.core as pm

from core import utils


def matrix_constraint(driver, driven, maintain_rotation=True, maintain_offset=False):
    parent = utils.get_parent_and_children(driven)[0]
    if parent is not None:
        name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["mtrx"])
        mult = utils.check_hypergraph_node(name, "multMatrix")
        pm.connectAttr(driver.worldMatrix[0], mult.matrixIn[0], f=1)
        pm.connectAttr(parent.parentInverseMatrix[0], mult.matrixIn[1], f=1)
        pm.connectAttr(mult.matrixSum, driven.offsetParentMatrix, f=1)
    else:
        mult = None
        pm.connectAttr(driver.worldMatrix[0], driven.offsetParentMatrix, f=1)
    utils.reset_transforms([driven], m=False)
    if maintain_rotation and driven.type() == "joint":
        utils.transfer_offset_to_orient([driven])
    if maintain_offset:
        # TODO: get maintain offset work with compose and decompose matrix. Possibly a maintain offset function
        print("Coming Soon: maintain offset using compose and decompose matrix nodes")
    return mult


def matrix_constrain_transform(driver, driven, maintain_rotation=True, maintain_offset=False,
                               translate=True, rotate=True, scale=False):
    mult = matrix_constraint(driver, driven, maintain_rotation, maintain_offset)
    dec = utils.check_hypergraph_node(mult.name().replace("_mtrx", "_dec"), "decomposeMatrix", shading=False)
    comp = utils.check_hypergraph_node(mult.name().replace("_mtrx", "_comp"), "composeMatrix", shading=False)
    if translate:
        pm.connectAttr(dec.outputTranslate, comp.inputTranslate, f=1)
    if rotate:
        pm.connectAttr(dec.outputRotate, comp.inputRotate, f=1)
    if scale:
        pm.connectAttr(dec.outputScale, comp.inputScale, f=1)
    pm.connectAttr(mult.matrixSum, dec.inputMatrix, f=1)
    pm.connectAttr(comp.outputMatrix, driven.offsetParentMatrix, f=1)
    return mult, dec, comp


def worldspace_to_matrix(obj, source):
    if int(pm.about(v=1)) >= 2020:
        mtrx = pm.xform(source, q=1, ws=1, m=1)
        pm.setAttr("{}.offsetParentMatrix".format(obj), mtrx)
        return mtrx
    else:
        pm.matchTransform(obj, source)

