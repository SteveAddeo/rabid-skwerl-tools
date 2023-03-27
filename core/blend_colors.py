import pymel.core as pm
from core import constants


def check_connections(drivers, driven, bc_nodes):
    """
    checks to see if there are any connections between the drivers and the driven nodes
    :param drivers: list: objects that are driving the driven object
    :param driven: PyNode: the driven object
    :param bc_nodes: list: nodes that blend the transforms of the driver objects
    """
    for node in bc_nodes:
        if str(node).split("_")[-2] == "pos":
            attr = "translate"
        elif str(node).split("_")[-2] == "rot":
            attr = "rotate"
        else:
            attr = "scale"
        if not pm.isConnected(f"{drivers[0]}.{attr}", f"{node}.color1"):
            pm.connectAttr(f"{drivers[0]}.{attr}", f"{node}.color1")
        if not pm.isConnected(f"{node}.output", f"{driven.name()}.{attr}"):
            pm.connectAttr(f"{node}.output", f"{driven.name()}.{attr}")
        if len(drivers) > 1:
            if not pm.isConnected(f"{drivers[1]}.{attr}", f"{node}.color2"):
                pm.connectAttr(f"{drivers[1]}.{attr}", f"{node}.color2")
        else:
            pm.setAttr("{}.blender".format(node), 1)


def get_blend_colors(drivers=None, driven=None, constraint="all"):
    """
    returns a list of blend colors for the driven object
    :param drivers: list: objects that are driving the driven object
    :param driven: PyNode: the driven object
    :param constraint: str: the constraint to use
    :return: list: blend colors for the driven object
    """
    node_list = []
    if drivers is None or driven is None:
        driven = get_driver_driven()[1]
    for attr in constants.get_constrain_attrs(constraint):
        # Create a Blend Colors node (if one doesn't already exist)
        name = "_".join(driven.name().split("_")[:-1] + [attr, "bc"])
        if not driven.name().split("_")[:-1]:
            name = "_".join([driven.name(), attr, "bc"])
        if pm.ls(name):
            node_list.append(pm.PyNode(name))
            continue
        node = pm.createNode("blendColors", n=name)
        # Make sure both color(transform) values are set to 0
        node.color1.set(0, 0, 0)
        node.color2.set(0, 0, 0)
        # Add node to list of blend colors
        node_list.append(node)
    check_connections(drivers, driven, node_list)
    return node_list


def get_driver_driven():
    """
    returns the driven object and the driver objects
    :return: tuple: driven object and driver objects
    """
    # Check to make sure at least two objects are selected
    if not len(pm.ls(sl=1)) >= 2:
        return pm.error("Please select your driver objects and a driven object")

    driven = pm.ls(sl=1)[-1]
    drivers = [node for node in pm.ls(sl=1) if node not in driven]
    if len(drivers) > 2:
        pm.warning("more than two drivers were selected; only the first two are used")
    drivers = drivers[0:2]
    return drivers, driven
