import bpy
from contextlib import contextmanager

@contextmanager
def ensure_mode(obj, mode):
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
