import pymel.core as pm

from core import constants
from core import utils
from core import matrix
from ctls import controls
from rigs import ik
from rigs import stretch


def make_spline_control_joints(joint, curve, span="upper", splits=1, const_node=None):
    """
    Create the joints that drive a spline curve and will eventually be driven by a control
    :param joint: PyNode: base joint driving the overall rig (typically the Driver Joint)
    :param curve: PyNode: the spline curve being driven by joints
    :param span: str: the span name of the section you are creating joints for
    :param splits: int: number of joint in between the ones at the top and bottom of the curve
    :param const_node: PyNode: Used if any axes are constrained (typically a Twist Joint)
    :return: list: control joints that were created
    """
    # Create the outliner group to store the nodes this process creates
    name = f"{utils.get_info_from_joint(joint, name=True)}_{span}_ctl_jnt"
    grp = utils.make_group(
        f"{name}_grp", parent=utils.make_group(
            f"{utils.get_info_from_joint(joint, name=True)}_ctl_jnt_grp", parent=utils.make_group(
                "ctl_jnt_grp", parent=utils.make_group("jnt_grp"))))
    pm.xform(grp, t=pm.xform(joint, q=1, ws=1, rp=1))
    # Check variables
    if splits < 0:
        splits = -splits
    if splits > 1:
        pm.rebuildCurve(curve, s=curve.spans.get())
    if const_node is not None:
        matrix.matrix_constraint(const_node, grp)
    else:
        matrix.matrix_constraint(joint, grp)
    # Create control joints
    ctlJnts = []
    for i in range(splits + 2):
        jnt = utils.duplicate_chain([joint], "ctl", grp)[0]
        pm.rename(jnt, name.replace("_ctl", f"ctl{str(i+1).zfill(2)}"))
        jnt.radius.set(jnt.radius.get() * 2)
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


def make_spline_twist(jnt_chain, curve, handle, index=0, twist_jnt=None):
    """
    Uses a list of joints to drive an advanced spline twist setup. Can either be used for a single-span
    chain like a neck, spine, or tail, or in a multi span chain like an arm or leg.
    :param jnt_chain: list: the joints driving the twist
    :param curve: PyNode: the curve driving the spline
    :param handle: PyNode: the IK handle with the twist attribute
    :param index: int: the iteration integer of the function (used in for loops)
    :param twist_jnt: PyNode: defined if the spline chain has a twist joint
    """
    # TODO: doesn't appear to work on mirrored joints.
    #  May have to add a negative multiplier for mirrored joints
    # Set the twist attributes in the handle
    handle.dTwistControlEnable.set(1)
    handle.dWorldUpType.set(3)
    handle.dTwistValueType.set(1)
    # Make the connections
    if index == 0 and len(jnt_chain) > 2:
        if twist_jnt is None:
            twist_jnt = jnt_chain[0]
        pm.connectAttr(twist_jnt.worldMatrix[0], handle.dWorldUpMatrix)
        addNode = utils.check_hypergraph_node(curve.name().replace("_crv", "_add"), "addDoubleLinear")
        pm.connectAttr(jnt_chain[index].rotateX, addNode.input1)
        pm.connectAttr(jnt_chain[index + 1].rotateX, addNode.input2)
        pm.connectAttr(addNode.output, handle.dTwistEnd)
    else:
        pm.connectAttr(jnt_chain[index].worldMatrix[0], handle.dWorldUpMatrix)
        pm.connectAttr(jnt_chain[index + 1].rotateX, handle.dTwistEnd)


