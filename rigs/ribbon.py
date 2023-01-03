import pymel.core as pm
from core import utils
from core import constants
from ctls import attributes


ATTRCONN = {
    "sine": {"amplitude": "amplitude",
             "wavelength": "wavelength",
             "orientation": "rotate",
             "animate": "offset"},
    "twist": {"base": "startAngle",
              "tip": "endAngle"},
}


def make_ribbon_for_chain(base_jnt, scale=10, def_types=None, o="Z", n="Y", a="X", u="Y", mir=False, neg=False):
    """
    Created a ribbon based on the length and number of bones in a chain
    :param base_jnt: the base joint of the chain
    :param scale: the scale of the ribbon (not super important)
    :param def_types: a list of the types of deformers being applied
    :param o: Axis ribbon will orient to
    :param n: Ribbon's normal up axis (acts as up for skin joints)
    :param a: Axis joints will aim down
    :param u: Up axis for the skin joints
    :param mir: whether or not the rig is mirrored across the global X axis (right side for example)
    :param neg: Direction ribbon points along its orient axis
    :return: obj ribbon
    """
    # Get variable values from Base Joint
    if def_types is None:
        def_types = ["sine", "twist"]
    num = utils.get_info_from_joint(base_jnt, num=True)
    name = utils.get_info_from_joint(base_jnt, name=True)
    width = utils.get_length_of_chain(base_jnt)
    side = utils.get_info_from_joint(base_jnt, side=True)
    # Check to make sure ribbon doesn't exist
    if pm.ls(f"{side}_{name}_rbn"):
        return pm.PyNode(f"{side}_{name}_rbn")
    # Build the ribbon
    rbn =  (name, num*2, width, side, scale, o, n, a, u, mir, neg)
    grp = pm.PyNode(f"{rbn.name}_grp")
    pm.xform(grp, piv=pm.xform(base_jnt, q=1, ws=1, rp=1))
    pm.xform(rbn.rbn, t=pm.xform(base_jnt, q=1, ws=1, rp=1))
    pm.makeIdentity(rbn.rbn, a=1)
    return rbn


def position_ribbon_on_chain(rbn, base_jnt):
    # Set Variables
    jnts = utils.get_joints_in_chain(base_jnt)
    num = utils.get_info_from_joint(base_jnt, num=True)
    rbnDir = [rbn.orient, rbn.normal]
    dv = [2, 2, 2]
    dv[constants.get_axis_index(rbn.orient)] = num
    # Create Lattice
    pm.select(rbn.rbn, r=1)
    lat = pm.lattice(dv=dv, oc=1)
    # Position lattice points on each joint
    for i, jnt in enumerate(jnts):
        pm.select(f"{lat[1]}.pt[0:1][0:1][{i}]", r=1)
        if "X" in rbnDir and "Y" in rbnDir:
            pm.move((pm.xform(jnt, q=1, ws=1, rp=1))[:1], xy=1, ws=1)
        elif "X" in rbnDir and "Z" in rbnDir:
            tVal = [(pm.xform(jnt, q=1, ws=1, rp=1))[0], (pm.xform(jnt, q=1, ws=1, rp=1))[-1]]
            pm.move(tVal, xz=1, ws=1)
        else:
            pm.move((pm.xform(jnt, q=1, ws=1, rp=1))[1:], yz=1, ws=1)
    pm.delete(rbn, ch=1)


