"""
Generic 3D model rendering module for Blender.

This module provides classes and utilities for rendering 3D models in Blender. It should remain
game/application agnostic and NOT contain any Minecraft-specific logic. Any game-specific
transformations (like UV coordinate normalization or texture rotation) should be handled before
the data reaches this module.

IMPORTANT: DO NOT UPDATE THIS MODULE WITH ANYTHING RELATED TO MINECRAFT.

Coordinate Systems:
- Blender uses a right-handed coordinate system:
  - +X axis points right
  - +Y axis points inward/forward (away from view)
  - +Z axis points up
  - One Blender unit = 1 meter by default
  - Rotating counterclockwise around Z: +X -> +Y -> -X -> -Y

- In contrast, Minecraft uses a left-handed system:
  - +X axis points East (right)
  - +Y axis points Up
  - +Z axis points South (away from player)
  - One block = 1 unit in any direction
  - Rotating counterclockwise around Y: +X -> -Z -> -X -> +Z

Coordinate System Conversion:
When converting between Minecraft and Blender coordinates:
- Minecraft Y becomes Blender Z
- Minecraft Z becomes Blender -Y (note the sign flip)
- Minecraft X remains Blender X

Example:
Minecraft (X=1, Y=2, Z=3) -> Blender (X=1, Y=-3, Z=2)

The core classes are:
- Block: Represents a 3D object composed of one or more models
- Model: A collection of 3D elements that make up part of a block
- Element: A single 3D mesh element with vertices and faces
- Face: A single face of an element with UV mapping and texture information
"""

import math
import os
import textwrap
from typing import Optional, Tuple

import bpy

import bmesh  # isort: skip
import enum
import time

from mathutils import Vector


class TimeOfDay(enum.Enum):
    DAWN = "dawn"
    NOON = "noon"
    DUSK = "dusk"
    MIDNIGHT = "midnight"


class Block:
    def __init__(self, name, models, light_emission=None, ambient_occlusion=False):
        self.name = name
        self.models = models
        self.light_emission = light_emission
        self.ambient_occlusion = ambient_occlusion

    def __repr__(self):
        formatted_models = textwrap.indent(
            ",\n".join(repr(model) for model in self.models), "    "
        )
        attrs = [f"name={self.name!r}", f"models=[\n{formatted_models}\n]"]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"Block(\n{formatted_attrs}\n)"


class Model:
    def __init__(self, name, elements):
        self.name = name
        self.elements = elements

    def __repr__(self):
        formatted_elements = textwrap.indent(
            ",\n".join(repr(element) for element in self.elements), "    "
        )
        attrs = [f"name={self.name!r}", f"elements=[\n{formatted_elements}\n]"]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"Model(\n{formatted_attrs}\n)"


class Element:
    """A 3D mesh element with vertices and faces.

    An element represents a single mesh component of a model with explicit vertex positions.

    The vertices list must contain exactly 8 vertices in the following order:
    0: left bottom back    [min_x, min_y, min_z]
    1: right bottom back   [max_x, min_y, min_z]
    2: right top back     [max_x, min_y, max_z]
    3: left top back      [min_x, min_y, max_z]
    4: left bottom front   [min_x, max_y, min_z]
    5: right bottom front  [max_x, max_y, min_z]
    6: right top front    [max_x, max_y, max_z]
    7: left top front     [min_x, max_y, max_z]

    Face indices refer to these vertices and must maintain correct winding order
    for proper face normals.
    """

    def __init__(self, name, vertices, faces):
        """Initialize an Element.

        Args:
            name: Element identifier
            vertices: List of 8 [x,y,z] vertices defining the element's geometry
            faces: List of Face objects defining the element's surfaces

        Raises:
            ValueError: If vertices count is not 8 or if element exceeds 1x1x1 bounds
        """
        self.name = name
        self.vertices = vertices
        self.faces = faces

    @property
    def key(self):
        """Generate a unique key for this element based on its geometry and materials.

        Returns:
            str: A unique identifier string for this element's geometry and materials.
        """
        # Convert vertices to tuples for hashing
        vertex_tuples = tuple(tuple(v) for v in self.vertices)

        # Generate face keys that capture material and UV info
        face_keys = []
        for face in self.faces:
            face_key = (
                tuple(face.vertex_indices),
                face.material_name,
                tuple(tuple(uv) for uv in face.uvs) if face.uvs else None,
                face.tint,
                face.ambient_occlusion,
                face.cull,
            )
            face_keys.append(face_key)

        # Create final key from element properties
        key_parts = (
            self.name,
            vertex_tuples,
            tuple(sorted(face_keys)),  # Sort for consistent ordering
        )
        return str(hash(key_parts))

    def __repr__(self):
        formatted_faces = textwrap.indent(
            ",\n".join(repr(face) for face in self.faces), "    "
        )
        attrs = [
            f"name={self.name!r}",
            f"vertices={self.vertices!r}",
            f"faces=[\n{formatted_faces}\n]",
        ]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"Element(\n{formatted_attrs}\n)"


