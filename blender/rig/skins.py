import os
import json
import bpy


def apply_vertex_weights(name, weights_path):
    bpy.ops.object.mode_set(mode='OBJECT')
    for obj in [obj for obj in bpy.data.collections[name].children["model"].all_objects if obj.type == 'MESH']:
        # Get the object's skin weights data from the skin pack
        with open(os.path.join(weights_path, f"{obj.name}.jSkin")) as skin:
            skin_data = json.load(skin)
        weights = skin_data["objDDic"][0]["weights"]
        for bone in weights:
            if bone not in [g.name for g in obj.vertex_groups]:
                obj.vertex_groups.new(name=bone)
            vertex_group = obj.vertex_groups[bone]
            for vert in weights[bone]:
                vertex_group.add([int(vert)], weights[bone][vert] * (1 / len(weights)), 'ADD')


def get_vertex_weights(obj):
    verts = obj.data.vertices
    vert_groups = list(obj.vertex_groups)
    weight_data = {}
    for g, grp in enumerate(vert_groups):
        group_weights = {}
        for v, vert in enumerate(verts):
            if verts[v].groups[g].weight > 0.0:
                group_weights[v] = verts[v].groups[g].weight
        weight_data[grp.name] = group_weights
    return weight_data


def write_vertex_weights():
    # TODO: how to get asset name and path
    rig = bpy.data.armatures[0]
    meshes = [mesh for mesh in bpy.data.objects if mesh.type == "MESH" and mesh.parent.name == rig.name]
    for mesh in meshes:
        get_vertex_weights(mesh)
