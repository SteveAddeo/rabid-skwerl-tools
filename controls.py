import pymel.core as pm
from core import utils


def make_sphere_ctl(name=None, scale=10):
    if name is None:
        name = "sphere_ctl1"
    radius = scale * .2
    crv1 = pm.circle(n=name, nrx=1, nry=0, nrz=0, r=radius)
    crv2 = pm.circle(n=name, nrx=0, nry=1, nrz=0, r=radius)
    crv3 = pm.circle(n=name, nrx=0, nry=0, nrz=1, r=radius)
    utils.parent_crv([crv3[0], crv2[0], crv1[0]])
