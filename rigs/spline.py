import pymel.core as pm

from core import constants
from core import utils
from ctls import controls
from rigs import ik
from rigs import stretch


UPINDEX = {"X": 6, "Y": 0, "Z": 3}


# TODO: Spline and control joints still need to scale
# TODO: This module should have a Build() class

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
        pm.pointConstraint(const_node, grp)
    else:
        pm.pointConstraint(joint, grp)
    # Create control joints
    ctl_jnts = []
    for i in range(splits + 2):
        jnt = utils.duplicate_chain([joint], "ctl", grp)[0]
        pm.rename(jnt, name.replace("_ctl", f"_ctl{str(i+1).zfill(2)}"))
        jnt.radius.set(jnt.radius.get() * 2)
        pm.parent(jnt, w=1)
        pm.xform(jnt, t=pm.pointOnCurve(curve, pr=i/(splits + 1), top=1))
        pm.parent(jnt, grp)
        ctl_jnts.append(jnt)
    if splits:
        for i, midJnt in enumerate(ctl_jnts[1:-1]):
            mid_grp = utils.make_offset_groups([midJnt], reset=False)
            # TODO: will this work just as well with the matrix orient constraint?
            pm.orientConstraint(mid_grp, ctl_jnts[0])
            pt_const = pm.pointConstraint([ctl_jnts[0], ctl_jnts[-1]], mid_grp, mo=1)
            eval(f"pt_const.{ctl_jnts[0].name()}W0.set({1 - ((i + 1) / (splits + 1))})")
            eval(f"pt_const.{ctl_jnts[-1].name()}W1.set({(i + 1) / (splits + 1)})")
    utils.skin_to_joints(ctl_jnts, curve)
    return ctl_jnts


def make_spline_twist(jnt_chain, curve, handle, index=0, twist_jnt=None, invert=False):
    """
    Uses a list of joints to drive an advanced spline twist setup. Can either be used for a single-span
    chain like a neck, spine, or tail, or in a multi span chain like an arm or leg.
    :param jnt_chain: list: the joints driving the twist
    :param curve: PyNode: the curve driving the spline
    :param handle: PyNode: the IK handle with the twist attribute
    :param index: int: the iteration integer of the function (used in for loops)
    :param twist_jnt: PyNode: defined if the spline chain has a twist joint
    :param invert: bool: mirrored joints
    """
    twist_axis = str(jnt_chain[0].getRotationOrder())[0]
    up_axis = str(jnt_chain[0].getRotationOrder())[1]
    # Set the twist attributes in the handle
    handle.dTwistControlEnable.set(1)
    handle.dWorldUpType.set(3)
    handle.dForwardAxis.set(constants.AXES.index(twist_axis) * 2)
    handle.dWorldUpAxis.set(UPINDEX[up_axis])
    for i, v in enumerate(constants.get_axis_vector(up_axis)):
        eval(f"handle.dWorldUpVector{constants.AXES[i]}.set({v})")
    handle.dTwistValueType.set(1)
    # Make the connections
    if index == 0 and len(jnt_chain) > 2:
        if twist_jnt is None:
            twist_jnt = jnt_chain[0]
        pm.connectAttr(twist_jnt.worldMatrix[0], handle.dWorldUpMatrix)
        addNode = utils.check_hypergraph_node(curve.name().replace("_crv", "_add"), "addDoubleLinear")
        pm.connectAttr(eval(f"jnt_chain[index].rotate{twist_axis}"), addNode.input1)
        pm.connectAttr(eval(f"jnt_chain[index + 1].rotate{twist_axis}"), addNode.input2)
        pm.connectAttr(addNode.output, handle.dTwistEnd)
    else:
        pm.connectAttr(jnt_chain[index].worldMatrix[0], handle.dWorldUpMatrix)
        pm.connectAttr(jnt_chain[index + 1].rotateX, handle.dTwistEnd)
    # Inverted chains need the twist rotate value to be inverted as well
    if invert:
        utils.invert_attribute(handle.dTwistEnd)
        handle.dForwardAxis.set(handle.dForwardAxis.get() + 1)
        handle.dWorldUpAxis.set(handle.dWorldUpAxis.get() + 1)
        for i, v in enumerate(constants.get_axis_vector(up_axis, invert=True)):
            eval(f"handle.dWorldUpVector{constants.AXES[i]}.set({v})")


