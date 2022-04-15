import os
import pymel.core as pm
from core import constants
from core import utils


SHAPES = utils.get_data_from_json(os.path.join(utils.RSTPATH, "rabid-skwerl-tools", "ctls", "shapes.json"))


def make_circle(name=None, scale=10, aim="X"):
    if name is None:
        name = "circle_ctl1"
    aimAxis = constants.get_axis_vector(aim)
    radius = scale * .3
    ctl = pm.circle(n=name, nr=aimAxis, r=radius)[0]
    return ctl


def make_gimbal(name=None, scale=10, aim="X", angle="Z", invert=False):
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


def make_pin(name=None, scale=10, aim="X", up="Y", invert=False):
    if name is None:
        name = "gimbal_ctl1"
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


def make_rombus(name=None, scale=10):
    if name is None:
        name = "rombus_ctl1"
    points = SHAPES["Rombus"]
    ptsScaled = []
    for point in points:
        ptsScaled.append([axis * scale for axis in point])
    ctl = pm.curve(n=name, d=1, p=ptsScaled)
    return ctl


def make_sphere(name=None, scale=10):
    if name is None:
        name = "sphere_ctl1"
    radius = scale * .2
    crv1 = pm.circle(nr=[1, 0, 0], r=radius)
    crv2 = pm.circle(nr=[0, 1, 0], r=radius)
    crv3 = pm.circle(nr=[0, 0, 1], r=radius)
    ctl = utils.parent_crv(name, [crv3[0], crv2[0], crv1[0]])
    return ctl


def make_spline(name=None, scale=10, aim="X", up="Y", invert=False):
    if name is None:
        name = "spline_ctl1"
    points = SHAPES["Spline"]
    ptsScaled = []
    for point in points:
        ptsScaled.append([axis * scale for axis in point])
    ctl = pm.curve(n=name, d=1, p=ptsScaled)
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


def make_square(name=None, scale=10, aim="X"):
    if name is None:
        name = "square_ctl1"
    vector = [1, 1, 1]
    vector[constants.get_axis_index(aim)] = 0
    indexes = [x for i, x in enumerate(range(3)) if not i == constants.get_axis_index(aim)]
    ptVector = [v * (scale * .3) for v in vector]
    ctl = pm.curve(n=name, d=1, p=[ptVector, [-v if i == indexes[0] else v for i, v in enumerate(ptVector)], [
        -v for v in ptVector], [-v if i == indexes[1] else v for i, v in enumerate(ptVector)], ptVector])
    return ctl
