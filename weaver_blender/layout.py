import bpy
import math
import os
from mathutils import geometry, Vector
from mathutils.geometry import intersect_line_plane


def bezier_tangent(pt0=Vector(), pt1=Vector(), pt2=Vector(), pt3=Vector(), step=0.5):
    # Return early if step is out of bounds [0, 1].
    if step <= 0.0:
        return pt1 - pt0
    if step >= 1.0:
        return pt3 - pt2

    # Find coefficients.
    u = 1.0 - step
    ut6 = u * step * 6.0
    tsq3 = step * step * 3.0
    usq3 = u * u * 3.0

    # Find tangent and return.
    return (pt1 - pt0) * usq3 + (pt2 - pt1) * ut6 + (pt3 - pt2) * tsq3


def distribute_points_on_curve(curve, num_points):
    bez_points = curve.data.splines[0].bezier_points

    # Create an empty list.
    points_on_curve = []

    # Loop through the bezier points in the bezier curve.
    bez_len = len(bez_points)
    res_per_section = 1 if bez_len / \
        2 >= num_points else math.ceil((num_points - (bez_len / 2)) / (bez_len / 2))

    i_range = range(1, bez_len, 1)

    for i in i_range:
        # Cache a current and next point.
        curr_point = bez_points[i - 1]
        next_point = bez_points[i]

        # Calculate bezier points for this segment.
        calc_points = geometry.interpolate_bezier(
            curr_point.co,
            curr_point.handle_right,
            next_point.handle_left,
            next_point.co,
            res_per_section + 1)

        # The last point on this segment will be the
        # first point on the next segment in the spline.
        if i != bez_len - 1:
            calc_points.pop()

        point_tangent_pairs = []

        # Loop through the calculated points.
        points_len = len(calc_points)
        to_percent = 1.0 / (points_len - 1) if points_len > 1 else 1.0
        j_range = range(0, points_len, 1)
        for j in j_range:
            # Convert progress through the loop to a percent.
            j_percent = j * to_percent

            # Calculate the tangent.
            tangent = bezier_tangent(
                pt0=curr_point.co,
                pt1=curr_point.handle_right,
                pt2=next_point.handle_left,
                pt3=next_point.co,
                step=j_percent)

            # Set the vector to unit length.
            tangent.normalize()

            # Place the point and tangent in a dictionary.
            entry = {'co': calc_points[j], 'tan': tangent}

            # Append the dictionary to the list.
            point_tangent_pairs.append(entry)

        # Concatenate lists.
        points_on_curve += point_tangent_pairs

    return points_on_curve


def add_audio(name, sound_path, scene, frame_start, library_path):
    scene.sequence_editor_create()

    scene.sequence_editor.sequences.new_sound(
        name=name, filepath=sound_path, channel=3, frame_start=frame_start)

    sequence = scene.sequence_editor.sequences_all[name]
    sequence.show_waveform = True

    if frame_start > 1:
        scene.sequence_editor.sequences.new_sound(
            name="{}.transition".format(name), filepath=os.path.join(library_path, "swoosh-transition.wav"), channel=2, frame_start=frame_start - 30)

    frame_end = sequence.frame_final_end

    return frame_end


def add_image(filepath, scene, stage, tag, location, audio_start_frame, audio_end_frame, library_path):
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
    else:
        # center
        point = (stage_points["tr"] + stage_points["bl"]) / 2

    outside_point = point + (point.normalized() * 20)

    object_name = "screenshot.{}.{}".format(
        audio_start_frame, tag["timeOffset"])

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

    image_plane.scale = (4, 4, 4)
    image_plane.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)

    asset_start_frame = audio_start_frame + \
        math.floor(tag['timeOffset'] * scene.render.fps) - 10
    asset_end_frame = asset_start_frame + 60

    image_plane.location = outside_point
    image_plane.hide_render = True
    image_plane.keyframe_insert("hide_render", frame=asset_start_frame - 11)
    image_plane.hide_render = False
    image_plane.keyframe_insert("location", frame=asset_start_frame - 10)
    image_plane.keyframe_insert("hide_render", frame=asset_start_frame - 10)

    image_plane.location = point
    image_plane.keyframe_insert("location", frame=asset_start_frame)
    image_plane.keyframe_insert("location", frame=asset_start_frame + 60)

    image_plane.location = outside_point
    image_plane.keyframe_insert("location", frame=asset_start_frame + 70)
    image_plane.keyframe_insert("hide_render", frame=asset_start_frame + 70)
    image_plane.hide_render = True
    image_plane.keyframe_insert("hide_render", frame=asset_start_frame + 71)

    swoosh_in_name = "{}.swoosh-in".format(object_name)
    scene.sequence_editor.sequences.new_sound(
        name=swoosh_in_name, filepath=os.path.join(library_path, "swoosh-in.wav"), channel=2, frame_start=asset_start_frame)
    seq = scene.sequence_editor.sequences_all[swoosh_in_name]
    seq.volume = 0.5

    if asset_end_frame < audio_end_frame - 30:
        swoosh_out_name = "{}.swoosh-out".format(object_name)
        scene.sequence_editor.sequences.new_sound(
            name=swoosh_out_name, filepath=os.path.join(library_path, "swoosh-out.wav"), channel=2, frame_start=asset_end_frame)
        seq = scene.sequence_editor.sequences_all[swoosh_out_name]
        seq.volume = 0.5

    return (asset_start_frame, asset_end_frame)