def make_split_spline(jnt_chain, twist_jnt=None, chain_type="spline", splits=3, invert=False):
    """
    Creates a new "split" joint chain that has a stretchy splike IK and control joints.
    :param jnt_chain: list: joint chain that is acting as the base (typically the driver joint
    :param twist_jnt: PyNode: looks for a twist joint and, if none provided assigns the base joint
    :param chain_type: str:
    :param splits: int: number of mid joints between the base and tip of a joint span
    :param invert: bool: mirrored joints need rotations inverted
    :return: list: the instantiated stretch classes of the chain.
    """
    if twist_jnt is None:
        twist_jnt = jnt_chain[0]
    spilne_jnts = utils.split_chain(jnt_chain, chain_type, 3)
    all_ctl_jnts = []
    hndl_grp = utils.make_group(f"{utils.get_info_from_joint(jnt_chain[0], name=True)}_hndl_grp",
                                parent=utils.make_group("hndl_grp", parent=utils.make_group("utils_grp")))
    stretch_obj_list = []
    for i, jnt in enumerate(jnt_chain[:-1]):
        # Create a spline setup for each span of the chain
        if not i == len(jnt_chain[:-2]):
            # Make sure a chain isn't parented to the chain above it
            pm.parent(spilne_jnts[(i + 1) * (splits + 2)], pm.listRelatives(spilne_jnts[0], p=1)[0])
        # Set up the rig components
        span = constants.get_span(i, len(jnt_chain[:-1]))
        crv = utils.make_curve_from_chain(spilne_jnts[i * 5],
                                          name=f"{utils.get_info_from_joint(jnt, name=True)}_{span}_crv")
        pm.parent(pm.listRelatives(crv, p=1), utils.make_group(f"{utils.get_info_from_joint(jnt, name=True)}_crv_grp"))
        if not i:
            ctl_jnts = make_spline_control_joints(jnt, crv, span, splits=1, const_node=twist_jnt)
            pm.pointConstraint(jnt, ctl_jnts[0])
        else:
            ctl_jnts = make_spline_control_joints(jnt, crv, span, splits=1, const_node=jnt)
        all_ctl_jnts.append(ctl_jnts)
        jnts = utils.get_joints_in_chain(spilne_jnts[i * 5])
        hndl = ik.make_handle(jnts[0], jnts[-1], name=crv.name().replace("_crv", "_hndl"),
                              solver="spline", spline_crv=crv)[0]
        pm.parent(hndl, hndl_grp)
        stretch_obj = stretch.Build(utils.get_joints_in_chain(spilne_jnts[i * 5]), crv)
        make_spline_twist(jnt_chain, crv, hndl, i, twist_jnt, invert)
        stretch_obj_list.append(stretch_obj)
    bend_jnts = controls.make_limb_bend_control_joints(jnt_chain)
    for i, ctl_jnts in enumerate(all_ctl_jnts):
        if i == len(all_ctl_jnts) - 1:
            connect_splines(jnt_chain[i + 1], ctl_jnts[-1])
        else:
            connect_splines(bend_jnts[i], ctl_jnts[-1], all_ctl_jnts[i + 1][0])
    return stretch_obj_list


def connect_splines(mid, upper, lower=None):
    """
    Uses matrix constraints and a bit of math to merge the ends of two chains and dirve it with a single joint
    :param mid: PyNode: joint that will connect both splines
    :param upper: PyNode: last joint controlling the upper spline
    :param lower: PyNode: first joint controlling the lower spline
    :return:
    """
    aim = str(mid.getRotationOrder())[0]
    # pm.connectAttr(eval(f"mid.scale{aim}"), eval(f"upper.scale{aim}"), f=1)
    if lower is not None:
        pm.pointConstraint(mid, lower)
        # pm.connectAttr(eval(f"mid.scale{aim}"), eval(f"lower.scale{aim}"), f=1)
    pm.pointConstraint(mid, upper)
    pm.connectAttr(eval(f"mid.scale{aim}"), eval(f"upper.scale{aim}"), f=1)