class Face:
    def __init__(
        self,
        name,
        vertex_indices,
        texture,
        uvs,
        source=None,
        tint=None,
        ambient_occlusion=True,
        cull=False,
    ):
        self.name = name
        self.vertex_indices = vertex_indices
        self.texture = texture
        self.uvs = uvs
        self.source = source
        self.tint = tint
        self.ambient_occlusion = ambient_occlusion
        self.cull = cull

    @property
    def tint_rgb(self):
        if self.tint:
            return hex_to_rgb(self.tint)

    @property
    def material_name(self):
        _, filename = os.path.split(self.texture)
        name, _ = os.path.splitext(filename)
        if self.tint:
            name = f"{name}_tinted_{self.tint.lstrip('#')}"

        return name

    def __repr__(self):
        attrs = [
            f"name={self.name!r}",
            f"vertex_indices={self.vertex_indices!r}",
            f"texture={self.texture!r}",
            f"uvs={self.uvs!r}",
            f"source={self.source!r}",
            f"tint={self.tint!r}",
        ]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"Face(\n{formatted_attrs}\n)"


class PlacedBlock:
    def __init__(self, block: Block, x: int, y: int, z: int):
        self.block = block
        self.x = x
        self.y = y
        self.z = z

    def __repr__(self):
        formatted_block = textwrap.indent(repr(self.block), "    ")
        attrs = [
            f"block=\n{formatted_block}",
            f"x={self.x!r}",
            f"y={self.y!r}",
            f"z={self.z!r}",
        ]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"PlacedBlock(\n{formatted_attrs}\n)"


