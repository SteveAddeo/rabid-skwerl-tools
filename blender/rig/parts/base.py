import bpy
from ...utils import mode_utils
from ..bones import lib as bones_lib


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
        self.subdiv_bones = None
        self.mta_bones = []
        self.def_bones = []
        self.debug = debug
    
    def build(self):
        """Builds the DEF rig part by duplicating MTA bones and subdividing where specified."""
        self._get_armature()
        self._build_def_bones()
        if self.debug:
            print(f"✅ DEF bones created from MTA bones: {self.def_bones}")
        
    def _build_def_bones(self):
        """Internal method to generate DEF bones from MTA bones and apply subdivisions."""
        # Step 1: Duplicate all MTA bones to DEF
        def_bone_names = bones_lib.make_def_from_meta(self.armature_name, self.meta_bones)
        # Step 2: Subdivide requested DEF bones in one batch
        if self.subdiv_bones:
            subdivided = bones_lib.subdivide_bones(self.armature_name, bone_names=self.subdiv_bones, segments=self.segments)
            def_bone_names.extend(subdivided)
        self.def_bones = def_bone_names
    
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


class SpineRig(Rig):
    """Specialized rig part for building a spine with optional subdivisions."""
    def __init__(self, armature_name, side="c"):
        """Initializes a spine rig part with default spine bones and segment count.

        Args:
            armature_name (str): The name of the Blender armature object.
            side (str, optional): Side identifier ('c', 'l', or 'r'). Defaults to "c".
        """
        super().__init__(armature_name, meta_prefix="spine", side=side)
        self.meta_bones: list[str] = ["MTA-hips.c", "MTA-spine.c", "MTA-chest.c"]
        self.segments = 3
        self.subdiv_bones = ['DEF-spine.c']

