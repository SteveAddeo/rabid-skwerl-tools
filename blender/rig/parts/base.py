import re
import bpy
from ...utils import mode_utils
from ..bones import lib as bones_lib
from ..curves import lib as curves_lib


def sanitize_armature(armature_obj: bpy.types.Object, debug: bool = False):
    """Sanitizes all EditBones and PoseBones in an armature object.

    Args:
        armature_obj (bpy.types.Object): The armature to sanitize.
        debug (bool, optional): If True, prints debug information. Defaults to False.
    """
    if armature_obj.mode == 'EDIT':
        bones_lib.sanitize_bone_names(armature_obj.data.edit_bones, debug=debug)
    else:
        with mode_utils.ensure_mode(armature_obj, 'EDIT'):
            bones_lib.sanitize_bone_names(armature_obj.data.edit_bones, debug=debug)

    with mode_utils.ensure_mode(armature_obj, 'POSE'):
        bones_lib.sanitize_bone_names(armature_obj.pose.bones, debug=debug)

    if debug:
        print(f"✅ Armature '{armature_obj.name}' fully sanitized.")


class Rig:
    """Base class for building rig components from meta bones.

    Attributes:
        armature_name (str): Name of the Blender armature object.
        meta_prefix (str): Prefix identifying the part (e.g., 'spine', 'arm').
        side (str): Side identifier ('c', 'l', 'r').
        segments (int): Number of segments to subdivide each bone into.
        debug (bool): If True, prints debug information.
        mta_bones (list[str]): List of MTA bone names to process.
        def_bones (list[str]): Resulting DEF bone names.
        subdiv_bones (list[str] or None): Bones to subdivide after duplication.
    """
    def __init__(self, armature_name, meta_prefix, side='c', debug=False):
        """Initializes a rig part instance.

        Args:
            armature_name (str): Name of the armature object in the scene.
            meta_prefix (str): The naming prefix for the rig part.
            side (str, optional): Side indicator ('c', 'l', or 'r'). Defaults to 'c'.
            debug (bool, optional): Enables debug output. Defaults to False.
        """
        self.armature_name = armature_name
        self.meta_prefix = meta_prefix
        self.side = side
        self.armature_obj = None
        self.armature_data = None
        self.segments = 2
        self.mta_bones = []
        self.def_bones = []
        self.debug = debug
    
    def build(self, subdiv_bones=None):
        """Builds the DEF rig part by duplicating MTA bones and subdividing where specified."""
        self._get_armature()
        sanitize_armature(self.armature_obj, debug=self.debug)
        self._build_def_bones()
        self._finalize_def_bones()
        if self.debug:
            print(f"✅ DEF bones created from MTA bones: {self.def_bones}")
        
    def _build_def_bones(self):
        """Internal method to generate DEF bones from MTA bones and apply subdivisions."""
        def_bone_names = bones_lib.make_def_from_meta(self.armature_name, self.mta_bones, debug=self.debug)

        if self.subdiv_bones:
            subdivided = bones_lib.subdivide_bones(self.armature_name, self.subdiv_bones, self.segments)
            def_bone_names.extend(subdivided)

        self.def_bones = def_bone_names

    def _build_curve(self, source_bone_name):
        """Creates the spline curve from a source meta bone.

        Args:
            source_bone_name (str): The name of the starting MTA bone.
        """
        if not self.armature_obj:
            raise RuntimeError("Armature not initialized.")
        self.spline_curve = curves_lib.make_spline_curve(source_bone_name, self.armature_obj, debug=self.debug)
    
    def _finalize_def_bones(self):
        """Moves any DEF- bones into Deformer Bones collection after building."""
        if not self.armature_obj:
            return

        with mode_utils.ensure_mode(self.armature_obj, 'OBJECT'):
            def_col = self.armature_data.collections.get("Deformer Bones")
            if not def_col:
                def_col = self.armature_data.collections.new(name="Deformer Bones")

            for bone in self.armature_data.bones:
                if bone.name.startswith("DEF-"):
                    def_col.assign(bone)

            if self.debug:
                print(f"✅ Moved all DEF bones into 'Deformer Bones' collection.")
    
    def _get_armature(self):
        """Internal method to set `self.armature_obj` and `self.armature_data` from armature_name.

        Raises:
            ValueError: If the armature is not found or is not of type 'ARMATURE'.
        """
        self.armature_obj = bpy.data.objects.get(self.armature_name)
        if not self.armature_obj or self.armature_obj.type != 'ARMATURE':
            raise ValueError(f"Invalid armature: {self.armature_name}")
        self.armature_data = self.armature_obj.data
        bpy.context.view_layer.objects.active = self.armature_obj

    def _get_bones_by_type(self, bone_type='MTA'):
        """
        Retrieves a list of bone names matching a given type and this part's prefix,
        allowing for optional mid-layers (e.g., CTL-FK, CTL-TWK).

        Args:
            bone_type (str, optional): Bone layer type prefix (e.g., 'MTA', 'DEF', 'CTL', 'CTL-FK'). Defaults to 'MTA'.

        Returns:
            list[str]: List of sanitized matching bone names.
        """
        if not self.armature_obj:
            raise RuntimeError("Armature object not initialized.")

        # Build regex pattern
        pattern = re.compile(rf"^{re.escape(bone_type)}(?:-[\w]+)?-{re.escape(self.meta_prefix)}", re.IGNORECASE)

        with mode_utils.ensure_mode(self.armature_obj, 'EDIT'):
            edit_bones = self.armature_obj.data.edit_bones

            matching_bones = (bone for bone in edit_bones if pattern.match(bone.name))
            safe_names = bones_lib.sanitize_bone_names(matching_bones, debug=self.debug)

        return safe_names


class NeckRig(Rig):
    """Specialized rig part for building a neck with optional subdivisions."""
    def __init__(self, armature_name, side="c"):
        """Initializes a neck rig part with default neck bones and segment count.

        Args:
            armature_name (str): The name of the Blender armature object.
            side (str, optional): Side identifier ('c', 'l', or 'r'). Defaults to "c".
        """
        super().__init__(armature_name, meta_prefix="neck", side=side)
        self.mta_bones: list[str] = []
        self.subdiv_bones: list[str] = []

    def build(self):
        self._get_armature()
        self.mta_bones = self._get_bones_by_type('MTA')
        self.subdiv_bones = [name.replace("MTA-", "DEF-") for name in self.mta_bones]
        super().build()
        self._build_curve(source_bone_name=self.mta_bones[0])


class SpineRig(Rig):
    """Specialized rig part for building a spine with optional subdivisions."""
    def __init__(self, armature_name, side="c"):
        """Initializes a spine rig part with default spine bones and segment count.

        Args:
            armature_name (str): The name of the Blender armature object.
            side (str, optional): Side identifier ('c', 'l', or 'r'). Defaults to "c".
        """
        super().__init__(armature_name, meta_prefix="spine", side=side)
        self.mta_bones: list[str] = ["MTA-hips.c", "MTA-spine.c", "MTA-chest.c"]
        self.subdiv_bones = ["DEF-spine.c"]
        self.segments = 3

    def build(self):
        self._get_armature()
        self._build_curve(source_bone_name="MTA-spine.c")
        super().build()

