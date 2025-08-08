"""
Standalone PyOpenGL app: Dancing Apple on a Path
- Loads apple.obj and two PNG face images
- Animates apple along a Bezier path with dance (oscillation, bounce, rotation)
- Swaps face images for blinking/expressions
- Renders in real time with a black background

Dependencies:
- PyOpenGL
- Pillow (for PNG loading)
- numpy
- glfw (for windowing)
- A simple OBJ loader (provided inline)

Place apple.obj in ./models/, smile_1.png and smile_2.png in ./images/
"""

import sys
import math
import time
import numpy as np
import os
from PIL import Image
from OpenGL.GL import *
from OpenGL.GLU import *
import glfw


# --- Simple OBJ loader (vertices, normals, texcoords, faces) ---
def load_obj(filename):
    vertices, normals, texcoords, faces = [], [], [], []
    with open(filename, "r") as f:
        for line in f:
            if line.startswith("v "):
                vertices.append(list(map(float, line.split()[1:4])))
            elif line.startswith("vn "):
                normals.append(list(map(float, line.split()[1:4])))
            elif line.startswith("vt "):
                texcoords.append(list(map(float, line.split()[1:3])))
            elif line.startswith("f "):
                # Parse face indices
                face_indices = []
                for v in line.split()[1:]:
                    w = v.split("/")
                    vi = int(w[0]) - 1
                    ti = int(w[1]) - 1 if len(w) > 1 and w[1] else -1
                    ni = int(w[2]) - 1 if len(w) > 2 and w[2] else -1
                    face_indices.append((vi, ti, ni))
                # Triangulate face if needed (fan method)
                if len(face_indices) == 3:
                    faces.append(face_indices)
                elif len(face_indices) > 3:
                    for i in range(1, len(face_indices) - 1):
                        tri = [face_indices[0], face_indices[i], face_indices[i + 1]]
                        faces.append(tri)
    return np.array(vertices), np.array(normals), np.array(texcoords), faces


# --- MTL loader ---


# --- Robust MTL loader ---
def load_mtl(mtl_path, obj_dir):
    materials = {}
    current_mat = None
    print(f"[DEBUG] Loading MTL: {mtl_path}")
    with open(mtl_path, "r") as f:
        for line in f:
            if line.startswith("newmtl "):
                current_mat = line.split()[1].strip()
                materials[current_mat] = {"map_Kd": None, "Kd": [1.0, 1.0, 1.0]}
            elif line.startswith("map_Kd") and current_mat:
                tex_file = line.split(None, 1)[1].strip()
                materials[current_mat]["map_Kd"] = os.path.join(obj_dir, tex_file)
                print(
                    f"[DEBUG] Material '{current_mat}' has texture: {materials[current_mat]['map_Kd']}"
                )
            elif line.startswith("Kd ") and current_mat:
                kd_vals = list(map(float, line.split()[1:4]))
                materials[current_mat]["Kd"] = kd_vals
                print(
                    f"[DEBUG] Material '{current_mat}' has Kd (diffuse color): {kd_vals}"
                )
    print(f"[DEBUG] Materials loaded: {materials}")
    return materials


# --- OBJ loader with MTL support ---


