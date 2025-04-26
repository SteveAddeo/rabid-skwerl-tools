import bpy
from contextlib import contextmanager

@contextmanager
def ensure_mode(obj, mode):
    """Context manager that ensures the specified object is in a given mode,
    and restores the original mode and active object afterward.

    Args:
        obj (bpy.types.Object): The Blender object to operate on.
        mode (str): The mode to switch to (e.g., 'EDIT', 'OBJECT', 'POSE').

    Yields:
        None: Allows code to run within the desired mode context.
    """
    prev_mode = bpy.context.object.mode if bpy.context.object else 'OBJECT'
    prev_active = bpy.context.view_layer.objects.active

    if bpy.context.view_layer.objects.active != obj:
        bpy.context.view_layer.objects.active = obj
    if obj.mode != mode:
        bpy.ops.object.mode_set(mode=mode)

    try:
        yield
    finally:
        if obj.mode != prev_mode:
            bpy.ops.object.mode_set(mode=prev_mode)
        bpy.context.view_layer.objects.active = prev_active
