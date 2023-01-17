import pymel.core as pm

from core import utils
from rigs import ik


def make_split_spline(jnt_chain, twist_jnt, splits=3):
    splnJnts = utils.split_chain(jnt_chain, "spline", 3)
    for i, jnt in enumerate(jnt_chain[:-1]):
        if not i == len(jnt_chain[:-2]):
            pm.parent(splnJnts[(i + 1) * (splits + 2)], pm.listRelatives(splnJnts[0], p=1)[0])
        crv = utils.make_curve_from_chain(splnJnts[i * 5],
                                          f"{'_'.join(splnJnts[i * 5].name().split('_')[:-2])[:-2]}_crv",
                                          bind=[jnt, jnt_chain[i + 1]])
        jnts = utils.get_joints_in_chain(splnJnts[i * 5])
        hndl = ik.make_handle(jnts[0], jnts[-1], name=crv.name().replace("_crv", "_hndl"),
                              solver="spline", spline_crv=crv)
        hndl[0].dTwistControlEnable.set(1)
        hndl[0].dWorldUpType.set(3)
        hndl[0].dTwistValueType.set(1)
        if i == 0:
            pm.connectAttr(twist_jnt.worldMatrix[0], hndl[0].dWorldUpMatrix)