# --- OBJ loader with robust MTL/material support ---
def load_obj(filename):
    vertices, normals, texcoords = [], [], []
    faces_by_mat = {}
    obj_dir = os.path.dirname(filename)
    active_mat = None
    mtl_path = None
    print(f"[DEBUG] Loading OBJ: {filename}")
    with open(filename, "r") as f:
        for line in f:
            if line.startswith("mtllib "):
                mtl_path = os.path.join(obj_dir, line.split()[1].strip())
                print(f"[DEBUG] OBJ references MTL: {mtl_path}")
            elif line.startswith("usemtl "):
                active_mat = line.split()[1].strip()
                if active_mat not in faces_by_mat:
                    faces_by_mat[active_mat] = []
            elif line.startswith("v "):
                vertices.append(list(map(float, line.split()[1:4])))
            elif line.startswith("vn "):
                normals.append(list(map(float, line.split()[1:4])))
            elif line.startswith("vt "):
                texcoords.append(list(map(float, line.split()[1:3])))
            elif line.startswith("f "):
                # Parse face indices
                face_indices = []
                for v in line.split()[1:]:
                    w = v.split("/")
                    vi = int(w[0]) - 1
                    ti = int(w[1]) - 1 if len(w) > 1 and w[1] else -1
                    ni = int(w[2]) - 1 if len(w) > 2 and w[2] else -1
                    face_indices.append((vi, ti, ni))
                # Triangulate face if needed (fan method)
                if len(face_indices) == 3:
                    faces = [face_indices]
                elif len(face_indices) > 3:
                    faces = []
                    for i in range(1, len(face_indices) - 1):
                        tri = [face_indices[0], face_indices[i], face_indices[i + 1]]
                        faces.append(tri)
                else:
                    faces = []
                if active_mat is None:
                    active_mat = "default"
                    if active_mat not in faces_by_mat:
                        faces_by_mat[active_mat] = []
                faces_by_mat[active_mat].extend(faces)
    print(f"[DEBUG] Faces by material: {{k: len(v) for k,v in faces_by_mat.items()}}")
    # Parse MTL if present
    materials = {}
    if mtl_path and os.path.exists(mtl_path):
        materials = load_mtl(mtl_path, obj_dir)
    else:
        print(f"[WARN] No MTL file found or referenced: {mtl_path}")
    if not materials:
        print("[WARN] No materials loaded!")
    return (
        np.array(vertices),
        np.array(normals),
        np.array(texcoords),
        faces_by_mat,
        materials,
    )
    return (
        np.array(vertices),
        np.array(normals),
        np.array(texcoords),
        faces_by_mat,
        materials,
    )


# --- Texture loading ---


def load_texture(path):
    img = Image.open(path).convert("RGBA")
    img_data = np.array(img)[::-1]
    tex_id = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex_id)
    glTexImage2D(
        GL_TEXTURE_2D,
        0,
        GL_RGBA,
        img.width,
        img.height,
        0,
        GL_RGBA,
        GL_UNSIGNED_BYTE,
        img_data,
    )
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBindTexture(GL_TEXTURE_2D, 0)
    return tex_id


# --- Bezier path evaluation ---
def bezier_point(t, points):
    # Cubic Bezier for 4 points
    p0, p1, p2, p3 = points
    return (
        (1 - t) ** 3 * p0
        + 3 * (1 - t) ** 2 * t * p1
        + 3 * (1 - t) * t**2 * p2
        + t**3 * p3
    )


# --- Animation parameters ---
OBJ_PATH = "./models/apple.obj"
FACE1_PATH = "./images/smile_1.png"
FACE2_PATH = "./images/smile_2.png"

# Path control points (match Blender's)
PATH_POINTS = [
    np.array([-10, 0, 0], dtype=float),
    np.array([-3, 5, 0], dtype=float),
    np.array([3, -5, 0], dtype=float),
    np.array([10, 0, 0], dtype=float),
]


# --- OpenGL rendering ---


def draw_obj(vertices, normals, texcoords, faces_by_mat, materials, texture_ids):
    for mat_name, faces in faces_by_mat.items():
        tex_id = None
        kd = [1.0, 1.0, 1.0]
        if mat_name in materials:
            tex_path = materials[mat_name].get("map_Kd")
            if tex_path and tex_path in texture_ids:
                tex_id = texture_ids[tex_path]
            kd = materials[mat_name].get("Kd", [1.0, 1.0, 1.0])
        if tex_id:
            glBindTexture(GL_TEXTURE_2D, tex_id)
            glColor4f(1, 1, 1, 1)
        else:
            glBindTexture(GL_TEXTURE_2D, 0)
            glColor3f(*kd)
        glBegin(GL_TRIANGLES)
        for face in faces:
            for vi, ti, ni in face:
                if len(normals) > 0 and ni >= 0 and ni < len(normals):
                    glNormal3fv(normals[ni])
                if len(texcoords) > 0 and ti >= 0 and ti < len(texcoords):
                    glTexCoord2fv(texcoords[ti])
                glVertex3fv(vertices[vi])
        glEnd()
        if tex_id:
            glBindTexture(GL_TEXTURE_2D, 0)


