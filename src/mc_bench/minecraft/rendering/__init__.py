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

import os
import textwrap

import bpy
from mathutils import Vector


class Block:
    def __init__(self, name, models):
        self.name = name
        self.models = models

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

    def __repr__(self):
        formatted_faces = textwrap.indent(
            ",\n".join(repr(face) for face in self.faces), "    "
        )
        attrs = [f"name={self.name!r}", f"faces=[\n{formatted_faces}\n]"]
        formatted_attrs = textwrap.indent((",\n".join(attrs)), "    ")
        return f"Element(\n{formatted_attrs}\n)"


class Face:
    def __init__(self, name, vertex_indices, texture, uvs, source=None):
        self.name = name
        self.vertex_indices = vertex_indices
        self.texture = texture
        self.uvs = uvs
        self.source = source

    def __repr__(self):
        attrs = [
            f"name={self.name!r}",
            f"vertex_indices={self.vertex_indices!r}",
            f"texture={self.texture!r}",
            f"uvs={self.uvs!r}",
            f"source={self.source!r}",
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

    def get_next_index(self):
        index = self._next_index
        self._next_index += 1
        return index

    def render(self, block: Block, x: int, y: int, z: int):
        # Should probably call place_block with a PlacedBlock instance
        placed_block = PlacedBlock(block, x, y, z)
        self.place_block(placed_block)

    def setup_blender_env(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

        # Remove default objects
        for obj in bpy.data.objects:
            bpy.data.objects.remove(obj, do_unlink=True)

        # Set up basic scene
        scene = bpy.context.scene
        scene.render.engine = "CYCLES"

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

        models_objects = {}
        for i, model in enumerate(block.models):
            # Create an empty object for the model to act as parent
            model_empty = bpy.data.objects.new(f"{object_index_str}_{model.name}", None)
            bpy.context.scene.collection.objects.link(model_empty)
            # No need to link model_empty to collection
            model_empty.parent = block_empty

            # Create the actual model objects
            objects = self.create_model(
                model, f"{object_index_str}_{model.name}", object_index_str
            )

            # Parent all model objects to the model empty
            for obj in objects:
                obj.parent = model_empty

            models_objects[f"model_{i}"] = {"parent": model_empty, "objects": objects}

        return {"parent": block_empty, "models": models_objects}

    def create_model(
        self, model: Model, name: str, index_str: str, collection=None
    ) -> list[bpy.types.Object]:
        """Create all elements for a model"""

        if collection is None:
            collection = bpy.context.scene.collection

        objects = []
        for i, element in enumerate(model.elements):
            obj = self.create_element_mesh(element, f"{index_str}_{element.name}")
            collection.objects.link(obj)
            objects.append(obj)

        return objects

    def create_element_mesh(self, element, name):
        """Create a mesh object for an element."""
        mesh = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, mesh)

        # Get vertices and faces
        vertices = element.vertices
        faces = []

        # Debug check for duplicate faces
        seen_faces = set()
        for face in element.faces:
            face_tuple = tuple(face.vertex_indices)
            if face_tuple in seen_faces:
                print(f"Warning: Duplicate face found in {name}: {face_tuple}")
            seen_faces.add(face_tuple)
            faces.append(face.vertex_indices)

        # Create the mesh
        mesh.from_pydata(vertices, [], faces)
        mesh.update()

        # Validate mesh normals
        mesh.validate(verbose=True)

        # Create UV layers and assign materials
        if not mesh.uv_layers:
            mesh.uv_layers.new()

        # Create materials for each face
        for face in element.faces:
            if face.texture:
                mat = self.create_material(face.texture)
                if mat.name not in mesh.materials:
                    mesh.materials.append(mat)

        # Assign UVs and materials
        for i, face in enumerate(element.faces):
            if i < len(mesh.polygons):
                # Assign material index
                if face.texture:
                    mat_name = os.path.splitext(os.path.basename(face.texture))[0]
                    mat_idx = mesh.materials.find(mat_name)
                    if mat_idx >= 0:
                        mesh.polygons[i].material_index = mat_idx

                # Assign UVs
                if face.uvs:
                    for j, loop_idx in enumerate(mesh.polygons[i].loop_indices):
                        mesh.uv_layers.active.data[loop_idx].uv = face.uvs[j]

        return obj

    def create_material(self, texture_path, name=None) -> bpy.types.Material:
        """Create a material with baked textures for Minecraft blocks."""
        if name is None:
            name = os.path.splitext(os.path.basename(texture_path))[0]

        # First check if material already exists
        mat = bpy.data.materials.get(name)
        if mat is not None:
            return mat

        # Load and bake the texture
        img = bpy.data.images.get(os.path.basename(texture_path))
        if img is None:
            img = bpy.data.images.load(texture_path)
            img.use_fake_user = True

            # Create a new image for the baked result
            baked_name = f"{name}_baked"
            baked_img = bpy.data.images.new(
                name=baked_name, width=img.size[0], height=img.size[1], alpha=True
            )

            # Copy pixel data and ensure alpha is properly set
            if img.has_data:
                pixels = list(img.pixels[:])
                baked_img.pixels = pixels
                baked_img.pack()  # Pack image data into .blend file

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

        # Create nodes
        output = nodes.new("ShaderNodeOutputMaterial")
        principled_bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        tex_image = nodes.new("ShaderNodeTexImage")
        mapping = nodes.new("ShaderNodeMapping")
        tex_coord = nodes.new("ShaderNodeTexCoord")

        # Setup texture
        tex_image.image = baked_img if "baked_img" in locals() else img
        tex_image.interpolation = "Closest"
        tex_image.extension = "REPEAT"

        # Position nodes
        tex_coord.location = (-600, 0)
        mapping.location = (-400, 0)
        tex_image.location = (-200, 0)
        principled_bsdf.location = (200, 0)
        output.location = (400, 0)

        # Connect nodes
        links.new(tex_coord.outputs["UV"], mapping.inputs["Vector"])
        links.new(mapping.outputs["Vector"], tex_image.inputs["Vector"])
        links.new(tex_image.outputs["Color"], principled_bsdf.inputs["Base Color"])

        # Only connect alpha if transparency is detected
        if has_transparency:
            links.new(tex_image.outputs["Alpha"], principled_bsdf.inputs["Alpha"])
        else:
            # Set alpha to 1.0 for opaque materials
            principled_bsdf.inputs["Alpha"].default_value = 1.0

        links.new(principled_bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Material settings based on transparency
        if has_transparency:
            mat.blend_method = "BLEND"
            mat.use_backface_culling = True
        else:
            mat.blend_method = "OPAQUE"
            mat.use_backface_culling = True

        # Optimize Principled BSDF settings for Minecraft textures
        principled_bsdf.inputs["Specular IOR Level"].default_value = 0
        principled_bsdf.inputs["Roughness"].default_value = 1
        principled_bsdf.inputs["Metallic"].default_value = 0
        principled_bsdf.inputs["Alpha"].default_value = 1

        return mat

    def place_block(self, placed_block: PlacedBlock):
        """Place a block at the specified coordinates"""
        block_data = self.create_block(placed_block.block)

        # Move only the main parent object, which will move all children
        block_data["parent"].location = Vector(
            (placed_block.x, placed_block.y, placed_block.z)
        )

    def export_to_gltf(self, filepath):
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
            export_unused_textures=True,
            export_vertex_color="MATERIAL",
        )

    def convert_blocks_to_file(
        self, placed_blocks: list[PlacedBlock], output_filepath: str
    ):
        """Convert a list of PlacedBlock instances to a 3D file format."""
        # Setup clean environment
        self.setup_blender_env()

        # Import each placed block
        for placed_block in placed_blocks:
            self.place_block(placed_block)

        # Export based on file extension
        if output_filepath.endswith(".glb"):
            self.export_to_gltf(output_filepath)
        elif output_filepath.endswith(".blend"):
            self.export_to_blend(output_filepath)
        else:
            raise ValueError("Unsupported file format. Use .glb or .blend")

        # Clear data for next run
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def export_to_blend(self, filepath):
        """Export the scene to Blender's native format."""
        # Ensure we have a valid file extension
        if not filepath.endswith(".blend"):
            filepath += ".blend"

        # Save current file
        bpy.ops.wm.save_as_mainfile(
            filepath=filepath,
            copy=True,  # Make a copy instead of saving current file
            compress=True,  # Compress the file
            relative_remap=True,  # Make paths relative
        )
