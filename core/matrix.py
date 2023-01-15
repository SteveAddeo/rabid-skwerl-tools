import pymel.core as pm
from core import utils


def matrix_constraint(driver, driven):
    parent = utils.get_parent_and_children(driven)[0]
    if parent is not None:
        mult = pm.shadingNode("multMatrix", n=driver.name().replace(driver.name().split("_")[-1], "mtrx"), au=1)
        pm.connectAttr(driver.worldMatrix[0], mult.matrixIn[0], f=1)
        pm.connectAttr(parent.parentInverseMatrix[0], mult.matrixIn[1], f=1)
        pm.connectAttr(mult.matrixSum, driven.offsetParentMatrix, f=1)
    else:
        pm.connectAttr(driver.worldMatrix[0], driven.offsetParentMatrix, f=1)
    # TODO: this works so far but it offsets the driven. Transform data needs
    #  to be cleared (including joint orientation data if applicable) and
    #  object needs to be repositioned.
    utils.reset_transforms(driven, m=False)


def worldspace_to_matrix(obj, source):
    if int(pm.about(v=1)) >= 2020:
        mtrx = pm.xform(source, q=1, ws=1, m=1)
        pm.setAttr("{}.offsetParentMatrix".format(obj), mtrx)
        return mtrx
    else:
        pm.matchTransform(obj, source)

