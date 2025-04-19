import os
import sys
import bpy
import rigify
from importlib import util
from .. import skins


# TODO: these are temporary; need to get name and path info from scene
# NAME = "genericGenie_0009_gen6Unified"
# METARIG_PATH = r"C:\Users\steve\Documents\blender\rigs\_metadata\metarig_v04.py"
# SKIN_PATH = r"C:\Users\steve\Documents\blender\tests\rig\skin"
# WGT_PATH = r"C:\Users\steve\Documents\blender\rigs\ctl_wgts.blend\Collection"


def apply_skins(rig):
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for obj in bpy.data.collections['model'].all_objects:
        obj.select_set(True)
    bpy.ops.object.parent_set(type='ARMATURE')
    skins.apply_vertex_weights(rig.name[:-4], SKIN_PATH)


def build_metarig(name, path):
    if not os.path.isfile(path):
        return "ERROR", f"Could not find file at {path}"
    check_rigify()
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.armature_add(enter_editmode=True, align='WORLD', location=(0, 0, 0), scale=(1, 1, 1))
    bpy.ops.armature.select_all(action='SELECT')
    bpy.ops.armature.delete()
    bpy.context.object.name = f"{name}_metarig"
    builder = import_builder(path)
    builder.create(bpy.context.active_object)
    bpy.ops.object.mode_set(mode='OBJECT')
    return bpy.data.objects[f'{name}_metarig']


def build_rig(name):
    metarig = build_metarig(name, METARIG_PATH)
    rig = generate_rig(metarig)
    update_controls(rig)
    apply_skins(rig)
    # Cleanup Scene and Select Rig
    delete_temps(name)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)


def check_rigify():
    if not bpy.context.preferences.addons.get('rigify'):
        bpy.ops.preferences.addon_enable(module="rigify")


def delete_temps(name):
    bpy.data.objects.remove(bpy.data.objects[f"{name}_metarig"])
    bpy.data.collections.remove(bpy.data.collections[f'WGTS_{name}_rig'])


def generate_rig(metarig):
    rigify.generate.Generator(context=bpy.context, metarig=metarig).generate()
    return bpy.data.objects[f'{metarig.name.replace("_metarig", "_rig")}']


def import_builder(path):
    builder_name = path.split("\\")[-1].split(".")[0]
    spec = util.spec_from_file_location(builder_name, path)
    builder = util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def reload_ui():
    for text in [text for text in bpy.data.texts if "rig_ui.py" in text.name]:
        sys.modules[text.name.split(".py")[0]] = text.as_module()


def update_controls(rig):
    bpy.ops.wm.append(filename='WGTS', directory=WGT_PATH)
    bpy.context.view_layer.layer_collection.children[NAME].children['WGTS'].exclude = True
    ctl_bones = [bone for bone in rig.pose.bones if bone.custom_shape is not None]
    for bone in ctl_bones:
        bone.custom_shape = bpy.data.objects[f"WGT-{bone.name}"]
        if "palm" in bone.name:
            bone.custom_shape_rotation_euler[1] = 1.5708