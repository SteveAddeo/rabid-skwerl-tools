import pymel.core as pm

from core import constants
from core import utils


def orient_joint(joint, aim_obj, up_obj=None, local=False, neg=False, mirror=False):
    """
    Uses an aim constraint to orient a joint.
    :param joint: joint to orient
    :param aim_obj: object for joint to aim at
    :param up_obj: object to orient the joint up to
    :param local: if True, orient the joint in local space
    :param neg: if True, orient the joint to the negative of the up vector
    :param mirror: if True, orient the joint to the mirror of the aim vector
    """
    roo = str(joint.getRotationOrder())
    up = constants.get_axis_vector(roo[1].capitalize(), invert=mirror)
    aim = constants.get_axis_vector(roo[0].capitalize(), invert=mirror)
    if local:
        up = [-v for v in constants.get_axis_vector(roo[2], invert=mirror)]
    if neg:
        up = [-v for v in up]
    if up_obj is None:
        aimConst = pm.aimConstraint([aim_obj], joint, aim=aim, u=up, wut="vector")
    else:
        aimConst = pm.aimConstraint([aim_obj], joint, aim=aim, u=up, wut="object", wuo=up_obj)
    pm.delete(aimConst)
    pm.makeIdentity(joint, a=1)


def base_joint(joint, jnt_list, to_world=True, chain_to_world=False, neg=False, mirror=False):
    """
    Uses an aim constraint to orient the base joint in a chain
    :param joint: joint to orient
    :param jnt_list: list of joints to orient
    :param to_world: if True, orient the joint in world space
    :param chain_to_world: if True, orient all the joints in the chain in world space
    :param neg: if True, orient the joint to the negative of the up vector
    :param mirror: if True, orient the joint to the mirror of the aim vector
    """
    if to_world:
        orient_joint(joint, jnt_list[1], neg=neg, mirror=mirror)
    if chain_to_world:
        orient_joint(joint, jnt_list[1], local=True, neg=neg, mirror=mirror)
    else:
        orient_joint(joint, jnt_list[1], jnt_list[2], neg=neg, mirror=mirror)


def mid_joints(joint, i, jnt_list, to_world=False, neg=False, mirror=False):
    """
    Uses an aim constraint to orient the mid joints in a chain
    :param joint: joint to orient
    :param i: index of the first joint in the chain
    :param jnt_list: list of joints to orient
    :param to_world: if True, orient the joint in world space
    :param neg: if True, orient the joint to the negative of the up vector
    :param mirror: if True, orient the joint to the mirror of the aim vector
    """
    # Center Chains align to World Up
    if to_world:
        orient_joint(joint, jnt_list[i + 1], neg=neg, mirror=mirror)
    else:
        orient_joint(joint, jnt_list[i + 1], jnt_list[i - 1], neg=neg, mirror=mirror)
    pm.parent(joint, jnt_list[i - 1])


def tip_joint(joint, prev_jnt=None, to_joint=True):
    """
    Uses an aim constraint to orient the tip joint in a chain
    :param joint: joint to orient
    :param prev_jnt: previous joint in the chain
    :param to_joint: if True, orient the joint to the rest of the chain
    """
    if prev_jnt is None and pm.listRelatives(joint, p=1):
        pm.parent(joint, w=1)
    # Orient tip to World or local
    if not to_joint:
        pm.xform(joint, ws=1, ro=(0, 0, 0))
        pm.makeIdentity(joint, a=1)
    pm.parent(joint, prev_jnt)
    if to_joint:
        utils.reset_transforms([joint], t=False, r=False, s=False, m=False, o=True)


def joints_in_chain(joints=None, orient_tip=True, group=None,
                    base_to_world=True, chain_to_world=False, neg=False, mirror=False):
    """
    Uses an aim constraint to orient all the joints in a chain
    :param joints: list of joints to orient
    :param orient_tip: if True, orient the tip joint to the rest of the chain
    :param group: the group the chain is parented to
    :param base_to_world: if True, orient the base joint in world space
    :param chain_to_world: if True, orient the chain in world space
    :param neg: if True, orient the joint to the negative of the up vector
    :param mirror: if True, orient the joint to the mirror of the aim vector
    """
    if joints is None:
        if not pm.ls(sl=1) or pm.ls(sl=1)[0].type() != "joint":
            pm.error("Joint not selected")
        joints = utils.get_joints_in_chain(pm.ls(sl=1)[0])
    # Unparent all joints before orienting
    for jnt in joints:
        if pm.listRelatives(jnt, p=1):
            pm.parent(jnt, w=1)
    # Orient Joints
    for i, jnt in enumerate(joints):
        # Set orientation for the Base Joint
        if i == 0:
            base_joint(jnt, jnt_list=joints, to_world=base_to_world,
                       chain_to_world=chain_to_world, neg=neg, mirror=mirror)
        # Set orientation for the Tip Joint
        elif i == len(joints) - 1:
            tip_joint(jnt, joints[i - 1], to_joint=orient_tip)
        # Set orientation for all joints in between
        else:
            mid_joints(jnt, i, jnt_list=joints, to_world=chain_to_world, neg=neg, mirror=mirror)
    if group is not None:
        pm.xform(group, t=pm.xform(joints[0], q=1, ws=1, rp=1))
        pm.parent(joints[0], group)
