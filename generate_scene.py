import bpy
import math
import argparse
import sys
import os
import json
import requests
from weaver_blender import layout


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


if '__main__' == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument('--library', type=str, required=True,
                        help='path to library')
    parser.add_argument('--story', type=str, required=True,
                        help='path to story descriptor JSON')
    parser.add_argument('--output', type=str, required=True,
                        help='output path', default='/tmp/output.blend')

    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

    with open(args.story, 'r') as f:
        story = json.load(f)

    bpy.ops.preferences.addon_enable(module='io_import_images_as_planes')

    video_scene = bpy.data.scenes.new('Video')

    video_scene.view_settings.view_transform = 'Standard'
    video_scene.render.fps = 30
    video_scene.render.resolution_x = 1080
    video_scene.render.resolution_y = 1920
    video_scene.render.sequencer_gl_preview = 'MATERIAL'

    bpy.context.window.scene = video_scene

    scene_camera = bpy.data.objects.new("SceneCameraControl", None)
    scene_camera_ob = bpy.data.objects.new(
        "SceneCamera", bpy.data.cameras.new("SceneCamera"))
    scene_camera_ob.parent = scene_camera
    scene_camera_ob.location = (20, 0, 0)
    scene_camera_ob.rotation_euler = (math.pi / 2, math.pi / 2, math.pi / 2)
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
    text_output = text_material.node_tree.nodes.new("ShaderNodeOutputMaterial")
    text_material.node_tree.links.new(
        text_emission.outputs[0], text_output.inputs[0])

    print('generating scene')

    current_frame = 0
    buffer_frames = 30

    for bi, block in enumerate(story['blocks']):
        if 'speech' not in block:
            raise Exception("block missing speech")

        # add audio to sequence, get frame start
        # download speech
        speech_file = "{}/{}".format(asset_workspace, block['id'])
        download_storage_object(
            'assets', block['speech']['asset']['key'], speech_file)

        # add to sequence
        frame_start = current_frame
        frame_end = layout.add_audio("{}.speech".format(
            block['id']), speech_file, video_scene, current_frame, library_path)

        # create stage, animate in camera

        stage = layout.add_stage(block['id'], video_scene, (0, bi*30, 0))

        bpy.context.evaluated_depsgraph_get().update()

        camera = stage["camera"]
        scene_camera.matrix_world = camera.matrix_world
        scene_camera.keyframe_insert("location", frame=frame_start)
        scene_camera.keyframe_insert(
            "rotation_euler", frame=frame_start)
        scene_camera.keyframe_insert("location", frame=frame_end-buffer_frames)
        scene_camera.keyframe_insert(
            "rotation_euler", frame=frame_end-buffer_frames)

        standard_duration = 60  # frames
        fps = video_scene.render.fps

        if 'speech' in block:
            tags = block['speech']['tags']
            directions = block['stage']['directions']

            # a list of dicts with each direction, and it's corresponding tag (or None)
            tagged_directions = []
            for i, direction in enumerate(directions):
                tag = tags.get(str(i))
                tagged_directions.append({
                    'direction': direction,
                    'tag': tag
                })

            # sort tagged directions by tag time offset
            tagged_directions = sorted(
                tagged_directions, key=lambda x: x['tag']['timeOffset'] if x['tag'] else 0)

            # place assets with timings
            for i in range(len(tagged_directions)):
                direction = tagged_directions[i]['direction']
                tag = tagged_directions[i]['tag']

                if tag:
                    duration = standard_duration

                    tag_frame_start = frame_start + \
                        int((tag['timeOffset']) * fps)

                    # if there is a next tag, bridge the gap
                    if i < len(tagged_directions) - 1:
                        next_direction = tagged_directions[i+1]['direction']

                        if 'asset' in next_direction or next_direction['type'] == 'text':
                            next_tag = tagged_directions[i+1]['tag']
                            if next_tag:
                                next_tag_frame_start = frame_start + \
                                    int((next_tag['timeOffset']) * fps)
                                if next_tag_frame_start - tag_frame_start > 60:
                                    duration = next_tag_frame_start - tag_frame_start
                    else:
                        # make the asset last until the end of the speech
                        duration = frame_end - tag_frame_start

                    if direction['type'] in ('image', 'screenshot') and 'asset' in direction:
                        asset = direction['asset']
                        asset_file = "{}/{}_{}".format(asset_workspace,
                                                       block['id'], i)
                        download_storage_object(
                            'assets', asset['key'], asset_file)
                        layout.add_image(
                            library_path, asset_file, video_scene, stage, direction['location'], tag_frame_start, tag_frame_start + duration)
                    elif direction['type'] == 'text':
                        layout.add_text(library_path, direction['data'], video_scene, stage,
                                        direction['location'], tag_frame_start, tag_frame_start + duration, text_material)
                elif direction['location'] == 'background':
                    if direction['type'] in ('image', 'screenshot') and 'asset' in direction:
                        asset = direction['asset']
                        asset_file = "{}/{}_{}".format(asset_workspace,
                                                       block['id'], i)
                        download_storage_object(
                            'assets', asset['key'], asset_file)
                        layout.add_image(
                            library_path, asset_file, video_scene, stage, direction['location'], None, None)
                    elif direction['type'] == 'text':
                        layout.add_text(
                            library_path, direction['data'], video_scene, stage, direction['location'], None, None, text_material)

        current_frame = frame_end + 1

    video_scene.frame_end = current_frame - 1

    # add music
    video_scene.sequence_editor.sequences.new_sound(
        name="music", filepath=os.path.join(library_path, "music.mp3"), channel=1, frame_start=1)
    music = video_scene.sequence_editor.sequences_all['music']
    music.volume = 0.2

    print('done generating scene')

    bpy.ops.wm.save_mainfile(filepath=args.output)
