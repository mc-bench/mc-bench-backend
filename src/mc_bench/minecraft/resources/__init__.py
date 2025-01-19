"""Minecraft Resource Loading and Model Processing

This module handles loading and processing of Minecraft block models, blockstates, and textures.

Coordinate Systems:
- Minecraft uses a left-handed coordinate system:
  - +X axis points East (right)
  - +Y axis points Up
  - +Z axis points South (away from player)
  - One block = 1 unit in any direction
  - Rotating counterclockwise around Y: +X -> -Z -> -X -> +Z
  - This affects how rotations are interpreted in blockstates and models

Rotations:
- Due to the left-handed system, positive rotations follow the left-hand rule:
  - Curl fingers of left hand along positive axis direction
  - Thumb points in positive rotation direction
- Y-axis rotation examples (counter-clockwise looking down):
  - 0°: Model faces north (-Z)
  - 90°: Model faces east (+X)
  - 180°: Model faces south (+Z)
  - 270°: Model faces west (-X)

UV Coordinates:
- Origin (0,0) is at top-left of texture
- (16,16) is at bottom-right
- U increases rightward (like X)
- V increases downward (unlike Y)

Block Models:
- Used to depict all blocks in the game
- Stored as JSON files in assets/<namespace>/models/block/
- Can inherit from parent models
- Define geometry through elements with faces and textures
- Support rotation, UV mapping, and ambient occlusion

Block States:
- Define different variants/states of blocks (e.g. door open/closed)
- Stored in assets/<namespace>/blockstates/
- Can use either "variants" or "multipart" format:
  - variants: Maps state combinations to models
  - multipart: Combines multiple models based on conditions

Model Properties:
- parent: Inherits from another model
- textures: Maps texture variables to texture files
- elements: List of cuboid elements that make up the model
- ambientocclusion: Controls ambient occlusion rendering
- display: Controls how item is displayed in different contexts

Element Properties:
- from/to: Define cuboid bounds [x,y,z] (-16 to 32)
- rotation: Optional {origin, axis, angle, rescale}
- faces: Define textures and properties for each face

Face Properties:
- uv: Texture coordinates [x1,y1,x2,y2]
- texture: Reference to texture variable
- cullface: Face culling direction
- rotation: Texture rotation (0,90,180,270)
- tintindex: For color tinting

This module provides classes to load these resources and convert them into
a programmatic representation that can be used for rendering or export.

UV Lock and Rotation Behavior:
- UV locking affects how texture coordinates behave during model rotation
- When UV lock is enabled:
  - Textures maintain their world-space orientation regardless of model rotation
  - Example: Wood grain stays vertical even when fence connects diagonally
  - Only affects model-level rotation from blockstates
  - Does NOT affect element-level or face-level rotations
- Processing order (from lowest to highest level):
  1. Face UV coordinates are applied (from model JSON)
  2. Face rotation is applied (0°, 90°, 180°, 270°)
  3. Element rotation is applied (-45° to +45°)
  4. Model rotation is applied (0°, 90°, 180°, 270°)
  5. UV lock is applied (if enabled)
"""

import collections
import copy
import itertools
import json
import os
import random
import re
import textwrap
from functools import lru_cache
from math import cos, radians, sin

import minecraft_assets
import minecraft_data
import numpy as np
import PIL.Image

from .. import rendering

WATERLOGGABLE_BLOCKS = [
    "sea_pickle",
]


class BlockStates:
    def __init__(self, data):
        self._data = data

    def get_model_specifications(self, states=None):
        specifications = []
        states = states or {}

        if "variants" in self._data:
            predicate_sets = _make_predicate_sets_from_variant_keys(
                self._data["variants"]
            )

            selected_variant = None

            for predicates, variant in predicate_sets:
                if _match_predicates(predicates, states):
                    selected_variant = variant

            if selected_variant is None:
                raise Exception(
                    f"No variant found for {states} in {self._data['variants'].keys()}."
                )

            if selected_variant is not None:
                if isinstance(selected_variant, list):
                    specifications.append(random.choice(selected_variant))
                else:
                    specifications.append(selected_variant)

        elif "multipart" in self._data:
            for part in self._data["multipart"]:
                if "when" not in part or _match_predicates(part["when"], states):
                    state_or_states = part["apply"]
                    if isinstance(state_or_states, list):
                        weights = [state.get("weight", 1) for state in state_or_states]
                        specifications.extend(
                            random.choices(state_or_states, weights, k=1)
                        )
                    else:
                        specifications.append(state_or_states)
        return specifications


def _match_predicates(predicates, states):
    for key, value in predicates.items():
        if key == "OR":
            return any(
                [
                    _match_predicates(other_predicates, states)
                    for other_predicates in value
                ]
            )
        elif key == "AND":
            return all(
                [
                    _match_predicates(other_predicates, states)
                    for other_predicates in value
                ]
            )
        elif "|" in value:
            return states.get(key, "false") in value.split("|")
        elif states.get(key, "false") != value:
            return False
        else:
            return True

    # we conspire to have a wildcard predicate that matches everything at the
    # end of predicate list, if possible
    return True


