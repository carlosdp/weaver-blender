import bpy
import math
import os
import random
from mathutils import Vector
from mathutils.geometry import intersect_line_plane

from . import animation


def add_audio(name, sound_path, scene, frame_start, library_path):
    scene.sequence_editor_create()

    scene.sequence_editor.sequences.new_sound(
        name=name, filepath=sound_path, channel=3, frame_start=frame_start)

    sequence = scene.sequence_editor.sequences_all[name]
    sequence.show_waveform = True

    # if frame_start > 1:
    #     scene.sequence_editor.sequences.new_sound(
    #         name="{}.transition".format(name), filepath=os.path.join(library_path, "swoosh-transition.wav"), channel=2, frame_start=frame_start - 30)

    frame_end = sequence.frame_final_end

    return frame_end


def add_image(library_path, filepath, scene, stage, location, start_frame, end_frame):
    stage_points = stage["reference_points"]
    if location == "top":
        point = (stage_points["tr"] + stage_points["tl"]) / 2
    elif location == "left":
        point = (stage_points["tl"] + stage_points["bl"]) / 2
    elif location == "right":
        point = (stage_points["tr"] + stage_points["br"]) / 2
    elif location == "bottom":
        point = (stage_points["br"] + stage_points["bl"]) / 2
    elif location == "center":
        point = (stage_points["tr"] + stage_points["bl"]) / 2
    elif location == "top_right":
        point = (stage_points["tr"] + stage_points["tl"]) / 4
    elif location == "top_left":
        point = (stage_points["tl"] + stage_points["tr"]) / 4
    elif location == "bottom_right":
        point = (stage_points["br"] + stage_points["bl"]) / 4
    elif location == "bottom_left":
        point = (stage_points["bl"] + stage_points["br"]) / 4
    elif location == "background":
        point = stage_points["bg"]
    else:
        # center
        point = (stage_points["tr"] + stage_points["bl"]) / 2

    object_name = "screenshot.{}.{}".format(start_frame, end_frame)

    filename = os.path.basename(filepath)
    file_base = os.path.splitext(filename)[0]

    bpy.ops.import_image.to_plane(
        files=[{"name": filepath}], align_axis="Z+", shader="EMISSION")
    image_plane = scene.objects[file_base]
    image_plane.name = "asset.{}".format(object_name)
    image_plane.parent = stage["root"]
    image_data = image_plane.material_slots[0].material.node_tree.nodes['Image Texture'].image
    image_data.name = "asset.{}".format(object_name)
    image_data.pack()

    image_plane.location = point
    image_plane.scale = (4, 4, 4) if location != "background" else (25, 25, 25)
    image_plane.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)

    if start_frame is not None and end_frame is not None:
        animation.slow_zoom(
            image_plane, start_frame, end_frame)
        asset_start_frame = start_frame
        asset_end_frame = end_frame

        # swoosh_in_name = "{}.swoosh-in".format(object_name)
        # scene.sequence_editor.sequences.new_sound(
        #     name=swoosh_in_name, filepath=os.path.join(library_path, "swoosh-in.wav"), channel=2, frame_start=asset_start_frame)
        # seq = scene.sequence_editor.sequences_all[swoosh_in_name]
        # seq.volume = 0.5

        # if asset_end_frame < audio_end_frame - 30:
        #     swoosh_out_name = "{}.swoosh-out".format(object_name)
        #     scene.sequence_editor.sequences.new_sound(
        #         name=swoosh_out_name, filepath=os.path.join(library_path, "swoosh-out.wav"), channel=2, frame_start=asset_end_frame)
        #     seq = scene.sequence_editor.sequences_all[swoosh_out_name]
        #     seq.volume = 0.5
    else:
        asset_start_frame = None
        asset_end_frame = None

    return (asset_start_frame, asset_end_frame)


