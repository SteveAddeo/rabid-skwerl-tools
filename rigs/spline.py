import pymel.core as pm

from core import utils
from core import matrix
from rigs import ik


def make_spline_control_joints(joint, curve, splits=1, const_node=None):
    """
    Create the joints that drive a spline curve and will eventually be driven by a control
    :param joint: PyNode: base joint driving the overall rig (typically the Driver Joint)
    :param curve: PyNode: the spline curve being driven by joints
    :param splits: int: number of joint in between the ones at the top and bottom of the curve
    :param const_node: PyNode: Used if any axes are constrained (typically a Twist Joint)
    :return: list: control joints that were created
    """
    # Create the outliner group to store the nodes this process creates
    grp = utils.make_group(f"{joint.name().replace(utils.get_joint_type(joint), 'ctl')}_grp",
                           parent=utils.make_group(
                               f"{utils.get_info_from_joint(joint, name=True)}_ctl_jnt_grp",
                               parent=utils.make_group(
                                                       f"{utils.get_info_from_joint(joint, name=True)}_ctl_grp",
                                                       parent=utils.make_group("ctl_grp"))))
    pm.xform(grp, t=pm.xform(joint, q=1, ws=1, rp=1))
    if splits < 0:
        splits = -splits
    if splits > 1:
        pm.rebuildCurve(curve, s=curve.spans.get())
    if const_node is not None:
        matrix.matrix_constraint(const_node, grp)
    else:
        matrix.matrix_constraint(joint, grp)
    ctlJnts = []
    for i in range(splits + 2):
        jnt = utils.duplicate_chain([joint], f"ctl{str(i+1).zfill(2)}", grp)[0]
        jnt.radius.set(jnt.radius.get() * 4)
        pm.parent(jnt, w=1)
        pm.xform(jnt, t=pm.pointOnCurve(curve, pr=i/(splits + 1), top=1))
        pm.parent(jnt, grp)
        ctlJnts.append(jnt)
    if splits:
        for i, midJnt in enumerate(ctlJnts[1:-1]):
            midGrp = utils.make_offset_groups([midJnt], reset=False)
            pConst = pm.parentConstraint([ctlJnts[0], ctlJnts[-1]], midGrp, mo=1)
            eval(f"pConst.{ctlJnts[0].name()}W0.set({1 - ((i + 1) / (splits + 1))})")
            eval(f"pConst.{ctlJnts[-1].name()}W1.set({(i + 1) / (splits + 1)})")
    utils.skin_to_joints(ctlJnts, curve)
    return ctlJnts


def make_split_spline(jnt_chain, twist_jnt=None, splits=3):
    """
    Creates a new "split" joint chain that has a stretchy splike IK and control joints.
    :param jnt_chain: list: joint chain that is acting as the base (typically the driver joint
    :param twist_jnt: looks for a twist joint and, if none provided assigns the base joint
    :param splits: number of mid joints between the base and tip of a joint span
    :return:
    """
    if twist_jnt is None:
        twist_jnt = jnt_chain[0]
    splnJnts = utils.split_chain(jnt_chain, "spline", 3)
    for i, jnt in enumerate(jnt_chain[:-1]):
        if not i == len(jnt_chain[:-2]):
            pm.parent(splnJnts[(i + 1) * (splits + 2)], pm.listRelatives(splnJnts[0], p=1)[0])
        crv = utils.make_curve_from_chain(splnJnts[i * 5],
                                          name=f"{'_'.join(splnJnts[i * 5].name().split('_')[:-2])[:-2]}_crv",
                                          bind=[jnt, jnt_chain[i + 1]])
        jnts = utils.get_joints_in_chain(splnJnts[i * 5])
        hndl = ik.make_handle(jnts[0], jnts[-1], name=crv.name().replace("_crv", "_hndl"),
                              solver="spline", spline_crv=crv)
        if not i:
            ctlJnts = make_spline_control_joints(jnt, crv, splits=1, const_node=twist_jnt)
        else:
            ctlJnts = make_spline_control_joints(jnt, crv, splits=1, const_node=jnt)
        hndl[0].dTwistControlEnable.set(1)
        hndl[0].dWorldUpType.set(3)
        hndl[0].dTwistValueType.set(1)
        if i == 0:
            pm.connectAttr(twist_jnt.worldMatrix[0], hndl[0].dWorldUpMatrix)
    # TODO: create a joint at the overlap point to act as the true control joint there (may need to be new function)
