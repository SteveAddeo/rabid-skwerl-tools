import os
import pymel.core as pm

from core import constants
from core import matrix
from core import utils


SHAPES = utils.get_data_from_json(os.path.join(utils.RSTPATH, "rabid-skwerl-tools", "ctls", "shapes.json"))


###################
# Joints
###################

def make_limb_bend_control_joints(jnts):
    grp = utils.make_group(
        f"{utils.get_info_from_joint(jnts[0], name=True)}_ctl_jnt_grp", parent=utils.make_group(
            "ctl_jnt_grp", parent=utils.make_group("jnt_grp")))
    ctlJnts = []
    name = f"{utils.get_info_from_joint(jnts[0], name=True)}_mid_ctl_jnt"
    for i, jnt in enumerate(jnts[1:-1]):
        if len(jnts) > 3:
            name = name.replace(name.split("_")[-3], f"mid{str(i+1).zfill(2)}")
        ctlJntGrp = utils.make_group(f"{name}_grp", parent=grp)
        ctlJnt = utils.duplicate_chain([jnt], "ctl", ctlJntGrp)[0]
        pm.rename(ctlJnt, name)
        ctlJnt.radius.set(ctlJnt.radius.get() * 4)
        # TODO: a warning is being thrown here. It looks like this part of the code is
        #  running multiple times not a big deal
        matrix.parent_constraint(jnt, ctlJntGrp)
        utils.reset_transforms([ctlJntGrp], m=False)
        pm.parent(ctlJnt, ctlJntGrp)
        utils.reset_transforms([ctlJnt], m=False)
        ctlJnts.append(ctlJnt)
    return ctlJnts


###################
# Shapes
###################

def make_shape(name=None, scale=10.0, shape="Cube", rot90=False, mirror_x=False):
    if name is None:
        name = f"{shape.lower()}_ctl1"
    points = SHAPES[shape]
    if mirror_x:
        points = [[-axis for axis in point] for point in points]
    if rot90:
        points = [[point[2], point[1], point[0]] for point in points]
    ptsScaled = [[axis * scale for axis in point] for point in points]
    ctl = pm.curve(n=name, d=1, p=ptsScaled)
    pm.delete(ctl, ch=1)
    return ctl


def make_circle(name=None, scale=10.0, aim="X"):
    if name is None:
        name = "circle_ctl1"
    aimAxis = constants.get_axis_vector(aim)
    radius = scale * .3
    ctl = pm.circle(n=name, nr=aimAxis, r=radius)[0]
    pm.delete(ctl, ch=1)
    return ctl


def make_cog(name=None, scale=10.0, aim="Y"):
    ctl = make_shape(name, scale, "COG")
    if aim == "X":
        pm.xform(ctl, ro=[0, 0, 90])
    if aim == "Z":
        pm.xform(ctl, ro=[90, 0, 0])
    pm.makeIdentity(ctl, a=1)
    return ctl


def make_cube(name=None, scale=10.0, length=None, aim="X", mirror=False):
    ctl = make_shape(name, scale, "Cube", mirror_x=mirror)
    if aim == "Y":
        pm.xform(ctl, ro=[0, 0, 90])
    if aim == "Z":
        pm.xform(ctl, ro=[0, -90, 0])
    if length is not None:
        resize_cube(ctl, length, aim)
    pm.makeIdentity(ctl, a=1)
    return ctl


def resize_cube(cube, length, aim="X"):
    cvList = ["{}.cv[{}]".format(str(cube), i) for i in range(
        pm.getAttr("{}.spans".format(cube)) + 1) if i in [0, 1, 4, 5, 8, 9, 10, 13]]
    for i, cv in enumerate(cvList):
        offset = pm.xform(cv, ws=1, t=1, q=1)
        if i == 0 and offset[constants.get_axis_index(aim)] < 0:
            length = -length
        offset[constants.get_axis_index(aim)] = length
        pm.xform(cv, ws=1, t=offset)


def make_gimbal(name=None, scale=10.0, aim="X", angle="Z", invert=False):
    if name is None:
        name = "gimbal_ctl1"
    aimAxis = constants.get_axis_vector(aim)
    angleAxis = [item for item in constants.get_axis_vector(angle)]
    if invert:
        angleAxis = [-item for item in angleAxis]
    radius = scale * .35
    cir = pm.circle(r=radius, nr=aimAxis)[0]
    subCir = pm.circle(c=[item * radius for item in angleAxis], nr=aimAxis, r=radius * .25)[0]
    ctl = utils.parent_crv(name, [subCir, cir])
    pm.delete(ctl, ch=1)
    return ctl