def _make_predicates(predicate_str):
    predicates = {}
    for predicate in predicate_str.split(","):
        key, value = predicate.split("=")
        predicates[key] = value
    return predicates


PREDICATE_REGEX = re.compile(r"(.*)\[(.*)\]")


def _make_predicate_sets_from_variant_keys(states: dict):
    predicate_sets = []
    default_predicate = None
    for key, value in states.items():
        result = PREDICATE_REGEX.findall(key)
        if not result:
            default_predicate = key
            continue
        else:
            predicates = _make_predicates(result[1])
            predicate_sets.append((predicates, value))

    if default_predicate is not None:
        predicate_sets.append(({}, states[default_predicate]))

    return predicate_sets


class ResourceLoader:
    def __init__(self, version):
        self._asset_dir = minecraft_assets.get_asset_dir(version)
        self._data_files = minecraft_data.MinecraftDataFiles(
            minecraft_data.GameType.PC, version
        )

        with open(self._asset_dir / "blocks_models.json", "r") as f:
            self._block_models = json.load(f)

        with open(self._asset_dir / "blocks_states.json", "r") as f:
            self._block_states = json.load(f)

        with open(self._asset_dir / "blocks_textures.json", "r") as f:
            self._block_textures = json.load(f)

        with open(self._data_files.get("tints", "tints.json"), "r") as f:
            self._tints = json.load(f)

        with open(self._data_files.get("blocks", "blocks.json"), "r") as f:
            self._blocks = json.load(f)

    def get_models(self, canonical_name):
        split_name = canonical_name.split("[")
        if len(split_name) > 1:
            states = split_name[1].strip("]")
            states = states.split(",")
            states = dict(map(lambda x: x.split("="), states))

            name = split_name[0]
            if name not in WATERLOGGABLE_BLOCKS:
                if "waterlogged" in states:
                    del states["waterlogged"]
        else:
            states = None
            name = canonical_name

        block_states = BlockStates(self.get_block_states(name))

        model_specifications = block_states.get_model_specifications(states)

        models = []
        for model_spec in model_specifications:
            model_name = model_spec["model"]
            merged_model_spec = self.get_merged_block_model(model_name)
            if merged_model_spec:
                textures = self._get_textures_for_model(merged_model_spec)
                out = copy.deepcopy(merged_model_spec)
                for element in out.get("elements", []):
                    for face, face_data in element["faces"].items():
                        texture_key = face_data["texture"]
                        if texture_key.startswith("#"):
                            texture_key = texture_key[1:]
                            face_data["texture"] = textures[texture_key]

                models.append(
                    ModelData(
                        specification=out,
                        uv_lock=model_spec.get("uvlock", False),
                        x=model_spec.get("x", 0),
                        y=model_spec.get("y", 0),
                        z=model_spec.get("z", 0),
                        light_emission=0,
                    )
                )
        return models

    def _get_textures_for_model(self, model_spec):
        textures = {}

        for texture_key, texture_name in model_spec["textures"].items():
            if texture_name.startswith("#"):
                continue

            textures[texture_key] = self.get_block_texture(texture_name)

        for texture_key in model_spec["textures"]:
            key = texture_key
            value = model_spec["textures"][key]
            while value.startswith("#"):
                key = value[1:]
                value = model_spec["textures"][key]
            if texture_key not in textures:
                textures[texture_key] = textures[key]

        return textures

    @lru_cache(maxsize=None)
    def get_block_model(self, block_name) -> dict:
        if block_name.startswith("minecraft:block/"):
            block_name = block_name.replace("minecraft:block/", "")
        if "/" in block_name:
            block_name = block_name.split("/")[1].strip()

        return self._block_models.get(block_name, None)

    def list_blocks(self):
        return [block["name"] for block in self._blocks]

    def list_blockstates(self):
        for path in self._paths:
            for root, _, files in os.walk(os.path.join(path, "blockstates")):
                for file in files:
                    if file.endswith(".json"):
                        block_name, _ = os.path.splitext(file)
                        yield block_name

    def get_all_block_variants(self):
        variants = []
        for block_name in self.list_blockstates():
            block_variants = []
            block_states = self.get_block_states(block_name)
            if "multipart" in block_states:
                parts = block_states["multipart"]
                conditions = collections.defaultdict(set)
                for part in parts:
                    if "when" not in part:
                        continue
                    for key, value in part["when"].items():
                        if key in ("OR", "AND"):
                            for cond_set in value:
                                for key, value in cond_set.items():
                                    conditions[key].add(value)
                        else:
                            conditions[key].add(value)
                variant_data = list(
                    itertools.product(
                        *[[(k, v) for v in vals] for k, vals in conditions.items()]
                    )
                )
                for variant in variant_data:
                    state = ",".join(map(lambda x: f"{x[0]}={x[1]}", variant))
                    if state:
                        block_variants.append(f"{block_name}[{state}]")
                    else:
                        block_variants.append(block_name)
            variants.extend(block_variants)
        return variants

    def get_merged_block_model(self, block_name) -> dict:
        if block_name.startswith("minecraft:block/"):
            block_name = block_name.replace("minecraft:block/", "")

        final_block_model = {}
        block_model = self.get_block_model(block_name)
        if not block_model:
            return final_block_model

        # Get light emission for this block
        # light_emission = self.get_block_light_emission(block_name)

        if block_model.get("parent"):
            parent_block = block_model.get("parent")
            parent = self.get_merged_block_model(parent_block)
            final_block_model.update(parent)
            for key, value in block_model.items():
                if key == "parent":
                    continue

                if isinstance(value, dict):
                    if key in final_block_model:
                        final_block_model[key].update(value)
                    else:
                        final_block_model[key] = value
                else:
                    final_block_model[key] = value
        else:
            final_block_model.update(block_model)

        return final_block_model

    @lru_cache(maxsize=None)
    def get_block_states(self, block_name) -> dict:
        if block_name.startswith("minecraft:block/"):
            block_name = block_name.replace("minecraft:block/", "")

        if "/" in block_name:
            block_name = block_name.split("/")[1].strip()

        return self._block_states.get(block_name, None)

    @lru_cache(maxsize=None)
    def get_block_texture(self, texture_name):
        if texture_name.startswith("minecraft:block/"):
            texture_name = texture_name.replace("minecraft:block/", "")

        if "/" in texture_name:
            texture_name = texture_name.split("/")[1].strip()

        path = self._asset_dir / "blocks" / f"{texture_name}.png"

        return str(path) if path.exists() else None

    @lru_cache(maxsize=None)
    def get_block(self, canonical_name):
        models = self.get_models(canonical_name)
        return BlockData(canonical_name, models)


