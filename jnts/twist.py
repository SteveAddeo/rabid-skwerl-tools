import pymel.core as pm
from core import utils
from jnts import primary


def make_base_tip_joints(joint, name="twist"):
    # Call joint's parent and children as variables
    parent = primary.get_parent_and_children(joint)[0]
    children = primary.get_parent_and_children(joint)[1]
    childJnt = [child for child in children if pm.nodeType(child) == "joint"]

    # Check to see if joint is able to twist
    if not childJnt:
        pm.warning("{} has no children that are joints so there's nothing to twist.".format(str(joint)))
        return None

    # Parent joints to world and remove children
    if parent is not None:
        pm.parent(joint, w=1)
    pm.parent(children, w=1)
    gen3 = primary.get_parent_and_children(childJnt[0])[1]
    if gen3:
        pm.parent(gen3, w=1)

    # Get name for duplicate joints
    if "_prime_" in str(joint):
        dupName = str(joint).replace("_prime_", "_{}_".format(name))
    elif "_jnt" in str(joint):
        dupName = str(joint).replace("_jnt", "_{}_jnt".format(name))
    else:
        dupName = "_".join([str(joint), "{}".format(name), "jnt"])
    baseName = dupName.replace(name, "{}_base".format(name))
    tipName = dupName.replace(name, "{}_tip".format(name))

    # Duplicate joints
    print(joint, childJnt[0])
    baseJnt = pm.duplicate(joint, n=baseName)[0]
    tipJnt = pm.duplicate(childJnt, n=tipName)[0]

    # Set a different radius for the new joints
    pm.setAttr("{}.radius".format(baseJnt), (pm.getAttr("{}.radius".format(joint)) * .8))
    pm.setAttr("{}.radius".format(tipJnt), (pm.getAttr("{}.radius".format(childJnt[0])) * .8))

    # Point constrain new joints to the original
    pm.pointConstraint(joint, baseJnt, n=str(baseJnt).replace("_jnt", "_pt_cnst".format(name)))
    pm.pointConstraint(childJnt[0], tipJnt, n=str(tipJnt).replace("_jnt", "_pt_cnst".format(name)))

    # Re-parent joints
    if parent is not None:
        pm.parent(joint, parent)
    if gen3:
        pm.parent(gen3, childJnt)
    pm.parent(children, joint)

    return [baseJnt, tipJnt]


class Build:
    def __init__(self, prime_joints, prime_obj):
        self.primeJoints = prime_joints
        self.primeObj = prime_obj
        self.upLocs = self.get_up_locs()
        self.twistJointsGrp = self.get_twist_grp()
        self.twistJoints = self.get_twist_joints()

    def get_twist_grp(self):
        return "twist group"

    def get_twist_joints(self):
        return "twist joints"

    def get_up_locs(self):
        return "locators"

    def make_twist_joints(self):
        twistDict = {}
        for jnt in self.primeJoints:
            twist = make_base_tip_joints(jnt)
            twistDict[jnt] = twist
        return twistDict

    def make_twist_rig(self, base, tip, base_up, tip_up):
        baseAim = pm.aimConstraint(tip, base, aim=self.primeObj.aimVector, u=self.primeObj.upVector, wuo=base_up)
        tipAim = pm.aimConstraint(base, tip, aim=self.primeObj.aimVector, u=self.primeObj.upVector, wuo=tip_up)
        return [baseAim, tipAim]

    def make_up_locs(self):
        upLocators = []
        for joint in self.primeJoints:
            locator = pm.spaceLocator(n=str(joint).replace("_jnt", "_up_loc"))
            pm.parent(locator, joint)
            utils.reset_transforms(locator)
            pm.move(locator, [(v * self.primeObj.guidesObj.scale * .2) for v in self.primeObj.aimVector])
            pm.makeIdentity(locator, a=1)
            upLocators.append(locator)
        return upLocators