def make_icon(name=None, icon_type="FK", scale=10.0, aim="Z"):
    if name is None:
        name = "{}_dsp1".format(icon_type.lower())
    if icon_type == "IK":
        fi = make_shape("i", scale, "I")
    else:
        fi = make_shape("f", scale, "F")
    k = make_shape("k", scale, "K")
    icon = utils.parent_crv(name, [k, fi])
    pm.xform(icon, cp=1)
    pm.move(icon, [0, 0, 0], rpr=1)
    if aim == "X":
        pm.xform(icon, ro=[0, 90, 0])
    if aim == "Y":
        pm.xform(icon, ro=[0, 0, 90])
    pm.makeIdentity(icon, a=1)
    return icon


def make_pin(name=None, scale=10.0, aim="X", up="Y", invert=False):
    if name is None:
        name = "pin_ctl1"
    aimAxis = constants.get_axis_vector(aim)
    upAxis = [item for item in constants.get_axis_vector(up)]
    if invert:
        upAxis = [-item for item in upAxis]
    length = scale * .3
    radius = scale * .1
    center = [item * (length + radius) for item in upAxis]
    curve = pm.curve(d=1, p=([0, 0, 0], [item * length for item in upAxis]))
    circle = pm.circle(c=center, nr=aimAxis, r=radius)[0]
    ctl = utils.parent_crv(name, [circle, curve])
    pm.delete(ctl, ch=1)
    return ctl


def make_rhombus(name=None, scale=10.0):
    ctl = make_shape(name, scale, "Rhombus")
    return ctl


def make_sphere(name=None, scale=10.0):
    if name is None:
        name = "sphere_ctl1"
    radius = scale * .2
    crv1 = pm.circle(nr=[1, 0, 0], r=radius)
    crv2 = pm.circle(nr=[0, 1, 0], r=radius)
    crv3 = pm.circle(nr=[0, 0, 1], r=radius)
    ctl = utils.parent_crv(name, [crv3[0], crv2[0], crv1[0]])
    pm.delete(ctl, ch=1)
    return ctl


def make_spline(name=None, scale=10.0, aim="X", up="Y", invert=False):
    ctl = make_shape(name, scale, "Spline")
    rotation = [0, 0, 0]
    if up == "X" or aim == "Y":
        rotation[2] = -90
    if up == "Z":
        rotation[0] = 90
    if aim == "Z":
        rotation[1] = 90
    if invert:
        rotation = [-axis for axis in rotation]
    pm.xform(ctl, ro=rotation)
    pm.makeIdentity(ctl, a=1)
    return ctl


def make_square(name=None, scale=10.0, aim="X"):
    if name is None:
        name = "square_ctl1"
    vector = [1, 1, 1]
    vector[constants.get_axis_index(aim)] = 0
    indexes = [x for i, x in enumerate(range(3)) if not i == constants.get_axis_index(aim)]
    ptVector = [v * (scale * .3) for v in vector]
    ctl = pm.curve(n=name, d=1, p=[ptVector, [-v if i == indexes[0] else v for i, v in enumerate(ptVector)], [
        -v for v in ptVector], [-v if i == indexes[1] else v for i, v in enumerate(ptVector)], ptVector])
    pm.delete(ctl, ch=1)
    return ctl


def make_trs(name=None, scale=10.0, aim="Y"):
    if name is None:
        name = "trs_ctl"
    outer = make_shape("trs_outerRing", scale, "TRS")
    circle = pm.circle(n="trs_innerRing", nr=[0, 1, 0], r=1.9 * scale)[0]
    lt = make_shape("trs_ltArrow", scale, "TRS Arrow")
    rt = make_shape("trs_rtArrow", scale, "TRS Arrow", mirror_x=True)
    up = make_shape("trs_upArrow", scale, "TRS Arrow", rot90=True)
    dn = make_shape("trs_dnArrow", scale, "TRS Arrow", rot90=True, mirror_x=True)
    ctl = utils.parent_crv(name, [circle, lt, rt, up, dn, outer])
    if aim == "X":
        pm.xform(ctl, ro=[0, 0, 90])
    if aim == "Z":
        pm.xform(ctl, ro=[90, 0, 0])
    pm.makeIdentity(ctl, a=1)
    return ctl


