def translate_mgear_to_rigify(joint_name):
    mgear_list = list(filter(lambda x: RIGIFY_MGEAR_BONES[x] == joint_name, RIGIFY_MGEAR_BONES))
    if not mgear_list:
        mgear_list = [key for key, val in RIGIFY_MGEAR_BONES.items() if any(joint_name in s for s in val)]
    if not mgear_list:
        return False, f"Joint {joint_name} does not have a Rigify equivalent. Please check the name"
    return True, mgear_list


def translate_rigify_to_mgear(bone_name):
    if not RIGIFY_MGEAR_BONES[bone_name]:
        return False, f"Bone {bone_name} does not does not have an MGear equivalent. Please check the name"
    return True, RIGIFY_MGEAR_BONES[bone_name]


RIGIFY_MGEAR_BONES = {
    "DEF-spine": "spine_C0_0_jnt",
    "DEF-thigh.L": ["leg_L0_0_jnt", "leg_L0_1_jnt"],
    "DEF-thigh.L.001": ["leg_L0_2_jnt", "leg_L0_1_jnt"],
    "DEF-shin.L": ["leg_L0_3_jnt", "leg_L0_4_jnt"],
    "DEF-shin.L.001": ["leg_L0_5_jnt", "leg_L0_4_jnt", "leg_L0_6_jnt"],
    "DEF-foot.L": "leg_L0_end_jnt",
    "DEF-toe.L": "foot_L0_1_jnt",
    "DEF-thigh.R": ["leg_R0_0_jnt", "leg_R0_1_jnt"],
    "DEF-thigh.R.001": ["leg_R0_2_jnt", "leg_R0_1_jnt"],
    "DEF-shin.R": ["leg_R0_3_jnt", "leg_R0_4_jnt"],
    "DEF-shin.R.001": ["leg_R0_5_jnt", "leg_R0_4_jnt", "leg_R0_6_jnt"],
    "DEF-foot.R": "leg_R0_end_jnt",
    "DEF-toe.R": "foot_R0_1_jnt",
    "DEF-spine.001": "spine_C0_1_jnt",
    "DEF-spine.002": "spine_C0_2_jnt",
    "DEF-spine.003": "spine_C0_3_jnt",
    "DEF-spine.004": "spine_C0_4_jnt",
    "DEF-spine.005": "neck_C0_0_jnt",
    "DEF-spine.006": "neck_C0_1_jnt",
    "DEF-spine.007": "Face",
    "DEF-shoulder.L": "shoulder_L0_shoulder_jnt",
    "DEF-upper_arm.L": ["arm_L0_0_jnt", "arm_L0_1_jnt"],
    "DEF-upper_arm.L.001": ["arm_L0_2_jnt", "arm_L0_1_jnt"],
    "DEF-forearm.L": ["arm_L0_3_jnt", "arm_L0_4_jnt"],
    "DEF-forearm.L.001": ["arm_L0_5_jnt", "arm_L0_4_jnt"],
    "DEF-hand.L": "arm_L0_end_jnt",
    "DEF-palm.01.L": "meta_L0_0_jnt",
    "DEF-f_index.01.L": "finger_L0_0_jnt",
    "DEF-f_index.02.L": "finger_L0_1_jnt",
    "DEF-f_index.03.L": "finger_L0_2_jnt",
    "DEF-palm.02.L": "meta_L0_1_jnt",
    "DEF-f_middle.01.L": "finger_L1_0_jnt",
    "DEF-f_middle.02.L": "finger_L1_1_jnt",
    "DEF-f_middle.03.L": "finger_L1_2_jnt",
    "DEF-palm.03.L": "meta_L0_2_jnt",
    "DEF-f_ring.01.L": "finger_L2_0_jnt",
    "DEF-f_ring.02.L": "finger_L2_1_jnt",
    "DEF-f_ring.03.L": "finger_L2_2_jnt",
    "DEF-palm.04.L": "meta_L0_3_jnt",
    "DEF-f_pinky.01.L": "finger_L3_0_jnt",
    "DEF-f_pinky.02.L": "finger_L3_1_jnt",
    "DEF-f_pinky.03.L": "finger_L3_2_jnt",
    "DEF-thumb.01.L": "thumb_L0_0_jnt",
    "DEF-thumb.02.L": "thumb_L0_1_jnt",
    "DEF-thumb.03.L": "thumb_L0_2_jnt",
    "DEF-shoulder.R ": "shoulder_R0_shoulder_jnt",
    "DEF-upper_arm.R": ["arm_R0_0_jnt", "arm_R0_1_jnt"],
    "DEF-upper_arm.R.001": ["arm_R0_2_jnt", "arm_R0_1_jnt"],
    "DEF-forearm.R": ["arm_R0_3_jnt", "arm_R0_4_jnt"],
    "DEF-forearm.R.001": ["arm_R0_5_jnt", "arm_R0_4_jnt"],
    "DEF-hand.R": "arm_R0_end_jnt",
    "DEF-palm.01.R": "meta_R0_0_jnt",
    "DEF-f_index.01.R": "finger_R0_0_jnt",
    "DEF-f_index.02.R": "finger_R0_1_jnt",
    "DEF-f_index.03.R": "finger_R0_2_jnt",
    "DEF-palm.02.R": "meta_R0_1_jnt",
    "DEF-f_middle.01.R": "finger_R1_0_jnt",
    "DEF-f_middle.02.R": "finger_R1_1_jnt",
    "DEF-f_middle.03.R": "finger_R1_2_jnt",
    "DEF-palm.03.R": "meta_R0_2_jnt",
    "DEF-f_ring.01.R": "finger_R2_0_jnt",
    "DEF-f_ring.02.R": "finger_R2_1_jnt",
    "DEF-f_ring.03.R": "finger_R2_2_jnt",
    "DEF-palm.04.R": "meta_R0_3_jnt",
    "DEF-f_pinky.01.R": "finger_R3_0_jnt",
    "DEF-f_pinky.02.R": "finger_R3_1_jnt",
    "DEF-f_pinky.03.R": "finger_R3_2_jnt",
    "DEF-thumb.01.R": "thumb_R0_0_jnt",
    "DEF-thumb.02.R": "thumb_R0_1_jnt",
    "DEF-thumb.03.R": "thumb_R0_2_jnt",
}
