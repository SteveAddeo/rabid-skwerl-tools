import pymel.core as pm
from ctls import controls


DFRMATTRS = {
    "sine": {"lockTip": [1, "byte", 1, 1, 0, 1],
             "amplitude": [1, "float", 1, 0.0, 0.0, 3.0],
             "wavelength": [1, "float", 1, 1.0, 0.1, 5.0],
             "orientation": [1, "float", 1, 0.0, -1080.0, 1080.0],
             "animate": [1, "float", 1, 0.0, -50.0, 50.0]},
    "twist": {"base": [1, "float", 1, 0.0, -1080.0, 1080.0],
              "tip": [1, "float", 1, 0.0, -1080.0, 1080.0]},
}
DFRMCONN = {
    "sine": {"amplitude": "amplitude",
             "wavelength": "wavelength",
             "orientation": "rotate",
             "animate": "offset"},
    "twist": {"base": "startAngle",
              "tip": "endAngle"},
}


def make_ribbon_def_attrs(node, def_type):
    if "deformers" not in pm.listAttr(node, ud=1):
        pm.addAttr(node, ln="space", nn="________", at="enum", en="________", k=1)
        pm.addAttr(node, ln="deformers", nn="DEFORMERS", at="enum", en="________", k=1)
    pm.addAttr(node, ln=f"{def_type}Options", nn="________", at="enum", en=f"{def_type.upper()}", k=1)
    pm.addAttr(node, ln=f"{def_type}Blend", nn="Blend", s=1, at="float", min=0.0, max=1.0, k=1)
    if def_type in DFRMATTRS:
        a = DFRMATTRS[def_type]
        for attr in a:
            pm.addAttr(node, ln=attr, s=a[attr][0], at=a[attr][1], k=a[attr][2], dv=a[attr][3])
            if len(a[attr]) == 6:
                newAttr = pm.PyNode(f"{node}.{attr}")
                newAttr.setMin(a[attr][4])
                newAttr.setMax(a[attr][5])


def make_spline_attrs(node, base="Base", tip="Tip", mid=False, head=False):
    pm.addAttr(node, ln="space", nn="________", at="enum", en="________", k=1)
    if mid:
        pm.addAttr(node, ln="follow", nn="Follow", at="enum", en=f"Both:{tip}:{base}:World", k=1)
    else:
        pm.addAttr(node, ln="stretch", nn="Stretch", s=1, at="byte", min=0, max=1, k=1)
    pm.addAttr(node, ln="arch", nn="Arch", s=1, at="float", min=0.0, max=3.0, k=1)
    if head:
        pm.addAttr(node, ln="inherit", nn="________", at="enum", en="INHERIT", k=1)
        pm.addAttr(node, ln="position", nn="Position", s=1, at="float", min=0.0, max=1.0, k=1)
        pm.addAttr(node, ln="orientation", nn="Orientation", s=1, at="float", min=0.0, max=1.0, k=1)


class Add:
    def __init__(self, ctls_obj, rig_type):
        self.ctlsObj = ctls_obj
        self.rigType = rig_type
