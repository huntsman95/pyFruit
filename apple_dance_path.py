import bpy
import math
import os


# Path to the apple OBJ file (relative to the Blender file location)
def get_apple_obj_path():
    return bpy.path.abspath("//models/apple.obj")


# Remove all existing objects
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


# Add a Bezier curve path for the apple to follow
def add_path_curve():
    bpy.ops.curve.primitive_bezier_curve_add()
    curve = bpy.context.active_object
    curve.name = "ApplePath"
    # Edit the curve points for a nice path
    spline = curve.data.splines[0]
    spline.bezier_points[0].co = (-10, 0, 0)
    spline.bezier_points[1].co = (10, 0, 0)
    # Add more points for a wavy path
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.curve.select_all(action="SELECT")
    bpy.ops.curve.subdivide(number_cuts=2)
    bpy.ops.object.mode_set(mode="OBJECT")
    # Move the new points
    spline = curve.data.splines[0]
    spline.bezier_points[1].co = (-3, 5, 0)
    spline.bezier_points[2].co = (3, -5, 0)
    return curve


# Import the apple OBJ model
def import_apple(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Apple OBJ file not found at: {path}")
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.obj(filepath=path)
    apple = bpy.context.selected_objects[0]
    apple.name = "DancingApple"
    apple.rotation_euler[0] = math.radians(90)
    bpy.context.view_layer.objects.active = apple
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    for mat_slot in apple.material_slots:
        mat = mat_slot.material
        if mat is not None:
            if hasattr(mat, "blend_method"):
                mat.blend_method = "OPAQUE"
            if hasattr(mat, "alpha"):
                mat.alpha = 1.0
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        if "Alpha" in node.inputs:
                            node.inputs["Alpha"].default_value = 1.0
                        if "Metallic" in node.inputs:
                            node.inputs["Metallic"].default_value = 1.0
    return apple


# Add a face plane with a PNG texture and parent it to the apple
def add_animated_face(
    apple,
    face_size=2.5,
    face_offset=-3.07,
    start_frame=1,
    end_frame=120,
):
    img1 = bpy.data.images.load(bpy.path.abspath("//images/smile_1.png"))
    img2 = bpy.data.images.load(bpy.path.abspath("//images/smile_2.png"))
    bpy.ops.mesh.primitive_plane_add(
        size=face_size, location=(0, face_offset, apple.location.z + 0.5)
    )
    face_plane = bpy.context.active_object
    face_plane.name = "AppleFace"
    face_plane.rotation_euler[0] = 3.14159 / 2
    face_plane.parent = apple
    face_plane.matrix_parent_inverse = apple.matrix_world.inverted()
    mat = bpy.data.materials.new(name="FaceMaterial")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    tex_image1 = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_image1.image = img1
    tex_image1.interpolation = "Closest"
    tex_image1.image.colorspace_settings.name = "sRGB"
    tex_image1.extension = "CLIP"
    tex_image2 = mat.node_tree.nodes.new("ShaderNodeTexImage")
    tex_image2.image = img2
    tex_image2.interpolation = "Closest"
    tex_image2.image.colorspace_settings.name = "sRGB"
    tex_image2.extension = "CLIP"
    mix_node = mat.node_tree.nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = "MIX"
    mix_node.inputs["Fac"].default_value = 0.0
    mat.node_tree.links.new(mix_node.inputs[1], tex_image1.outputs["Color"])
    mat.node_tree.links.new(mix_node.inputs[2], tex_image2.outputs["Color"])
    mat.node_tree.links.new(bsdf.inputs["Base Color"], mix_node.outputs["Color"])
    mix_alpha = mat.node_tree.nodes.new("ShaderNodeMixRGB")
    mix_alpha.blend_type = "MIX"
    mix_alpha.inputs["Fac"].default_value = 0.0
    mat.node_tree.links.new(mix_alpha.inputs[1], tex_image1.outputs["Alpha"])
    mat.node_tree.links.new(mix_alpha.inputs[2], tex_image2.outputs["Alpha"])
    mat.node_tree.links.new(bsdf.inputs["Alpha"], mix_alpha.outputs["Color"])
    bsdf.inputs["Metallic"].default_value = 1.0
    mat.blend_method = "BLEND"
    if hasattr(mat, "shadow_method"):
        mat.shadow_method = "NONE"
    mat.use_backface_culling = False
    mat.alpha_threshold = 0.0
    face_plane.data.materials.clear()
    face_plane.data.materials.append(mat)
    bpy.context.view_layer.objects.active = face_plane
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    scene = bpy.context.scene
    if scene.render.engine == "BLENDER_EEVEE":
        scene.eevee.use_ssr = True
        scene.eevee.use_ssr_refraction = True
        scene.render.film_transparent = True
    fac_curve = mix_node.inputs["Fac"]
    fac_alpha_curve = mix_alpha.inputs["Fac"]
    for frame in range(start_frame, end_frame + 1):
        if (40 <= frame <= 45) or (60 <= frame <= 65) or (90 <= frame <= 95):
            fac_curve.default_value = 1.0
            fac_alpha_curve.default_value = 1.0
        else:
            fac_curve.default_value = 0.0
            fac_alpha_curve.default_value = 0.0
        fac_curve.keyframe_insert("default_value", frame=frame)
        fac_alpha_curve.keyframe_insert("default_value", frame=frame)
    return face_plane


# Animate the apple along the path
def animate_apple_on_path(apple, path_obj, start_frame=1, end_frame=120):
    # Remove any existing Follow Path constraint to avoid conflicts
    for c in apple.constraints:
        if c.type == "FOLLOW_PATH":
            apple.constraints.remove(c)

    curve = path_obj.data
    spline = curve.splines[0]
    # Get the total length of the path
    path_length = (
        path_obj.data.path_duration
        if hasattr(path_obj.data, "path_duration") and path_obj.data.use_path
        else 100
    )
    # Ensure path is evaluated as a path
    path_obj.data.use_path = True
    path_obj.data.eval_time = 0

    for frame in range(start_frame, end_frame + 1):
        t = (frame - start_frame) / (end_frame - start_frame)
        # Evaluate position along the path
        path_obj.data.eval_time = t * (path_length - 1)
        bpy.context.view_layer.update()
        # Get world position of the path at this eval_time
        path_matrix = path_obj.matrix_world
        path_pos = (
            path_obj.matrix_world @ path_obj.data.splines[0].bezier_points[0].co.copy()
        )
        if hasattr(path_obj, "evaluated_get"):
            # Blender 2.8+ API
            eval_curve = path_obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
            path_pos = (
                eval_curve.matrix_world
                @ eval_curve.data.splines[0].bezier_points[0].co.copy()
            )
        # Use the path's as_numpy API if available (Blender 3.0+)
        if hasattr(curve, "splines") and hasattr(
            curve.splines[0], "evaluate"
        ):  # Blender 3.0+
            path_pos = path_obj.matrix_world @ curve.splines[0].evaluate(t)
        else:
            # Fallback: interpolate between points
            num_points = len(spline.bezier_points)
            idx = int(t * (num_points - 1))
            next_idx = min(idx + 1, num_points - 1)
            p0 = path_obj.matrix_world @ spline.bezier_points[idx].co.copy()
            p1 = path_obj.matrix_world @ spline.bezier_points[next_idx].co.copy()
            local_t = (t * (num_points - 1)) - idx
            path_pos = p0.lerp(p1, local_t)

        # --- DANCE ANIMATION (offset from path) ---
        x = math.sin(2 * math.pi * t * 2) * 2
        z = abs(math.sin(2 * math.pi * t * 3)) * 2 + 1
        rot_z = math.radians(30) * math.sin(2 * math.pi * t * 2)
        rot_x = math.sin(2 * math.pi * t * 1.5) * 0.3
        rot_y = math.cos(2 * math.pi * t * 1.2) * 0.2

        # Add dance offset to path position
        apple.location = (path_pos.x + x, path_pos.y, path_pos.z + z)
        apple.rotation_euler = (rot_x, rot_y, rot_z)
        apple.keyframe_insert(data_path="location", frame=frame)
        apple.keyframe_insert(data_path="rotation_euler", frame=frame)


# Add a fixed camera
def add_fixed_camera(location=(0, -40, 8)):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.active_object
    cam.name = "FixedCamera"
    bpy.context.scene.camera = cam
    cam.rotation_euler = (math.radians(82), 0, 0)
    return cam


# Add multiple strong lights to illuminate the apple
def add_apple_lighting():
    import mathutils

    bpy.ops.object.light_add(type="AREA", location=(0, -20, 15))
    key = bpy.context.active_object
    key.data.energy = 80000
    key.data.size = 100
    key.name = "AppleKeyLight"
    direction = (0 - key.location.x, 0 - key.location.y, 2 - key.location.z)
    key.rotation_euler = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.light_add(type="AREA", location=(20, -10, 10))
    fill = bpy.context.active_object
    fill.data.energy = 30000
    fill.data.size = 80
    fill.name = "AppleFillLight"
    direction = (0 - fill.location.x, 0 - fill.location.y, 2 - fill.location.z)
    fill.rotation_euler = (
        mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    )
    bpy.ops.object.light_add(type="AREA", location=(-15, 10, 12))
    rim = bpy.context.active_object
    rim.data.energy = 20000
    rim.data.size = 60
    rim.name = "AppleRimLight"
    direction = (0 - rim.location.x, 0 - rim.location.y, 2 - rim.location.z)
    rim.rotation_euler = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    cam = bpy.data.objects.get("FixedCamera")
    if cam:
        cam_light_loc = (cam.location.x, cam.location.y + 2, cam.location.z)
        bpy.ops.object.light_add(type="AREA", location=cam_light_loc)
        cam_light = bpy.context.active_object
        cam_light.data.energy = 60000
        cam_light.data.size = 80
        cam_light.name = "AppleCameraLight"
        direction = (
            0 - cam_light.location.x,
            0 - cam_light.location.y,
            2 - cam_light.location.z,
        )
        cam_light.rotation_euler = (
            mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
        )


# Set the world background to black
def set_black_background():
    bpy.context.scene.world.use_nodes = True
    world = bpy.context.scene.world
    nt = world.node_tree
    bg = nt.nodes["Background"]
    bg.inputs[0].default_value = (0, 0, 0, 1)
    bg.inputs[1].default_value = 1.0
    for node in list(nt.nodes):
        if (
            node.name == "AmbientMix" or node.name.startswith("ShaderNodeBackground")
        ) and node != bg:
            nt.nodes.remove(node)
    for link in list(nt.links):
        if link.to_node.name == "World Output" and link.from_node != bg:
            nt.links.remove(link)
    if not any(
        link.from_node == bg and link.to_node.name == "World Output"
        for link in nt.links
    ):
        nt.links.new(bg.outputs[0], nt.nodes["World Output"].inputs[0])


# Main execution
def main():
    clear_scene()
    path_obj = add_path_curve()
    apple_obj_path = get_apple_obj_path()
    print(f"Importing apple from: {apple_obj_path}")
    apple = import_apple(apple_obj_path)
    print(f"Apple location: {apple.location}")
    add_animated_face(apple, start_frame=1, end_frame=120)
    animate_apple_on_path(apple, path_obj, start_frame=1, end_frame=120)
    add_fixed_camera()
    add_apple_lighting()
    set_black_background()


if __name__ == "__main__":
    main()
