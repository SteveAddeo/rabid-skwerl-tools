import re
import bpy

# TODO: Bezier handles need to align with second bone not an in-between tangent

def add_hook_modifiers(curve_obj, armature_obj, hook_bone_names, debug=False):
    """
    Adds a hook modifier to a curve for each given bone and assigns curve points to the corresponding hooks.

    Each modifier is named "hook_{bone.name}" and targets the specified bone in the armature.
    The function ensures the curve is in Object mode before adding modifiers and then calls
    assign_curve_to_hooks to assign each Bezier point to its respective hook.

    Args:
        curve_obj (bpy.types.Object): The curve object to which hook modifiers will be added.
        armature_obj (bpy.types.Object): The armature object containing the target bones.
        bones (List[bpy.types.Bone]): List of bones that each correspond to a curve point.
        debug (bool, optional): If True, prints debug information during processing. Defaults to False.

    Returns:
        bpy.types.HookModifier: The last hook modifier created.
    """
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)

    if bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

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
    
    print(f"Hook Bones: {hook_bone_names}")
    assign_curve_to_hooks(curve_obj, hook_bone_names, debug)
    return curve_obj.modifiers[-1]


def assign_curve_to_hooks(curve_obj, bones, debug=False):
    """
    Assigns each point on a Bezier spline to the hook modifier associated with its corresponding bone.

    This function assumes that the hook modifiers have already been added to the curve object.
    It selects each curve point and assigns it (and its handles) to the hook named after its bone.

    Args:
        curve_obj (bpy.types.Object): The curve object containing the points to assign.
        armature_obj (bpy.types.Object): The armature containing the bones.
        bones (List[bpy.types.Bone]): List of bones matching the curve points by index.
        debug (bool, optional): If True, prints debug information. Defaults to False.

    Returns:
        None
    """
    spline = curve_obj.data.splines[0]

    if len(spline.bezier_points) != len(bones):
        if debug:
            print("Mismatch between number of points and bones.")
        return

    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')

    for i, bone in enumerate(bones):
        assign_point_to_hook(curve_obj, i, f"hook_{bone}", debug)

    bpy.ops.object.mode_set(mode='OBJECT')


def assign_point_to_hook(curve_obj, point_index, hook_name, debug=False):
    """
    Selects a Bezier curve point and both of its handles, and assigns them to a hook modifier.

    Uses Blender’s operator bpy.ops.object.hook_assign() within an overridden VIEW_3D context
    to ensure proper execution.

    Args:
        curve_obj (bpy.types.Object): The curve object containing the point.
        point_index (int): Index of the Bezier point in the spline.
        hook_name (str): Name of the hook modifier to assign the point to.
        debug (bool, optional): If True, prints debug messages on success or failure. Defaults to False.

    Returns:
        None
    """
    spline = curve_obj.data.splines[0]
    pt = spline.bezier_points[point_index]

    # Deselect all first
    for p in spline.bezier_points:
        p.select_control_point = False
        p.select_left_handle = False
        p.select_right_handle = False

    # Select control point and both handles
    pt.select_control_point = True
    pt.select_left_handle = True
    pt.select_right_handle = True

    # Make sure we're in Edit mode
    bpy.context.view_layer.objects.active = curve_obj
    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    # Find a 3D View area
    area = next((a for a in bpy.context.screen.areas if a.type == 'VIEW_3D'), None)
    if not area:
        print("❌ No valid VIEW_3D area found.")
        return

    override = bpy.context.copy()
    override['area'] = area
    override['region'] = area.regions[-1]
    override['space_data'] = area.spaces.active

    # Assign to hook
    try:
        with bpy.context.temp_override(**override):
            bpy.ops.object.hook_assign(modifier=hook_name)
        if debug:
            print(f"✅ Assigned point {point_index} (with handles) to {hook_name}")
    except Exception as e:
        print(f"❌ Failed to assign point {point_index} to {hook_name}: {e}")

    