class Renderer:
    def __init__(self):
        self.setup_blender_env()
        self._next_index = 0
        self.texture_paths = set()  # Track unique textures
        self.atlas = None  # Will store the atlas image
        self.atlas_mapping = {}  # Will store UV mapping info for each texture
        self.materials = {}  # Track materials by texture path
        self.baked_images = {}
        self.element_cache = {}  # Cache for instanced elements

    def get_next_index(self):
        index = self._next_index
        self._next_index += 1
        return index

    def render(self, block: Block, x: int, y: int, z: int):
        # Should probably call place_block with a PlacedBlock instance
        placed_block = PlacedBlock(block, x, y, z)
        self.place_block(placed_block)

    def setup_blender_env(self):
        """Set up Blender environment with optimized render settings."""
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # Remove default objects
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

        # Set up basic scene with optimized settings
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"

        # Configure render settings for baking
        scene.render.bake.use_pass_direct = True
        scene.render.bake.use_pass_indirect = True
        scene.render.bake.use_pass_diffuse = True
        scene.render.bake.use_pass_emit = True
        scene.render.bake.margin = 2  # No margin to prevent pixel bleeding

        # Disable anti-aliasing and set minimum samples
        scene.cycles.samples = 16  # Increased from 1 to get better quality
        scene.cycles.preview_samples = 16
        scene.cycles.pixel_filter_type = (
            "GAUSSIAN"  # Changed from BOX for smoother edges
        )
        scene.cycles.filter_width = 1.5  # Adjusted for better anti-aliasing
        scene.cycles.use_denoising = True
        scene.cycles.denoising_prefilter = "NONE"

        # Add these new settings
        scene.render.filter_size = 1.5
        scene.render.use_border = False

        # Create new world if it doesn't exist
        if scene.world is None:
            world = bpy.data.worlds.new("World")
            scene.world = world

        scene.world.use_nodes = True

    def create_block(self, block: Block) -> dict[str, list[bpy.types.Object]]:
        """Create all models for a block"""
        object_index = self.get_next_index()
        object_index_str = f"{object_index:05d}"
        # Create an empty object to act as the block's parent
        block_empty = bpy.data.objects.new(f"{object_index_str}_{block.name}", None)
        bpy.context.scene.collection.objects.link(block_empty)

        # Add point light for emissive blocks
        if block.light_emission is not None:
            light_data = bpy.data.lights.new(
                name=f"{object_index_str}_light", type="POINT"
            )
            # Base energy level (relatively bright but not extreme)
            light_data.energy = 20.0 * block.light_emission
            light_data.use_custom_distance = True
            light_data.cutoff_distance = 10.0  # Total light reach

            # Setup nodes for custom falloff
            light_data.use_nodes = True
            nodes = light_data.node_tree.nodes
            links = light_data.node_tree.links

            # Clear default nodes
            nodes.clear()

            # Create nodes for custom falloff
            emission = nodes.new("ShaderNodeEmission")
            output = nodes.new("ShaderNodeOutputLight")
            falloff = nodes.new("ShaderNodeLightFalloff")

            # Position nodes
            emission.location = (200, 0)
            falloff.location = (0, 0)
            output.location = (400, 0)

            # Set falloff parameters
            falloff.inputs["Strength"].default_value = 6.0  # Adjusted strength
            falloff.inputs["Smooth"].default_value = 0.5

            # Set warm light color directly on emission
            emission.inputs["Color"].default_value = (
                1.0,
                0.898,
                0.718,
                1.0,
            )  # #FFE5B7FF

            # Connect nodes
            links.new(
                falloff.outputs["Linear"], emission.inputs["Strength"]
            )  # Changed to Linear
            links.new(emission.outputs["Emission"], output.inputs["Surface"])

            # Performance optimizations
            light_data.shadow_soft_size = 0.3
            light_data.use_shadow = False
            light_data.cycles.max_bounces = 1
            light_data.cycles.use_multiple_importance_sampling = False

            light_obj = bpy.data.objects.new(
                name=f"{object_index_str}_light", object_data=light_data
            )
            bpy.context.scene.collection.objects.link(light_obj)
            light_obj.parent = block_empty
            light_obj.location = (0.5, -0.5, 0.5)

        models_objects = {}
        for i, model in enumerate(block.models):
            # Create an empty object for the model to act as parent
            model_empty = bpy.data.objects.new(f"{object_index_str}_{model.name}", None)
            bpy.context.scene.collection.objects.link(model_empty)
            model_empty.parent = block_empty

            # Create the actual model objects, passing down emission info
            objects = self.create_model(
                model,
                object_index_str,
                light_emission=block.light_emission,
            )

            # Parent all model objects to the model empty
            for obj in objects:
                obj.parent = model_empty

            models_objects[f"model_{i}"] = {"parent": model_empty, "objects": objects}

        return {"parent": block_empty, "models": models_objects}

    def create_model(
        self,
        model: Model,
        index_str: str,
        collection=None,
        light_emission=None,
    ) -> list[bpy.types.Object]:
        """Create all elements for a model"""

        if collection is None:
            collection = bpy.context.scene.collection

        objects = []
        for element in model.elements:
            # Skip elements with no faces
            if not element.faces:
                continue

            obj = self.create_element_mesh(
                element,
                f"{index_str}_{element.name}",
                index_str,
                light_emission=light_emission,
            )
            collection.objects.link(obj)
            objects.append(obj)

        return objects

    def create_element_mesh(self, element, name, index_str, light_emission=None):
        """Create a mesh object for an element, using instancing when possible."""
        # Check if we already have this element cached
        element_key = element.key
        if element_key in self.element_cache:
            # Create a linked duplicate (instance) of the cached mesh
            cached_obj = self.element_cache[element_key]
            obj = bpy.data.objects.new(name, cached_obj.data)
            return obj

        # Create new mesh if not cached
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        # Get vertices and faces
        vertices = element.vertices
        faces = []

        # Track which vertices are actually used by faces
        used_vertices = set()
        vertex_map = {}
        new_vertices = []

        # First pass - collect used vertices and build face list
        for face in element.faces:
            for idx in face.vertex_indices:
                used_vertices.add(idx)
            faces.append(face.vertex_indices)

        # Second pass - create new vertex list and mapping
        for i, vertex in enumerate(vertices):
            if i in used_vertices:
                vertex_map[i] = len(new_vertices)
                new_vertices.append(vertex)

        # Third pass - remap face indices to new vertex indices
        new_faces = []
        for face_indices in faces:
            new_face = [vertex_map[idx] for idx in face_indices]
            new_faces.append(new_face)

        # Create the mesh with only used vertices
        mesh.from_pydata(new_vertices, [], new_faces)
        mesh.update()

        # Clean up mesh geometry
        bm = bmesh.new()
        bm.from_mesh(mesh)

        # Remove duplicate vertices
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)

        # Ensure consistent face normals
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

        # Remove any internal faces
        bmesh.ops.dissolve_degenerate(bm, dist=0.0001, edges=bm.edges)

        bm.to_mesh(mesh)
        bm.free()

        # Create UV layer
        if not mesh.uv_layers:
            mesh.uv_layers.new()

        # Create materials for each face
        face_lookup = {}
        for idx, face in enumerate(element.faces):
            if face.texture:
                material_name = face.material_name
                face_lookup[id(face)] = material_name
                mat = self.create_material(
                    face.texture,
                    name=material_name,
                    tint=face.tint_rgb,
                    light_emission=light_emission,
                    ambient_occlusion=face.ambient_occlusion,
                )
                if mat.name not in mesh.materials:
                    mesh.materials.append(mat)

        # Assign UVs and materials before triangulation
        for i, face in enumerate(element.faces):
            if i < len(mesh.polygons):
                # Assign material index
                if face.material_name:
                    mat_idx = mesh.materials.find(face_lookup[id(face)])
                    if mat_idx >= 0:
                        mesh.polygons[i].material_index = mat_idx

                # Assign UVs
                if face.uvs:
                    for j, loop_idx in enumerate(mesh.polygons[i].loop_indices):
                        mesh.uv_layers.active.data[loop_idx].uv = face.uvs[j]

        # Validate mesh
        mesh.validate(verbose=True)

        # Triangulate the mesh after UV assignment
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(mesh)
        bm.free()

        # Cache the object for future instancing
        self.element_cache[element_key] = obj

        return obj

    def create_material(
        self,
        texture_path: str,
        name: str,
        tint: Optional[Tuple[int, int, int]] = None,
        light_emission: Optional[float] = None,
        ambient_occlusion: bool = True,
    ) -> bpy.types.Material:
        """Create a material with baked textures for Minecraft blocks.

        Args:
            texture_path (str): The path to the texture file.
            name (str): The name of the material.
            tint (tuple, optional): The tint color for the material.
            light_emission (float, optional): The light emission level for the material.
            ambient_occlusion (bool, optional): Whether to include ambient occlusion.
        Returns:
            bpy.types.Material: The created material.
        """
        # Track texture for atlas generation
        self.texture_paths.add(texture_path)

        # Store material reference for later UV remapping
        if texture_path not in self.materials:
            self.materials[texture_path] = []
        self.materials[texture_path].append(name)

        # First check if material already exists
        mat = bpy.data.materials.get(name)
        if mat is not None:
            return mat
            # TODO: if we want to bake lighting, we need to make sure all materials are unique
            # raise RuntimeError(
            #     f"All materials must be unique due to baking. {name} not unique"
            # )

        alpha_baked_image_name = f"{name}_copy"

        # Load and bake the texture
        img = bpy.data.images.get(alpha_baked_image_name)

        if img is None:
            img = bpy.data.images.load(texture_path)
            img.use_fake_user = True

            # Create a new image for the baked result
            img_copy = bpy.data.images.new(
                name=alpha_baked_image_name,
                width=img.size[0],
                height=img.size[1],
                alpha=True,
            )

            # Copy pixel data and ensure alpha is properly set
            if img.has_data:
                pixels = list(img.pixels[:])
                img_copy.pixels = pixels
                img_copy.pack()  # Pack image data into .blend file

        # Check for transparency in the image
        has_transparency = False
        if img and img.has_data:
            pixels = list(img.pixels[:])
            # Check alpha values (every 4th value in RGBA)
            alpha_values = pixels[3::4]
            has_partial_transparency = any(a < 1.0 for a in alpha_values)
            has_transparency = has_partial_transparency

        # Create new material
        mat = bpy.data.materials.new(name=name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Base Nodes
        tex_coord = nodes.new("ShaderNodeTexCoord")
        tex_coord.location = (-600, 0)
        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-400, 0)
        tex_image = nodes.new("ShaderNodeTexImage")
        tex_image.location = (-200, 0)

        # Tinting Nodes
        tint_node = nodes.new("ShaderNodeRGB")
        tint_node.location = (-200, 200)
        tint_multiply_node = nodes.new("ShaderNodeMixRGB")
        tint_multiply_node.location = (100, 250)
        tint_multiply_node.blend_type = "MULTIPLY"
        tint_multiply_node.inputs[0].default_value = 1.0

        # Ambient Occlusion Nodes
        ao_node = nodes.new("ShaderNodeAmbientOcclusion")
        ao_node.location = (-200, -300)
        ao_mix_node = nodes.new("ShaderNodeMixRGB")
        ao_mix_node.location = (300, 0)
        ao_mix_node.blend_type = "MULTIPLY"
        ao_mix_node.inputs[0].default_value = 1.0

        # Emission Nodes

        principled_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        principled_bsdf.location = (500, 0)

        emission_node = nodes.new("ShaderNodeEmission")
        emission_node.location = (300, 200)
        emission_mix_node = nodes.new("ShaderNodeMixShader")
        emission_mix_node.location = (800, 200)
        emission_transparent_bsdf = nodes.new("ShaderNodeBsdfTransparent")
        emission_transparent_bsdf.location = (1000, 200)
        emission_alpha_mix_node = nodes.new("ShaderNodeMixShader")
        emission_alpha_mix_node.location = (1200, 200)

        output_node = nodes.new("ShaderNodeOutputMaterial")
        output_node.location = (1000, 0)

        # Optimize Principled BSDF settings for more vibrant Minecraft-like textures
        principled_bsdf.inputs["Specular IOR Level"].default_value = 0  # No specular
        principled_bsdf.inputs["Roughness"].default_value = 1.0  # Full roughness
        principled_bsdf.inputs["Metallic"].default_value = 0  # No metallic
        principled_bsdf.inputs["Alpha"].default_value = 1.0  # Full opacity

        # Add color correction nodes for more vibrant colors
        color_correct = nodes.new("ShaderNodeBrightContrast")
        color_correct.location = (0, 0)
        color_correct.inputs["Bright"].default_value = 0.0
        color_correct.inputs["Contrast"].default_value = 0.09

        # Update these settings for the texture image node
        tex_image.interpolation = "Closest"
        tex_image.extension = "CLIP"  # Changed from REPEAT to prevent edge bleeding

        # Modify Principled BSDF settings to prevent edge artifacts
        principled_bsdf.inputs["Specular IOR Level"].default_value = 0
        principled_bsdf.inputs["Roughness"].default_value = 1
        principled_bsdf.inputs["Metallic"].default_value = 0
        principled_bsdf.inputs["Alpha"].default_value = 1

        tex_image.image = img
        tex_image.interpolation = "Closest"
        tex_image.extension = "REPEAT"

        color = tex_image.outputs["Color"]
        raw_color = tex_image.outputs["Color"]

        has_tint = tint is not None
        # TODO: Add emission if we get a better rendering pipeline built
        has_emission = False  # light_emission is not None
        # TODO: Add ambient occlusion that doesn't black out most side blocks
        has_ambient_occlusion = False  # ambient_occlusion

        # with the color input from the image to create a tinted image
        if has_tint:
            _rgba_tint = (tint[0], tint[1], tint[2], 1)
            tint_node.outputs[0].default_value = _rgba_tint
            links.new(tint_node.outputs[0], tint_multiply_node.inputs[1])
            links.new(color, tint_multiply_node.inputs[2])
            color = tint_multiply_node.outputs[0]
            raw_color = tint_multiply_node.outputs[0]
        else:
            nodes.remove(tint_node)
            nodes.remove(tint_multiply_node)

        links.new(color, color_correct.inputs["Color"])
        color = color_correct.outputs["Color"]
        raw_color = color_correct.outputs["Color"]

        if has_ambient_occlusion:
            links.new(color, ao_mix_node.inputs[1])
            links.new(ao_node.outputs["Color"], ao_mix_node.inputs[2])
            color = ao_mix_node.outputs[0]
            links.new(color, principled_bsdf.inputs["Base Color"])
        else:
            links.new(color, principled_bsdf.inputs["Base Color"])
            nodes.remove(ao_node)
            nodes.remove(ao_mix_node)

        if has_emission:
            links.new(raw_color, emission_node.inputs[0])
            links.new(emission_node.outputs[0], emission_mix_node.inputs[1])
            links.new(principled_bsdf.outputs[0], emission_mix_node.inputs[2])
            links.new(emission_mix_node.outputs[0], output_node.inputs["Surface"])

            if has_transparency:
                links.new(
                    emission_transparent_bsdf.outputs[0],
                    emission_alpha_mix_node.inputs[1],
                )
                links.new(
                    emission_mix_node.outputs[0], emission_alpha_mix_node.inputs[2]
                )
                links.new(tex_image.outputs["Alpha"], emission_alpha_mix_node.inputs[0])
                links.new(
                    emission_alpha_mix_node.outputs[0], output_node.inputs["Surface"]
                )
            else:
                links.new(emission_mix_node.outputs[0], output_node.inputs["Surface"])
                nodes.remove(emission_transparent_bsdf)
                nodes.remove(emission_alpha_mix_node)

        else:
            links.new(principled_bsdf.outputs[0], output_node.inputs["Surface"])
            nodes.remove(emission_node)
            nodes.remove(emission_mix_node)

        # Connect nodes
        links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex_image.inputs["Vector"])

        # Only connect alpha if transparency is detected
        if has_transparency:
            links.new(tex_image.outputs["Alpha"], principled_bsdf.inputs["Alpha"])
        else:
            # Set alpha to 1.0 for opaque materials
            principled_bsdf.inputs["Alpha"].default_value = 1.0

        # Material settings based on transparency
        if has_transparency:
            mat.blend_method = "BLEND"
            mat.use_backface_culling = True
        else:
            mat.blend_method = "OPAQUE"
            mat.use_backface_culling = True
        return mat

    def place_block(self, placed_block: PlacedBlock):
        """Place a block at the specified coordinates"""
        block_data = self.create_block(placed_block.block)

        # Move only the main parent object, which will move all children
        block_data["parent"].location = Vector(
            (placed_block.x, placed_block.y, placed_block.z)
        )

    def export_glb(self, filepath):
        """Export the scene to GLTF format with proper alpha handling."""
        if not filepath.endswith(".glb"):
            filepath += ".glb"

        bpy.ops.export_scene.gltf(
            # Basic export settings
            filepath=filepath,
            export_format="GLB",
            export_texture_dir="",
            # Texture and material settings
            export_materials="EXPORT",
            export_image_format="AUTO",
            export_keep_originals=False,
            export_texcoords=True,
            export_attributes=True,
            # Image quality settings
            export_image_quality=100,
            export_jpeg_quality=100,
            # Disable WebP to avoid compatibility issues
            export_image_add_webp=False,
            export_image_webp_fallback=False,
            # Material and mesh settings
            export_tangents=True,
            export_normals=True,
            # Disable compression to preserve quality
            export_draco_mesh_compression_enable=False,
            # Transform settings
            export_yup=True,  # Y-up for standard glTF convention
            # Include all materials and textures
            export_unused_textures=False,
            export_vertex_color="MATERIAL",
        )

    def bake_material(self, material: bpy.types.Material, time_of_day: TimeOfDay):
        """Bake a single material into a new baked version."""
        # Skip if material doesn't use nodes
        if not material.use_nodes:
            return None

        # Find original texture node and image
        nodes = material.node_tree.nodes
        orig_tex_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
        if not orig_tex_node or not orig_tex_node.image:
            return None

        orig_image = orig_tex_node.image

        # Create a new image with same dimensions as original
        bake_image = bpy.data.images.new(
            name=f"{material.name}_baked",
            width=orig_image.size[0],
            height=orig_image.size[1],
            alpha=True,
            float_buffer=False,  # Use integer pixels for sharper results
        )

        # Set image filtering to closest for sharp pixels
        bake_image.use_generated_float = False

        # Store reference for atlas generation
        self.baked_images[material.name] = bake_image

        # Create temporary bake node while preserving original nodes
        bake_node = nodes.new("ShaderNodeTexImage")
        bake_node.name = "Bake_Target"
        bake_node.image = bake_image
        bake_node.interpolation = "Closest"
        bake_node.extension = "REPEAT"  # Prevent texture wrapping artifacts
        bake_node.select = True
        nodes.active = bake_node

        # Store current selection and active object
        old_selection = bpy.context.selected_objects[:]
        old_active = bpy.context.active_object

        try:
            # Select objects using this material
            bpy.ops.object.select_all(action="DESELECT")
            objects_with_material = []
            for obj in bpy.data.objects:
                if obj.type == "MESH":
                    for slot in obj.material_slots:
                        if slot.material == material:
                            obj.select_set(True)
                            objects_with_material.append(obj)

            if not objects_with_material:
                return None

            # Set active object
            bpy.context.view_layer.objects.active = objects_with_material[0]

            # Bake the material with color-only settings
            bpy.ops.object.bake(
                type="DIFFUSE",  # Changed from COMBINED to DIFFUSE
                pass_filter={"COLOR"},  # Only bake color information
                use_selected_to_active=False,
                margin=2,
                use_clear=True,
            )

        finally:
            # Restore original selection
            bpy.ops.object.select_all(action="DESELECT")
            for obj in old_selection:
                obj.select_set(True)
            if old_active:
                bpy.context.view_layer.objects.active = old_active

            # Remove temporary bake node
            nodes.remove(bake_node)

        # Pack the image
        bake_image.pack()

        return bake_image

    def apply_baked_materials(self):
        """Apply all baked images to their respective materials."""
        if not hasattr(self, "baked_images"):
            return

        for material_name, baked_image in self.baked_images.items():
            material = bpy.data.materials.get(material_name)
            if not material or not material.use_nodes:
                continue

            # Find original texture node
            nodes = material.node_tree.nodes
            tex_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
            if not tex_node:
                continue

            # Replace original image with baked version
            tex_node.image = baked_image
            tex_node.interpolation = "Closest"  # Ensure pixelated look is maintained

            # Force updates
            material.update_tag()
            for obj in bpy.data.objects:
                for slot in obj.material_slots:
                    if slot.material == material:
                        obj.data.update()

        # Final update to refresh everything
        bpy.context.view_layer.update()

    def delete_unnecessary_nodes(self):
        """Delete sunlights, unncessary world nodes, shaders, etc.

        None of this is necessary because we have baked everything into the textures already.
        """
        # Delete sun lights
        for obj in bpy.data.objects:
            if obj.type == "LIGHT" and obj.data.type == "SUN":
                bpy.data.objects.remove(obj, do_unlink=True)

        # Delete point lights (from emissive blocks)
        for obj in bpy.data.objects:
            if obj.type == "LIGHT" and obj.data.type == "POINT":
                bpy.data.objects.remove(obj, do_unlink=True)

        # Clear world nodes
        world = bpy.context.scene.world
        if world and world.use_nodes:
            world.node_tree.nodes.clear()

            # Add minimal world setup
            background = world.node_tree.nodes.new("ShaderNodeBackground")
            output = world.node_tree.nodes.new("ShaderNodeOutputWorld")
            world.node_tree.links.new(background.outputs[0], output.inputs[0])

            # Set black background
            background.inputs[0].default_value = (0, 0, 0, 1)
            background.inputs[1].default_value = 1.0

        # Clean up unused lights
        for light in bpy.data.lights:
            if not light.users:
                bpy.data.lights.remove(light)

    def render_blocks(
        self,
        placed_blocks: list[PlacedBlock],
        name: str,
        types=None,
        time_of_day: TimeOfDay = TimeOfDay.NOON,
        pre_export: bool = False,
        fast_render: bool = False,
    ):
        """Render a list of PlacedBlock instances."""
        types = types or ["blend", "glb"]

        name, _ = os.path.splitext(name)

        print("Placing blocks", flush=True)

        # Place all blocks first
        for placed_block in placed_blocks:
            self.place_block(placed_block)

        print("Done placing blocks", flush=True)

        if pre_export:
            # Continue with existing render code...
            if "blend" in types:
                self.export_blend(f"pre-{name}.blend")

            if "glb" in types:
                self.export_glb(f"pre-{name}.glb")

        if fast_render:
            if "blend" in types:
                self.export_blend(f"{name}.blend")

            if "glb" in types:
                self.export_glb(f"{name}.glb")

            return

        print("Baking materials", flush=True)
        # Stage 1: Bake all materials
        for material in bpy.data.materials:
            self.bake_material(material, time_of_day)

        print("Done baking materials", flush=True)

        print("Applying baked materials", flush=True)
        # Stage 2: Apply all baked materials
        self.apply_baked_materials()
        print("Done applying baked materials", flush=True)

        print("Deleting unnecessary nodes", flush=True)
        self.delete_unnecessary_nodes()
        print("Done deleting unnecessary nodes", flush=True)

        print("Generating texture atlas", flush=True)
        # Generate atlas after baking
        self.generate_texture_atlas(margin=4)
        print("Done generating texture atlas", flush=True)

        print("Remapping UVs to atlas", flush=True)
        self.remap_uvs_to_atlas()
        print("Done remapping UVs to atlas", flush=True)

        print("Exporting", flush=True)
        # Export based on file extension
        if "blend" in types:
            self.export_blend(f"{name}.blend")

        if "glb" in types:
            self.export_glb(f"{name}.glb")

        print("Done", flush=True)

    def export_blend(self, filepath):
        """Export the scene to Blender's native format."""
        # Ensure we have a valid file extension
        if not filepath.endswith(".blend"):
            filepath += ".blend"

        if os.path.exists(filepath):
            name, ext = os.path.splitext(filepath)
            filepath = f"{name}-{str(time.time()).split('.')[0]}{ext}"

        # Save current file
        bpy.ops.wm.save_as_mainfile(
            filepath=filepath,
            copy=True,  # Make a copy instead of saving current file
            compress=True,  # Compress the file
            relative_remap=True,  # Make paths relative
        )

    def calculate_atlas_size(self, materials, margin=1):
        """Calculate optimal power-of-2 size for atlas based on material textures."""
        # Find the largest texture dimension
        max_size = 0
        for material_name in materials:
            material = bpy.data.materials.get(material_name)
            if not material or not material.use_nodes:
                continue

            nodes = material.node_tree.nodes
            tex_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
            if tex_node and tex_node.image:
                max_size = max(max_size, max(tex_node.image.size))

        if not max_size:
            return 1024, 16  # Default fallback

        # Round cell size up to nearest power of 2 and add margins
        cell_size = 1 << (max_size - 1).bit_length()
        cell_size_with_margin = cell_size + (2 * margin)

        # Calculate minimum atlas size needed
        total_materials = len(materials)
        min_dimension = math.ceil(math.sqrt(total_materials)) * cell_size_with_margin

        # Round atlas size up to nearest power of 2
        atlas_size = 1 << (min_dimension - 1).bit_length()

        return atlas_size, cell_size, cell_size_with_margin

    def generate_texture_atlas(self, margin=4):
        """Generate a texture atlas from all material textures."""
        all_materials = []
        for material_names in self.materials.values():
            all_materials.extend(material_names)

        if not all_materials:
            return

        # Calculate optimal atlas and cell sizes
        atlas_size, cell_size, cell_size_with_margin = self.calculate_atlas_size(
            all_materials, margin
        )

        # Create new image for atlas
        atlas_name = "TextureAtlas"
        existing_atlas = bpy.data.images.get(atlas_name)
        if existing_atlas:
            bpy.data.images.remove(existing_atlas)

        self.atlas = bpy.data.images.new(
            atlas_name, width=atlas_size, height=atlas_size, alpha=True
        )
        self.atlas.use_fake_user = True
        self.atlas.file_format = "PNG"

        # Clear atlas pixels
        pixels = [0.0] * (atlas_size * atlas_size * 4)
        self.atlas.pixels = pixels[:]

        # Calculate grid size based on cell size with margins
        grid_size = atlas_size // cell_size_with_margin

        for idx, material_name in enumerate(all_materials):
            material = bpy.data.materials.get(material_name)
            if not material or not material.use_nodes:
                continue

            nodes = material.node_tree.nodes
            tex_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
            if not tex_node or not tex_node.image:
                continue

            # Calculate grid position with margins
            grid_x = idx % grid_size
            grid_y = idx // grid_size

            # Calculate UV mapping for this material (excluding margins)
            x_start = (grid_x * cell_size_with_margin + margin) / atlas_size
            y_start = (grid_y * cell_size_with_margin + margin) / atlas_size
            x_end = (grid_x * cell_size_with_margin + margin + cell_size) / atlas_size
            y_end = (grid_y * cell_size_with_margin + margin + cell_size) / atlas_size

            self.atlas_mapping[material_name] = {
                "u_start": x_start,
                "v_start": y_start,
                "u_end": x_end,
                "v_end": y_end,
            }

            # Copy texture pixels to atlas (with margin offset)
            self.copy_texture_to_atlas(
                tex_node.image,
                grid_x * cell_size_with_margin + margin,
                grid_y * cell_size_with_margin + margin,
                cell_size,
            )

        self.atlas.pack()
        self.atlas.update()
        self.atlas.pixels = self.atlas.pixels[:]

    def copy_texture_to_atlas(self, src_img, x_offset, y_offset, cell_size):
        """Copy source texture pixels to the atlas at specified position."""
        # Resize source image pixels to cell size
        temp_img = src_img.copy()
        temp_img.scale(cell_size, cell_size)

        src_pixels = list(temp_img.pixels[:])
        atlas_pixels = list(self.atlas.pixels[:])

        # Copy pixels with border extension
        for y in range(cell_size):
            for x in range(cell_size):
                src_idx = (y * cell_size + x) * 4
                atlas_idx = ((y + y_offset) * self.atlas.size[0] + (x + x_offset)) * 4

                # Copy main pixel
                for i in range(4):
                    atlas_pixels[atlas_idx + i] = src_pixels[src_idx + i]

                # Extend edge pixels by 1px in each direction
                if x == 0:  # Left edge
                    left_idx = (
                        (y + y_offset) * self.atlas.size[0] + (x + x_offset - 1)
                    ) * 4
                    for i in range(4):
                        atlas_pixels[left_idx + i] = src_pixels[src_idx + i]
                elif x == cell_size - 1:  # Right edge
                    right_idx = (
                        (y + y_offset) * self.atlas.size[0] + (x + x_offset + 1)
                    ) * 4
                    for i in range(4):
                        atlas_pixels[right_idx + i] = src_pixels[src_idx + i]

                if y == 0:  # Bottom edge
                    bottom_idx = (
                        (y + y_offset - 1) * self.atlas.size[0] + (x + x_offset)
                    ) * 4
                    for i in range(4):
                        atlas_pixels[bottom_idx + i] = src_pixels[src_idx + i]
                elif y == cell_size - 1:  # Top edge
                    top_idx = (
                        (y + y_offset + 1) * self.atlas.size[0] + (x + x_offset)
                    ) * 4
                    for i in range(4):
                        atlas_pixels[top_idx + i] = src_pixels[src_idx + i]

        self.atlas.pixels = atlas_pixels[:]
        bpy.data.images.remove(temp_img)

    def remap_uvs_to_atlas(self):
        """Remap all material UVs to use the texture atlas."""
        if not self.atlas or not self.atlas_mapping:
            raise ValueError("Atlas or mapping not found")

        # Update all materials to use atlas
        for material_name in self.atlas_mapping:
            print(f"Remapping UVs for material {material_name}")
            material = bpy.data.materials.get(material_name)
            if not material or not material.use_nodes:
                print(f"Material {material_name} not found or not using nodes")
                continue

            uv_map = self.atlas_mapping[material_name]

            # Get material nodes and links
            nodes = material.node_tree.nodes
            links = material.node_tree.links

            # Find and update texture node
            tex_node = next((n for n in nodes if n.type == "TEX_IMAGE"), None)
            if not tex_node:
                print(f"Texture node for material {material_name} not found")
                continue

            # Store old image for cleanup
            old_image = tex_node.image

            # Update texture node to use atlas
            tex_node.image = self.atlas
            tex_node.update()  # Force the texture node to update

            # Find or create mapping node
            mapping = nodes.get("Mapping")
            if not mapping:
                mapping = nodes.new("ShaderNodeMapping")
                # Position it between TexCoord and Image Texture nodes
                mapping.location = (-400, 0)

                # Find or create texture coordinate node
                tex_coord = nodes.get("Texture Coordinate")
                if not tex_coord:
                    tex_coord = nodes.new("ShaderNodeTexCoord")
                    tex_coord.location = (-600, 0)

                # Connect TexCoord -> Mapping -> Image Texture
                links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
                links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

            # Update mapping node to remap UVs to atlas position
            mapping.inputs["Location"].default_value[0] = uv_map["u_start"]
            mapping.inputs["Location"].default_value[1] = uv_map["v_start"]
            mapping.inputs["Scale"].default_value[0] = (
                uv_map["u_end"] - uv_map["u_start"]
            )
            mapping.inputs["Scale"].default_value[1] = (
                uv_map["v_end"] - uv_map["v_start"]
            )

            # Force material update
            material.update_tag()

            # Clean up old image if it's not used anymore
            if old_image and not old_image.users:
                bpy.data.images.remove(old_image)

        # Force scene update to refresh materials
        bpy.context.view_layer.update()


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    """Convert a hex color string to RGB tuple with values between 0 and 1.

    Args:
        hex_color: Hex color string (e.g. '#79c05f' or '79c05f')

    Returns:
        Tuple of (red, green, blue) values normalized between 0 and 1

    Example:
        >>> hex_to_rgb('#79c05f')
        (0.4745098039215686, 0.7529411764705882, 0.37254901960784315)
    """
    # Remove '#' if present
    hex_color = hex_color.lstrip("#")

    # Convert hex to RGB values (0-255)
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    # Normalize to 0-1 range
    return (r / 255.0, g / 255.0, b / 255.0)
