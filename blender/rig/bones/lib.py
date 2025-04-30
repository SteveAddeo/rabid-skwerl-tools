import re
import bpy
from mathutils import Vector
from ..curves import lib as curves_lib
from ...utils import mode_utils


def create_root(armature_obj, name):
    """Creates a root bone at the origin with no parent and use_deform=False.

    Args:
        armature_obj (bpy.types.Object): The armature object.
        name (str): Name of the root bone to create.

    Returns:
        bpy.types.EditBone: The created root bone.
    """
    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_obj.data.edit_bones
        if name in edit_bones:
            return edit_bones[name]
        root = edit_bones.new(name)
        root.head = Vector((0, 0, 0))
        root.tail = Vector((0, 1, 0))
        root.use_connect = False
        return root
    

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


def duplicate_bones(armature_name, bone_names, source_prefix, target_prefix, debug=False):
    """Duplicates a list of bones with a new prefix (e.g., from DEF- to TGT-).

    Args:
        armature_name (str): Name of the armature object.
        bone_names (list[str]): List of bone names to duplicate.
        source_prefix (str): Prefix to replace in source bone names.
        target_prefix (str): Prefix to use for duplicated bones.
        debug (bool): Print debug information.

    Returns:
        list[str]: List of new duplicated bone names.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if not armature_obj:
        raise ValueError(f"Armature '{armature_name}' not found.")

    new_bone_names = []

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_obj.data.edit_bones

        for old_name in bone_names:
            orig_bone = edit_bones.get(old_name)
            if not orig_bone:
                if debug:
                    print(f"⚠️ Bone not found: {old_name}")
                continue

            new_name = old_name.replace(source_prefix, target_prefix, 1)
            new_bone = duplicate_bone(edit_bones, orig_bone, new_name)
            new_bone_names.append(new_name)

    return new_bone_names


def get_armature_obj(armature_name_or_obj='Armature'):
    """Returns the armature object from name or passes through if already an object.

    Args:
        armature_name_or_obj (str or bpy.types.Object): Armature name or object.

    Returns:
        bpy.types.Object: Armature object.

    Raises:
        ValueError: If the armature cannot be found or is the wrong type.
    """
    if isinstance(armature_name_or_obj, bpy.types.Object):
        if armature_name_or_obj.type != 'ARMATURE':
            raise ValueError(f"Provided object is not an armature.")
        return armature_name_or_obj
    armature_obj = bpy.data.objects.get(armature_name_or_obj)
    if not armature_obj:
        raise ValueError(f"Armature '{armature_name_or_obj}' not found.")
    if armature_obj.type != 'ARMATURE':
        raise ValueError(f"Object '{armature_name_or_obj}' is not an armature.")
    return armature_obj


def get_bone_direction(armature_obj, bone_name):
    """Returns the normalized direction vector from head to tail of the specified bone in world space.

    Args:
        armature_obj (bpy.types.Object): The armature object containing the bone.
        bone_name (str): The name of the bone.

    Returns:
        Vector: Normalized direction vector in world space.
    """
    bone = armature_obj.pose.bones.get(bone_name)
    if bone is None:
        raise ValueError(f"Bone '{bone_name}' not found in armature '{armature_obj.name}'.")

    head_world = armature_obj.matrix_world @ bone.head
    tail_world = armature_obj.matrix_world @ bone.tail
    return (tail_world - head_world).normalized()


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


def make_def_from_meta(armature_name: str, mta_bone_names: list[str], debug: bool = False) -> list[str]:
    """Creates DEF bones by duplicating the provided list of MTA bones.

    Args:
        armature_name (str): Name of the armature.
        mta_bone_names (list[str]): List of MTA bone names.
        debug (bool, optional): Whether to print debug logs. Defaults to False.

    Returns:
        list[str]: List of newly created DEF bone names.
    """
    armature_obj = get_armature_obj(armature_name)
    bpy.context.view_layer.objects.active = armature_obj
    all_def_bones = []

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        armature_data = armature_obj.data
        edit_bones = armature_data.edit_bones

        # 🛡️ First thing: sanitize edit bones BEFORE anything else
        sanitize_bone_names(edit_bones, debug=debug)

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

    # After switching to OBJECT mode
    with mode_utils.ensure_mode(armature_obj, 'OBJECT'):
        mta_col = armature_data.collections.get("Meta Bones")
        def_col = armature_data.collections.get("Deformer Bones")
        if not def_col:
            def_col = armature_data.collections.new(name="Deformer Bones")
        safe_def_names = sanitize_bone_names(all_def_bones, debug=debug)
        move_bones_to_collection(safe_def_names, armature_data, mta_col, def_col, debug)

    if debug:
        print(f"✅ DEF bones successfully created: {safe_def_names}")

    return safe_def_names


def match_bone_hierarchy(armature_name, source_bones, target_bones):
    """Matches parenting of target bones to match their source counterparts.

    Args:
        armature_obj (bpy.types.Object): The armature object.
        source_bones (list[str]): List of source bone names.
        target_bones (list[str]): List of corresponding target bone names.
    """
    armature_obj = get_armature_obj(armature_name)
    bone_map = dict(zip(source_bones, target_bones))
    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_obj.data.edit_bones
        for src, tgt in bone_map.items():
            src_bone = edit_bones.get(src)
            tgt_bone = edit_bones.get(tgt)
            if src_bone and tgt_bone and src_bone.parent:
                src_parent = src_bone.parent.name
                tgt_parent = bone_map.get(src_parent)
                if tgt_parent and tgt_parent in edit_bones:
                    tgt_bone.parent = edit_bones[tgt_parent]
                    tgt_bone.use_connect = False


def move_bones_to_collection(bone_names, armature_data, old_col, new_col, unassign_old=True, debug=False):
    """Moves bones to a new bone collection, safely handling bone name corrections.

    Args:
        bone_names (List[str]): List of valid bone names to move.
        armature_data (bpy.types.Armature): The armature data block.
        old_col (bpy.types.BoneCollection): Original bone collection.
        new_col (bpy.types.BoneCollection): Target bone collection.
        unassign_old (bool, optional): Whether to unassign from the old collection. Defaults to True.
    """
    with mode_utils.ensure_mode(bpy.context.object, 'OBJECT'):
        for bone_name in bone_names:
            bone = armature_data.bones.get(bone_name)
            if not bone:
                if debug:
                    print(f"⚠️ Bone '{bone_name}' not found in armature '{armature_data.name}'. Skipping.")
                continue

            new_col.assign(bone)

            if unassign_old and old_col and bone.name in old_col.bones:
                old_col.unassign(bone)
        if debug:
            print(f"✅ Moved {len(bone_names)} bones to collection '{new_col.name}'.")


def reparent_with_offset(armature_obj, parent_name, child_names):
    """Reparents edit bones under a new parent using Blender's operator with 'OFFSET'.

    Args:
        armature_obj (bpy.types.Object): The armature object.
        parent_name (str): Name of the new parent bone.
        child_names (list[str]): Names of child bones to reparent.
    """
    bpy.context.view_layer.objects.active = armature_obj
    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        for bone in armature_obj.data.edit_bones:
            bone.select = False

        for name in child_names:
            bone = armature_obj.data.edit_bones.get(name)
            if bone:
                bone.select = True

        parent_bone = armature_obj.data.edit_bones.get(parent_name)
        if parent_bone:
            parent_bone.select = True
            armature_obj.data.edit_bones.active = parent_bone

        bpy.ops.armature.parent_set(type='OFFSET')

def sanitize_bone_names(bones, debug=False):
    """Ensures bone names are valid UTF-8; renames if necessary.

    Args:
        bones (Iterable[bpy.types.Bone or bpy.types.EditBone]): The bones to sanitize.
        debug (bool, optional): If True, print debug messages.

    Returns:
        List[str]: A list of safe bone names after renaming (if needed).
    """
    cleaned = []
    for i, bone in enumerate(bones):
        try:
            name = bone.name
            _ = name.encode('utf-8')  # Try accessing and encoding
            cleaned.append(name)
        except Exception:
            # Fix broken names
            new_name = f"recovered_bone_{i:03d}"
            if debug:
                print(f"⚠️ Invalid bone name detected — assigning: {new_name}")
            try:
                bone.name = new_name
            except Exception as e:
                if debug:
                    print(f"❌ Failed to rename bone index {i}: {e}")
            cleaned.append(new_name)
    return cleaned


def subdivide_bone(edit_bones, bone_name, segments, connect_chain=True):
    """Subdivides a bone into multiple segments.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): Collection of EditBones.
        bone_name (str): Name of the bone to subdivide.
        segments (int): Number of segments.
        connect_chain (bool, optional): Whether to connect segments. Defaults to True.

    Returns:
        List[str]: List of newly created segment bone names.
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

    # Properly split the side from the name
    # Find LAST period
    last_dot = bone_name.rfind('.')
    if last_dot != -1:
        base_name = bone_name[:last_dot]
        side_suffix = bone_name[last_dot:]  # includes the dot
    else:
        base_name = bone_name
        side_suffix = ""

    edit_bones.remove(orig_bone)

    new_bones = []
    prev_bone = None
    for i in range(segments):
        seg_head = head + direction * i
        seg_tail = head + direction * (i + 1)

        new_name = f"{base_name}.{i+1:03d}{side_suffix}"
        if new_name in edit_bones:
            # Ensure unique (rare)
            counter = 1
            while f"{new_name}.{counter}" in edit_bones:
                counter += 1
            new_name = f"{new_name}.{counter}"

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

    return sanitize_bone_names(new_bones)