class BlockData:
    def __init__(self, canonical_name, models):
        self.canonical_name = canonical_name
        self.models = list(models)

    @classmethod
    def from_resource_loader(cls, rl, canonical_name):
        models = rl.get_models(canonical_name)
        return cls(canonical_name, models)

    def to_minecraft_block(self):
        models = []
        for idx, model in enumerate(self.models):
            models.append(model.to_minecraft_model(name=f"model_{idx}"))
        return MinecraftBlock(
            self.canonical_name,
            models,
            states=self.states,
        )

    @property
    def states(self):
        result = PREDICATE_REGEX.findall(self.canonical_name)
        if not result:
            return {}
        return _make_predicates(result[0][1])


class ModelData:
    """Represents a Minecraft model with its transformation data.

    Model-level rotation is applied to the entire model as a whole:
    - x_rotation: Rotation around X axis in degrees (0, 90, 180, 270)
    - y_rotation: Rotation around Y axis in degrees (0, 90, 180, 270)
    - z_rotation: Rotation around Z axis in degrees (0, 90, 180, 270)

    UV Lock Behavior:
    - uv_lock determines if textures maintain world-space orientation during model rotation
    - When uv_lock=True:
        - Textures stay aligned with world axes regardless of model rotation
        - Example: Wood grain texture remains vertical even when block is rotated
        - Only affects model-level rotation from blockstates
        - Does NOT affect element-level or face-level rotations
    - When uv_lock=False:
        - Textures rotate along with the model
        - Standard behavior for most blocks

    Processing Order:
    1. Face UV coordinates from model JSON
    2. Face rotation (0°, 90°, 180°, 270°)
    3. Element rotation (-45° to +45°)
    4. Model rotation (0°, 90°, 180°, 270°)
    5. UV lock compensation (if enabled)

    Example:
        A fence post connecting diagonally might use:
        - Element rotation of 45° around Y axis (rotates with texture)
        - Model rotation from blockstate (texture stays aligned if uv_lock=True)
    """

    def __init__(self, specification, light_emission=0, uv_lock=False, x=0, y=0, z=0):
        self._specification = specification
        self.light_emission = light_emission
        self.uv_lock = uv_lock
        self.x_rotation = x
        self.y_rotation = y
        self.z_rotation = z

    def to_minecraft_model(self, name=None):
        return MinecraftModel.from_specification(
            name or "model",
            self._specification,
            uv_lock=self.uv_lock,
            x_rotation=self.x_rotation,
            y_rotation=self.y_rotation,
            z_rotation=self.z_rotation,
        )