def make_fkik(name=None, scale=10.0, aim="Z"):
    if name is None:
        name = "fkik_ctl1"
    fk = make_icon("{}_fk".format(name.split("_")[0]), icon_type="FK", scale=(scale * .3), aim=aim)
    ik = make_icon("{}_ik".format(name.split("_")[0]), icon_type="IK", scale=(scale * .3), aim=aim)
    fkShapes = fk.getShapes()
    ikShapes = ik.getShapes()
    box = make_shape("{}_ik".format(name.split("_")[0]), scale=(scale * .3), shape="FKIK Box")
    if aim == "X":
        i = 1
        pm.xform(box, ro=[0, 90, 0])
        pm.makeIdentity(box, a=1)
    elif aim == "Y":
        i = 2
        pm.xform(box, ro=[90, 0, 0])
        pm.makeIdentity(box, a=1)
    else:
        i = 1
    lineBase = [0, 0, 0]
    lineTip = [0, 0, 0]
    lineBase[i] = scale * -.13423841468
    lineTip[i] = scale * -.3
    line = pm.curve(n="line", d=1, p=[lineBase, lineTip])
    lineShapes = line.getShapes()
    ctl = utils.parent_crv(name, [line, fk, ik, box])
    return [ctl, fkShapes, ikShapes, lineShapes]


###################
# Rig Setups
###################

def make_global_controls(scale=10):
    # Create Controls and groups
    trs = make_trs("global_ctl", scale)
    loc = make_circle("loc_ctl", 3*scale, aim="Y")
    cog = make_cog("root_ctl", .6 * scale)
    grp = utils.make_group("global_ctl_grp", trs)
    utils.make_group("ctl_grp", grp)
    pm.parent(cog, loc)
    pm.parent(loc, trs)
    # Set the rotation order and lock the X & Z scale axis to the Y df each controls
    ctls = [trs, loc, cog]
    for ctl in ctls:
        ctl.rotateOrder.set(2)
        pm.connectAttr(ctl.scalY, ctl.scaleX)
        pm.connectAttr(ctl.scaleY, ctl.scaleX)
        # Color the shape nodes
        for shape in ctl.getShapes():
            shape.overrideEnabled.set(1)
            shape.overrideColor.set(17)
    # Add scale multipliers to scale the driver joints and
    gMult = pm.shadingNode("multDoubleLinear", n="global_scale_mult", au=1)
    lMult = pm.shadingNode("multDoubleLinear", n="local_scale_mult", au=1)
    # Connect the nodes
    pm.connectAttr(trs.scaleY, gMult.input1, f=1)
    pm.connectAttr(cog.scaleY, gMult.input2, f=1)
    pm.connectAttr(gMult.output, lMult.input1, f=1)
    pm.connectAttr(cog.scaleY, lMult.input2, f=1)
    # TODO: add attributes to controls


# TODO: build controls from driver skeleton
class Build(object):
    def __init__(self, driver_obj, fk=True, ik=True, spline=False, mid=1):
        self.driver = driver_obj
        self.name = self.driver.name
        self.fk = fk
        self.ik = ik
        self.spline = spline
        if self.spline:
            self.mid = mid
        self.ctls = {"FK": [],
                     "IK": [],
                     "Tweak": []}
        pm.select(cl=1)

    def set_ik_mid_follow(self):
        # TODO: get to work with one mid ctl
        # TODO: figure out how to apply to two mid ctls (they can go fuck themselves if they want more XD)
        both = pm.shadingNode("condition", n="CT_neck_mid01_both_cond", au=1)
        tip = pm.shadingNode("condition", n="CT_neck_mid01_tip_cond", au=1)
        base = pm.shadingNode("condition", n="CT_neck_mid01_base_cond", au=1)
        world = pm.shadingNode("condition", n="CT_neck_mid01_world_cond", au=1)
        weights = pm.parentConstraint("CT_neck_mid01_IK_ctl_grp_parentConstraint1", q=1, wal=1)
        for node in [both, tip, base, world]:
            node.colorIfTrueR.set(1)
            node.colorIfFalseR.set(0)
        both.colorIfTrueG.set(1)
        both.colorIfFalseG.set(0)
        tip.secondTerm.set(1)
        base.secondTerm.set(2)
        world.secondTerm.set(3)
        pm.connectAttr(both.outColorR, weights[0], f=1)
        pm.connectAttr(both.outColorG, weights[1], f=1)
        pm.connectAttr(both.outColorB, weights[2], f=1)

