import pymel.core as pm


def worldspace_to_matrix(obj, source):
    if int(pm.about(v=1)) >= 2020:
        mtrx = pm.xform(source, q=1, ws=1, m=1)
        pm.setAttr("{}.offsetParentMatrix".format(obj), mtrx)
        return mtrx
    else:
        pm.matchTransform(obj, source)

