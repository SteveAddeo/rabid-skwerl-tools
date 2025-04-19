import pymel.core as pm

from core import constants
from core import utils
from rigs import ik


def check_for_child_joint(joint):
    if not utils.get_parent_and_children(joint)[1] or not [child for child in utils.get_parent_and_children(
            joint)[1] if pm.nodeType(child) == "joint"]:
        pm.warning("{} has no children that are joints so there's nothing to twist.".format(str(joint)))
        return False
    return True


def make_base_tip_joints(joint, jnt_type, parent=None):
    # Check to see if joint is able to twist
    if not check_for_child_joint(joint):
        return None
    # Call joint's parent and children as variables
    if parent is None:
        parent = utils.get_parent_and_children(joint)[0]
    # Create joints to be used as base and tip
    children = utils.get_parent_and_children(joint)[1]
    childJnt = [child for child in children if child.type() == "joint"][0]
    dupChain = utils.duplicate_chain([joint, childJnt], jnt_type, parent)
    baseJnt = dupChain[0]
    tipJnt = dupChain[1]
    # Rename joints
    baseName = baseJnt.name().replace(jnt_type, "{}_base".format(jnt_type))
    tipName = baseName.replace("_base_jnt", "_tip_jnt")
    pm.rename(baseJnt, baseName)
    pm.rename(tipJnt, tipName)
    # Zero out tip joint orientation:
    utils.reset_transforms([tipJnt], t=False, s=False)
    for axis in constants.AXES:
        pm.setAttr("{}.jointOrient{}".format(str(tipJnt), axis), 0.0)

    return [baseJnt, tipJnt]


