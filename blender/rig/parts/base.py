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
        self.armature_name: str = armature_name
        self.meta_prefix: str = meta_prefix
        self.side: str = side
        self.armature_obj = None
        self.armature_data = None
        self.segments: list[str]  = 2
        self.mta_bones: list[str]  = []
        self.def_bones: list[str]  = []
        self.subdiv_bones: list[str]  = []
        self.debug: bool = debug
    
    def build(self):
        """Builds the DEF rig part by duplicating MTA bones and subdividing where specified."""
        self._get_armature()
        sanitize_armature(self.armature_obj, debug=self.debug)
        self._build_def_bones()
        self._batch_autoclean_collections()
        print(f"Deformer bones for {self.meta_prefix}: {self.def_bones}")
    
    def _autoclean_bone_collections(self, prefix, collection):
        """Ensures bones with a prefix only exist in the expected bone collection.

        Args:
            prefix (str, optional): Prefix to match bone names (e.g., 'DEF-').
            collection (str, optional): The target collection where bones should be assigned.
        """
        if not self.armature_obj:
            raise RuntimeError("Armature object not initialized.")
        with mode_utils.ensure_mode(self.armature_obj, 'OBJECT'):
            target_col = self.armature_data.collections.get(collection)
            if not target_col:
                if self.debug:
                    print(f"⚠️ Target collection '{collection}' not found. Skipping autoclean.")
                return
            # Bones matching the prefix
            matching_bone_names = self._get_bones_by_type(bone_type=prefix.rstrip("-"))
            for bone_name in matching_bone_names:
                bone_data = self.armature_data.bones.get(bone_name)
                if not bone_data:
                    continue
                # Remove from all wrong collections
                for col in self.armature_data.collections:
                    if bone_data.name in col.bones and col != target_col:
                        col.unassign(bone_data)
                # Make sure assigned to the correct one
                if bone_data.name not in target_col.bones:
                    target_col.assign(bone_data)
            if self.debug:
                print(f"✅ Autocleaned '{prefix}' bones into '{collection}'.")
    
    def _batch_autoclean_collections(self):
        """Automatically reassigns known bone prefixes to their expected bone collections."""
        if not self.armature_obj:
            raise RuntimeError("Armature object not initialized.")
        # Define your expected bone prefixes and their collections
        clean_map = {
            "MTA-": "Meta Bones",
            "DEF-": "Deformer Bones",
            "TGT-": "Target Bones",
            "CTL-": "Control Bones",
            "CTL-TWK-": "Tweak Control",
            "CTL-FK-": "FK Control",
            "CTL-IK-": "IK Control",
            "FK-": "FK Bones",
            "IK-": "IK Bones",
            "DRV-": "Driver Bones",
            "UTL-": "Utility Bones",
        }
        for prefix, collection_name in clean_map.items():
            self._autoclean_bone_collections(prefix=prefix, collection=collection_name)
        
    def _build_def_bones(self):
        """Internal method to generate DEF bones from MTA bones and apply subdivisions."""
       # Step 1: Create DEF bones from MTA
        def_bone_names = bones_lib.make_def_from_meta(self.armature_name, self.mta_bones, debug=self.debug)
        # Step 2: Subdivide any requested DEF bones
        if self.subdiv_bones:
            subdivided = bones_lib.subdivide_bones(self.armature_name, self.subdiv_bones, self.segments, debug=self.debug)
            # Remove only the bones that were subdivided, not others
            for orig in self.subdiv_bones:
                if orig in def_bone_names:
                    def_bone_names.remove(orig)
            def_bone_names.extend(subdivided)
        # Step 3: Clean recovered bones ONLY
        final_bones = [name for name in def_bone_names if not name.startswith("recovered_bone_")]
        # Step 4: Assign bones to Deformer Bone collection
        self._finalize_bones("DEF-", "Deformer Bones")
        root_bone = self._get_root_bone(final_bones)
        self.def_bones = self._sort_bone_chain(root_bone, final_bones)
        if self.debug:
            print(f"✅ DEF bones created from MTA bones: {self.def_bones}")

    def _build_curve(self, source_bone_name):
        """Creates the spline curve from a source meta bone.

        Args:
            source_bone_name (str): The name of the starting MTA bone.
        """
        if not self.armature_obj:
            raise RuntimeError("Armature not initialized.")
        self.spline_curve = curves_lib.make_spline_curve(source_bone_name, self.armature_obj, debug=self.debug)
    
    def _finalize_bones(self, prefix, collection):
        """Moves bones with a given prefix into a specified bone collection and updates the internal list.

        Args:
            prefix (str, optional): Prefix to filter bones (e.g., 'DEF-', 'CTL-').
            collection (str, optional): Target bone collection name.
        """
        if not self.armature_obj:
            raise RuntimeError("Armature object not initialized.")
        # Ensure the collection exists
        with mode_utils.ensure_mode(self.armature_obj, 'OBJECT'):
            bone_col = self.armature_data.collections.get(collection)
            if not bone_col:
                bone_col = self.armature_data.collections.new(name=collection)
            # Get all matching bones
            matching_bones = self._get_bones_by_type(bone_type=prefix.rstrip("-"))
            for bone_name in matching_bones:
                bone_data = self.armature_data.bones.get(bone_name)
                if bone_data:
                    bone_col.assign(bone_data)
            # Debug
            if self.debug:
                print(f"✅ Finalized {len(matching_bones)} '{prefix}' bones into '{collection}'.")
    
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
        """Retrieves a list of bone names matching a given type and this part's prefix,
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
    
    def _get_root_bone(self, bones):
        """Finds the topmost root bone among a list of bone names.

        Args:
            bones (list[str]): Bone names to search.

        Returns:
            str: Root bone name.
        """
        armature_data = self.armature_obj.data
        candidate_set = set(bones)
        for name in bones:
            bone = armature_data.bones.get(name)
            if not bone:
                continue
            # If no parent or parent not inside candidates → it's a root
            if not bone.parent or bone.parent.name not in candidate_set:
                return name
        raise ValueError("Root bone not found in candidates.")

    
    def _sort_bone_chain(self, root_bone_name, candidates):
        """Sorts bones following parenting from a root.

        Args:
            root_bone_name (str): Name of starting parent bone.
            candidates (list[str]): List of bone names to sort.

        Returns:
            list[str]: Bones sorted in parent → child order.
        """
        chain = []
        current = root_bone_name
        while current:
            chain.append(current)
            next_bone = None
            for bname in candidates:
                bone = self.armature_obj.data.bones.get(bname)
                if bone and bone.parent and bone.parent.name == current:
                    next_bone = bname
                    break
            current = next_bone
        return chain



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
        self.subdiv_bones: list[str]  = ["DEF-spine.c"]
        self.segments: int = 3

    def build(self):
        self._get_armature()
        self._build_curve(source_bone_name="MTA-spine.c")
        super().build()

