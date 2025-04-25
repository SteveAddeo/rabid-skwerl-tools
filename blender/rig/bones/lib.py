import re
import bpy
from ...utils import mode_utils

# TODO: move_bones_to_colletion() moves bones out of the original collection but not inot the new collection

def duplicate_bone(edit_bones, orig_bone, new_name):
    """Duplicates an EditBone with a new name.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): Collection of EditBones.
        orig_bone (bpy.types.EditBone): The original bone to duplicate.
        new_name (str): The name of the new duplicated bone.

    Returns:
        bpy.types.EditBone: The new duplicated bone.
    """
    head = orig_bone.head.copy()
    tail = orig_bone.tail.copy()
    roll = orig_bone.roll

    if new_name in edit_bones:
        edit_bones.remove(edit_bones[new_name])

    new_bone = edit_bones.new(new_name)
    new_bone.head = head
    new_bone.tail = tail
    new_bone.roll = roll
    new_bone.use_connect = False
    return new_bone

def get_unique_bone_name(base_name, suffix, edit_bones):
    """Generates a unique bone name using a base name, suffix, and index.

    Args:
        base_name (str): The base bone name.
        suffix (str): Side suffix (e.g., '.L', '.C').
        edit_bones (bpy.types.ArmatureEditBones): Collection to check for conflicts.

    Returns:
        str: A unique bone name.
    """
    i = 1
    while True:
        candidate = f"{base_name}.{i:03d}{suffix}"
        if candidate not in edit_bones:
            return candidate
        i += 1

def get_bone_chain(chain_prefix, side, armature_obj):
    """Returns a sorted list of bones in a chain by naming convention.

    Args:
        chain_prefix (str): Prefix of the bone name.
        side (str): Side identifier (e.g., 'c', 'l', 'r').
        armature_obj (bpy.types.Object): Armature object.

    Returns:
        List[bpy.types.EditBone]: Sorted list of chain bones.
    """
    bones = armature_obj.data.edit_bones
    pattern = re.compile(rf"^{re.escape(chain_prefix)}\.(\d+)\.{side}$", re.IGNORECASE)
    chain = [(int(m.group(1)), b) for b in bones if (m := pattern.match(b.name))]
    return [b for _, b in sorted(chain)]

def move_bones_to_collection(bone_names, armature_data, old_col, new_col, unassign_old=True):
    """Moves bones from one collection to another.

    Args:
        bone_names (List[str]): List of bone names to move.
        armature_data (bpy.types.Armature): The armature data block.
        old_col (bpy.types.BoneCollection): Original bone collection.
        new_col (bpy.types.BoneCollection): Target bone collection.
        unassign_old (bool, optional): Unassign from old collection. Defaults to True.
    """
    with mode_utils.ensure_mode(bpy.context.object, 'OBJECT'):
        for bone_name in bone_names:
            bone_data = armature_data.bones.get(bone_name)
            if not bone_data:
                continue
            new_col.assign(bone_data)
            if unassign_old and bone_data.name in old_col.bones:
                old_col.unassign(bone_data)

def subdivide_bone(edit_bones, bone_name, segments, connect_chain=True):
    """Subdivides a bone into multiple segments.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): Collection of EditBones.
        bone_name (str): Name of the bone to subdivide.
        segments (int): Number of segments.
        connect_chain (bool, optional): Whether to connect segments. Defaults to True.

    Returns:
        List[bpy.types.EditBone]: List of newly created segment bones.
    """
    orig_bone = edit_bones.get(bone_name)
    if not orig_bone:
        raise ValueError(f"Bone '{bone_name}' not found.")

    head = orig_bone.head.copy()
    tail = orig_bone.tail.copy()
    roll = orig_bone.roll
    parent = orig_bone.parent
    children = [b for b in edit_bones if b.parent == orig_bone]
    direction = (tail - head) / segments

    match = re.match(r"(.*?)(\.[A-Z])?$", bone_name)
    base_name = match.group(1)
    suffix = match.group(2) if match.group(2) else ""

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
            new_bone.use_connect = False

        prev_bone = new_bone
        new_bones.append(new_bone)

    for child in children:
        child.parent = new_bones[-1]
        child.use_connect = False

    return new_bones

def make_def_from_meta(armature_obj, spine_div=3):
    """Creates a DEF skeleton based on MTA bones, preserving hierarchy.

    Args:
        armature_obj (bpy.types.Object): Armature object.
        spine_div (int, optional): Number of spine segments to subdivide. Defaults to 3.

    Raises:
        ValueError: If armature or required collections are missing.
    """
    if armature_obj.type != 'ARMATURE':
        raise ValueError("Selected object is not an armature!")

    bpy.context.view_layer.objects.active = armature_obj
    armature_data = armature_obj.data

    with mode_utils.ensure_mode(armature_obj, 'OBJECT'):
        mta_bone_col = armature_data.collections.get("Meta Bones")
        if not mta_bone_col:
            raise ValueError("Bone Collection 'Meta Bones' not found.")

        def_bone_col = armature_data.collections.get("Deformer Bones")
        if not def_bone_col:
            def_bone_col = armature_data.collections.new(name="Deformer Bones")

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_data.edit_bones
        mta_to_def = {}
        for bone in mta_bone_col.bones:
            if not bone.name.startswith("MTA-"):
                continue
            mta_bone = edit_bones.get(bone.name)
            if not mta_bone:
                continue
            def_name = bone.name.replace("MTA-", "DEF-", 1)
            def_bone = duplicate_bone(edit_bones, mta_bone, def_name)
            mta_to_def[bone.name] = def_bone

        for mta_name, def_bone in mta_to_def.items():
            sanitize_bad_names(mta_to_def.values())
            mta_bone = edit_bones.get(mta_name)
            if mta_bone and mta_bone.parent and mta_bone.parent.name in mta_to_def:
                def_bone.parent = mta_to_def[mta_bone.parent.name]
                def_bone.use_connect = mta_bone.use_connect

    with mode_utils.ensure_mode(armature_obj, 'OBJECT'):
        move_bones_to_collection([b.name for b in mta_to_def.values()], armature_data, mta_bone_col, def_bone_col)

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        subdivide_bone(armature_data.edit_bones, "DEF-spine.c", spine_div)

    print("✅ Deformer bones successfully created!")


def sanitize_bad_names(bones):
    """Ensures all bone names are valid UTF-8 strings.

    Args:
        bones (Iterable[bpy.types.EditBone or bpy.types.Bone]): Bones to sanitize.

    Returns:
        List[bpy.types.Bone]: The list of bones with cleaned names.
    """
    for i, bone in enumerate(bones):
        try:
            bone.name.encode('utf-8')
        except UnicodeEncodeError:
            old = bone.name
            bone.name = f"recovered_bone_{i:03d}"
            print(f"⚠️ Renamed invalid bone '{old}' to '{bone.name}'")
    return bones    

# armature = bpy.data.objects['Armature']
# make_def_from_meta(armature)
# curves.create_spline_curve("MTA-neck.01.c", armature)