# TODO: Test the twist Build class
# TODO: can the twist work by just adding a middle joint to each span and applyting an IK advanced twist setup?
class Build:
    def __init__(self, driver_obj):
        self.driver = driver_obj
        self.mainTwistJointGrp = utils.make_group("twist_jnt_grp", parent="jnt_grp")
        self.twistJointsGrp = utils.make_group(f"{self.driver.name}_twist_jnt_grp", parent=self.mainTwistJointGrp)
        self.followJointsGrp = utils.make_group(f"{self.driver.name}_follow_jnt_grp", parent="jnt_grp")
        self.twistJoints = self.get_joints("twist")
        self.followJoints = self.get_joints("follow")
        self.midMultipliers = {}
        self.upLocators = self.get_up_locs()
        self.aimConstraints = self.get_constraints()
        self.ikHandles = self.get_handles()

    # TODO: add a function to have the base_twist_up_loc_offset_grp receive twist data from prime_jnt
    # TODO: add a function to have the tip_twist_up_loc_offset_grp receive twist data from prime_jnt child and
    #  change the midMultiplier.input2 to 1.0

    def get_constraints(self):
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

    def get_handles(self):
        hndls = {}
        for i, jnt in enumerate(self.driver.driver_joints[0:-1]):
            hndlName = str(jnt).replace("_base_jnt", "_IK_hndl")
            if pm.ls(hndlName):
                hndl = pm.ls(hndlName)[0]
            else:
                # TODO: this doesn't appear to be running when it should
                hndl = self.make_handle(jnt, hndlName)
            if not [c for c in pm.listConnections(hndl, c=1) if pm.nodeType(c[1]) == "pointConstraint"]:
                pm.pointConstraint(self.driver.driver_joints[i + 1], hndl, mo=1)
            hndls[jnt] = hndl
        return hndls

    def get_joints(self, jnt_type):
        jntsDict = {}
        if jnt_type == "follow":
            parentGrp = self.followJointsGrp
        else:
            parentGrp = self.twistJointsGrp
        for i, jnt in enumerate(self.driver.driver_joints[0:-1]):
            grpName = "{}_grp".format(str(jnt).replace("prime", jnt_type))
            jntGrp = pm.ls(grpName)
            # Create a group for the twist joints if one does not exist
            if not jntGrp or grpName not in [str(child) for child in utils.get_parent_and_children(parentGrp)]:
                jntGrp = [pm.group(em=1, n=grpName)]
                pm.parent(jntGrp, parentGrp)
            # Get the list of twist joints
            jntList = utils.get_parent_and_children(pm.ls(grpName)[0])[1]
            # Create twist joints if list is empty
            if not jntList:
                jntList = self.make_joints(jnt, jntGrp[0], jnt_type)
            if not [child for child in utils.get_parent_and_children(jntGrp[0])[1] if "Constraint" in str(child)]:
                if i == 0:
                    pm.pointConstraint(self.driver.driver_joints[i], jntGrp[0], mo=1)
                else:
                    pm.parentConstraint(self.driver.driver_joints[i - 1], jntGrp, mo=1)
            jntsDict[jnt] = jntList
        return jntsDict

    def get_up_locs(self):
        upLocs = {}
        for prime in self.twistJoints:
            twistUps = [pm.ls(str(twist).replace("_jnt", "_up_loc"))[0] for twist in self.twistJoints[
                prime] if pm.ls(str(twist).replace("_jnt", "_up_loc"))]
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
                aimVec = [-v for v in self.driver.aim_vector]
            else:
                aimJnt = self.twistJoints[prime_jnt][-1]
                aimVec = self.driver.aim_vector
            upV = self.driver.up_vector
            aim = pm.aimConstraint(aimJnt, jnt, aim=aimVec, u=upV, wuo=up, wut="objectrotation")
            aimConsts.append(aim)
        return aimConsts

    def make_handle(self, joint, name):
        ikObj = ik.Build(self.driver, self.twistJoints[joint], handle_name=name)
        print(ikObj.handles)
        return ikObj.handles[0]

    def make_joints(self, prime_jnt, parent_grp, jnt_type, mid=True):
        # TODO: figure out a way to turn mid off
        if not check_for_child_joint(prime_jnt):
            return None
        baseTipJnts = make_base_tip_joints(prime_jnt, jnt_type, parent_grp)
        baseJnt = baseTipJnts[0]
        tipJnt = baseTipJnts[1]
        if jnt_type == "follow":
            color = 3
            radiusMult = .2
            newJnts = baseTipJnts
        else:
            color = 20
            radiusMult = .8
            newJnts = self.make_twist_jnts(prime_jnt, parent_grp, baseJnt, tipJnt, mid)
        pm.setAttr("{}.radius".format(baseJnt), (pm.getAttr("{}.radius".format(baseJnt)) * radiusMult))
        pm.setAttr("{}.radius".format(tipJnt), (pm.getAttr("{}.radius".format(tipJnt)) * radiusMult))
        for jnt in newJnts:
            pm.setAttr("{}.overrideEnabled".format(str(jnt)), 1)
            pm.setAttr("{}.overrideColor".format(str(jnt)), color)
        return newJnts

    def make_twist_jnts(self, prime_jnt, parent_grp, base, tip, mid=True):
        childJnt = [node for node in utils.get_parent_and_children(prime_jnt)[1] if pm.nodeType(node) == "joint"][0]
        pm.parent(tip, parent_grp)
        jnts = [base, tip]
        if mid:
            midJnt = self.make_twist_mid(base, tip, parent_grp)
            jnts = [base, midJnt, tip]
        # Point constrain new joints to the original
        pm.pointConstraint(prime_jnt, base, n=str(base).replace("_jnt", "_pt_cnst"))
        pm.pointConstraint(childJnt, tip, n=str(tip).replace("_jnt", "_pt_cnst"))
        return jnts

    def make_twist_mid(self, base, tip, parent_grp):
        midName = str(base).replace("_base_jnt", "_mid_jnt")
        midJnt = pm.duplicate(base, n=midName)[0]
        pm.setAttr("{}.radius".format(midJnt), (pm.getAttr("{}.radius".format(base)) * .8))
        pm.pointConstraint(base, tip, midJnt, n=midName.replace("_jnt", "_pt_cnst"))
        pm.parent(midJnt, parent_grp)
        return midJnt

    def make_up_locs(self, prime_jnt):
        upLocs = []
        for jnt in self.twistJoints[prime_jnt]:
            loc = pm.spaceLocator(n=str(jnt).replace("_jnt", "_up_loc"))
            pm.move(loc, [(v * self.driver.guidesObj.scale * .2) for v in self.driver.up_vector], r=1, os=1)
            pm.makeIdentity(loc, a=1)
            offsetGrp = utils.make_offset_groups([loc])[0]
            pm.parent(offsetGrp, jnt)
            utils.reset_transforms([offsetGrp])
            pm.parent(offsetGrp, self.followJoints[prime_jnt][0])
            if "_mid_jnt" in str(jnt):
                self.set_mid_up(jnt, loc)
            # TODO: if "_tip_jnt" in str(jnt): connect rotateX of the prime joint to the rotateX of the offset grp
            # TODO: up_locs need X rotation of base and tip for end joint
            upLocs.append(loc)
        return upLocs

    def set_mid_up(self, mid_jnt, mid_loc):
        axis = self.driver.orientation[0].upper()
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

