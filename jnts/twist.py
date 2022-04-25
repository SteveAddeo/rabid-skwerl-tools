import pymel.core as pm

from core import utils
from core import matrix


def make_base_tip_joints(joint, name="twist", mid_jnt=True):
    # Call joint's parent and children as variables
    parent = utils.get_parent_and_children(joint)[0]
    children = utils.get_parent_and_children(joint)[1]
    childJnt = [child for child in children if pm.nodeType(child) == "joint"]

    # Check to see if joint is able to twist
    if not childJnt:
        pm.warning("{} has no children that are joints so there's nothing to twist.".format(str(joint)))
        return None

    # Parent joints to world and remove children
    if parent is not None:
        pm.parent(joint, w=1)
    pm.parent(children, w=1)
    gen3 = utils.get_parent_and_children(childJnt[0])[1]
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
    baseJnt = pm.duplicate(joint, n=baseName)[0]
    tipJnt = pm.duplicate(joint, n=tipName)[0]
    twistJnts = [baseJnt, tipJnt]

    # Set a different radius for the new joints
    pm.setAttr("{}.radius".format(baseJnt), (pm.getAttr("{}.radius".format(joint)) * .8))
    pm.setAttr("{}.radius".format(tipJnt), (pm.getAttr("{}.radius".format(childJnt[0])) * .8))

    # Make mid joints if needed
    if mid_jnt:
        midName = baseName.replace("_base_jnt", "_mid_jnt")
        midJnt = pm.duplicate(baseJnt, n=midName)[0]
        pm.pointConstraint(baseJnt, tipJnt, midJnt, n=midName.replace("_jnt", "_pt_cnst"))
        twistJnts = [baseJnt, midJnt, tipJnt]

    # Point constrain new joints to the original
    pm.pointConstraint(joint, baseJnt, n=str(baseJnt).replace("_jnt", "_pt_cnst"))
    pm.pointConstraint(childJnt[0], tipJnt, n=str(tipJnt).replace("_jnt", "_pt_cnst"))

    # Re-parent joints
    if parent is not None:
        pm.parent(joint, parent)
    if gen3:
        pm.parent(gen3, childJnt)
    pm.parent(children, joint)

    return twistJnts