def subdivide_bone_to_curve(edit_bones, orig_bone, segment_points, segments=2, follow_curve_roll=False):
    """Subdivides a bone into multiple connected segments aligned to a curve, optionally aligning roll to the curve tangent.

    Args:
        edit_bones (bpy.types.ArmatureEditBones): Edit bones collection.
        orig_bone (bpy.types.EditBone): Original bone to subdivide.
        segment_points (List[Vector]): List of `segments + 1` points along a curve span.
        segments (int): Number of segments to create.
        follow_curve_roll (bool): Whether to align bone roll with the curve's direction.

    Returns:
        List[str]: Names of the new subdivided bones.
    """
    if len(segment_points) != segments + 1:
        raise ValueError(f"Expected {segments + 1} segment points, got {len(segment_points)}")

    # Cache everything we need BEFORE removing the original bone
    roll = orig_bone.roll
    parent = orig_bone.parent
    children = [b for b in edit_bones if b.parent == orig_bone]

    match = re.match(r"^(.*?)(\.\d+)?\.(c|l|r)$", orig_bone.name)
    if not match:
        raise ValueError(f"Bone name '{orig_bone.name}' does not match naming convention")
    base, segment_id, side = match.groups()
    base_name = base + (segment_id or "")
    suffix = f".{side}"

    # Now we can safely remove the original bone
    edit_bones.remove(orig_bone)

    new_bones = []
    prev_bone = None

    for i in range(segments):
        head = segment_points[i]
        tail = segment_points[i + 1]
        new_name = f"{base_name}.{i+1:03d}{suffix}"

        b = edit_bones.new(new_name)
        b.head = head
        b.tail = tail
        b.parent = prev_bone or parent
        b.use_connect = prev_bone is not None

        if follow_curve_roll:
            # Align Z axis (up) using a consistent up vector
            direction = (tail - head).normalized()
            up = Vector((0, 0, 1))
            if abs(direction.dot(up)) > 0.99:  # Avoid gimbal locking if nearly vertical
                up = Vector((0, 1, 0))
            quat = direction.to_track_quat('Y', 'Z')  # Y = bone axis
            b.roll = quat.to_euler().z
        else:
            b.roll = roll  # Default roll from the original bone

        new_bones.append(b)
        prev_bone = b

    # Reassign children to the last new bone
    for child in children:
        child.parent = new_bones[-1]
        child.use_connect = False

    return sanitize_bone_names(new_bones)


