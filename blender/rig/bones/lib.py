import re
import bpy


def duplicate_bone(edit_bones, orig_bone, new_name):
    """
    Duplicates a bone in Edit Mode with a new name.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): The edit bones collection of the armature.
        orig_bone (bpy.types.EditBone): The bone to duplicate.
        new_name (str): The name for the new duplicated bone.

    Returns:
        bpy.types.EditBone: The newly created bone.

    Notes:
        - If a bone with the name `new_name` already exists, it will be removed before duplication.
        - The new bone copies the head, tail, and roll from the original bone.
        - The duplicated bone is created without any connection to other bones (`use_connect = False`).
    """
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    # Save properties from orig_bone BEFORE doing any deletion
    head = orig_bone.head.copy()
    tail = orig_bone.tail.copy()
    roll = orig_bone.roll
    # If a bone with the new name exists, remove it
    if new_name in edit_bones:
        edit_bones.remove(edit_bones[new_name])
    new_bone = edit_bones.new(new_name)
    new_bone.head = head
    new_bone.tail = tail
    new_bone.roll = roll
    new_bone.use_connect = False
    return new_bone


def get_unique_bone_name(base_name, suffix, edit_bones):
    """
    Generates a unique bone name by appending a numbered suffix.
    
    Args:
        base_name (str): The base part of the name (e.g. 'DEF-spine').
        suffix (str): The side/ending part (e.g. '.L' or '.C').
        edit_bones (bpy.types.ArmatureEditBones): The edit bones to check against.

    Returns:
        str: A unique bone name.
    """
    i = 1
    while True:
        candidate = f"{base_name}.{i:03d}{suffix}"
        if candidate not in edit_bones:
            return candidate
        i += 1


def make_def_from_meta(armature_obj, spine_div=3):
    """
    Duplicates all 'MTA-' bones from the 'Meta Bones' bone collection into a new 
    set of 'DEF-' bones under the 'Deformer Bones' collection.

    The DEF bones are independent of the original MTA bones but preserve the same 
    internal parent-child hierarchy among themselves. This creates a separate 
    parallel deformation hierarchy, commonly used in rig setups where control and 
    deformation structures are separated.

    The function also handles:
    - Automatic creation of the 'Deformer Bones' bone collection if it doesn't exist.
    - Removal of DEF bones from the 'Meta Bones' collection if they were accidentally assigned.

    Args:
        armature_obj (bpy.types.Object): The armature object containing the MTA bones 
        in the 'Meta Bones' collection.

    Raises:
        ValueError: If the provided object is not an armature.
        ValueError: If the 'Meta Bones' bone collection is not found.
    """
    if armature_obj.type != 'ARMATURE':
        raise ValueError("Selected object is not an armature!")

    bpy.context.view_layer.objects.active = armature_obj
    arm_data = armature_obj.data

    # Switch to Object Mode to access bone collections
    bpy.ops.object.mode_set(mode='OBJECT')

    # Setup new bone collections
    mta_bone_col = arm_data.collections.get("Meta Bones")
    if not mta_bone_col:
        raise ValueError("Bone Collection 'Meta Bones' not found.")
    def_bone_col = arm_data.collections.get("Deformer Bones")
    if not def_bone_col:
        def_bone_col = arm_data.collections.new(name="Deformer Bones")

    # Get MTA bone names
    mta_bone_names = [bone.name for bone in mta_bone_col.bones if bone.name.startswith("MTA-")]

    # Duplicate bones and store name mapping
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm_data.edit_bones
    mta_to_def = {}  # Map MTA bone name → DEF EditBone
    for mta_name in mta_bone_names:
        mta_bone = edit_bones.get(mta_name)
        if not mta_bone:
            continue
        def_name = mta_name.replace("MTA-", "DEF-", 1)
        def_bone = duplicate_bone(edit_bones, mta_bone, def_name)
        mta_to_def[mta_name] = def_bone

    # Rebuild DEF hierarchy based on MTA structure
    for mta_name, def_bone in mta_to_def.items():
        mta_bone = edit_bones[mta_name]
        if mta_bone.parent and mta_bone.parent.name in mta_to_def:
            def_bone.parent = mta_to_def[mta_bone.parent.name]
            def_bone.use_connect = mta_bone.use_connect

    bpy.ops.object.mode_set(mode='OBJECT')
    move_bones_to_collection([bone.name for bone in mta_to_def.values()], arm_data, mta_bone_col, def_bone_col)
    subdivide_bone(edit_bones, "DEF-spine.c", spine_div)
    print("✅ Deformer bones successfully created!")


def move_bones_to_collection(bone_names, arm_data, old_col, new_col, unassign_old=True):
    """
    Moves specified bones from one bone collection to another in Object Mode.

    Args:
        bones (list[bpy.types.PoseBone]): A list of pose bones to move.
        arm_data (bpy.types.Armature): The armature data block that contains the bones.
        old_col (bpy.types.BoneCollection): The bone collection to remove bones from.
        new_col (bpy.types.BoneCollection): The bone collection to assign bones to.
        unassign_old (bool, optional): Whether to unassign bones from the old collection. Defaults to True.

    Notes:
        - Ensures Blender is in Object Mode before processing.
        - Each bone is assigned to the `new_col`.
        - If `unassign_old` is True and a bone is part of `old_col`, it will be removed from it.
    """
    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for bone_name in bone_names:
        bone_data = arm_data.bones.get(bone_name)
        if not bone_data:
            continue
        new_col.assign(bone_data)
        if unassign_old and bone_data.name in old_col.bones:
            old_col.unassign(bone_data)


def subdivide_bone(edit_bones, bone_name, segments, connect_chain=True):
    """
    Subdivides a given EditBone into evenly spaced segments with a specific naming convention.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): The edit bones collection from the armature.
        bone_name (str): The name of the bone to subdivide.
        segments (int): Number of segments to split the bone into.
        connect_chain (bool): Whether the subdivided bones should be connected in a chain.

    Returns:
        list[bpy.types.EditBone]: A list of newly created bones in order from root to tip.
    """
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    orig_bone = edit_bones.get(bone_name)
    if not orig_bone:
        raise ValueError(f"Bone '{bone_name}' not found.")

    # Backup source bone data before removal
    head = orig_bone.head.copy()
    tail = orig_bone.tail.copy()
    roll = orig_bone.roll
    parent = orig_bone.parent
    children = [b for b in edit_bones if b.parent == orig_bone]
    direction = (tail - head) / segments

    # Extract base + side suffix
    match = re.match(r"(.*?)(\.[A-Z])?$", bone_name)
    base_name = match.group(1)
    suffix = match.group(2) if match.group(2) else ""

    # Remove original bone
    edit_bones.remove(orig_bone)

    new_bones = []
    prev_bone = None

    for i in range(segments):
        seg_head = head + direction * i
        seg_tail = head + direction * (i + 1)

        new_name = get_unique_bone_name(base_name, suffix, edit_bones)
        new_bone = edit_bones.new(new_name)
        new_bone.head = seg_head
        new_bone.tail = seg_tail
        new_bone.roll = roll

        if prev_bone:
            new_bone.parent = prev_bone
            new_bone.use_connect = connect_chain
        else:
            new_bone.parent = parent
            new_bone.use_connect = False  # Always disconnect from original parent

        prev_bone = new_bone
        new_bones.append(new_bone)

    # Reparent old children to the last new bone
    for child in children:
        child.parent = new_bones[-1]
        child.use_connect = False

    return new_bones

armature = bpy.data.objects['Armature']
# make_def_from_meta(armature)
# curves.create_spline_curve("MTA-neck.01.c", armature)