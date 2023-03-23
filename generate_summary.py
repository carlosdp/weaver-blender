import bpy
import math
import argparse
import sys
import os
import math
import json
import subprocess
import requests
import sentry_sdk
from weaver_blender import layout


if os.environ.get('ENV') == 'production':
    sentry_sdk.init(
        dsn="https://ca84baeebae44315978743b944328285@o4504624881205248.ingest.sentry.io/4504640068124672",

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )


supabase_url = os.environ["SUPABASE_URL"]
service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
asset_workspace = os.environ.get('ASSET_WORKSPACE', '/tmp')
library_path = os.path.join(os.path.dirname(__file__), 'library')


def download_storage_object(bucket, storage_key, output_path):
    res = requests.post(
        "{}/storage/v1/object/sign/{}/{}".format(
            supabase_url, bucket, storage_key),
        headers={
            'Authorization': 'Bearer {}'.format(service_role_key),
            'Content-Type': 'application/json',
        },
        json={
            "expiresIn": 120,
        }
    )

    if res.status_code != 200:
        print(res.text)
        raise Exception("error getting signed url")

    res_data = res.json()
    image_url = res_data['signedURL']

    fileRes = requests.get(
        "{}/storage/v1/{}".format(supabase_url, image_url))

    with open(output_path, "wb") as f:
        f.write(fileRes.content)


current_text_position = 'top'


def next_text_position():
    global current_text_position

    if current_text_position == 'center':
        current_text_position = 'bottom'
    elif current_text_position == 'bottom':
        current_text_position = 'top'
    else:
        current_text_position = 'center'

    return current_text_position


if '__main__' == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument('--library', type=str, required=True,
                        help='path to library')
    parser.add_argument('--story', type=str, required=True,
                        help='path to story descriptor JSON')
    parser.add_argument('--output', type=str, required=True,
                        help='output path', default='/tmp/output.blend')
    parser.add_argument('--resolution', type=str, required=False,
                        help='output path', default='1920x1080')

    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

    with open(args.story, 'r') as f:
        story = json.load(f)

    bpy.ops.preferences.addon_enable(module='io_import_images_as_planes')

    res_x, res_y = [int(x) for x in args.resolution.split('x')]

    sequence_scene = bpy.data.scenes.new('Sequence')
    sequence_scene.sequence_editor_create()

    sequence_scene.view_settings.view_transform = 'Standard'
    sequence_scene.render.fps = 30
    sequence_scene.render.resolution_x = res_x
    sequence_scene.render.resolution_y = res_y
    sequence_scene.render.sequencer_gl_preview = 'MATERIAL'

    current_frame = 1

    for bi, block in enumerate(story['blocks']):
        video_scene = bpy.data.scenes.new('Video')

        video_scene.view_settings.view_transform = 'Standard'
        video_scene.render.fps = 30
        video_scene.render.resolution_x = res_x
        video_scene.render.resolution_y = res_y
        video_scene.render.sequencer_gl_preview = 'MATERIAL'

        bpy.context.window.scene = video_scene

        scene_camera = bpy.data.objects.new("SceneCameraControl", None)
        scene_camera_ob = bpy.data.objects.new(
            "SceneCamera", bpy.data.cameras.new("SceneCamera"))
        scene_camera_ob.parent = scene_camera
        scene_camera_ob.location = (20, 0, 0)
        scene_camera_ob.rotation_euler = (
            math.pi / 2, math.pi / 2, math.pi / 2)
        video_scene.collection.objects.link(scene_camera)
        video_scene.collection.objects.link(scene_camera_ob)
        video_scene.camera = scene_camera_ob

        if 'colors' in story['metadata']:
            bg = story['metadata']['colors']['background']
            tc = story['metadata']['colors']['text']

            bg_color = (bg['r']/255.0, bg['g']/255.0, bg['b']/255.0, 1.0)
            text_color = (tc['r']/255.0, tc['g']/255.0, tc['b']/255.0, 1.0)
        else:
            bg_color = (1.0, 1.0, 1.0, 1.0)
            text_color = (0.0, 0.0, 0.0, 1.0)

        world = bpy.data.worlds.new("World")
        world.use_nodes = True
        world.node_tree.nodes.clear()
        world_emission = world.node_tree.nodes.new("ShaderNodeEmission")
        world_emission.inputs[0].default_value = bg_color
        world_output = world.node_tree.nodes.new("ShaderNodeOutputWorld")
        world.node_tree.links.new(
            world_emission.outputs[0], world_output.inputs[0])
        video_scene.world = world

        text_material = bpy.data.materials.new("TextMaterial")
        text_material.use_nodes = True
        text_material.node_tree.nodes.clear()
        text_emission = text_material.node_tree.nodes.new("ShaderNodeEmission")
        text_emission.inputs[0].default_value = text_color
        text_output = text_material.node_tree.nodes.new(
            "ShaderNodeOutputMaterial")
        text_material.node_tree.links.new(
            text_emission.outputs[0], text_output.inputs[0])

        print('generating scene')

        buffer_frames = 30

        if 'speech' not in block:
            raise Exception("block missing speech")

        # add audio to sequence, get frame start
        # download speech
        speech_file = "{}/{}".format(asset_workspace, block['id'])
        download_storage_object(
            'assets', block['speech']['asset']['key'], speech_file)

        # add to sequence
        audio_frame_start = current_frame
        audio_frame_end = layout.add_audio("{}.speech".format(
            block['id']), speech_file, sequence_scene, audio_frame_start, library_path)
        frame_start = 0
        frame_end = audio_frame_end - audio_frame_start

        video_scene.frame_end = frame_end
        sequence_scene.sequence_editor.sequences.new_scene(
            name=block["id"], scene=video_scene, channel=4, frame_start=current_frame)

        current_frame = audio_frame_end

        # create stage, animate in camera

        stage = layout.add_stage(block['id'], video_scene, (0, bi*30, 0))

        bpy.context.evaluated_depsgraph_get().update()

        camera = stage["camera"]
        scene_camera.matrix_world = camera.matrix_world
        scene_camera.keyframe_insert("location", frame=frame_start)
        scene_camera.keyframe_insert(
            "rotation_euler", frame=frame_start)
        scene_camera.keyframe_insert(
            "location", frame=frame_end-buffer_frames)
        scene_camera.keyframe_insert(
            "rotation_euler", frame=frame_end-buffer_frames)

        standard_duration = 60  # frames
        fps = video_scene.render.fps

        if block['type'] in ('image', 'screenshot'):
            if block['type'] == 'image':
                asset = story['assets'][block['arguments']['image_id']]
            else:
                asset = story['assets'][block['arguments']['url_id']]

            if 'storage' in asset:
                asset_file = "{}/{}_{}".format(asset_workspace,
                                               block['id'], asset['id'])
                download_storage_object(
                    'assets', asset['storage']['key'], asset_file)
                layout.add_image(
                    library_path, asset_file, video_scene, stage, 'background', None, None)
            else:
                print('missing asset {}'.format(asset['id']))

        if story['metadata']['title']:
            layout.add_text(library_path, story['metadata']['title'],
                            video_scene, stage, 'bottom', None, None, text_material)

    sequence_scene.frame_end = current_frame
    # add music
    # sequence_scene.sequence_editor.sequences.new_sound(
    #     name="music", filepath=os.path.join(library_path, "music.mp3"), channel=1, frame_start=1)
    # music = sequence_scene.sequence_editor.sequences_all['music']
    # music.volume = 0.2

    print('done generating scene')

    bpy.ops.wm.save_mainfile(filepath=args.output)