def make_split_spline(jnt_chain, twist_jnt=None, chain_type="spline", splits=3):
    """
    Creates a new "split" joint chain that has a stretchy splike IK and control joints.
    :param jnt_chain: list: joint chain that is acting as the base (typically the driver joint
    :param twist_jnt: PyNode: looks for a twist joint and, if none provided assigns the base joint
    :param chain_type: str:
    :param splits: int: number of mid joints between the base and tip of a joint span
    :return:
    """
    if twist_jnt is None:
        twist_jnt = jnt_chain[0]
    splnJnts = utils.split_chain(jnt_chain, chain_type, 3)
    allCtlJnts = []
    hndlGrp = utils.make_group(f"{utils.get_info_from_joint(jnt_chain[0], name=True)}_hndl_grp",
                               parent=utils.make_group("hndl_grp", parent=utils.make_group("utils_grp")))
    for i, jnt in enumerate(jnt_chain[:-1]):
        # Create a spline setup for each span of the chain
        if not i == len(jnt_chain[:-2]):
            # Make sure a chain isn't parented to the chain above it
            pm.parent(splnJnts[(i + 1) * (splits + 2)], pm.listRelatives(splnJnts[0], p=1)[0])
        # Set up the rig components
        span = constants.get_span(i, len(jnt_chain[:-1]))
        crv = utils.make_curve_from_chain(splnJnts[i * 5],
                                          name=f"{utils.get_info_from_joint(jnt, name=True)}_{span}_crv")
        pm.parent(pm.listRelatives(crv, p=1), utils.make_group(f"{utils.get_info_from_joint(jnt, name=True)}_crv_grp"))
        if not i:
            ctlJnts = make_spline_control_joints(jnt, crv, span, splits=1, const_node=twist_jnt)
        else:
            ctlJnts = make_spline_control_joints(jnt, crv, span, splits=1, const_node=jnt)
        allCtlJnts.append(ctlJnts)
        jnts = utils.get_joints_in_chain(splnJnts[i * 5])
        hndl = ik.make_handle(jnts[0], jnts[-1], name=crv.name().replace("_crv", "_hndl"),
                              solver="spline", spline_crv=crv)[0]
        pm.parent(hndl, hndlGrp)
        stretch.Build(utils.get_joints_in_chain(splnJnts[i * 5]), crv)
        make_spline_twist(jnt_chain, crv, hndl, i, twist_jnt)
    bendJnts = controls.make_limb_bend_control_joints(jnt_chain)
    for i, ctlJnts in enumerate(allCtlJnts[:-1]):
        connect_splines(bendJnts[i], ctlJnts[-1], allCtlJnts[i + 1][0], jnt_chain[i + 1])


def connect_splines(mid, upper, lower, lower_drive):
    """
    Uses matrix constraints and a bit of math to merge the ends of two chains and dirve it with a single joint
    :param mid: PyNode: joint that will connect both splines
    :param upper: PyNode: last joint controlling the upper spline
    :param lower: PyNode: first joint controlling the lower spline
    :param lower_drive: PyNode: the lower drive joint in the chain (needed for some offset math)
    :return:
    """
    matrix.matrix_constraint(mid, lower, maintain_rotation=True)
    upperMtrx = matrix.matrix_constraint(mid, upper, maintain_rotation=True)
    decMtrx = utils.check_hypergraph_node(
        upperMtrx.name().replace("_mtrx", "_dec_mtrx"), "decomposeMatrix", shading=False)
    compMtrx = utils.check_hypergraph_node(
        upperMtrx.name().replace("_mtrx", "_comp_mtrx"), "composeMatrix", shading=False)
    subtract = utils.check_hypergraph_node(f"{mid.name()}_driver_rot_min", "plusMinusAverage")
    subtract.operation.set(2)
    pm.connectAttr(upperMtrx.matrixSum, decMtrx.inputMatrix, f=1)
    pm.connectAttr(decMtrx.outputRotate, subtract.input3D[0], f=1)
    pm.connectAttr(lower_drive.rotate, subtract.input3D[1], f=1)
    pm.connectAttr(subtract.output3D, compMtrx.inputRotate, f=1)
    pm.connectAttr(decMtrx.outputScale, compMtrx.inputScale, f=1)
    pm.connectAttr(decMtrx.outputTranslate, compMtrx.inputTranslate, f=1)
    pm.connectAttr(compMtrx.outputMatrix, upper.offsetParentMatrix, f=1)