# TODO: should all of these be included under the Builder? should it be a new class that inherits
#  from the builder? That could be a great way to separate Chain ribbons (spine, neck, tail) from
#  Limb ribbons (legs, arms, etc)
class Builder(object):
    def __init__(self, name, spans, width, side, scale=10, orient="Z", normal="X", aim_axis="X", up_axis="Y",
                 mirror=False, neg=False, sine=True, twist=True, skin_jnts=True, matrix=True, lock_tip=True):
        if orient == normal or aim_axis == up_axis:
            pm.error("The neither the ribbon's nor its joint's aim axes can be the same as their up axis")
        self.name = f"{side}_{name}_rbn"
        self.spans = spans
        self.width = width
        self.scale = scale
        self.orient = orient.upper()
        self.normal = normal.upper()
        self.aimAxis = aim_axis.upper()
        self.upAxis = up_axis.upper()
        self.mirror = mirror
        self.neg = neg
        self.sine = sine
        self.twist = twist
        self.matrix = matrix
        self.rbn = self.make_ribbon()
        self.deformers = []
        self.deformRbns = []
        self.deformHndls = []
        if self.sine:
            self.deformers.append("sine")
        if self.twist:
            self.deformers.append("twist")
        if self.deformers:
            for d in self.deformers:
                attributes.make_ribbon_def_attrs(self.rbn, d)
                self.make_ribbon_deformer(d)
                self.make_ribbon_blendshape(self.deformRbns[-1], self.rbn)
                self.connect_ribbon_deformer(self.deformRbns[-1])
        if skin_jnts:
            self.skinJoints = self.make_skin_joints()
        self.ctlJoints = []
        if not lock_tip:
            self.rbn.lockTip.set(0)

    def connect_lock_tip(self, hndl):
        """
        Used for Sine deformers to set up nodes to calculate the position and size of the handle based on
        whether or not the animator wants the tip locked down or not
        :param hndl: The deformer handle being manipulated
        """
        # Create the math nodes to do the calculations
        cond = pm.shadingNode("condition", au=1, n=f"{self.name}_lock_tip_cond")
        mult = pm.shadingNode("multDoubleLinear", au=1, n=f"{self.name}_lock_tip_mult")
        # Set the values
        cond.secondTerm.set(1)
        cond.colorIfTrueR.set(1)
        cond.colorIfFalseR.set(2)
        mult.input1.set(hndl.scaleY.get())
        # Get the translate axis for the handle
        if self.orient != "Y":
            if not self.orient == "Z" and not self.normal == "Y":
                pos = "X"
            elif self.orient == "X" and self.normal == "Y":
                pos = "X"
            else:
                pos = "Z"
        else:
            pos = "Y"
        # Make the connections
        pm.connectAttr(self.rbn.lockTip, cond.firstTerm, f=1)
        pm.connectAttr(cond.outColorR, mult.input2, f=1)
        pm.connectAttr(mult.output, f"{hndl}.translate{pos}", f=1)
        pm.connectAttr(mult.output, hndl.scaleY, f=1)
        if self.neg:
            negMult = pm.shadingNode("multDoubleLinear", au=1, n=f"{self.name}_lock_tip_neg")
            negMult.input2.set(-1)
            pm.connectAttr(mult.output, negMult.input1, f=1)
            pm.connectAttr(negMult.output, f"{hndl}.translate{pos}", f=1)

    def connect_ribbon_deformer(self, def_rbn):
        """
        Make the connections to the main ribbon based on the deformer created
        :param def_rbn: The deformer ribbon being connected to the main ribbon
        """
        # Make connections
        defType = def_rbn.name().split("_")[-2]
        pm.connectAttr(f"{self.rbn.name()}.{defType}Blend", f"{self.rbn.name()}_def_bs.{self.rbn.name()}_{defType}_bs")
        hndl = pm.PyNode(f"{self.rbn.name()}_{defType}_def_hndl")
        if defType in ATTRCONN:
            if defType == "sine":
                self.connect_lock_tip(hndl)
            a = ATTRCONN[defType]
            for attr in a:
                if a[attr] in constants.TRNSFRMATTRS:
                    # Transform values go to the offset parent matrix of the deformer' tranform node
                    oAxis = f"{a[attr]}".capitalize() + f"{self.orient}"
                    if pm.ls(f"{hndl.name()[:-5]}_{attr}_mtrx"):
                        mtrx = pm.PyNode(f"{hndl.name()[:-5]}_{attr}_mtrx")
                    else:
                        mtrx = pm.createNode("composeMatrix", n=f"{hndl.name()[:-5]}_{attr}_mtrx")
                    pm.connectAttr(f"{self.rbn.name()}.{attr}", f"{mtrx}.input{oAxis}", f=1)
                    pm.connectAttr(f"{mtrx}.outputMatrix", f"{hndl}.offsetParentMatrix", f=1)
                else:
                    # All other values plug drirectly into the deformer's shape node
                    pm.connectAttr(f"{self.rbn.name()}.{attr}", f"{hndl}Shape.{a[attr]}", f=1)

    def follicle_pin(self, joint, i):
        """
        Use a follicle node to pin joint to ribbon surface
        :param joint: joint being pinned
        :param i: order joint is in chain
        """
        pass

    def make_ribbon(self):
        """
        Create the ribbon that will be the base for your rig
        :return: PyNode ribbon that was created
        """
        ratio = 3.0 / self.width
        oVal = self.set_ribbon_orient_values()
        # Check to see if ribbon exists
        if pm.ls(self.name):
            return pm.PyNode(self.name)
        # Build ribbon
        rbn = pm.nurbsPlane(p=oVal[0], ax=oVal[1], w=self.width, lr=ratio,
                            d=3, u=(self.spans - 1), v=1, name=self.name, ch=0)[0]
        self.orient_ribbon(rbn)
        rbn.inheritsTransform.set(0)
        # Parent ribbon to group
        utilGrp = utils.make_group("util_grp")
        rbnsGrp = utils.make_group("rbn_grp", child=None, parent=utilGrp)
        rbnGrp = utils.make_group(f"{self.name}_grp", child=rbn, parent=rbnsGrp)
        # pm.xform(rbnGrp, t=pm.xform(self.baseJnt, q=1, ws=1, rp=1))
        return rbn

    def make_ribbon_deformer(self, def_type):
        """
        Create the ribbon that will receive the given deformer
        :param def_type: deformer being applied to the ribbon
        :return: PyNode deformer ribbon
        """
        # Check to make sure deformer ribbon doesn't exist
        if pm.ls(f"{self.rbn.name()}_{def_type}_bs"):
            return pm.PyNode(f"{self.rbn.name()}_{def_type}_bs")
        # Create deformer components
        bsRbn = pm.duplicate(self.rbn, n=f"{self.rbn.name()}_{def_type}_bs")[0]
        for attr in pm.listAttr(bsRbn, ud=1):
            pm.deleteAttr(bsRbn, at=attr)
        dfrm = pm.nonLinear(bsRbn, typ=def_type)
        self.orient_deformer(dfrm[1])
        # Set attribute values
        if def_type == "sine":
            dfrm[0].dropoff.set(1)
        # Group deformer components in outliner
        bsGrp = utils.make_group(name=f"{self.rbn.name()}_{def_type}_grp",
                                 child=[bsRbn, dfrm[1]],
                                 parent=f"{self.rbn.name()}_grp")
        bsGrp.visibility.set(0)
        pm.select(cl=1)
        # Rename deformer components
        pm.rename(dfrm[0], f"{self.rbn.name()}_{def_type}_def")
        pm.rename(dfrm[1], f"{self.rbn.name()}_{def_type}_def_hndl")
        self.deformHndls.append(pm.PyNode(f"{self.rbn.name()}_{def_type}_def_hndl"))
        self.deformRbns.append(bsRbn)
        return bsRbn

    def make_ribbon_blendshape(self, source, target):
        """
        Applies a blendshape to a ribbon to use for things like deformers
        :param source: ribbons doing the deforming
        :param target: ribbon getting deformed
        """
        # Create blendshape or add to existing one
        bsName = f"{target.name()}_def_bs"
        if pm.ls(bsName):
            bsLen = len(pm.blendShape(target, q=1, t=1))
            pm.blendShape(bsName, e=1, t=(target, bsLen, source, 1.0))
        else:
            pm.blendShape(source, target, n=bsName, foc=1)

    def make_skin_joints(self):
        """
        Create the joints that will be pinned to the ribbon's surface
        :return: list joints created
        """
        # Check to see if joints exist
        # TODO: set rotation order for joints
        grpName = f"{self.name[:-4]}_skn_jnt_grp"
        if pm.ls(grpName):
            return pm.listRelatives(grpName, c=1)
        grp = pm.group(n=grpName, em=1)
        if pm.ls("skn_jnt_grp"):
            pm.parent(grpName, "skn_jnt_grp")
        # Make a joint for each span and add it to the jntList
        jntList = []
        for i in range(self.spans):
            # Create joint
            jntName = f"{self.name}{str(i + 1).zfill(2)}_skn_jnt"
            jnt = pm.joint(rad=(0.1 * self.scale), n=jntName)
            jnt.overrideEnabled.set(1)
            jnt.overrideColor.set(9)
            utils.reset_transforms(jnt)
            # Pin joint to ribbon
            if self.matrix:
                self.matrix_pin(jnt, i)
            else:
                self.follicle_pin(jnt, i)
            # Add joint to parent grp
            pm.parent(jnt, grp)
            pm.select(cl=1)
            # Add joint to data set
            jntList.append(jnt)
        self.skinJoints = jntList
        return jntList

    def matrix_pin(self, joint, i):
        """
        Use a uvPin node to pin joint to ribbon surface
        :param joint: joint being pinned
        :param i: order joint is in the chain
        """
        if pm.ls(f"{joint.name()}_uvPin"):
            return pm.PyNode(f"{joint.name()}_uvPin")
        uvPin = pm.shadingNode("uvPin", au=1, n=f"{joint.name()}_uvPin")
        # Set UV Pin node values
        uvPin.coordinate[0].coordinateV.set(0.5)
        uvPin.coordinate[0].coordinateU.set(i / (self.spans - 1.0))
        nVal = constants.AXES.index(self.upAxis)
        tVal = constants.AXES.index(self.aimAxis)
        if self.mirror:
            tVal = tVal + 3
        if self.neg and self.orient == "X":
            nVal = nVal + 3
        if self.mirror:
            if self.orient == "Y" or self.orient == "Z":
                nVal = nVal + 3
        uvPin.normalAxis.set(nVal)
        uvPin.tangentAxis.set(tVal)
        # Create connections
        pm.connectAttr(uvPin.outputMatrix[0], joint.offsetParentMatrix)
        pm.connectAttr(self.rbn.getShape().worldSpace, uvPin.deformedGeometry)
        return uvPin

    def orient_deformer(self, hndl):
        """
        Orients the deformer handle to the ribbon based on class orientation
        :param hndl: the deformer handle being oriented
        """
        if self.orient == "X":
            rVal = -90
            if self.neg and not self.mirror:
                rVal = 90
            if self.mirror and not self.neg:
                rVal = 90
            hndl.rotateZ.set(rVal)
        if self.orient == "Y":
            if self.neg and not self.mirror:
                hndl.rotateZ.set(180)
            if self.mirror and not self.neg:
                hndl.rotateZ.set(180)
        if self.orient == "Z":
            rVal = 90
            if self.neg and not self.mirror:
                rVal = -90
            if self.mirror and not self.neg:
                rVal = -90
            hndl.rotateX.set(rVal)
        aList = [self.orient, self.normal]
        if aList == ["X", "Z"] or aList == ["Y", "Z"]:
            hndl.rotateY.set(90)
        if aList == ["Z", "Y"]:
            hndl.rotateZ.set(90)

    def orient_ribbon(self, rbn):
        """
        Orients the ribbon based on class orientation
        :param rbn: the ribon being oriented.
        """
        if self.orient == "X":
            if self.neg and not self.mirror:
                rbn.scaleX.set(-1)
            if self.mirror and not self.neg:
                rbn.scaleX.set(-1)
        if self.orient == "Y":
            rVal = 90
            if self.neg and not self.mirror:
                rVal = -90
            if self.mirror and not self.neg:
                rVal = -90
            if self.normal == "X":
                rbn.rotateX.set(rVal)
            if self.normal == "Z":
                rbn.rotateZ.set(rVal)
        if self.orient == "Z":
            if self.normal == "Y":
                rVal = -90
                if self.neg and not self.mirror:
                    rVal = 90
                if self.mirror and not self.neg:
                    rVal = 90
                rbn.rotateY.set(rVal)
            if self.normal == "X":
                if self.neg and self.mirror:
                    rbn.rotateX.set(180)
                if not self.neg and not self.mirror:
                    rbn.rotateX.set(180)
        pm.makeIdentity(rbn, r=1, a=1)

    def set_ribbon_orient_values(self):
        """
        Generate a set of variables used to create the main ribbon based on class orientation
        :return: list of variables
        """
        if self.normal == "X":
            offset = (0, 0, -self.width / 2.0)
        else:
            offset = (self.width / 2.0, 0, 0)
        axis = constants.get_axis_vector(self.normal)
        return [offset, axis]


