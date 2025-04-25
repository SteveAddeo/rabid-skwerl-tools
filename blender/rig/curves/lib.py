import re
import bpy
from ...utils import mode_utils
from ..bones import lib as bones_lib

def add_hook_modifiers(curve_obj, armature_obj, hook_bone_names, debug=False):
    """Adds hook modifiers to a curve for the given bone names.

    Args:
        curve_obj (bpy.types.Object): The curve object to receive hook modifiers.
        armature_obj (bpy.types.Object): The armature containing the target bones.
        hook_bone_names (List[str]): Names of bones to create hooks for.
        debug (bool, optional): If True, prints debug info. Defaults to False.

    Returns:
        bpy.types.HookModifier: The last hook modifier added.
    """
    with mode_utils.ensure_mode(curve_obj, 'OBJECT'):
        for bone in hook_bone_names:
            bpy.ops.object.modifier_add(type='HOOK')
            hook = curve_obj.modifiers[-1]
            hook.name = f"hook_{bone}"
            hook.object = armature_obj
            hook.subtarget = bone

        for b in armature_obj.data.bones:
            try:
                b.name.encode('utf-8')
            except UnicodeEncodeError:
                b.name = "fixme_broken"

        if debug:
            print(f"Hook Bones: {hook_bone_names}")

        assign_curve_to_hooks(curve_obj, hook_bone_names, debug)

    return curve_obj.modifiers[-1]


def assign_curve_to_hooks(curve_obj, bones, debug=False):
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


def build_bezier_curve(curve_name, obj_name, points, child_dir=None, handle_len=0.5, debug=False):
    """Builds and returns a Bezier curve object from a list of points.

    Args:
        curve_name (str): Name for the curve data-block.
        obj_name (str): Name for the curve object.
        points (List[Vector]): World-space points defining the curve.
        child_dir (Vector, optional): Direction for the last handle. Defaults to None.
        handle_len (float, optional): Length of handle vectors. Defaults to 0.5.
        debug (bool, optional): If True, prints debug info. Defaults to False.

    Returns:
        bpy.types.Object: The newly created curve object.
    """
    curve_data = bpy.data.curves.new(name=curve_name, type='CURVE')
    curve_data.dimensions = '3D'
    spline = curve_data.splines.new(type='BEZIER')
    spline.bezier_points.add(len(points) - 1)

    for i, point in enumerate(points):
        pt = spline.bezier_points[i]
        pt.co = point
        pt.handle_left_type = pt.handle_right_type = 'FREE'
        pt.select_control_point = True

    if len(points) == 2:
        p0, p1 = spline.bezier_points[0], spline.bezier_points[1]
        vec = (p1.co - p0.co) / 3
        p0.handle_right, p0.handle_left = p0.co + vec, p0.co - vec
        p1.handle_left, p1.handle_right = p1.co - vec, p1.co + vec
    else:
        for i, pt in enumerate(spline.bezier_points):
            dir = (points[min(i + 1, len(points) - 1)] - points[max(i - 1, 0)]).normalized()
            pt.handle_right = pt.co + dir * handle_len
            pt.handle_left = pt.co - dir * handle_len

    curve_obj = bpy.data.objects.new(obj_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)

    if debug:
        print(f"Created curve '{obj_name}' with {len(points)} points.")
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
    """Creates a spline curve and hooks it to a bone chain.

    Args:
        bone_name (str): Name of the bone (or first in chain).
        armature_obj (bpy.types.Object): Armature with bones.
        debug (bool, optional): If True, prints debug info. Defaults to False.
    """
    with mode_utils.ensure_mode(armature_obj, 'EDIT'):
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

    add_hook_modifiers(curve_obj, armature_obj, hook_names, debug)


# make_spline_curve("MTA-neck.01.c", bpy.data.objects["Armature"], True)