def build_bezier_curve(curve_name, obj_name, points, child_dir=None, handle_len=0.5, debug=False):
    """Builds and adds a Bezier curve object to the scene using given points.

    The function creates a 3D Bezier curve with control handles calculated for smooth interpolation.
    The curve is linked to the active collection and uses free handle types.

    Args:
        curve_name (str): The internal name of the curve data-block.
        obj_name (str): The name of the curve object to be created.
        points (List[mathutils.Vector]): A list of world-space points to define the curve.

    Returns:
        bpy.data.objects(curve_name): The newly created curve
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
        # Just two points: use simple tangent-style handles
        p0 = spline.bezier_points[0]
        p1 = spline.bezier_points[1]
        vec = (p1.co - p0.co) / 3
        p0.handle_right = p0.co + vec
        p0.handle_left = p0.co - vec
        p1.handle_left = p1.co - vec
        p1.handle_right = p1.co + vec
    else:
        for i in range(len(points)):
            pt = spline.bezier_points[i]

            if i == 0:
                dir = (points[1] - points[0]).normalized()
                pt.handle_right = pt.co + dir * handle_len
                pt.handle_left = pt.co - dir * handle_len  # Optional
            elif i == len(points) - 1:
                if child_dir is not None:
                    dir = child_dir.normalized()
                else:
                    dir = (points[-1] - points[-2]).normalized()
                pt.handle_left = pt.co - dir * handle_len
                pt.handle_right = pt.co + dir * handle_len  # Optional
            else:
                dir_to_next = (points[i + 1] - points[i]).normalized()
                pt.handle_right = pt.co + dir_to_next * handle_len
                pt.handle_left = pt.co - dir_to_next * handle_len

    curve_obj = bpy.data.objects.new(obj_name, curve_data)
    bpy.context.collection.objects.link(curve_obj)

    if debug:
        print(f"Created curve '{obj_name}' with {len(points)} points.")
    return curve_obj


def get_bone_chain(chain_prefix, side, armature_obj):
    """Collects a sorted list of bones forming a multi-span chain.

    This is used for chains such as necks or tails where the bones are named 
    sequentially (e.g., MTA-neck.01.c, MTA-neck.02.c, etc.).

    Args:
        chain_prefix (str): The prefix of the chain, e.g., 'MTA-neck'.
        side (str): The side identifier, typically 'c', 'l', or 'r'.
        armature_obj (bpy.types.Object): The armature containing the bones.

    Returns:
        List[bpy.types.EditBone]: A list of bones in the chain, sorted by index.
    """
    bones = armature_obj.data.edit_bones
    pattern = re.compile(rf"^{re.escape(chain_prefix)}\.(\d+)\.{side}$", re.IGNORECASE)
    chain_bones = []

    for bone in bones:
        match = pattern.match(bone.name)
        if match:
            index = int(match.group(1))
            chain_bones.append((index, bone))

    chain_bones.sort(key=lambda item: item[0])
    return [b for _, b in chain_bones]


def get_bone_world_direction(armature_obj, bone_name):
    """Returns the world-space direction vector of a bone."""
    print(f"Child Bone Name: {bone_name}")
    bone = armature_obj.data.edit_bones.get(bone_name)
    if not bone:
        return None
    head_world = armature_obj.matrix_world @ bone.head
    tail_world = armature_obj.matrix_world @ bone.tail
    return (tail_world - head_world).normalized()


def get_curve_points_from_bones(bones, armature_obj):
    """Generates a list of world-space points from a list of bones.

    The list includes the head of each bone, and the tail of the last bone,
    forming a smooth path through the entire chain.

    Args:
        bones (List[bpy.types.EditBone]): The bones to extract points from.
        armature_obj (bpy.types.Object): The armature object to get world transforms.

    Returns:
        List[mathutils.Vector]: A list of points in world space.
    """
    points = [armature_obj.matrix_world @ bone.head for bone in bones]
    points.append(armature_obj.matrix_world @ bones[-1].tail)
    return points


def get_hook_bones(bone_names, armature_obj):
    bones = [armature_obj.data.bones.get(name) for name in bone_names]
    hook_bones = []

    if not bones or any(b is None for b in bones):
        print("⚠️ Some bones were not found.")
        return []

    # Parent of the first bone
    first_bone = bones[0]
    if first_bone.parent:
        hook_bones.append(first_bone.parent)
    else:
        print(f"⚠️ First bone '{first_bone.name}' has no parent. Skipping.")
        return []  # You can decide if you want to bail or fall back

    # Middle bones (excluding first)
    hook_bones.extend(bones[1:])

    # Child of the last bone (if it exists)
    last_bone = bones[-1]
    if last_bone.children:
        hook_bones.append(last_bone.children[0])

    return hook_bones


def make_spline_curve(bone_name, armature_obj, debug=False):
    """Creates a spline curve from a bone or a chain of bones in an armature.

    This function identifies whether the provided bone name refers to a single bone 
    or a chain (e.g., MTA-neck.01.c), collects the relevant world-space points, 
    and builds a Bezier curve accordingly.

    Args:
        bone_name (str): The name of the starting bone, following naming conventions 
            like 'MTA-neck.01.c' for multi-span chains or 'MTA-spine.c' for single bones.
        armature_obj (bpy.types.Object): The armature object containing the bones.

    Returns:
        None
    """
    # Ensure the armature is the active object before proceeding
    bpy.context.view_layer.objects.active = armature_obj

    if bpy.context.object.mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')

    multi_match = re.match(r"(MTA-[\w]+)\.(\d+)\.(c|l|r)$", bone_name, re.IGNORECASE)

    if multi_match:
        chain_prefix, start_index, side = multi_match.groups()
        bones = get_bone_chain(chain_prefix, side, armature_obj)
        bones = sanitize_bone_names(bones)

        if not bones:
            print(f"No bones found for chain '{chain_prefix}.{side}'")
            return

        points = get_curve_points_from_bones(bones, armature_obj)
        base_name = chain_prefix.replace("MTA-", "")

        # Get last bone's world direction
        if len(points) > 2:
            child_bone = bones[-1]
            if child_bone.children:
                child_bone = child_bone.children[0]
            child_dir = get_bone_world_direction(armature_obj, child_bone.name)
        else:
            child_dir = None

    else:
        # Single-span case
        bone = armature_obj.data.edit_bones.get(bone_name)
        if not bone:
            print(f"Bone '{bone_name}' not found.")
            return

        points = [
            armature_obj.matrix_world @ bone.head,
            armature_obj.matrix_world @ bone.tail
        ]
        child_dir = None  # Only 2 points, handles default to tangent style

        base_match = re.match(r"(?:.*-)?([\w]+?)(?:\.\d+)?\.(?:c|l|r)$", bone_name, re.IGNORECASE)
        if not base_match:
            print(f"Could not parse bone name '{bone_name}' for naming.")
            return
        base_name = base_match.group(1)

    curve_name = f"{base_name}.crv"
    obj_name = f"{base_name}.spln"

    curve_obj = build_bezier_curve(curve_name, obj_name, points, child_dir=child_dir, debug=debug)

    bone_names = [b.name for b in bones]  # Save the names before they die
    hook_bones = get_hook_bones(bone_names, armature_obj)
    hook_bone_names = [b.name for b in hook_bones]
    # Clear to avoid accidental access
    bones = None
    hook_bones = None

    # Prepare for hook assignment without switching modes in loop
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.objects.active = curve_obj
    curve_obj.select_set(True)

    # Enter Edit Mode on the curve (safe single switch)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.curve.select_all(action='SELECT')
    
    # Back to Object Mode for hook assignment
    add_hook_modifiers(curve_obj, armature_obj, hook_bone_names, debug)
    bpy.ops.object.mode_set(mode='OBJECT')


def sanitize_bone_names(bones):
    """Ensures all bone names are UTF-8 clean. Fixes corrupted ones."""
    for i, b in enumerate(bones):
        try:
            b.name.encode('utf-8')
        except UnicodeEncodeError:
            old_name = b.name
            b.name = f"recovered_bone_{i:03d}"
            print(f"⚠️ Renamed invalid bone '{old_name}' to '{b.name}'")
    return bones


make_spline_curve("MTA-neck.01.c", bpy.data.objects["Armature"], True)