def subdivide_bones(armature_name, bone_names, segments=2, curve_obj=None, debug=False):
    """Subdivides bones into segments, optionally aligning to spans of a curve.

    Args:
        armature_name (str): Name of the armature.
        bone_names (list[str]): Names of bones to subdivide.
        segments (int): Number of subdivisions per bone.
        curve_obj (bpy.types.Object, optional): If provided, align bones to spans of curve.
        debug (bool): If True, print debug info.

    Returns:
        list[str]: List of new subdivided bone names.
    """
    armature_obj = bpy.data.objects.get(armature_name)
    if not armature_obj or armature_obj.type != 'ARMATURE':
        raise ValueError(f"Invalid armature: {armature_name}")

    new_bone_names = []

    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        edit_bones = armature_obj.data.edit_bones

        total_spans = len(bone_names)

        for i, bone_name in enumerate(bone_names):
            if bone_name not in edit_bones:
                if debug:
                    print(f"⚠️ Cannot subdivide: '{bone_name}' not found.")
                continue

            orig_bone = edit_bones[bone_name]

            if curve_obj:
                # Normalized start and end ratio for this bone's span along the curve
                start_ratio = i / total_spans
                end_ratio = (i + 1) / total_spans
                segment_points = curves_lib.sample_curve_segment_points(curve_obj, start_ratio, end_ratio, segments)
                new_names = subdivide_bone_to_curve(edit_bones, orig_bone, segment_points, segments, follow_curve_roll=False)
            else:
                new_names = subdivide_bone(edit_bones, bone_name, segments)

            new_bone_names.extend(new_names)
    if debug:
        print(f"✅ Subdivided {len(bone_names)} bones into {len(new_bone_names)} new bones.")
    return new_bone_names






"""def subdivide_bones(armature_name, bone_names, segments=2, debug=False):"""
"""Subdivides a list of bones into multiple segments.

    Args:
        armature_name (str): Name of the armature.
        bone_names (list[str]): Names of the bones to subdivide.
        segments (int): Number of segments to divide each into.
        debug (bool): runs print statements for debugging

    Returns:
        list[str]: List of all newly created segment bone names.
    """
"""armature_obj = bpy.data.objects.get(armature_name)
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

    return new_bone_names"""


# armature = bpy.data.objects['Armature']
# bones.make_def_from_meta('Armature')
# curves.create_spline_curve("MTA-neck.01.c", armature)