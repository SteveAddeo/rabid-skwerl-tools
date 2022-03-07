import pymel.core as pm
import matrix


def make_offset_groups():
    offsetGrps = []
    if not pm.ls(sl=1):
        pm.error("Nothing Selected")
    for node in pm.ls(sl=1):
        parent = pm.listRelatives(p=1)
        grp = pm.group(em=1, n="{}_offset_grp".format(node))
        matrix.worldspace_to_matrix(grp, node)
        if parent:
            pm.parent(grp, parent[0])
        pm.parent(node, grp)
        offsetGrps.append(grp)
    return offsetGrps
