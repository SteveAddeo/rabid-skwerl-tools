import pymel.core as pm


class Build(object):
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

    def make_up_locs(self):
        for joint in self.primeJoints:
            parent = pm.listRelatives(joint, p=1)[0]
            pm.spaceLocator(n=str(joint).replace("_jnt", "_up_loc"))
            # parent locator to joint parent
            # set position attrs to 0
            # offset up by .2(scale)

# Make twist joints:
# twistJnts = []
# for i, jnt in enumerate(joints, 1):
#     parent = pm.listRelatives(jnt, p=1)[0]
#     parent jnt, joints[i+1] to world
#     if joints[i+1] has a joint child:
#         parent joints[i+2] to world
#     twistName = jnt.replace("_prime_", "_twist_base_")
#     twistBase = duplicate jnt named twistName
#     twistTip = duplicate joints[i+1] named twistName.replace("_base_", "_tip_")
#     twistJnts.append(twistBase)
#     twistJnts.append(twistTip)
#     baseUp = [child for child in pm.listRelatives(parent, c=1) if pm.nodeType(child) == "transform"][0]
#     tipUp = [child for child in pm.listRelatives(jnt, c=1) if pm.nodeType(child) == "transform"][0]
#     point constrain twistBase to jnt
#     point constrain twistTip to joints[i+1]
#     self.make_twist_rig(twistBase, twistTip, baseUp, tipUp)

# make_twist_rig(base, tip, base_up, tip_up):
# aim base at tip orienting up to primary[i]_locator
# aim tip at base orienting up to primary[i+1]