# TODO: Test the twist Build class
class Build:
    def __init__(self, prime_obj):
        # TODO: should twist all joint but the end joint
        self.primeObj = prime_obj
        self.twistJointsGrp = self.get_twist_grp()
        self.twistJoints = self.get_twist_joints()
        self.midMultipliers = {}
        self.upLocators = self.get_up_locs()
        self.aimConstraints = self.get_aim_consts()

    # TODO: add a function to have the base_twist_up_loc_offset_grp receive twist data from prime_jnt
    # TODO: add a function to have the tip_twist_up_loc_offset_grp receive twist data from prime_jnt child and
    #  change the midMultiplier.input2 to 1.0

    def get_aim_consts(self):
        aimConsts = {}
        for prime in self.twistJoints:
            twistAim = [[child for child in utils.get_parent_and_children(twist)[1] if
                         pm.nodeType(child) == "aimConstraint"] for twist in self.twistJoints[prime]]
            if not twistAim or len(twistAim) == len(self.twistJoints[prime]):
                twistAim = self.make_aim_consts(prime)
            aimConsts[prime] = twistAim
        return aimConsts

    def get_prime_from_twist(self, joint):
        prime = [jnt for jnt in self.twistJoints if joint in self.twistJoints[jnt]]
        if not prime:
            return None
        return prime[0]

    def get_twist_grp(self):
        grpName = "{}_twist_jnts_grp".format(self.primeObj.name)
        if grpName not in [str(child) for child in utils.get_parent_and_children(self.primeObj.subJointsGrp)[1]]:
            grp = pm.group(em=1, n=grpName)
            pm.parent(grp, self.primeObj.subJointsGrp)
        return pm.ls(grpName)[0]

    def get_twist_joints(self):
        twistJnts = {}
        for jnt in self.primeObj.primaryJoints[0:-1]:
            grpName = "{}_grp".format(str(jnt).replace("prime", "twist"))
            twistGrp = pm.ls(grpName)
            # Create a group for the twist joints if one does not exist
            if not twistGrp or grpName not in [str(child) for
                                               child in utils.get_parent_and_children(self.twistJointsGrp)]:
                twistGrp = [pm.group(em=1, n=grpName)]
                pm.parent(twistGrp, self.twistJointsGrp)
            # Get the list of twist joints
            twistList = utils.get_parent_and_children(pm.ls(grpName)[0])[1]
            # Create twist joints if list is empty
            if not twistList:
                twistList = self.make_twist_joints(jnt, twistGrp[0])
            twistJnts[jnt] = twistList
        return twistJnts

    def get_up_locs(self):
        upLocs = {}
        for prime in self.twistJoints:
            twistUps = [pm.ls(str(twist).replace("_jnt", "_up_loc"))[0] for
                            twist in self.twistJoints[prime] if pm.ls(str(twist).replace("_jnt", "_up_loc"))]
            if not twistUps:
                twistUps = self.make_up_locs(prime)
            upLocs[prime] = twistUps
        return upLocs

    def make_aim_consts(self, prime_jnt):
        aimConsts = []
        for i in range(len(self.twistJoints[prime_jnt])):
            jnt = self.twistJoints[prime_jnt][i]
            up = self.upLocators[prime_jnt][i]
            if i == len(self.twistJoints[prime_jnt]) - 1:
                aimJnt = self.twistJoints[prime_jnt][0]
                aimVec = [-v for v in self.primeObj.aimVector]
            else:
                aimJnt = self.twistJoints[prime_jnt][-1]
                aimVec = self.primeObj.aimVector
            upV = self.primeObj.upVector
            print(jnt, up, upV)
            aim = pm.aimConstraint(aimJnt, jnt, aim=aimVec, u=upV, wuo=up, wut="objectrotation")
            aimConsts.append(aim)
        return aimConsts

    def make_twist_joints(self, prime_jnt, parent_grp):
        twistJnts = make_base_tip_joints(prime_jnt)
        for jnt in twistJnts:
            pm.parent(jnt, parent_grp)
            utils.reset_transforms(jnt, t=False, s=False)
        return twistJnts

    def make_up_locs(self, prime_jnt):
        upLocs = []
        for jnt in self.twistJoints[prime_jnt]:
            loc = pm.spaceLocator(n=str(jnt).replace("_jnt", "_up_loc"))
            pm.move(loc, [(v * self.primeObj.guidesObj.scale * .2) for v in self.primeObj.upVector], r=1, os=1)
            pm.makeIdentity(loc, a=1)
            offsetGrp = utils.make_offset_groups([loc])[0]
            pm.parent(offsetGrp, jnt)
            utils.reset_transforms(offsetGrp)
            if "_base_jnt" in str(jnt):
                pm.parent(offsetGrp, utils.get_parent_and_children(prime_jnt)[0])
            elif "_tip_jnt" in str(jnt):
                pm.parent(offsetGrp, prime_jnt)
            else:
                pm.parent(offsetGrp, self.twistJoints[prime_jnt][0])
                """pm.parent(loc, w=1)
                pm.setAttr("{}.rotate{}".format(str(offsetGrp), self.primeObj.orientation[0].upper()), 0.0)
                pm.parent(loc, offsetGrp)"""
                self.set_mid_up(jnt, loc)
            upLocs.append(loc)
        return upLocs

    def set_mid_up(self, mid_jnt, mid_loc):
        axis = self.primeObj.orientation[0].upper()
        primeJnt = self.get_prime_from_twist(mid_jnt)
        offsetGrp = utils.get_parent_and_children(mid_loc)[0]
        # Create a multiply node to have the rotation of the mid joint be 1/2 of the pirme joint
        mult = pm.shadingNode("multDoubleLinear", au=1, n=str(mid_jnt).replace("_jnt", "_mult"))
        pm.setAttr("{}.input2".format(mult), 0.5)
        # Connect aim axis rotation of the prime joint to to the offset group passing through the mult node
        pm.connectAttr("{}.rotate{}".format(str(primeJnt), axis), "{}.input1".format(str(mult)))
        pm.connectAttr("{}.output".format(str(mult)), "{}.rotate{}".format(str(offsetGrp), axis))
        self.midMultipliers[mid_jnt] = mult
        return mult

