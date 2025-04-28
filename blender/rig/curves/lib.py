import re
import bpy
from math import degrees
from mathutils import Vector
from ...utils import mode_utils
from ..bones import lib as bones_lib

# TODO: build_bezier_curve() needs the curve handles to align with the child bones
def add_hooks_to_curve(curve_obj, armature_obj, bone_names, debug=False):
    """Adds hook modifiers to a curve for the given bone names.

    Args:
        curve_obj (bpy.types.Object): The curve object to receive hook modifiers.
        armature_obj (bpy.types.Object): The armature containing the target bones.
        hook_bone_names (List[str]): Names of bones to create hooks for.
        debug (bool, optional): If True, prints debug info. Defaults to False.

    Returns:
        bpy.types.HookModifier: The last hook modifier added.
    """
    hook_bone_names = [b.name for b in get_hook_bones(bone_names, armature_obj) if b]
    with mode_utils.ensure_mode(curve_obj, 'OBJECT'):
        for bone in hook_bone_names:
            bpy.ops.object.modifier_add(type='HOOK')
            hook = curve_obj.modifiers[-1]
            hook.name = f"hook_{bone}"
            hook.object = armature_obj
            hook.subtarget = bone

        safe_hook_bone_names = bones_lib.sanitize_bone_names(hook_bone_names, debug)

        if debug:
            print(f"Hook Bones: {safe_hook_bone_names}")

        assign_points_to_hooks(curve_obj, safe_hook_bone_names, debug)

    return curve_obj.modifiers[-1]


def assign_points_to_hooks(curve_obj, bones, debug=False):
    """Assigns each curve point to its corresponding hook modifier.

    Args:
        curve_obj (bpy.types.Object): Curve with hook modifiers already added.
        bones (List[str]): List of bone names corresponding to curve points.
        debug (bool, optional): If True, prints debug info. Defaults to False.
    """
    with mode_utils.ensure_mode(curve_obj, 'EDIT'):
        spline = curve_obj.data.splines[0]
        if len(spline.bezier_points) != len(bones):
            if debug:
                print("Mismatch between number of points and bones.")
            return

        for i, bone in enumerate(bones):
            assign_point_to_hook(curve_obj, i, f"hook_{bone}", debug)


def assign_point_to_hook(curve_obj, point_index, hook_name, debug=False):
    """Assigns a specific curve point (and handles) to a hook modifier.

    Args:
        curve_obj (bpy.types.Object): The curve object.
        point_index (int): Index of the point to assign.
        hook_name (str): Name of the hook modifier.
        debug (bool, optional): If True, prints debug info. Defaults to False.
    """
    spline = curve_obj.data.splines[0]
    pt = spline.bezier_points[point_index]

    for p in spline.bezier_points:
        p.select_control_point = False
        p.select_left_handle = False
        p.select_right_handle = False

    pt.select_control_point = True
    pt.select_left_handle = True
    pt.select_right_handle = True

    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if not area:
        print("❌ No valid VIEW_3D area found.")
        return

    override = bpy.context.copy()
    override['area'] = area
    override['region'] = area.regions[-1]
    override['space_data'] = area.spaces.active

    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.hook_assign(modifier=hook_name)
        if debug:
            print(f"✅ Assigned point {point_index} to {hook_name}")
    except Exception as e:
        print(f"❌ Failed to assign point {point_index} to {hook_name}: {e}")


def build_bezier_curve(curve_name, obj_name, points, bone_dirs, handle_len=0.5, debug=False):
    """Builds and returns a Bezier curve object from a list of points and bone directions with adaptive smoothing."""
    curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    spline = curve_data.splines.new(type='BEZIER')
    spline.bezier_points.add(len(points) - 1)

    for i, point in enumerate(points):
        pt = spline.bezier_points[i]
        pt.co = point
        pt.handle_left_type = pt.handle_right_type = 'FREE'
        pt.select_control_point = True

        if i < len(bone_dirs):
            dir = bone_dirs[i]

            # Smoothing boost: adapt handle_len based on curvature
            handle_scale = 1.0
            if 0 < i < len(bone_dirs) - 1:
                # Compare previous and next directions
                prev_dir = bone_dirs[i-1]
                next_dir = bone_dirs[i+1]

                angle = prev_dir.angle(next_dir)
                angle_deg = degrees(angle)

                if debug:
                    print(f"🔍 Point {i}: Angle between prev/next = {angle_deg:.2f}°")

                # Less than 30 degrees = very straight → long handles
                # 90 degrees = medium handles
                # More than 150 degrees = sharp bend → short handles
                if angle_deg < 30:
                    handle_scale = 1.5
                elif angle_deg > 150:
                    handle_scale = 0.4
                else:
                    handle_scale = 1.0

            pt.handle_right = pt.co + dir * handle_len * handle_scale
            pt.handle_left = pt.co - dir * handle_len * handle_scale
        else:
            # fallback for final point
            if i > 0:
                fallback_dir = (points[i] - points[i-1]).normalized()
                pt.handle_right = pt.co + fallback_dir * handle_len
                pt.handle_left = pt.co - fallback_dir * handle_len
            else:
                pt.handle_right = pt.co + Vector((handle_len, 0, 0))
                pt.handle_left = pt.co - Vector((handle_len, 0, 0))

    curve_obj = bpy.data.objects.new(obj_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)

    if debug:
        print(f"✅ Created smoothed curve '{obj_name}' with {len(points)} points.")

    return curve_obj