def add_text(custom_text, scene, stage, tag, location, audio_start_frame, audio_end_frame, material, library_path):
    stage_root = stage["root"]

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
    else:
        # center
        point = (stage_points["tr"] + stage_points["bl"]) / 2

    outside_point = point + (point.normalized() * 20)

    object_name = "text.{}.{}".format(
        audio_start_frame, tag["timeOffset"])

    # Create a new text object
    text = bpy.data.curves.new(
        name="text", type="FONT")
    text.body = custom_text
    text.align_x = "CENTER"
    text.align_y = "CENTER"
    text.size = 1
    text.extrude = 0.1
    text.text_boxes[0].width = 8
    text.text_boxes[0].x = -4

    text_object = bpy.data.objects.new(
        name=object_name, object_data=text)
    text_object.parent = stage_root
    # put text a little above main image
    text_object.location = point
    text_object.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)
    text_object.data.materials.append(material)
    scene.collection.objects.link(text_object)

    asset_start_frame = audio_start_frame + \
        math.floor(tag['timeOffset'] * scene.render.fps) - 10
    asset_end_frame = asset_start_frame + 60

    text_object.location = outside_point
    text_object.hide_render = True
    text_object.keyframe_insert("hide_render", frame=asset_start_frame - 11)
    text_object.hide_render = False
    text_object.keyframe_insert("location", frame=asset_start_frame - 10)
    text_object.keyframe_insert("hide_render", frame=asset_start_frame - 10)

    text_object.location = point
    text_object.keyframe_insert("location", frame=asset_start_frame)
    text_object.keyframe_insert("location", frame=asset_start_frame + 60)

    text_object.location = outside_point
    text_object.keyframe_insert("location", frame=asset_start_frame + 70)
    text_object.keyframe_insert("hide_render", frame=asset_start_frame + 70)
    text_object.hide_render = True
    text_object.keyframe_insert("hide_render", frame=asset_start_frame + 71)

    swoosh_in_name = "{}.swoosh-in".format(object_name)
    scene.sequence_editor.sequences.new_sound(
        name=swoosh_in_name, filepath=os.path.join(library_path, "swoosh-in.wav"), channel=2, frame_start=asset_start_frame)
    seq = scene.sequence_editor.sequences_all[swoosh_in_name]
    seq.volume = 0.5

    if asset_end_frame < audio_end_frame - 30:
        swoosh_out_name = "{}.swoosh-out".format(object_name)
        scene.sequence_editor.sequences.new_sound(
            name=swoosh_out_name, filepath=os.path.join(library_path, "swoosh-out.wav"), channel=2, frame_start=asset_end_frame)
        seq = scene.sequence_editor.sequences_all[swoosh_out_name]
        seq.volume = 0.5

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
    for i, image_coord in enumerate(((left, bottom), (left, top), (right, top), (right, bottom))):
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

    # create bezier circle, rotate 90 degrees on y axis, parent to empty object, move it 5 units on the X axis using bpy.data API
    bpy.ops.curve.primitive_bezier_circle_add()
    circle_object = bpy.data.objects["BezierCircle"]
    circle_object.name = "{}.asset_stage".format(id)
    circle_object.parent = empty
    circle_object.location = (3, 0, 0)
    circle_object.scale = (2, 2, 2)
    circle_object.rotation_euler[1] = 1.5708

    circle_object.data.use_path = False

    bpy.context.evaluated_depsgraph_get().update()

    # todo: set to an actual count
    stage_points = distribute_points_on_curve(
        circle_object, 8)

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
    bpy.ops.object.add(type="EMPTY", location=bl)
    bpy.ops.object.add(type="EMPTY", location=tl)
    bpy.ops.object.add(type="EMPTY", location=tr)
    bpy.ops.object.add(type="EMPTY", location=br)

    return {
        'name': empty.name,
        'camera': camera_empty,
        'root': empty,
        'asset_stage': circle_object,
        'reference_points': {
            'bl': empty.matrix_world.inverted() @ bl,
            'tl': empty.matrix_world.inverted() @ tl,
            'tr': empty.matrix_world.inverted() @ tr,
            'br': empty.matrix_world.inverted() @ br
        },
    }
