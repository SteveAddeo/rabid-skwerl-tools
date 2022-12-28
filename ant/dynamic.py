import maya.cmds as cmds
import maya.mel as mel


def antcgiDynJoints(*args):
    globalName = cmds.textField('systemName', q=1, tx=1)
    addDynamics = cmds.checkBox('addDynamics', q=1, v=1)
    conScale = cmds.floatField('conScaleInput', q=1, v=1)
    rootJoint = cmds.ls(sl=1, type='joint')
    if not rootJoint:
        cmds.error('Please select the root joint.')
    else:
        if len(rootJoint) > 1:
            cmds.error('Please only select one joint.')
        jointChainList = cmds.listRelatives(type='joint', ad=1)
        jointChainList.reverse()
        jointChainList.insert(0, rootJoint[0])
        midJoint = jointChainList[int(len(jointChainList) / 2)]
        cmds.select(cl=1)
        for jointChain in jointChainList:
            addOrientJoint(jointChain + '_fk', jointChain, 'xyz', 0, 0, 0)

        cmds.select(cl=1)
        for jointChain in jointChainList:
            addOrientJoint(jointChain + '_ik', jointChain, 'xyz', 0, 0, 0)

        for jointChain in jointChainList:
            cmds.parentConstraint((jointChain.lower() + '_ik'),
                                  (jointChain.lower() + '_fk'), jointChain, w=1, mo=0)

        build_RigIcon('Slider', globalName + '_ctrl',
                      'Blue', conScale * 4, 'Y')
        build_RigIcon('FKLabel', globalName + '_ik_label',
                      'Black', conScale * 2, 'Y')
        build_RigIcon('IKLabel', globalName + '_fk_label',
                      'Black', conScale * 2, 'Y')
        cmds.parent(globalName + '_ik_label', globalName +
                    '_fk_label', globalName + '_ctrl')
        cmds.matchTransform((globalName + '_ctrl'), rootJoint, pos=1)
        cmds.setAttr(globalName + '_fk_label.rotateY', 90)
        cmds.setAttr(globalName + '_ik_label.rotateY', 90)
        cmds.move(0, 10, 0, (globalName + '_ctrl'), wd=1, r=1, os=1)
        cmds.addAttr((globalName + '_ctrl'), ln='FK_IK_Switch',
                     at='double', min=0, max=1, dv=0)
        cmds.setAttr((globalName + '_ctrl.FK_IK_Switch'), e=1, keyable=1)
        if addDynamics:
            cmds.addAttr((globalName + '_ctrl'), ln='dynDivider',
                         nn='----------', at='enum', en='DYNAMICS:')
            cmds.setAttr((globalName + '_ctrl.dynDivider'),
                         e=1, cb=1, keyable=0)
            cmds.addAttr((globalName + '_ctrl'), ln='Simulation',
                         at='double', min=0, max=1, dv=0)
            cmds.setAttr((globalName + '_ctrl.Simulation'), e=1, keyable=1)
            cmds.addAttr((globalName + '_ctrl'), ln='Follow_Pose',
                         at='double', min=0, max=1, dv=0)
            cmds.setAttr((globalName + '_ctrl.Follow_Pose'), e=1, keyable=1)
        cmds.pointConstraint(rootJoint, (globalName + '_ctrl'), w=1, mo=1)
        conColour = 'Yellow'
        if addDynamics:
            conType = ('_fk', '_dyn')
        else:
            conType = ('_fk', )
    for con in conType:
        if con == '_dyn':
            conColour = 'Green'
        for i in range(len(jointChainList)):
            build_RigIcon(
                'Circle', jointChainList[i] + con + '_ctrl', conColour, conScale * 3, 'Z')
            cmds.group((jointChainList[i] + con + '_ctrl'),
                       n=(jointChainList[i] + con + '_ctrl_offset'))
            cmds.xform((jointChainList[i] + con + '_ctrl_offset'), ws=1, piv=(0, 0,
                                                                              0))
            cmds.matchTransform(
                (jointChainList[i] + con + '_ctrl_offset'), (jointChainList[i].lower() + '_fk'), rot=1, pos=1)
            if con == '_fk':
                cmds.parentConstraint(
                    (jointChainList[i] + con + '_ctrl'), (jointChainList[i].lower() + con), w=1, mo=0)
            if i > 0:
                cmds.parent(
                    jointChainList[i] + con + '_ctrl_offset', jointChainList[(i - 1)] + con + '_ctrl')

    ikContList = (
        jointChainList[0] + '_ik_ctrl', jointChainList[(-1)] + '_ik_ctrl', midJoint + '_ik_ctrl')
    for ikCont in ikContList:
        build_RigIcon('IKHandle', ikCont, 'Red', conScale * 4, 'Z')
        cmds.group(ikCont, n=(ikCont + '_offset'))
        cmds.matchTransform((ikCont + '_offset'),
                            (ikCont.replace('_ik_ctrl', '')), rot=1, pos=1)

    cmds.select(cl=1)
    cmds.group((jointChainList[0] + '_ik_ctrl_offset'), (jointChainList[(-1)] +
                                                         '_ik_ctrl_offset'), (midJoint + '_ik_ctrl_offset'), n=(globalName + '_ik_controls'))
    cmds.group(em=1, n=(globalName + '_ctrljnts'))
    if addDynamics:
        cmds.group(em=1, n=(globalName + '_dynamics'))
        cmds.group(em=1, n=(globalName + '_deformers'))
        cmds.group(em=1, n=(globalName + '_follicles'))
    cmds.shadingNode('reverse', au=1, n=(globalName + '_fkik_reverse'))
    cmds.connectAttr((globalName + '_ctrl.FK_IK_Switch'),
                     (globalName + '_fkik_reverse.inputX'), f=1)
    cmds.connectAttr((globalName + '_fkik_reverse.outputX'),
                     (jointChainList[0] + '_fk_ctrl_offset.visibility'), f=1)
    cmds.connectAttr((globalName + '_fkik_reverse.outputX'),
                     (globalName + '_ik_label.visibility'), f=1)
    cmds.connectAttr((globalName + '_ctrl.FK_IK_Switch'),
                     (midJoint + '_ik_ctrl_offset.visibility'), f=1)
    cmds.connectAttr((globalName + '_ctrl.FK_IK_Switch'),
                     (jointChainList[0] + '_ik_ctrl_offset.visibility'), f=1)
    cmds.connectAttr((globalName + '_ctrl.FK_IK_Switch'),
                     (jointChainList[(-1)] + '_ik_ctrl_offset.visibility'), f=1)
    cmds.connectAttr((globalName + '_ctrl.FK_IK_Switch'),
                     (globalName + '_fk_label.visibility'), f=1)
    constBlend(jointChainList, '', globalName + '_ctrl.FK_IK_Switch',
               globalName + '_fkik_reverse.outputX')
    contJntList = (
        jointChainList[0], midJoint, jointChainList[(-1)])
    for contJnt in contJntList:
        addOrientJoint(contJnt.lower() + '_ctrljnt', contJnt, 'xyz', 0, 0, 0)
        cmds.parent(contJnt.lower() + '_ctrljnt', globalName + '_ctrljnts')
        if cmds.objExists(contJnt + '_ik_ctrl'):
            cmds.parentConstraint((contJnt + '_ik_ctrl'),
                                  (contJnt.lower() + '_ctrljnt'), w=1, mo=0)
        cmds.select(cl=1)

    rootPivot = cmds.xform((jointChainList[0]), q=True, ws=True, piv=True)
    cmds.curve(d=3, p=(rootPivot[0], rootPivot[1],
                       rootPivot[2]), n=(globalName + '_ik_curve'))
    for i in range(1, len(jointChainList)):
        pointPivot = cmds.xform((jointChainList[i]), q=True, ws=True, piv=True)
        cmds.curve((globalName + '_ik_curve'), a=1,
                   p=(pointPivot[0], pointPivot[1], pointPivot[2]))

    if addDynamics:
        cmds.duplicate((globalName + '_ik_curve'),
                       n=(globalName + '_ik_dynamic_curve'))
    cmds.ikHandle(n=(globalName + '_ikHandle'), sol='ikSplineSolver', ccv=0, roc=1, pcv=0, sj=(
        jointChainList[0].lower() + '_ik'), ee=(jointChainList[(-1)].lower() + '_ik'), c=(globalName + '_ik_curve'))
    cmds.skinCluster((jointChainList[0].lower() + '_ctrljnt', midJoint.lower() + '_ctrljnt', jointChainList[(-1)].lower(
    ) + '_ctrljnt'), (globalName + '_ik_curve'), tsb=1, dr=10, mi=3, n=(globalName + '_ik_curve_skinCluster'))
    cmds.shadingNode('plusMinusAverage', au=1,
                     n=(globalName + '_uppertwist_pma'))
    cmds.shadingNode('multiplyDivide', au=1, n=(
        globalName + '_uppercomp_mult'))
    cmds.setAttr(globalName + '_uppercomp_mult.input2X', -1)
    cmds.connectAttr(
        (jointChainList[0] + '_ik_ctrl.rotateX'), (globalName + '_ikHandle.roll'), f=1)
    cmds.connectAttr((globalName + '_ikHandle.roll'),
                     (globalName + '_uppercomp_mult.input1X'), f=1)
    cmds.connectAttr((jointChainList[(-1)] + '_ik_ctrl.rotateX'),
                     (globalName + '_uppertwist_pma.input1D[0]'), f=1)
    cmds.connectAttr((globalName + '_uppercomp_mult.outputX'),
                     (globalName + '_uppertwist_pma.input1D[1]'), f=1)
    cmds.connectAttr((globalName + '_uppertwist_pma.output1D'),
                     (globalName + '_ikHandle.twist'), f=1)
    cmds.shadingNode('curveInfo', au=1, n=(globalName + '_ik_curveinfo'))
    cmds.shadingNode('multiplyDivide', au=1, n=(
        globalName + '_ik_scaleFactor'))
    cmds.connectAttr((cmds.listRelatives((globalName + '_ik_curve'), c=1, s=1)
                      [0] + '.worldSpace[0]'), (globalName + '_ik_curveinfo.inputCurve'), f=1)
    cmds.connectAttr((globalName + '_ik_curveinfo.arcLength'),
                     (globalName + '_ik_scaleFactor.input1X'), f=1)
    cmds.setAttr(globalName + '_ik_scaleFactor.input2X',
                 cmds.getAttr(globalName + '_ik_scaleFactor.input1X'))
    cmds.setAttr(globalName + '_ik_scaleFactor.operation', 2)
    cmds.shadingNode('multiplyDivide', au=1, n=(globalName + '_ik_volume'))
    cmds.setAttr(globalName + '_ik_volume.operation', 3)
    cmds.setAttr(globalName + '_ik_volume.input2X', -1)
    cmds.connectAttr((globalName + '_ik_scaleFactor.outputX'),
                     (globalName + '_ik_volume.input1X'), f=1)
    for i in range(len(jointChainList) - 1):
        cmds.connectAttr((globalName + '_ik_scaleFactor.outputX'),
                         (jointChainList[i].lower() + '_ik.scaleX'), f=1)
        cmds.connectAttr((globalName + '_ik_scaleFactor.outputX'),
                         (jointChainList[i] + '.scaleX'), f=1)
        cmds.connectAttr((globalName + '_ik_volume.outputX'),
                         (jointChainList[i] + '.scaleY'), f=1)
        cmds.connectAttr((globalName + '_ik_volume.outputX'),
                         (jointChainList[i] + '.scaleZ'), f=1)

    if addDynamics:
        cmds.select((globalName + '_ik_dynamic_curve'), r=1)
        mel.eval('makeCurvesDynamic 2 { "0", "0", "1", "1", "0"}')
        dynFollicle = cmds.listRelatives(
            (globalName + '_ik_dynamic_curve'), p=1)[0]
        dynFollicleShape = cmds.listRelatives(dynFollicle, s=1)[0]
        hairSystemList = cmds.listConnections(dynFollicleShape)
        for hairSystem in hairSystemList:
            if 'hairSystem' in hairSystem:
                hairSystemShape = cmds.listRelatives(hairSystem, c=1)[0]

        cmds.setAttr(dynFollicleShape + '.pointLock', 1)
        dynCurveConnections = cmds.listConnections(dynFollicleShape, sh=1)
        for dynCurve in dynCurveConnections:
            if 'curveShape' in dynCurve:
                outputCurve = cmds.listRelatives(dynCurve, p=1)[0]

        cmds.rename(dynFollicle, globalName + '_follicle')
        cmds.rename(outputCurve, globalName + '_output_curve')
        cmds.blendShape((globalName + '_output_curve'),
                        (globalName + '_ik_curve'), n=(globalName + '_bshape'))
        cmds.connectAttr((globalName + '_ctrl.Simulation'),
                         (globalName + '_bshape.' + globalName + '_output_curve'), f=1)
        cmds.connectAttr((globalName + '_ctrl.Simulation'),
                         (jointChainList[0] + '_dyn_ctrl_offset.visibility'), f=1)
        cmds.connectAttr((globalName + '_ctrl.Simulation'),
                         (globalName + '_fkik_reverse.inputY'), f=1)
        cmds.connectAttr((globalName + '_fkik_reverse.outputY'),
                         (globalName + '_ik_controls.visibility'), f=1)
        cmds.connectAttr((globalName + '_ctrl.Follow_Pose'),
                         (hairSystemShape + '.startCurveAttract'), f=1)
        curveCVs = cmds.getAttr((globalName + '_ik_dynamic_curve.cp'), s=1)
        for i in range(curveCVs):
            cmds.cluster(
                (globalName + '_ik_dynamic_curve.cv[' + str(i) + ']'), n=(globalName + '_cluster_' + str(i)))
            cmds.parent(globalName + '_cluster_' + str(i) +
                        'Handle', jointChainList[i] + '_dyn_ctrl')

        cmds.parent(globalName + '_ik_dynamic_curve', globalName + '_output_curve',
                    globalName + '_ik_curve', globalName + '_ikHandle', globalName + '_deformers')
        cmds.parent(cmds.listRelatives(hairSystemShape, p=1)
                    [0], globalName + '_dynamics')
        cmds.parent(globalName + '_follicle', globalName + '_follicles')
    for con in conType:
        for i in range(len(jointChainList)):
            lockdownAttr(jointChainList[i] + con + '_ctrl', 0, 0, 1, 1, 0)
            lockdownAttr(jointChainList[i] + con +
                         '_ctrl_offset', 1, 1, 1, 1, 0)

    lockdownAttr(jointChainList[(-1)] + '_ik_ctrl', 0, 0, 1, 1, 0)
    lockdownAttr(jointChainList[(-1)] + '_ik_ctrl_offset', 1, 1, 1, 1, 0)
    lockdownAttr(midJoint + '_ik_ctrl', 0, 0, 1, 1, 0)
    lockdownAttr(midJoint + '_ik_ctrl_offset', 1, 1, 1, 1, 0)
    lockdownAttr(globalName + '_ctrl', 1, 1, 1, 1, 0)
    lockdownAttr(globalName + '_ik_label', 1, 1, 1, 1, 1)
    lockdownAttr(globalName + '_fk_label', 1, 1, 1, 1, 1)
    cmds.select(cl=1)