class MinecraftModelFace:
    """Represents a face in a Minecraft model element with texture mapping.

    Face rotation affects texture orientation:
    - rotation: Rotates texture in 90-degree increments (0, 90, 180, 270)
    - This rotation is applied in UV space, not 3D space
    - Applied BEFORE element rotation and model rotation
    - NOT affected by uv_lock setting

    UV coordinates define how texture maps to face:
    - uv: [x1, y1, x2, y2] where each component is 0-16
    - (0,0) is top-left of texture, (16,16) is bottom-right
    - UV coordinates can be flipped or rotated for different orientations

    Example UV mappings:
    - [0,0,16,16]: Uses full texture
    - [16,0,0,16]: Flips texture horizontally
    - [0,16,16,0]: Flips texture vertically

    When face rotation is applied:
    1. UV coordinates are interpreted normally
    2. The resulting texture is rotated around its center
    3. The rotation is counter-clockwise in texture space
    """

    def __init__(
        self,
        name,
        direction,
        texture,
        *,
        uv=None,
        cullface=None,
        rotation=0,
        tintindex=-1,
    ):
        self.name = name
        self.direction = direction
        self.texture = texture
        self.uv = uv or [0, 0, 16, 16]
        self.cullface = cullface
        self.rotation = rotation  # 0, 90, 180, or 270 degrees
        self.tintindex = tintindex

    def to_blender_face(self):
        # TODO: Implement conversion logic
        pass

    def debug_info(self, indent=0):
        indent_str = "  " * indent
        if isinstance(self.texture, str) and os.path.exists(self.texture):
            texture_path = os.path.relpath(self.texture)
        else:
            texture_path = self.texture

        info = [
            f"{indent_str}Face: {self.name}",
            f"{indent_str}  Direction: {self.direction}",
            f"{indent_str}  Texture: {texture_path}",
            f"{indent_str}  UV: {self.uv}",
            f"{indent_str}  Cullface: {self.cullface}",
            f"{indent_str}  Rotation: {self.rotation}",
            f"{indent_str}  Tint Index: {self.tintindex}",
        ]
        return "\n".join(info)


class ModelElementRotation:
    """Represents element-level rotation in a Minecraft model.

    Element rotation is more flexible than model rotation:
    - origin: [x,y,z] point around which to rotate (in model space)
    - axis: Which axis to rotate around ('x', 'y', or 'z')
    - angle: Rotation angle in degrees (-45 to +45)
    - rescale: Whether to rescale the element to maintain volume

    Unlike model rotation which is limited to 90-degree increments,
    element rotation supports any angle between -45 and +45 degrees.

    The rescale option is used for diagonal elements:
    - When True: Element is scaled to maintain its volume after rotation
    - When False: Element maintains its original dimensions

    Example:
        A fence post diagonal might use:
        {
            "origin": [8, 8, 8],  # Center of block
            "axis": "y",
            "angle": 45,
            "rescale": true
        }
    """

    def __init__(self, origin, axis, angle, rescale=False):
        self.origin = origin  # [x,y,z]
        self.axis = axis  # 'x', 'y', or 'z'
        self.angle = angle  # Between -45 and +45 degrees
        self.rescale = rescale

    @classmethod
    def from_dict(cls, rotation_dict):
        """Create a ModelElementRotation from a dictionary specification."""
        if rotation_dict is None:
            return None

        return cls(
            origin=rotation_dict.get("origin", [0, 0, 0]),
            axis=rotation_dict.get("axis", "y"),
            angle=rotation_dict.get("angle", 0),
            rescale=rotation_dict.get("rescale", False),
        )


class MinecraftModelElement:
    """Represents a cubic element in a Minecraft model.

    Properties:
    - from/to: Start/end points [x,y,z] between -16 and 32
    - rotation: Optional element rotation {origin, axis, angle, rescale}
    - shade: Whether faces cast shadows
    - faces: Dictionary of faces by direction
    """

    def __init__(self, name, from_pos, to_pos, faces, *, rotation=None, shade=True):
        self.name = name
        self.from_ = from_pos
        self.to_ = to_pos
        self.faces = faces
        self.rotation = (
            ModelElementRotation.from_dict(rotation)
            if isinstance(rotation, dict)
            else rotation
        )
        self.shade = shade

    def debug_info(self, indent=0):
        indent_str = "  " * indent
        info = [
            f"{indent_str}Element: {self.name}",
            f"{indent_str}  From: {self.from_}",
            f"{indent_str}  To: {self.to_}",
        ]

        if self.rotation:
            info.extend(
                [
                    f"{indent_str}  Rotation:",
                    f"{indent_str}    Origin: {self.rotation.origin}",
                    f"{indent_str}    Axis: {self.rotation.axis}",
                    f"{indent_str}    Angle: {self.rotation.angle}",
                    f"{indent_str}    Rescale: {self.rotation.rescale}",
                ]
            )
        else:
            info.append(f"{indent_str}  Rotation: None")

        info.extend([f"{indent_str}  Shade: {self.shade}", f"{indent_str}  Faces:"])

        for direction, face in self.faces.items():
            info.append(face.debug_info(indent + 2))

        return "\n".join(info)