def add_text(library_path, custom_text, scene, stage, location, start_frame, end_frame, material):
    stage_root = stage["root"]

    stage_points = stage["reference_points"]
    if location in ("top", "top_right", "top_left"):
        point = (stage_points["tr"] + stage_points["tl"]) / 2
    elif location in ("left", "right", "center"):
        point = (stage_points["tr"] + stage_points["bl"]) / 2
    elif location in ("bottom", "bottom_right", "bottom_left"):
        point = (stage_points["br"] + stage_points["bl"]) / 2
    elif location == "background":
        point = stage_points["bg"]
    else:
        # center
        point = (stage_points["tr"] + stage_points["bl"]) / 2

    object_name = "text.{}.{}".format(start_frame, end_frame)

    with bpy.data.libraries.load(os.path.join(__file__, '..', '..', 'library.blend')) as (data_from, data_to):
        data_to.objects = ['DetailText']

    text_object = data_to.objects[0]
    text_object.name = object_name

    text_object.parent = stage_root
    text_object.location = point
    text_object.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)

    stroke_material = bpy.data.materials.new("TextMaterial")
    stroke_material.use_nodes = True
    stroke_material.node_tree.nodes.clear()
    stroke_emission = stroke_material.node_tree.nodes.new("ShaderNodeEmission")
    stroke_emission.inputs[0].default_value = (0, 0, 0, 1)
    stroke_output = stroke_material.node_tree.nodes.new(
        "ShaderNodeOutputMaterial")
    stroke_material.node_tree.links.new(
        stroke_emission.outputs[0], stroke_output.inputs[0])

    text_object.modifiers["GeometryNodes"]["Input_2"] = custom_text
    text_object.modifiers["GeometryNodes"]["Input_3"] = material
    text_object.modifiers["GeometryNodes"]["Input_4"] = stroke_material
    text_object.modifiers["GeometryNodes"]["Input_5"] = 8.0

    scene.collection.objects.link(text_object)

    if start_frame is not None and end_frame is not None:
        asset_start_frame = start_frame - 21
        asset_end_frame = end_frame

        animation.scale_up(text_object, start_frame, end_frame)

        # swoosh_in_name = "{}.swoosh-in".format(object_name)
        # scene.sequence_editor.sequences.new_sound(
        #     name=swoosh_in_name, filepath=os.path.join(library_path, "swoosh-in.wav"), channel=2, frame_start=asset_start_frame)
        # seq = scene.sequence_editor.sequences_all[swoosh_in_name]
        # seq.volume = 0.5

        # if asset_end_frame < audio_end_frame - 30:
        #     swoosh_out_name = "{}.swoosh-out".format(object_name)
        #     scene.sequence_editor.sequences.new_sound(
        #         name=swoosh_out_name, filepath=os.path.join(library_path, "swoosh-out.wav"), channel=2, frame_start=asset_end_frame)
        #     seq = scene.sequence_editor.sequences_all[swoosh_out_name]
        #     seq.volume = 0.5
    else:
        asset_start_frame = None
        asset_end_frame = None

    return (asset_start_frame, asset_end_frame)


def camera_stage_box(camera, scene, distance, safe_area=None):
    mw = camera.matrix_world
    o = Vector()  # mw.translation

    if safe_area:
        left = safe_area[0]
        top = 1 - safe_area[1]
        right = 1 - safe_area[2]
        bottom = safe_area[3]
    else:
        left = 0
        top = 1
        right = 1
        bottom = 0

    plane_co = Vector((0, 0, distance * -1))
    plane_no = Vector((1, 0, distance * -1))

    tr, br, bl, tl = camera.data.view_frame(scene=scene)
    # offset vectors from bl.
    # eg middle would be bl + 0.5 * (x + y)
    x = tr - tl
    y = tr - br

    result = []

    # roll around in CCW direction
    for image_coord in ((left, bottom), (left, top), (right, top), (right, bottom)):
        cx, cy = image_coord
        # vector pointing from cam origin thru image point (PERSP)
        v = (bl + (cx * x + cy * y)) - o

        result.append(mw @ intersect_line_plane(o,
                      o + v, plane_co, plane_no, True))

    return result


def add_stage(id, video_scene, location=(0, 0, 0)):
    # create an empty object, rotated 90 degrees on the X axis, using bpy.data API
    empty = bpy.data.objects.new(id, None)
    empty.location = location
    empty.rotation_euler[0] = 1.5708
    video_scene.collection.objects.link(empty)

    # create a camera object, parented to the empty object, using bpy.data API
    camera_distance = 20
    camera_empty = bpy.data.objects.new(
        "{}.CameraControl".format(id), None)
    camera_empty.parent = empty
    camera = bpy.data.cameras.new("{}.Camera".format(id))
    camera_ob = bpy.data.objects.new(
        "{}.Camera".format(id), camera)
    camera_ob.parent = camera_empty
    camera_ob.location = (camera_distance, 0, 0)
    camera_ob.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)
    video_scene.collection.objects.link(camera_empty)
    video_scene.collection.objects.link(camera_ob)

    bpy.context.evaluated_depsgraph_get().update()

    # add stage directions
    bl, tl, tr, br = camera_stage_box(
        camera_ob, video_scene, camera_distance, safe_area=(0.1, 0.1, 0.1, 0.1))

    bg = ((empty.matrix_world.inverted() @ tl) +
          (empty.matrix_world.inverted() @ br)) / 2
    bg.x = -10

    # stage reference
    bpy.ops.object.add(type="EMPTY", location=bl)
    bpy.ops.object.add(type="EMPTY", location=tl)
    bpy.ops.object.add(type="EMPTY", location=tr)
    bpy.ops.object.add(type="EMPTY", location=br)
    bpy.ops.object.add(type="EMPTY", location=bg)

    return {
        'name': empty.name,
        'camera': camera_empty,
        'root': empty,
        'reference_points': {
            'bl': empty.matrix_world.inverted() @ bl,
            'tl': empty.matrix_world.inverted() @ tl,
            'tr': empty.matrix_world.inverted() @ tr,
            'br': empty.matrix_world.inverted() @ br,
            'bg': bg
        },
    }