def lockdownAttr(name, doTranslate, doRotate, doScale, doVisibility, doReference):
    if doTranslate:
        cmds.setAttr((name + '.tx'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.ty'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.tz'), l=1, k=0, cb=0)
    if doRotate:
        cmds.setAttr((name + '.rx'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.ry'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.rz'), l=1, k=0, cb=0)
    if doScale:
        cmds.setAttr((name + '.sx'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.sy'), l=1, k=0, cb=0)
        cmds.setAttr((name + '.sz'), l=1, k=0, cb=0)
    if doVisibility:
        cmds.setAttr((name + '.v'), l=1, k=0, cb=0)
    if doReference:
        cmds.setAttr(name + '.overrideEnabled', 1)
        cmds.setAttr(name + '.overrideDisplayType', 2)


def constBlend(nodeList, side, sourceAttr, destAttr, *args):
    for node in nodeList:
        getConstraint = cmds.listConnections(
            (node + side), type='parentConstraint')[0]
        getWeights = cmds.parentConstraint(getConstraint, q=1, wal=1)
        cmds.connectAttr(
            sourceAttr, (getConstraint + '.' + getWeights[0]), f=1)
        cmds.connectAttr(destAttr, (getConstraint + '.' + getWeights[1]), f=1)


def addOrientJoint(jointName, jointPosName, roOrder, *orientOffset):
    conScale = cmds.floatField('conScaleInput', q=1, v=1)
    getPosPoint = cmds.xform(jointPosName, q=1, ws=1, piv=1)
    cmds.joint(p=(getPosPoint[0], getPosPoint[1], getPosPoint[2]),
               rad=conScale, roo=roOrder, n=(jointName.lower()))
    cmds.orientConstraint(jointPosName, (jointName.lower()), w=1, n='tmpOC')
    cmds.delete('tmpOC')
    cmds.rotate((orientOffset[0]), (orientOffset[1]), (orientOffset[2]),
                (jointName.lower() + '.rotateAxis'), a=1, os=1, fo=1)
    cmds.joint((jointName.lower()), e=1, zso=1)
    cmds.makeIdentity((jointName.lower()), a=1, t=0, r=1, s=0)


def build_RigIcon(iconType, iconName, colour, scale, orientation):
    if colour == 'Red':
        colour = [1, 0, 0]
    else:
        if colour == 'Blue':
            colour = [0, 0, 1]
        else:
            if colour == 'Yellow':
                colour = [1, 1, 0]
            else:
                if colour == 'Green':
                    colour = [0, 1, 0]
                else:
                    if colour == 'Black':
                        colour = [0, 0, 0]
    if orientation == 'X':
        rotAxis = '.rotateX'
    if orientation == 'Z':
        rotAxis = '.rotateZ'
    if iconType == 'Circle':
        cmds.circle(nr=(0, 1, 0), n=iconName, r=0.5, s=12)
    if iconType == 'IKHandle':
        pointsListA = (
            [-7.138275697640435e-16, 1.1108536880093235e-16, -0.500284025538193],
            [-0.3187661567675381, 7.078030534291776e-17, -0.3187661567675343],
            [-0.5002840255381937, 0, 1.110853688009325e-16],
            [-0.318766156767538, -7.078030534291776e-17, 0.31876615676753434],
            [-4.916568321621789e-16, -1.1108536880093235e-16, 0.500284025538193],
            [0.318766156767532, -7.078030534291776e-17, 0.3187661567675343],
            [0.5002840255381937, 0, -1.110853688009325e-16],
            [0.3187661567675319, 7.078030534291776e-17, -0.31876615676753434],
            [-7.138275697640435e-16, 1.1108536880093235e-16, -0.500284025538193])
        pointsListB = (
            [0.30719697801356827, 9.646553170190997e-17, -0.30719697801356916],
            [-3.9882920891183316e-15, 6.100981948142313e-17, -0.3885746928086574],
            [-0.30719697801356927, 0, -0.3071969780135692],
            [-0.3885746928086576, -6.100981948142313e-17, -3.93716013925784e-15],
            [-0.30719697801356904, -9.646553170190997e-17, 0.3071969780135684],
            [-6.391493732561429e-16, -6.100981948142313e-17, 0.3885746928086528],
            [0.30719697801356927, 0, 0.3071969780135692],
            [0.3885746928086528, 6.100981948142313e-17, -7.669792479073714e-16],
            [0.30719697801356827, 9.646553170190997e-17, -0.30719697801356916])
        cmds.curve(d=1, p=(pointsListA[0]), n=iconName)
        for i in range(len(pointsListA)):
            if i < len(pointsListA) - 1:
                cmds.curve(iconName, a=1, p=(pointsListA[(i + 1)]))

        cmds.curve(d=1, p=(pointsListB[0]), n=(iconName + '_inner'))
        for i in range(len(pointsListB)):
            if i < len(pointsListB) - 1:
                cmds.curve((iconName + '_inner'), a=1,
                           p=(pointsListB[(i + 1)]))

        cmds.parent((cmds.listRelatives(iconName + '_inner')),
                    iconName, s=1, r=1)
        cmds.rotate(0, (-90), 0, iconName, r=1, fo=1)
        cmds.makeIdentity(iconName, a=1, r=1)
        cmds.delete(iconName + '_inner')
    if iconType == 'Slider':
        pointsList = (
            [-2.228315569214431e-16, -6.045349829263037e-16, -0.5017720583588998],
            [-4.4566311384289685e-17, -0.2007088233435597, -0.30106323501534193],
            [-8.913262276857779e-17, -0.10035441167178098, -0.30106323501534193],
            [1.7826524553715413e-16, -0.10035441167178098, 0.3010632350153377],
            [2.228315569214423e-16, -0.2007088233435597, 0.3010632350153377],
            [2.228315569214436e-16, -6.045349829263037e-16, 0.5017720583588998],
            [4.456631138428771e-17, 0.20070882334355994, 0.3010632350153377],
            [8.913262276857642e-17, 0.10035441167177984, 0.3010632350153377],
            [-1.782652455371555e-16, 0.10035441167177984, -0.30106323501534193],
            [-2.228315569214442e-16, 0.20070882334355994, -0.30106323501534193],
            [-2.228315569214431e-16, -6.045349829263037e-16, -0.5017720583588998])
        cmds.curve(d=1, p=(pointsList[0]), n=iconName)
        for i in range(len(pointsList)):
            if i < len(pointsList) - 1:
                cmds.curve(iconName, a=1, p=(pointsList[(i + 1)]))

        cmds.rotate(0, (-90), 0, iconName, r=1, fo=1)
        cmds.makeIdentity(iconName, a=1, r=1)
    if iconType == 'FKLabel':
        pointsListA = (
            [-0.3727645590402576, 0.3812559481781222, -0.0019004885689956341],
            [-0.3727645590402576, 0.6519729149728076, -0.0019004885689956341],
            [-0.15941631946163998, 0.6519729149728076, -0.0019004885689956341],
            [-0.15941631946163998, 0.7196521489060346, -0.0019004885689956341],
            [-0.3727645590402576, 0.7196521489060346, -0.0019004885689956341],
            [-0.3727645590402576, 0.9226898817674931, -0.0019004885689956341],
            [-0.1189673929634345, 0.9226898817674931, -0.0019004885689956341],
            [-0.1189673929634345, 0.9903690846389424, -0.0019004885689956341],
            [-0.45736360922223573, 0.9903690846389424, -0.0019004885689956341],
            [-0.45736360922223573, 0.3812559481781222, -0.0019004885689956341],
            [-0.3727645590402576, 0.3812559481781222, -0.0019004885689956341])
        pointsListB = (
            [0.08407030883624633, 0.3812559481781222, -0.0019003563829690928],
            [0.08407030883624633, 0.6899103103719815, -0.0019003563829690928],
            [0.34632738303744504, 0.3812559481781222, -0.0019003563829690928],
            [0.45736360922223573, 0.3812559481781222, -0.0019003563829690928],
            [0.1796408137725205, 0.7004851683483955, -0.0019003563829690928],
            [0.416914713785808, 0.9903690846389424, -0.0019003563829690928],
            [0.3294075978504716, 0.9903690846389424, -0.0019003563829690928],
            [0.08407030883624633, 0.6907034107424126, -0.0019003563829690928],
            [0.08407030883624633, 0.9903690846389424, -0.0019003563829690928],
            [-0.0005287413457317758, 0.9903690846389424, -0.0019003563829690928],
            [-0.0005287413457317758, 0.3812559481781222, -0.0019003563829690928],
            [0.08407030883624633, 0.3812559481781222, -0.0019003563829690928])
        cmds.curve(d=1, p=(pointsListA[0]), n=iconName)
        for i in range(len(pointsListA)):
            if i < len(pointsListA) - 1:
                cmds.curve(iconName, a=1, p=(pointsListA[(i + 1)]))

        cmds.curve(d=1, p=(pointsListB[0]), n=(iconName + '_inner'))
        for i in range(len(pointsListB)):
            if i < len(pointsListB) - 1:
                cmds.curve((iconName + '_inner'), a=1,
                           p=(pointsListB[(i + 1)]))

        cmds.parent((cmds.listRelatives(iconName + '_inner')),
                    iconName, s=1, r=1)
        cmds.rotate(0, (-90), 0, iconName, r=1, fo=1)
        cmds.makeIdentity(iconName, a=1, r=1)
        cmds.delete(iconName + '_inner')
    if iconType == 'IKLabel':
        pointsListA = (
            [-0.27672412079123787, 0.3812559481781222, 0.0019003563829691206],
            [-0.27672412079123787, 0.9903690846389424, 0.0019003563829691206],
            [-0.361323170973216, 0.9903690846389424, 0.0019003563829691206],
            [-0.361323170973216, 0.3812559481781222, 0.0019003563829691206],
            [-0.27672412079123787, 0.3812559481781222, 0.0019003563829691206])
        pointsListB = (
            [-0.03138687836967913, 0.3812559481781222, 0.0019004885689956341],
            [-0.03138687836967913, 0.6899103103719815, 0.0019004885689956341],
            [0.23087016476974187, 0.3812559481781222, 0.0019004885689956341],
            [0.341906453078088, 0.3812559481781222, 0.0019004885689956341],
            [0.06418362656659504, 0.7004851683483955, 0.0019004885689956341],
            [0.30145749551810486, 0.9903690846389424, 0.0019004885689956341],
            [0.2139503795827684, 0.9903690846389424, 0.0019004885689956341],
            [-0.03138687836967913, 0.6907034107424126, 0.0019004885689956341],
            [-0.03138687836967913, 0.9903690846389424, 0.0019004885689956341],
            [-0.11598592855165724, 0.9903690846389424, 0.0019004885689956341],
            [-0.11598592855165724, 0.3812559481781222, 0.0019004885689956341],
            [-0.03138687836967913, 0.3812559481781222, 0.0019004885689956341])
        cmds.curve(d=1, p=(pointsListA[0]), n=iconName)
        for i in range(len(pointsListA)):
            if i < len(pointsListA) - 1:
                cmds.curve(iconName, a=1, p=(pointsListA[(i + 1)]))

        cmds.curve(d=1, p=(pointsListB[0]), n=(iconName + '_inner'))
        for i in range(len(pointsListB)):
            if i < len(pointsListB) - 1:
                cmds.curve((iconName + '_inner'), a=1,
                           p=(pointsListB[(i + 1)]))

        cmds.parent((cmds.listRelatives(iconName + '_inner')),
                    iconName, s=1, r=1)
        cmds.rotate(0, (-90), 0, iconName, r=1, fo=1)
        cmds.makeIdentity(iconName, a=1, r=1)
        cmds.delete(iconName + '_inner')
    cmds.setAttr(iconName + '.ove', 1)
    cmds.setAttr(iconName + '.overrideRGBColors', 1)
    cmds.setAttr(iconName + '.overrideColorRGB',
                 colour[0], colour[1], colour[2])
    cmds.setAttr(iconName + '.scale', scale, scale, scale)
    if orientation != 'Y':
        cmds.setAttr(iconName + rotAxis, 90)
    cmds.makeIdentity(iconName, a=1, t=1, r=1, s=1)
    cmds.controller(iconName)
    cmds.delete(iconName, ch=1)
    cmds.select(cl=1)


def antcgiDynJointsUI():
    if cmds.window('antcgiDynJointsUI', ex=1):
        cmds.deleteUI('antcgiDynJointsUI')
    window = cmds.window(
        'antcgiDynJointsUI', t='Dynamic Joints v2', w=200, h=100, mnb=0, mxb=0, s=0)
    mainLayout = cmds.formLayout(nd=100)
    systemName = cmds.textField(
        'systemName', h=20, tx='Simulation_Name', ann='Dynamics Systems Name')
    conScaleLabel = cmds.text(
        'conScaleLabel', label='Control Scale', align='left', h=20)
    conScaleInput = cmds.floatField(
        'conScaleInput', h=20, w=50, pre=2, ann='Overall size of the controls.', v=1)
    button01 = cmds.button(l='Make Dynamic', h=50, c=antcgiDynJoints)
    addDynamics = cmds.checkBox(
        'addDynamics', l='Include Dynamics', h=20, ann='Include dynamics?', v=1)
    cmds.formLayout(mainLayout, e=1, attachForm=[
        (
            systemName, 'top', 5), (systemName, 'left', 5), (systemName, 'right', 5),
        (
            conScaleLabel, 'left', 20),
        (
            addDynamics, 'left', 25),
        (
            button01, 'bottom', 5), (button01, 'left', 5), (button01, 'right', 5)],
        attachControl=[
        (
            conScaleLabel, 'top', 5, systemName),
        (
            conScaleInput, 'top', 5, systemName), (conScaleInput, 'left', 5, conScaleLabel),
        (
            addDynamics, 'top', 5, conScaleLabel),
        (
            button01, 'top', 5, addDynamics)])
    cmds.showWindow(window)
