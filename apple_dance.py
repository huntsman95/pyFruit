import bpy
import math
import os


# Path to the apple OBJ file (relative to the Blender file location)
def get_apple_obj_path():
    # Use Blender's path utility to resolve relative to the .blend file or script
    return bpy.path.abspath("//models/apple.obj")


# Remove all existing objects
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


# Import the apple OBJ model
def import_apple(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Apple OBJ file not found at: {path}")
    # Import with Blender's default axes
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=path)
    else:
        bpy.ops.import_scene.obj(filepath=path)
    # Assume the imported object is the active object
    apple = bpy.context.selected_objects[0]
    apple.name = "DancingApple"
    # Rotate 90 degrees about X axis to correct orientation
    apple.rotation_euler[0] = math.radians(90)
    # Apply the rotation to make it permanent
    bpy.context.view_layer.objects.active = apple
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    # Force all apple materials to be opaque and metallic
    for mat_slot in apple.material_slots:
        mat = mat_slot.material
        if mat is not None:
            if hasattr(mat, "blend_method"):
                mat.blend_method = "OPAQUE"
            if hasattr(mat, "alpha"):  # For Principled BSDF
                mat.alpha = 1.0
            # For node-based materials
            if mat.use_nodes:
                for node in mat.node_tree.nodes:
                    if node.type == "BSDF_PRINCIPLED":
                        # Set Alpha
                        if "Alpha" in node.inputs:
                            node.inputs["Alpha"].default_value = 1.0
                        # Set Metallic
                        if "Metallic" in node.inputs:
                            node.inputs["Metallic"].default_value = 1.0
    return apple


# Animate the apple with a complex dance
def animate_apple(obj, start_frame=1, end_frame=120):
    bpy.context.scene.frame_start = start_frame
    bpy.context.scene.frame_end = end_frame
    for frame in range(start_frame, end_frame + 1):
        t = (frame - start_frame) / (end_frame - start_frame)
        # Side-to-side (sinusoidal)
        x = math.sin(2 * math.pi * t * 2) * 2
        # Up-and-down (bouncing)
        y = 0
        z = abs(math.sin(2 * math.pi * t * 3)) * 2 + 1
        # Spin (rotation around Z)
        rot_z = t * 2 * math.pi * 2  # 2 full spins
        # Sway (rotation around X and Y)
        rot_x = math.sin(2 * math.pi * t * 1.5) * 0.3
        rot_y = math.cos(2 * math.pi * t * 1.2) * 0.2
        obj.location = (x, y, z)
        obj.rotation_euler = (rot_x, rot_y, rot_z)
        obj.keyframe_insert(data_path="location", frame=frame)
        obj.keyframe_insert(data_path="rotation_euler", frame=frame)


# Add and animate a camera that pans left to right across the apple
def add_and_animate_camera(start_frame=1, end_frame=120, pan_distance=60, height=8):
    # Move camera farther back (increase Y distance)
    camera_y = -40
    bpy.ops.object.camera_add(location=(-pan_distance / 2, camera_y, height))
    cam = bpy.context.active_object
    cam.name = "PanningCamera"
    bpy.context.scene.camera = cam
    # Animate camera panning from left to right
    for frame in [start_frame, end_frame]:
        # X moves from -pan_distance/2 to +pan_distance/2
        t = (frame - start_frame) / (end_frame - start_frame)
        x = -pan_distance / 2 + t * pan_distance
        cam.location.x = x
        cam.keyframe_insert(data_path="location", frame=frame)
        # Always look straight ahead (along +Y axis)
        # cam.rotation_euler = (math.radians(90), 0, 0)
        cam.rotation_euler = (math.radians(82), 0, 0)
        cam.keyframe_insert(data_path="rotation_euler", frame=frame)


# Add multiple strong lights to illuminate the apple
def add_apple_lighting():
    import mathutils

    # Key light (front/above)
    bpy.ops.object.light_add(type="AREA", location=(0, -20, 15))
    key = bpy.context.active_object
    key.data.energy = 80000
    key.data.size = 100
    key.name = "AppleKeyLight"
    direction = (0 - key.location.x, 0 - key.location.y, 2 - key.location.z)
    key.rotation_euler = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()

    # Fill light (side)
    bpy.ops.object.light_add(type="AREA", location=(20, -10, 10))
    fill = bpy.context.active_object
    fill.data.energy = 30000
    fill.data.size = 80
    fill.name = "AppleFillLight"
    direction = (0 - fill.location.x, 0 - fill.location.y, 2 - fill.location.z)
    fill.rotation_euler = (
        mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()
    )

    # Rim light (back/side)
    bpy.ops.object.light_add(type="AREA", location=(-15, 10, 12))
    rim = bpy.context.active_object
    rim.data.energy = 20000
    rim.data.size = 60
    rim.name = "AppleRimLight"
    direction = (0 - rim.location.x, 0 - rim.location.y, 2 - rim.location.z)
    rim.rotation_euler = mathutils.Vector(direction).to_track_quat("-Z", "Y").to_euler()

    # Camera light (from camera direction)
    cam = bpy.data.objects.get("PanningCamera")
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
    bg.inputs[0].default_value = (0, 0, 0, 1)  # RGBA black
    bg.inputs[1].default_value = 1.0  # Main background strength
    # Remove any ambient mix nodes if present
    for node in list(nt.nodes):
        if (
            node.name == "AmbientMix"
            or node.name.startswith("ShaderNodeBackground")
            and node != bg
        ):
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
    apple_obj_path = get_apple_obj_path()
    print(f"Importing apple from: {apple_obj_path}")
    apple = import_apple(apple_obj_path)
    print(f"Apple location: {apple.location}")
    animate_apple(apple)
    add_and_animate_camera(start_frame=1, end_frame=120)
    add_apple_lighting()
    set_black_background()


if __name__ == "__main__":
    main()
