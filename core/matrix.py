import pymel.core as pm

from core import utils


def matrix_constraint(driver, driven, maintain_rotation=True, maintain_offset=False):
    parent = utils.get_parent_and_children(driven)[0]
    if parent is not None:
        name = "_".join(driver.name().split("_")[:-1] + ["to"] + driven.name().split("_")[:-1] + ["mtrx"])
        mult = utils.check_shading_node(name, "multMatrix")
        pm.connectAttr(driver.worldMatrix[0], mult.matrixIn[0], f=1)
        pm.connectAttr(parent.parentInverseMatrix[0], mult.matrixIn[1], f=1)
        pm.connectAttr(mult.matrixSum, driven.offsetParentMatrix, f=1)
    else:
        mult = None
        pm.connectAttr(driver.worldMatrix[0], driven.offsetParentMatrix, f=1)
    utils.reset_transforms([driven], m=False)
    if maintain_rotation and driven.type == "joint":
        utils.transfer_offset_to_orient([driven])
    if maintain_offset:
        # TODO: get maintain offset work with compose and decompose matrix. Possibly a maintain offset function
        print("Coming Soon: maintain offset using compose and decompose matrix nodes")
    return mult


def worldspace_to_matrix(obj, source):
    if int(pm.about(v=1)) >= 2020:
        mtrx = pm.xform(source, q=1, ws=1, m=1)
        pm.setAttr("{}.offsetParentMatrix".format(obj), mtrx)
        return mtrx
    else:
        pm.matchTransform(obj, source)

