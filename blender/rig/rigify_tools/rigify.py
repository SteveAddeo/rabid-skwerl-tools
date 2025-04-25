import os
import sys
import bpy
import rigify
from importlib import util
from .. import skins


NAME = ""
METARIG_PATH = ""
SKIN_PATH = ""
WGT_PATH = ""


def apply_skins(rig):
    """
    Applies skin weights to all objects in the 'model' collection and parents them to the rig.

    Args:
        rig (bpy.types.Object): The armature object to which the skins are applied.
    """
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    for obj in bpy.data.collections['model'].all_objects:
        obj.select_set(True)
    bpy.ops.object.parent_set(type='ARMATURE')
    skins.apply_vertex_weights(rig.name[:-4], SKIN_PATH)


def build_metarig(name, path):
    """
    Builds a metarig from a provided builder script.

    Args:
        name (str): The base name to give the new metarig.
        path (str): The file path to the builder script.

    Returns:
        tuple[str, str] or bpy.types.Object: Returns an error tuple if file not found, 
        otherwise returns the newly created metarig object.
    """
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
    """
    Builds a complete rig from a metarig and applies skinning and controls.

    Args:
        name (str): The base name used for the metarig and rig.
    """
    metarig = build_metarig(name, METARIG_PATH)
    rig = generate_rig(metarig)
    update_controls(rig)
    apply_skins(rig)
    # Cleanup Scene and Select Rig
    delete_temps(name)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)


def check_rigify():
    """Ensures the Rigify add-on is enabled in Blender."""
    if not bpy.context.preferences.addons.get('rigify'):
        bpy.ops.preferences.addon_enable(module="rigify")


def delete_temps(name):
    """
    Deletes temporary objects and collections created during rig generation.

    Args:
        name (str): The base name of the metarig and rig used for identifying temp assets.
    """
    bpy.data.objects.remove(bpy.data.objects[f"{name}_metarig"])
    bpy.data.collections.remove(bpy.data.collections[f'WGTS_{name}_rig'])


def generate_rig(metarig):
    """
    Generates a rig using Rigify from the given metarig.

    Args:
        metarig (bpy.types.Object): The metarig object used as input for rig generation.

    Returns:
        bpy.types.Object: The newly generated rig object.
    """
    rigify.generate.Generator(context=bpy.context, metarig=metarig).generate()
    return bpy.data.objects[f'{metarig.name.replace("_metarig", "_rig")}']


def import_builder(path):
    """
    Dynamically imports a Python module from a given file path.

    Args:
        path (str): The file path to the Python module.

    Returns:
        module: The imported Python module.
    """
    builder_name = path.split("\\")[-1].split(".")[0]
    spec = util.spec_from_file_location(builder_name, path)
    builder = util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    return builder


def reload_ui():
    """Reloads the custom rig UI from any text blocks named 'rig_ui.py'."""
    for text in [text for text in bpy.data.texts if "rig_ui.py" in text.name]:
        sys.modules[text.name.split(".py")[0]] = text.as_module()


def update_controls(rig):
    """
    Appends control shapes and applies them to bones with custom shapes.

    Args:
        rig (bpy.types.Object): The rig to which custom control shapes will be applied.
    """
    bpy.ops.wm.append(filename='WGTS', directory=WGT_PATH)
    bpy.context.view_layer.layer_collection.children[NAME].children['WGTS'].exclude = True
    ctl_bones = [bone for bone in rig.pose.bones if bone.custom_shape is not None]
    for bone in ctl_bones:
        bone.custom_shape = bpy.data.objects[f"WGT-{bone.name}"]
        if "palm" in bone.name:
            bone.custom_shape_rotation_euler[1] = 1.5708