class MinecraftModel:
    """Represents a complete Minecraft model with all its elements and transformations.

    Rotation and UV Lock Processing Order:
    1. Face-level:
       - UV coordinates are applied from model JSON
       - Face rotation applied (0°, 90°, 180°, 270°)
       - Not affected by uv_lock

    2. Element-level:
       - Element rotation applied (-45° to +45°)
       - Textures always rotate with element
       - Not affected by uv_lock

    3. Model-level:
       - Model rotation from blockstate (0°, 90°, 180°, 270°)
       - If uv_lock=True:
         - Additional transforms applied to keep textures aligned with world
         - Commonly used for fences, walls, and other connecting blocks
       - If uv_lock=False:
         - Textures rotate with model (default behavior)

    Example UV Lock Usage:
    - Fence post connecting to another post:
      1. Element rotated 45° around Y axis (texture rotates with element)
      2. Face rotations orient wood texture (independent of uv_lock)
      3. Model rotation from blockstate determines final orientation
      4. If uv_lock=True: Wood grain stays vertical despite rotation

    Rotation hierarchy (applied in this order):
    1. Element-level rotation (ModelElementRotation)
    2. Face texture rotation (MinecraftModelFace.rotation)
    3. Model-level rotation (from blockstate variants)

    UV Lock Behavior:
    - Without UV lock: Textures rotate with the model
    - With UV lock: Textures maintain world-space orientation
    - UV lock affects model-level rotation only
    - Element and face rotations ignore UV lock

    Example:
    A fence post connecting to another post might have:
    1. Element rotation of 45° around Y axis
    2. Face rotations to orient wood texture
    3. Model rotation from blockstate to face correct direction
    4. UV lock to keep wood grain consistent
    """

    def __init__(
        self,
        name,
        *,
        elements=None,
        parent=None,
        ambientocclusion=True,
        textures=None,
        display=None,
        gui_light="side",
        uv_lock=False,
        x_rotation=0,
        y_rotation=0,
        z_rotation=0,
    ):
        self.name = name
        self.parent = parent
        self.ambientocclusion = ambientocclusion
        self.textures = textures or {}
        self.elements = elements or []
        self.display = display or {}
        self.gui_light = gui_light
        # Add rotation and UV lock properties from blockstate
        self.uv_lock = uv_lock
        self.x_rotation = x_rotation
        self.y_rotation = y_rotation
        self.z_rotation = z_rotation

    @classmethod
    def from_specification(
        cls,
        name,
        specification,
        *,
        uv_lock=False,
        x_rotation=0,
        y_rotation=0,
        z_rotation=0,
    ):
        """Create a MinecraftModel from a model specification dictionary."""
        elements = []
        for idx, element_spec in enumerate(specification.get("elements", [])):
            element_name = f"element_{idx}"
            faces = {}

            for direction, face_data in element_spec.get("faces", {}).items():
                face_name = f"element_{idx}_face_{direction}"
                faces[direction] = MinecraftModelFace(
                    name=face_name,
                    direction=direction,
                    texture=face_data["texture"],
                    uv=face_data.get("uv"),
                    cullface=face_data.get("cullface"),
                    rotation=face_data.get("rotation", 0),
                    tintindex=face_data.get("tintindex", -1),
                )

            elements.append(
                MinecraftModelElement(
                    name=element_name,
                    from_pos=element_spec["from"],
                    to_pos=element_spec["to"],
                    faces=faces,
                    rotation=element_spec.get("rotation"),
                    shade=element_spec.get("shade", True),
                )
            )

        return cls(
            name=name,
            elements=elements,
            parent=specification.get("parent"),
            ambientocclusion=specification.get("ambientocclusion", True),
            textures=specification.get("textures", {}),
            display=specification.get("display", {}),
            gui_light=specification.get("gui_light", "side"),
            uv_lock=uv_lock,
            x_rotation=x_rotation,
            y_rotation=y_rotation,
            z_rotation=z_rotation,
        )

    def debug_info(self, indent=0):
        indent_str = "  " * indent

        # Create a copy of textures dict and make paths relative
        textures_debug = {}
        for key, path in self.textures.items():
            if isinstance(path, str) and os.path.exists(path):
                textures_debug[key] = os.path.relpath(path)
            else:
                textures_debug[key] = path

        info = [
            f"{indent_str}Model: {self.name}",
            f"{indent_str}  Parent: {self.parent}",
            f"{indent_str}  Ambient Occlusion: {self.ambientocclusion}",
            f"{indent_str}  GUI Light: {self.gui_light}",
            f"{indent_str}  Textures: {textwrap.indent(json.dumps(textures_debug, indent=2), indent_str)}",
            f"{indent_str}  UV Lock: {self.uv_lock}",
            f"{indent_str}  X Rotation: {self.x_rotation}",
            f"{indent_str}  Y Rotation: {self.y_rotation}",
            f"{indent_str}  Z Rotation: {self.z_rotation}",
            f"{indent_str}  Elements:",
        ]

        for element in self.elements:
            info.append(element.debug_info(indent + 2))

        return "\n".join(info)

    def to_blender_model(self):
        """Convert Minecraft model to Blender format.

        Coordinate System Conversion:
        Minecraft (left-handed):          Blender (right-handed):
        +X = East (right)                 +X = Right
        +Y = Up                          +Y = Forward (into screen)
        +Z = South (away)                +Z = Up

        So Minecraft (X,Y,Z) maps to Blender (X,-Z,Y)

        Rotation Order:
        Minecraft applies model rotations in this order:
        1. X rotation first (around X axis)
        2. Z rotation second (around Z axis)
        3. Y rotation last (around Y axis)

        When converting to Blender:
        - Minecraft X rotation -> Blender X rotation (negated due to coordinate flip)
        - Minecraft Y rotation -> Blender Z rotation (negated for right-hand rule)
        - Minecraft Z rotation -> Blender Y rotation (positive, maps to negative Y)

        Matrix multiplication must happen in reverse order of the rotations:
        model_rotation = z_matrix @ y_matrix @ x_matrix

        This ensures rotations are applied in the correct order: X, then Z, then Y
        """
        blender_elements = []

        # Convert Minecraft rotations to Blender rotations:
        # Minecraft coordinate system:
        # - X: East (right)
        # - Y: Up
        # - Z: South (away)
        #
        # Blender coordinate system:
        # - X: Right
        # - Y: Forward (into screen)
        # - Z: Up
        #
        # Conversion:
        # - Minecraft Y-rotation → Blender Z-rotation
        # - Minecraft Z-rotation → Blender -Y-rotation
        # - Minecraft X-rotation → Blender X-rotation
        x_matrix = create_rotation_matrix("x", -self.x_rotation)
        y_matrix = create_rotation_matrix(
            "y", self.z_rotation
        )  # Note: positive Z becomes negative Y
        z_matrix = create_rotation_matrix("z", -self.y_rotation)  # Y becomes Z

        # Combine rotations in Minecraft's order: X, then Z, then Y
        model_rotation = (
            z_matrix @ y_matrix @ x_matrix
            if any([self.x_rotation, self.y_rotation, self.z_rotation])
            else None
        )

        # Convert block center from Minecraft to Blender coordinates
        block_center = self._minecraft_to_blender_coords(
            [8, 8, 8]
        )  # Minecraft coordinates are in [0,16] range

        for element in self.elements:
            # Convert element coordinates from Minecraft to Blender space
            # TODO: Deal with zero-thickness elements to prevent z-fighting
            from_pos = self._minecraft_to_blender_coords(element.from_)
            to_pos = self._minecraft_to_blender_coords(element.to_)

            # Generate vertices for the element
            vertices = [
                [from_pos[0], from_pos[1], from_pos[2]],  # 0: left bottom back
                [to_pos[0], from_pos[1], from_pos[2]],  # 1: right bottom back
                [to_pos[0], from_pos[1], to_pos[2]],  # 2: right top back
                [from_pos[0], from_pos[1], to_pos[2]],  # 3: left top back
                [from_pos[0], to_pos[1], from_pos[2]],  # 4: left bottom front
                [to_pos[0], to_pos[1], from_pos[2]],  # 5: right bottom front
                [to_pos[0], to_pos[1], to_pos[2]],  # 6: right top front
                [from_pos[0], to_pos[1], to_pos[2]],  # 7: left top front
            ]

            # Apply element rotation if specified
            vertices = self._apply_element_rotation(vertices, element)

            # Apply model rotation if any
            if model_rotation is not None:
                vertices = [
                    rotate_point(vertex, block_center, model_rotation)
                    for vertex in vertices
                ]

            blender_faces = []
            for direction, face in element.faces.items():
                # Get vertex indices and UVs for this face direction
                vertex_indices = self._get_face_vertices(direction)
                uvs = self._process_face_uvs(face, direction)

                # Create Blender face with transformed data
                blender_face = rendering.Face(
                    name=face.name,
                    vertex_indices=vertex_indices,
                    texture=face.texture,
                    uvs=uvs,
                    source=face,
                )
                blender_faces.append(blender_face)

            # Create Blender element with rotated vertices
            blender_element = rendering.Element(
                name=element.name,
                vertices=vertices,  # Pass rotated vertices directly
                faces=blender_faces,
            )
            blender_elements.append(blender_element)

        return rendering.Model(self.name, blender_elements)

    def _minecraft_to_blender_coords(self, coords):
        """Convert coordinates from Minecraft to Blender space.

        Minecraft (left-handed):    Blender (right-handed):
        +X = East (right)          +X = Right
        +Y = Up                    +Y = Forward (-Z in Minecraft)
        +Z = South (forward)       +Z = Up (Y in Minecraft)

        The transformation matrix is:
        | 1  0  0 |   |x|   | x/16     |
        | 0  0  1 | * |y| = | y/16     |
        | 0 -1  0 |   |z|   |-z/16     |
        """
        x, y, z = coords
        return [x / 16, -z / 16, y / 16]

    def _get_face_vertices(self, direction):
        """Get vertex indices for a face in the correct winding order.

        When converting from Minecraft (left-hand) to Blender (right-hand):
        - Faces that point along Z axis need their winding order flipped
        - This is because Z becomes -Y in Blender
        - Vertices must be ordered counter-clockwise when looking at face from outside
        """
        # Updated vertex order mapping for each face to ensure outward-facing normals
        vertex_maps = {
            "down": [0, 1, 5, 4],  # -Y face (bottom)
            "up": [7, 6, 2, 3],  # +Y face (top)
            "north": [1, 0, 3, 2],  # -Z face
            "south": [4, 5, 6, 7],  # +Z face
            "west": [0, 4, 7, 3],  # -X face
            "east": [5, 1, 2, 6],  # +X face
        }
        return vertex_maps[direction]

    def _process_face_uvs(self, face, direction):
        """Process UV coordinates for a face with UV locking support."""
        if not face.uv:
            return [(0, 0), (1, 0), (1, 1), (0, 1)]

        # Get texture dimensions
        texture_path = face.texture
        if isinstance(texture_path, str) and os.path.exists(texture_path):
            with PIL.Image.open(texture_path) as img:
                width, height = img.size
                # Calculate vertical scale factor based on texture dimensions
                vertical_scale = (
                    width / height
                )  # This will be 1 for square textures, 0.5 for 16x32, etc.
        else:
            vertical_scale = 1.0  # Default to no scaling if texture can't be loaded

        # Normalize UVs from Minecraft (0-16) to Blender (0-1) space
        u1, v1, u2, v2 = face.uv

        # Scale vertical coordinates to only use top frame
        v1 = v1 * vertical_scale
        v2 = v2 * vertical_scale

        # UV mappings that match the new vertex order while preserving original texture appearance
        if direction == "down":  # [0,1,5,4]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]
        elif direction == "up":  # [7,6,2,3]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]
        elif direction == "north":  # [1,0,3,2]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]
        elif direction == "south":  # [4,5,6,7]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]
        elif direction == "west":  # [0,4,7,3]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]
        elif direction == "east":  # east [5,1,2,6]
            uvs = [
                (u1 / 16, 1 - v2 / 16),  # Bottom-left
                (u2 / 16, 1 - v2 / 16),  # Bottom-right
                (u2 / 16, 1 - v1 / 16),  # Top-right
                (u1 / 16, 1 - v1 / 16),  # Top-left
            ]

        # Apply face rotation
        if face.rotation:
            rotation_steps = (face.rotation // 90) % 4
            uvs = uvs[rotation_steps:] + uvs[:rotation_steps]

        # Apply UV lock transformations if enabled
        if self.uv_lock and self.y_rotation and direction in ["up", "down"]:
            y_steps = (self.y_rotation // 90) % 4

            # Rotate UVs around texture midpoint (8,8) based on y_rotation
            if y_steps > 0:  # 90°, 180° or 270°
                # Midpoint in normalized coordinates (8/16 = 0.5)
                mid_u = 0.5
                mid_v = 0.5

                # Rotate each UV coordinate around midpoint
                rotated_uvs = []
                for u, v in uvs:
                    # Translate to origin
                    u -= mid_u
                    v -= mid_v

                    # Apply rotation based on y_steps
                    # For "up" face, rotate clockwise (opposite of "down" face)
                    if direction == "up":
                        if y_steps == 1:  # 90°
                            new_u = v
                            new_v = -u
                        elif y_steps == 2:  # 180°
                            new_u = -u
                            new_v = -v
                        else:  # 270°
                            new_u = -v
                            new_v = u
                    else:  # "down" face - rotate counterclockwise (original behavior)
                        if y_steps == 1:  # 90°
                            new_u = -v
                            new_v = u
                        elif y_steps == 2:  # 180°
                            new_u = -u
                            new_v = -v
                        else:  # 270°
                            new_u = v
                            new_v = -u

                    # Translate back
                    new_u += mid_u
                    new_v += mid_v

                    rotated_uvs.append((new_u, new_v))
                uvs = rotated_uvs

        return uvs

    def _apply_element_rotation(self, vertices, element):
        """Apply element-level rotation transformation with proper rescaling.

        Minecraft's rotation system must be transformed to Blender's coordinate space:
        - Minecraft X rotation -> Blender X rotation
        - Minecraft Y rotation -> Blender Z rotation
        - Minecraft Z rotation -> Blender Y rotation (negated)

        This follows from the coordinate system transformation:
        - When we map Minecraft +Y to Blender +Z, Y-axis rotation becomes Z-axis rotation
        - When we map Minecraft +Z to Blender -Y, Z-axis rotation becomes negated Y-axis rotation
        """
        if not element.rotation:
            return vertices

        # Convert rotation origin to Blender space
        origin = self._minecraft_to_blender_coords(element.rotation.origin)

        # Get rotation axis and angle
        minecraft_axis = element.rotation.axis
        angle = element.rotation.angle

        # Transform rotation based on coordinate system mapping:
        # - X axis stays as X axis
        # - Y axis becomes Z axis
        # - Z axis becomes Y axis (negated angle due to coordinate flip)
        if minecraft_axis == "x":
            blender_axis = "x"
        elif minecraft_axis == "y":
            blender_axis = "z"
        else:  # minecraft_axis == 'z'
            blender_axis = "y"
            angle = -angle  # Negate angle due to Z->-Y mapping

        # Create rotation matrix in Blender space
        rotation_matrix = create_rotation_matrix(blender_axis, angle)

        # Apply rotation to each vertex
        rotated_vertices = []
        for vertex in vertices:
            rotated = rotate_point(vertex, origin, rotation_matrix)
            rotated_vertices.append(rotated.tolist())

        # Apply rescaling if needed
        if element.rotation.rescale:
            # Convert vertices to numpy array for easier calculations
            vertices_array = np.array(rotated_vertices)

            # Calculate current bounds of the rotated element
            mins = np.min(vertices_array, axis=0)
            maxs = np.max(vertices_array, axis=0)
            sizes = maxs - mins

            # Calculate scaling factor based on largest dimension
            # We want the element to fit within a 1x1x1 block after rotation
            # The scaling factor is calculated to preserve the original proportions
            max_size = np.max(sizes)
            if max_size > 1.0:  # Only scale down if exceeding bounds
                # Scale uniformly to fit within bounds
                scale = 1.0 / max_size

                # Apply scaling around rotation origin
                scaled_vertices = []
                for vertex in rotated_vertices:
                    # Convert to numpy array for calculations
                    v = np.array(vertex)
                    # Scale relative to origin
                    scaled = origin + (v - origin) * scale
                    scaled_vertices.append(scaled.tolist())
                return scaled_vertices

        return rotated_vertices


class MinecraftBlock:
    """Represents a Minecraft block with its models.
    A block can have multiple model variants based on its state."""

    def __init__(self, canonical_name, models, states=None):
        self.canonical_name = canonical_name
        self.models = list(models)
        # TODO: Use this somehow
        self.states = states or {}

    def to_blender_block(self):
        # Convert block models
        blender_models = []
        for model in self.models:
            blender_model = model.to_blender_model()
            blender_models.append(blender_model)

        # Create the block
        return rendering.Block(name=self.canonical_name, models=blender_models)

    def debug_info(self, indent=0):
        indent_str = "  " * indent
        info = [f"{indent_str}Block: {self.canonical_name}", f"{indent_str}Models:"]

        for model in self.models:
            info.append(model.debug_info(indent + 2))

        return "\n".join(info)


class PlacedMinecraftBlock:
    """Represents a Minecraft block placed in the world at specific coordinates."""

    def __init__(self, block, x=0.0, y=0.0, z=0.0):
        self.x = x
        self.y = y
        self.z = z
        self.block = block

    def to_blender_block(self):
        """Convert placed Minecraft block to Blender format.

        Handles:
        1. Converting block models to Blender format
        2. Converting Minecraft world coordinates to Blender coordinates
        3. Positioning the block correctly in Blender space
        """
        # Convert Minecraft world coordinates to Blender coordinates
        blender_x = self.x
        blender_y = -self.z  # Minecraft Z -> Blender -Y
        blender_z = self.y  # Minecraft Y -> Blender Z

        block = self.block.to_blender_block()

        # Create and return the placed block
        return rendering.PlacedBlock(block=block, x=blender_x, y=blender_y, z=blender_z)

    def debug_info(self, indent=0):
        indent_str = "  " * indent
        info = [
            f"{indent_str}Placed Block:",
            f"{indent_str}  Position: ({self.x}, {self.y}, {self.z})",
            self.block.debug_info(indent + 2),
        ]
        return "\n".join(info)


def create_rotation_matrix(axis, angle_degrees):
    """Create a 3D rotation matrix for the given axis and angle."""
    angle = radians(angle_degrees)
    c = cos(angle)
    s = sin(angle)

    if axis == "x":
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
    elif axis == "y":
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    else:  # z
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rotate_point(point, origin, rotation_matrix):
    """Rotate a point around an origin using a rotation matrix."""
    point = np.array(point)
    origin = np.array(origin)

    # Translate to origin, rotate, translate back
    return (rotation_matrix @ (point - origin)) + origin
