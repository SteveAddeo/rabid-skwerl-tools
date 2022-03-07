import pymel.core as pm


class Builder(object):
    def __init__(self, name, orientation="xyz", invert=False, orient_tip_to_world=False, orient_chain_to_world=False):
        self.name = name
        self.guidesGrp = "{}_guides_grp".format(self.name)
        if not pm.ls(self.guidesGrp):
            pm.error("Guides for {} do not exist. Create guides first".format(self.name))
        self.orientation = orientation
        self.invert = invert
        self.orientTip = orient_tip_to_world
        self.orientToWorld = orient_chain_to_world
        self.aimAxis = self.get_vector_from_axis(self.orientation[0].capitalize())
        self.upAxis = self.get_vector_from_axis(self.orientation[1].capitalize())
        self.tertiaryAxis = self.get_vector_from_axis(self.orientation[2].capitalize())
        self.joints = self.get_joints()

    def get_joints(self):
        jntList = pm.ls("{}_base_primary_jnt".format(self.name))
        if not jntList:
            return None
        for jnt in reversed(pm.listRelatives(jntList[0], ad=1)):
            jntList.append(jnt)
        return jntList

    def get_vector_from_axis(self, axis="X"):
        n = 1
        if self.invert:
            n = -1
        if axis == "Y":
            vector = [0, n, 0]
        elif axis == "Z":
            vector = [0, 0, n]
        else:
            vector = [n, 0, 0]
        return vector

    def make_joint_chain(self):
        if self.joints is not None:
            return pm.warning("Joint chain for {} already exists".format(self.name))
        guides = [node for node in pm.listRelatives(self.guidesGrp, ad=1) if str(node).split("_")[-1] == "guide"]
        jntList = []
        for guide in reversed(guides):
            jntName = str(guide).replace("_guide", "_primary_jnt")
            jntPos = pm.xform(guide, q=1, ws=1, rp=1)
            jnt = pm.joint(n=jntName, p=jntPos, roo=self.orientation)
            jntList.append(jnt)
        return jntList

    def orient_joint(self, joint, aim_obj, up_obj=None):
        if up_obj is None:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="vector")
        else:
            aimConst = pm.aimConstraint([aim_obj], joint, aim=self.aimAxis, u=self.upAxis, wut="object", wuo=up_obj)
        pm.delete(aimConst)
        pm.makeIdentity(joint, apply=True)

    def orient_base_joint(self, joint):
        if self.orientToWorld:
            self.orient_joint(joint, self.joints[1])
        else:
            self.orient_joint(joint, self.joints[1], self.joints[2])

    def orient_mid_joints(self, joint, i):
        vectors = ["X", "Y", "Z"]
        # Orient tip to World or local
        if self.orientTip:
            for v in vectors:
                pm.setAttr("{}.jointOrient{}".format(joint, v), 0)
            pm.parent(joint, self.joints[i - 1])
        else:
            pm.parent(joint, self.joints[i - 1])
            for v in vectors:
                pm.setAttr("{}.jointOrient{}".format(joint, v), 0)

    def orient_tip(self, joint, i):
        # Center Chains align to World Up
        if self.orientToWorld:
            self.orient_joint(joint, self.joints[i + 1])
        else:
            self.orient_joint(joint, self.joints[i + 1], self.joints[i - 1])
        pm.parent(joint, self.joints[i - 1])

    def orient_joints_in_chain(self):
        if self.joints is None:
            self.joints = self.get_joints()
        # Unparent all joints before orienting
        for jnt in self.joints:
            if pm.listRelatives(jnt, p=1):
                pm.parent(jnt, w=1)
        # Orient Joints
        for i, jnt in enumerate(self.joints):
            # Set orientation for the Base Joint
            if i == 0:
                self.orient_base_joint(jnt)
            # Set orientation for the Tip Joint
            elif i == len(self.joints) - 1:
                self.orient_tip(jnt, i)
            # Set orientation for all joints in between
            else:
                self.orient_mid_joints(jnt, i)

    def build_primary_joints(self):
        pm.select(cl=1)
        if self.joints is not None:
            return pm.warning("Joint chain for {} already exists".format(self.name))
        jnts = self.make_joint_chain()
        self.orient_joints_in_chain()
        return jnts