def draw_face_plane(size=2.5):
    glBegin(GL_QUADS)
    glTexCoord2f(0, 0)
    glVertex3f(-size / 2, 0, -size / 2)
    glTexCoord2f(1, 0)
    glVertex3f(size / 2, 0, -size / 2)
    glTexCoord2f(1, 1)
    glVertex3f(size / 2, 0, size / 2)
    glTexCoord2f(0, 1)
    glVertex3f(-size / 2, 0, size / 2)
    glEnd()


# --- Main app ---
def main():
    if not glfw.init():
        print("Could not initialize GLFW")
        sys.exit(1)
    window = glfw.create_window(800, 600, "Dancing Apple", None, None)
    if not window:
        glfw.terminate()
        print("Could not create window")
        sys.exit(1)
    glfw.make_context_current(window)
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_TEXTURE_2D)
    # Load assets
    vertices, normals, texcoords, faces_by_mat, materials = load_obj(OBJ_PATH)
    face_tex1 = load_texture(FACE1_PATH)
    face_tex2 = load_texture(FACE2_PATH)
    # Load all textures referenced in materials
    texture_ids = {}
    for mat_name, mat in materials.items():
        tex_path = mat.get("map_Kd")
        if tex_path:
            if os.path.exists(tex_path):
                print(f"[DEBUG] Loading texture for material '{mat_name}': {tex_path}")
                texture_ids[tex_path] = load_texture(tex_path)
            else:
                print(
                    f"[WARN] Texture file for material '{mat_name}' does not exist: {tex_path}"
                )
    if not texture_ids:
        print("[WARN] No textures loaded for materials!")

    # Camera setup
    def set_camera():
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, 800 / 600, 0.1, 100)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        gluLookAt(0, -40, 8, 0, 0, 0, 0, 0, 1)

    # Animation timing
    start_time = time.time()
    duration = 4.0  # seconds per loop
    while not glfw.window_should_close(window):
        now = time.time()
        t_anim = ((now - start_time) % duration) / duration
        # Path position
        path_pos = bezier_point(t_anim, PATH_POINTS)
        # Dance animation (offsets)
        x = math.sin(2 * math.pi * t_anim * 2) * 2
        z = abs(math.sin(2 * math.pi * t_anim * 3)) * 2 + 1
        rot_z = math.degrees(math.radians(30) * math.sin(2 * math.pi * t_anim * 2))
        rot_x = math.degrees(math.sin(2 * math.pi * t_anim * 1.5) * 0.3)
        rot_y = math.degrees(math.cos(2 * math.pi * t_anim * 1.2) * 0.2)
        # Face expression (blink/swap)
        if (0.33 < t_anim < 0.375) or (0.5 < t_anim < 0.541) or (0.75 < t_anim < 0.791):
            face_tex = face_tex2
        else:
            face_tex = face_tex1
        # Render
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        set_camera()
        glPushMatrix()
        glTranslatef(path_pos[0] + x, path_pos[1], path_pos[2] + z)
        # Stand apple upright: rotate +90 deg around X
        glRotatef(90, 1, 0, 0)
        glRotatef(rot_z, 0, 0, 1)
        glRotatef(rot_y, 0, 1, 0)
        glRotatef(rot_x, 1, 0, 0)
        # Draw apple (with robust material/texture support)
        glColor4f(1, 1, 1, 1)
        draw_obj(vertices, normals, texcoords, faces_by_mat, materials, texture_ids)
        # Draw face plane
        glPushMatrix()
        glTranslatef(0, 0.5, 2.95)  # Move smile up and further forward
        # Face upright: rotate -90 deg around X (relative to apple)
        glRotatef(-90, 1, 0, 0)
        glColor4f(1, 1, 1, 1)  # Ensure face is not tinted
        glBindTexture(GL_TEXTURE_2D, face_tex)
        draw_face_plane(size=2.5)
        glBindTexture(GL_TEXTURE_2D, 0)
        glPopMatrix()
        glPopMatrix()
        glfw.swap_buffers(window)
        glfw.poll_events()
    glfw.terminate()


if __name__ == "__main__":
    main()
