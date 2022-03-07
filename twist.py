import pymel.core as pm

# Make upper twist joints
# Unparent driverChain[2]
# Duplicate driverChain[0] to make Twist joints
# Rename duplicate joints. Replace "driver" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent driverChain[2] to driverChain[1]

# Make lowerj twist joints
# Unparent driverChain[1]
# if len(driverChain) > 3: Unparent driverChain[3]
# Duplicate driverChain[1]
# Rename duplicate joints. Replace "driver" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent driverChain[1] to driverChain[0]
# if driverChain[3]: reparent driverChain[3] to driverChain[2]

# Make meta twist joints
# Check if needed
# Unparent driverChain[2]
# if len(driverChain) > 4 (it shouldn't be): unparent driverChain[4]
# Duplicate driverChain[2]
# Rename duplicate joints. Replace "driver" with "twist_start" and "twist_end" (check for 1 at end of start)
# Reparent driverChain[2] to driverChain[1]
# if drivers[4] (there shouldn't be): reparent driverChain[4] to driverChain[3]

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
#   matrix move (or pt/orient constrain and delete if earlier Maya version) offset_grp to next joint in driver chain
#   move locator based on scale
#   parent twist_jnt to corresponding follow_jnt
#   parent twist_start_up_loc to follow_start
#   parent constrain twist_end_loc_grp to next joint diver chain (only constrain rotation along one axis)
#   aim constrain twist joint to its "start" or "end" partner - set corresponding up_loc as up




