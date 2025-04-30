import bpy
from ...utils import mode_utils


def add_constraint(armature_obj, bone_name, constraint_type, name=None, **kwargs):
    """Adds a constraint of the given type to a pose bone.

    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The name of the pose bone to receive the constraint.
        constraint_type (str): The Blender constraint type (e.g., 'COPY_TRANSFORMS').
        name (str, optional): The name of the constraint.
        **kwargs: Additional constraint options.

    Returns:
        bpy.types.Constraint: The newly added constraint.
    """
    pose_bone = armature_obj.pose.bones.get(bone_name)
    if not pose_bone:
        raise ValueError(f"Pose bone '{bone_name}' not found in armature '{armature_obj.name}'.")

    constraint = pose_bone.constraints.new(type=constraint_type)
    constraint.name = name or f"{constraint_type.lower()}_cnst"

    for attr, value in kwargs.items():
        setattr(constraint, attr, value)

    return constraint


def add_copy_transforms_constraint(armature_obj, bone_name, target_name, name=None, **kwargs):
    """Adds a Copy Transforms constraint to a pose bone.

    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The pose bone to constrain.
        target_name (str): The name of the target bone to copy from.
        name (str, optional): Custom constraint name.
        **kwargs: Additional constraint settings.

    Returns:
        bpy.types.Constraint: The created constraint.
    """
    return add_constraint(
        armature_obj,
        bone_name,
        constraint_type='COPY_TRANSFORMS',
        name=name or f"{target_name}_copyTransforms.cnst",
        target=armature_obj,
        subtarget=target_name,
        **kwargs
    )


def add_copy_location_constraint(armature_obj, bone_name, target_name, name=None, **kwargs):
    """Adds a Copy Location constraint to a pose bone.

    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The pose bone to constrain.
        target_name (str): The name of the target bone to copy from.
        name (str, optional): Custom constraint name.
        **kwargs: Additional constraint settings.

    Returns:
        bpy.types.Constraint: The created constraint.
    """
    return add_constraint(
        armature_obj,
        bone_name,
        constraint_type='COPY_LOCATION',
        name=name or f"{target_name}_copyLocation.cnst",
        target=armature_obj,
        subtarget=target_name,
        **kwargs
    )


def add_damped_track_constraint(armature_obj, bone_name, target_name, name=None, **kwargs):
    """Adds a Damped Track constraint to a pose bone.
    
    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The pose bone to constrain.
        target_name (str): The name of the target bone to copy from.
        name (str, optional): Custom constraint name.
        **kwargs: Additional constraint settings.

    Returns:
        bpy.types.Constraint: The created constraint.
    """
    return add_constraint(
        armature_obj,
        bone_name,
        constraint_type='DAMPED_TRACK',
        name=name or f"{target_name}_dampedTrack.cnst",
        target=armature_obj,
        subtarget=target_name,
        **kwargs
    )


def add_limit_rotation_constraint(armature_obj, bone_name, name=None, **kwargs):
    """Adds a Limit Rotation constraint to a pose bone.
    
    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The pose bone to constrain.
        name (str, optional): Custom constraint name.
        **kwargs: Additional constraint settings.

    Returns:
        bpy.types.Constraint: The created constraint.
    """
    return add_constraint(
        armature_obj,
        bone_name,
        constraint_type='LIMIT_ROTATION',
        name=name or "limitRotation.cnst",
        **kwargs
    )


def add_stretch_to_constraint(armature_obj, bone_name, target_name, name=None, **kwargs):
    """Adds a Stretch To constraint to a pose bone.
    
    Args:
        armature_obj (bpy.types.Object): The armature containing the pose bone.
        bone_name (str): The pose bone to constrain.
        target_name (str): The name of the target bone to copy from.
        name (str, optional): Custom constraint name.
        **kwargs: Additional constraint settings.

    Returns:
        bpy.types.Constraint: The created constraint.
    """
    return add_constraint(
        armature_obj,
        bone_name,
        constraint_type='STRETCH_TO',
        name=name or f"{target_name}_stretchTo.cnst",
        target=armature_obj,
        subtarget=target_name,
        **kwargs
    )
