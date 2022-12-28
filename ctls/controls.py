import os
import pymel.core as pm
from core import constants
from core import utils


SHAPES = utils.get_data_from_json(os.path.join(utils.RSTPATH, "rabid-skwerl-tools", "ctls", "shapes.json"))


def make_shape(name=None, scale=10.0, shape="Cube", rot90=False, mirror_x=False):
    if name is None:
        name = "{}_ctl1".format(shape.lower())
    points = SHAPES[shape]
    if mirror_x:
        points = [[-axis for axis in point] for point in points]
    if rot90:
        points = [[point[2], point[1], point[0]] for point in points]
    ptsScaled = [[axis * scale for axis in point] for point in points]
    ctl = pm.curve(n=name, d=1, p=ptsScaled)
    return ctl


def make_circle(name=None, scale=10.0, aim="X"):
    if name is None:
        name = "circle_ctl1"
    aimAxis = constants.get_axis_vector(aim)
    radius = scale * .3
    ctl = pm.circle(n=name, nr=aimAxis, r=radius)[0]
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