class Chain(Builder):
    def __init__(self, base_jnt, spans_per=3, humanoid=False):
        self.driveJnts = utils.get_joints_in_chain(base_jnt)
        if self.driveJnts[0].name()[:3] == "CT_":
            self.orient = "Z"
            self.normal = "Y"
            self.mirror = True
            self.neg = False
            self.lockTip = False
            if not self.driveJnts[0].name()[2:7] == "_tail":
                self.mirror = False
                self.lockTip = True
            if humanoid and self.driveJnts[0].name()[2:7] != "_tail":
                self.orient = "Y"
                self.normal = "Z"
        elif self.driveJnts[0].name()[:3] == "LT_":
            self.orient = "X"
            self.normal = "Y"
            self.mirror = False
            self.neg = False
            self.lockTip = False
        else:
            self.orient = "X"
            self.normal = "Y"
            self.mirror = True
            self.neg = False
            self.lockTip = False
        if self.driveJnts[0].name()[2:6] == "_leg":
            self.orient = "Y"
            self.normal = "X"
            self.neg = True
        super().__init__(name=utils.get_info_from_joint(base_jnt, name=True),
                         spans=spans_per*(utils.get_info_from_joint(base_jnt, num=True)-1),
                         width=utils.get_length_of_chain(base_jnt),
                         side=utils.get_info_from_joint(base_jnt, side=True),
                         orient=self.orient,
                         normal=self.normal,
                         mirror=self.mirror,
                         neg=self.neg,
                         lock_tip=self.lockTip)
        self.crv = self.make_curve()
        pm.select(cl=1)

    def connect_lock_tip(self, hndl):
        # Set position
        baseLoc = pm.spaceLocator(n=f"{self.name}_lock_base")
        tipLoc = pm.spaceLocator(n=f"{self.name}_lock_tip")
        pm.xform(baseLoc, t=pm.xform(self.driveJnts[0], q=1, ws=1, rp=1), ws=1)
        pm.xform(tipLoc, t=pm.xform(self.driveJnts[-1], q=1, ws=1, rp=1), ws=1)
        ptCon = pm.pointConstraint(baseLoc, tipLoc, hndl)
        pm.connectAttr(self.rbn.lockTip, f"{ptCon.name()}.{baseLoc}W0")
        pm.parent(baseLoc, tipLoc, f"{self.name}_{hndl.name().split('_')[-3]}_grp")
        # Set Scale with math nodes
        cond = pm.shadingNode("condition", au=1, n=f"{self.name}_lock_tip_cond")
        mult = pm.shadingNode("multDoubleLinear", au=1, n=f"{self.name}_lock_tip_mult")
        # Set attributes
        cond.secondTerm.set(1)
        cond.colorIfTrueR.set(1)
        cond.colorIfFalseR.set(2)
        mult.input1.set(hndl.scaleY.get())
        # Make scale connections
        pm.connectAttr(self.rbn.lockTip, cond.firstTerm, f=1)
        pm.connectAttr(cond.outColorR, mult.input2, f=1)
        pm.connectAttr(mult.output, hndl.scaleY)

    def connect_ribbon_deformer(self, def_rbn):
        """
        Make the connections to the main ribbon based on the deformer created
        :param def_rbn: The deformer ribbon being connected to the main ribbon
        """
        # Make connections
        defType = def_rbn.name().split("_")[-2]
        pm.connectAttr(f"{self.rbn.name()}.{defType}Blend", f"{self.rbn.name()}_def_bs.{self.rbn.name()}_{defType}_bs")
        hndl = pm.PyNode(f"{self.rbn.name()}_{defType}_def_hndl")
        if defType in ATTRCONN:
            if defType == "sine":
                self.connect_lock_tip(hndl)
            a = ATTRCONN[defType]
            for attr in a:
                if a[attr] in constants.TRNSFRMATTRS:
                    # Transform values go to the offset parent matrix of the deformer' tranform node
                    oAxis = f"{a[attr]}".capitalize() + f"{self.orient}"
                    if pm.ls(f"{hndl.name()[:-5]}_{attr}_mtrx"):
                        mtrx = pm.PyNode(f"{hndl.name()[:-5]}_{attr}_mtrx")
                    else:
                        mtrx = pm.createNode("composeMatrix", n=f"{hndl.name()[:-5]}_{attr}_mtrx")
                    pm.connectAttr(f"{self.rbn.name()}.{attr}", f"{mtrx}.input{oAxis}", f=1)
                    pm.connectAttr(f"{mtrx}.outputMatrix", f"{hndl}.offsetParentMatrix", f=1)
                else:
                    # All other values plug drirectly into the deformer's shape node
                    pm.connectAttr(f"{self.rbn.name()}.{attr}", f"{hndl}Shape.{a[attr]}", f=1)

    def make_curve(self):
        name = f"{self.driveJnts[0].split('_')[0]}_{self.driveJnts[0].split('_')[1]}_crv"
        crv = utils.make_curve_from_chain(self.driveJnts[0], name=name)
        utilGrp = utils.make_group("util_grp")
        crvsGrp = utils.make_group("crv_grp", child=None, parent=utilGrp)
        crvGrp = utils.make_group(f"{name}_grp", child=crv, parent=crvsGrp)
        pm.xform(crvGrp, t=pm.xform(self.driveJnts[0], q=1, ws=1, rp=1))
        return crv

    def make_ribbon(self):
        """
        Create the ribbon that will be the base for your rig
        :return: PyNode ribbon that was created
        """
        print("=============== RUNNING CHAIN! ===============")
        ratio = 3.0 / self.width
        oVal = self.set_ribbon_orient_values()
        # Check to see if ribbon exists
        if pm.ls(self.name):
            return pm.PyNode(self.name)
        # Build ribbon
        rbn = pm.nurbsPlane(p=oVal[0], ax=oVal[1], w=self.width, lr=ratio,
                            d=3, u=(self.spans - 1), v=1, name=self.name, ch=0)[0]
        self.orient_ribbon(rbn)
        self.position_ribbon_on_chain(rbn)
        rbn.inheritsTransform.set(0)
        # Parent ribbon to group
        utilGrp = utils.make_group("util_grp")
        rbnsGrp = utils.make_group("rbn_grp", child=None, parent=utilGrp)
        rbnGrp = utils.make_group(f"{self.name}_grp", child=rbn, parent=rbnsGrp)
        pm.xform(rbnGrp, t=pm.xform(self.driveJnts[0], q=1, ws=1, rp=1))
        return rbn

    def position_ribbon_on_chain(self, rbn):
        # Set Variables
        num = utils.get_info_from_joint(self.driveJnts[0], num=True)
        dv = [2, 2, 2]
        dv[constants.get_axis_index(self.orient)] = num
        # Create Lattice
        pm.select(rbn, r=1)
        lat = pm.lattice(pm.ls(sl=1), dv=dv, oc=1, foc=1)
        self.move_lattice(lat)
        # Delete history and transform data
        pm.xform(rbn, piv=pm.xform(self.driveJnts[0], q=1, ws=1, rp=1), ws=1)
        pm.makeIdentity(rbn, a=1)
        pm.delete(rbn, ch=1)

    def move_lattice(self, lattice):
        rbnDir = [self.orient, self.normal]
        lattice[0].local.set(1)
        for i, jnt in enumerate(self.driveJnts):
            print(jnt)
            pm.select(f"{lattice[1]}.pt[0:1][0:1][{i}]", r=1)
            print(pm.ls(sl=1))
            if "X" in rbnDir and "Y" in rbnDir:
                print("========== XY ==========")
                pm.move((pm.xform(jnt, q=1, ws=1, rp=1))[:1], xy=1, ws=1)
            elif "X" in rbnDir and "Z" in rbnDir:
                print("========== XZ ==========")
                tVal = [(pm.xform(jnt, q=1, ws=1, rp=1))[0], (pm.xform(jnt, q=1, ws=1, rp=1))[-1]]
                pm.move(tVal, xz=1, ws=1)
            else:
                print("========== YZ ==========")
                print((pm.xform(jnt, q=1, ws=1, rp=1)))
                pm.move((pm.xform(jnt, q=1, ws=1, rp=1))[1:], yz=1, ws=1)

    def orient_deformer(self, hndl):
        up = constants.get_axis_vector(self.normal)
        pos = pm.pointConstraint(self.driveJnts[0], self.driveJnts[-1], hndl)
        aim = pm.aimConstraint(self.driveJnts[-1], hndl, aim=[0, 1, 0], u=[1, 0, 0], wu=up, wut="vector")
        pm.delete(aim, pos)