def get_curve_points_from_bones(bones, armature_obj):
    """Generates world-space points from a list of bones.

    Args:
        bones (List[bpy.types.EditBone]): The bones.
        armature_obj (bpy.types.Object): The armature containing them.

    Returns:
        List[Vector]: The world-space coordinates.
    """
    return [armature_obj.matrix_world @ b.head for b in bones] + [armature_obj.matrix_world @ bones[-1].tail]


def get_hook_bones(bone_names, armature_obj):
    """Returns hook-related bones for a bone chain: parent, chain, and first child.

    Args:
        bone_names (List[str]): Bone names.
        armature_obj (bpy.types.Object): Armature to search in.

    Returns:
        List[bpy.types.Bone]: Relevant hook bones.
    """
    bones = [armature_obj.data.bones.get(n) for n in bone_names]
    if any(b is None for b in bones): return []
    hooks = [bones[0].parent] if bones[0].parent else []
    hooks.extend(bones[1:])
    if bones[-1].children:
        hooks.append(bones[-1].children[0])
    return hooks


def make_spline_curve(bone_name, armature_obj, debug=False):
    """Creates a spline curve based on a bone chain starting from a given meta bone.

    Args:
        bone_name (str): Base meta bone name to start the chain from.
        armature_obj (bpy.types.Object): The armature object containing the bones.
        debug (bool, optional): Whether to print debug info.

    Returns:
        bpy.types.Object: The newly created curve object.
    """
    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        multi = re.match(r"(MTA-[\w]+)\.(\d+)\.(c|l|r)$", bone_name, re.IGNORECASE)
        if multi:
            prefix, _, side = multi.groups()
            bones = bones_lib.get_bone_chain(prefix, side, armature_obj)
            base_name = prefix.replace("MTA-", "")
        else:
            bone = armature_obj.data.edit_bones.get(bone_name)
            if not bone:
                raise ValueError(f"⚠️ Bone '{bone_name}' not found.")
            bones = [bone]
            base_name = re.sub(r"(?:.*-)?([\w]+?)(?:\.\d+)?\.(?:c|l|r)$", r"\1", bone_name)

        if debug:
            print(f"🔍 Found {len(bones)} bones for spline: {[b.name for b in bones]}")

        if not bones:
            raise ValueError(f"No bones found for '{bone_name}'.")

        # Sanitize and get names
        bone_names = bones_lib.sanitize_bone_names(bones, debug=debug)

    # 🛠 Re-fetch pose bones now in OBJECT mode
    with mode_utils.ensure_mode(armature_obj, 'OBJECT'):
        pose_bones = armature_obj.pose.bones
        points = []
        bone_dirs = []

        for bone_name in bone_names:
            pose_bone = pose_bones.get(bone_name)
            if not pose_bone:
                raise ValueError(f"Pose bone '{bone_name}' not found.")

            head_world = armature_obj.matrix_world @ pose_bone.head
            tail_world = armature_obj.matrix_world @ pose_bone.tail

            points.append(head_world)
            bone_dirs.append((tail_world - head_world).normalized())

        # Add final tail point
        if pose_bone:
            points.append(armature_obj.matrix_world @ pose_bone.tail)

        # Calculate final direction
        last_pose_bone = pose_bone
        final_dir = None
        if last_pose_bone.children:
            child_bone = last_pose_bone.children[0]
            final_dir = (armature_obj.matrix_world @ child_bone.tail - armature_obj.matrix_world @ last_pose_bone.tail).normalized()
        else:
            # Fallback: use last two points
            final_dir = (points[-1] - points[-2]).normalized()

        bone_dirs.append(final_dir)

    # 🛠 Now build the Bezier curve
    curve_obj = build_bezier_curve(
        curve_name=f"{base_name}.crv",
        obj_name=f"{base_name}.spln",
        points=points,
        bone_dirs=bone_dirs,
        handle_len=0.5,
        debug=debug
    )

    if debug:
        print(f"✅ Built spline curve '{curve_obj.name}' with {len(points)} points.")

    return curve_obj



"""def make_spline_curve(bone_name, armature_obj, debug=False):"""
"""Creates a spline curve and hooks it to a bone chain.

    Args:
        bone_name (str): Name of the bone (or first in chain).
        armature_obj (bpy.types.Object): Armature with bones.
        debug (bool, optional): If True, prints debug info. Defaults to False.
    """
"""with mode_utils.ensure_mode(armature_obj, 'EDIT'):
        multi = re.match(r"(MTA-[\w]+)\.(\d+)\.(c|l|r)$", bone_name, re.IGNORECASE)
        if multi:
            prefix, _, side = multi.groups()
            bones = bones_lib.get_bone_chain(prefix, side, armature_obj)
            points = get_curve_points_from_bones(bones, armature_obj)
            child_dir = (bones[-1].children[0].head - bones[-1].tail).normalized() if bones[-1].children else None
            base_name = prefix.replace("MTA-", "")
        else:
            bone = armature_obj.data.edit_bones.get(bone_name)
            if not bone:
                print(f"Bone '{bone_name}' not found.")
                return
            bones = [bone]
            points = [armature_obj.matrix_world @ bone.head, armature_obj.matrix_world @ bone.tail]
            child_dir = None
            base_name = re.sub(r"(?:.*-)?([\w]+?)(?:\.\d+)?\.(?:c|l|r)$", r"\1", bone_name)

    curve_obj = build_bezier_curve(f"{base_name}.crv", f"{base_name}.spln", points, child_dir, debug=debug)
    bone_names = [b.name for b in bones]
    hook_names = [b.name for b in get_hook_bones(bone_names, armature_obj) if b]

    add_hook_modifiers(curve_obj, armature_obj, hook_names, debug)"""


# make_spline_curve("MTA-neck.01.c", bpy.data.objects["Armature"], True)