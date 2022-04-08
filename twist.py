import pymel.core as pm

# Make upper twist joints
# Unparent primaryChain[2]
# Duplicate primaryChain[0] to make Twist joints
# Rename duplicate joints. Replace "primary" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent primaryChain[2] to primaryChain[1]

# Make lower twist joints
# Unparent primaryChain[1]
# if len(primaryChain) > 3: Unparent primaryChain[3]
# Duplicate primaryChain[1]
# Rename duplicate joints. Replace "primary" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent primaryChain[1] to primaryChain[0]
# if primaryChain[3]: reparent primaryChain[3] to primaryChain[2]

# Make meta twist joints
# Check if needed
# Unparent primaryChain[2]
# if len(primaryChain) > 4 (it shouldn't be): unparent primaryChain[4]
# Duplicate primaryChain[2]
# Rename duplicate joints. Replace "primary" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent primaryChain[2] to primaryChain[1]
# if primarys[4] (there shouldn't be): reparent primaryChain[4] to primaryChain[3]

# Make the follow joints
# Duplicate Twist chains to make Follow joints
# Rename duplicate joints. Replace "twist" with "follow"
# IK constrain the follow chain
# Parent IK handle to next joint in driveChain
# Point constrain follow_end to corresponding driveChain joint (or, better yet, create a twist_grp)

# Set up twist functionality
# For joint in twist joint:
#   create locator
#   rename locator. Replace "jnt" with "up_loc"
#   create offset group for end_up_loc
#   matrix move (or pt/orient constrain and delete if earlier Maya version) offset_grp to next joint in primary chain
#   move locator based on scale
#   parent twist_jnt to corresponding follow_jnt
#   parent twist_start_up_loc to follow_start
#   parent constrain twist_end_loc_grp to next joint diver chain (only constrain rotation along one axis)
#   aim constrain twist joint to its "start" or "end" partner - set corresponding up_loc as up




