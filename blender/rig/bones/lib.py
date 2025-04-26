import re
import bpy
from ...utils import mode_utils


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


def make_def_from_meta(armature_name, mta_bone_names, debug=False):
    """Creates DEF bones by duplicating the provided list of MTA bones.

    Args:
        armature_name (str): Name of the armature.
        mta_bone_names (List[str]): List of MTA bone names to duplicate.
        div (int, optional): Number of segments to subdivide each bone. Defaults to 2.
        debug (bool): runs print statements for debugging

    Returns:
        List[str]: List of newly created DEF bone names.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if not armature_obj:
        raise ValueError(f"Armature '{armature_name}' not found.")
    if armature_obj.type != 'ARMATURE':
        raise ValueError(f"Object '{armature_name}' is not an armature.")

    bpy.context.view_layer.objects.active = armature_obj
    all_def_bones = []

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        armature_data = armature_obj.data
        edit_bones = armature_data.edit_bones
        mta_to_def = {}

        for mta_name in mta_bone_names:
            mta_bone = edit_bones.get(mta_name)
            if not mta_bone:
                if debug:
                    print(f"⚠️ MTA bone '{mta_name}' not found.")
                continue
            def_name = mta_name.replace("MTA-", "DEF-", 1)
            def_bone = duplicate_bone(edit_bones, mta_bone, def_name)
            mta_to_def[mta_name] = def_bone
            all_def_bones.append(def_bone)

        # Rebuild hierarchy
        for mta_name, def_bone in mta_to_def.items():
            mta_bone = edit_bones.get(mta_name)
            if mta_bone and mta_bone.parent and mta_bone.parent.name in mta_to_def:
                def_bone.parent = mta_to_def[mta_bone.parent.name]
                def_bone.use_connect = mta_bone.use_connect

    # Sanitize and move to Deformer Bones collection
    with mode_utils.ensure_mode(armature_obj, 'OBJECT'):
        armature_data = armature_obj.data
        safe_def_names = sanitize_bone_names(all_def_bones, debug)

        mta_col = armature_data.collections.get("Meta Bones")
        def_col = armature_data.collections.get("Deformer Bones")
        if not def_col:
            def_col = armature_data.collections.new(name="Deformer Bones")

        move_bones_to_collection(safe_def_names, armature_data, mta_col, def_col)
    if debug:
        print("✅ DEF bones successfully created.")
    return safe_def_names


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


def sanitize_bone_names(bones, debug=False):
    """Ensures bone names are valid UTF-8; renames if necessary.

    Args:
        bones (Iterable[bpy.types.Bone or bpy.types.EditBone]): The bones to sanitize.
        debug (bool): runs print statements for debugging

    Returns:
        List[str]: A list of safe bone names after renaming (if needed).
    """
    cleaned = []
    for i, bone in enumerate(bones):
        try:
            name = bone.name
            name.encode('utf-8')  # test access and encoding
            cleaned.append(name)
        except Exception:
            new_name = f"recovered_bone_{i:03d}"
            if debug:
                print(f"⚠️ Invalid bone name detected — assigning: {new_name}")
            try:
                bone.name = new_name
            except Exception:
                print(f"❌ Failed to rename bone index {i}")
            cleaned.append(new_name)
    return cleaned


def subdivide_bone(edit_bones, bone_name, segments, connect_chain=True, debug=False):
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

    return sanitize_bone_names(new_bones, debug)


def subdivide_bones(armature_name, bone_names, segments=2, debug=False):
    """Subdivides a list of bones into multiple segments.

    Args:
        armature_name (str): Name of the armature.
        bone_names (list[str]): Names of the bones to subdivide.
        segments (int): Number of segments to divide each into.
        debug (bool): runs print statements for debugging

    Returns:
        list[str]: List of all newly created segment bone names.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if not armature_obj or armature_obj.type != 'ARMATURE':
        raise ValueError(f"Invalid armature: {armature_name}")

    bpy.context.view_layer.objects.active = armature_obj
    new_bone_names = []

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_obj.data.edit_bones

        for bone_name in bone_names:
            if bone_name not in edit_bones:
                if debug:
                    print(f"⚠️ Cannot subdivide: '{bone_name}' not found in edit bones.")
                continue
            segments_created = subdivide_bone(edit_bones, bone_name, segments)
            new_bone_names.extend(segments_created)

    return new_bone_names


# armature = bpy.data.objects['Armature']
# bones.make_def_from_meta('Armature')
# curves.create_spline_curve("MTA-neck.01.c", armature)