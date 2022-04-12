import pymel.core as pm
import primary


def duplicate_joints_from_chain(joints):
    # can be used to make IK and FK joints as well as stretch joints
    pass


class Build(object):
    def __init__(self, fkik_obj):
        self.fkikObj = fkik_obj
        # Needs a curves option
        # The object-oriented nature of this will mean the the IK system will have been built by
        # the time we get to this point so knowing whether or not we need to use a curve function
        # can be entirely dependent on whether a curve exists
        # (if self.fkikObj.ikSplineCrv is not None)
        self.name = self.fkikObj.name
        self.ikCtls = None
        # Stretch functions require a number of different utility nodes in order to work properly
        # These can be stored as variables an called at a later time when it comes time to connect control attrs

        # FK and IK methods vary

        # Attrs:
        # Operations: [Squash, Stretch, Squash & Stretch, None]
        # Amnt
        # Max

        # IK stretch:

        # Get bone distance:
        # in a 3 joint chain, distance = {joint[1]}.translate{aimAxis} - {joint[2]}.translate{aimAxis}

        # Calculate bone distance based on rig scale:
        # Multiply Node: joint distance x scale of root control (matrix calculation)

        # Get control distance:
        # - create two locators and parent to the base and end IK controls
        # - use a distance between node

        # Get Scale Amount:
        # Divide node: control distance / bone distance

        # Calculate scale amount from Stretch Amnt
        # Multiply node: Scale Amount x Stretch Amnt

        # Calculate Max Stretch:
        # Clamp node: min = 1, max = Max Stretch, input = Scale Amount

        # Condition Node:
        # if control distance > bone distance:
        #    bone scale aim = clamped scale amount
        # else
        #    bone scale aim = 1
        # *** can the opperation change to be <, !=, or = to creat a stretch, squash, squash and stretch, none? ***

        # FK Stretch:

        # Calculate scale amount:
        # Multiply node: ctl aim scale x Stretch Amnt

        # Calculate Max Stretch (similar to IK, prehaps a different flag):
        # Clamp node: min = 1, max = Max Stretch, input = Scale Amount

