import bpy
import sys
import argparse
import subprocess
import os
import sentry_sdk


if os.environ.get('ENV') == 'production':
    sentry_sdk.init(
        dsn="https://ca84baeebae44315978743b944328285@o4504624881205248.ingest.sentry.io/4504640068124672",

        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )


if '__main__' == __name__:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=str, required=True,
                        help='output path', default='/tmp/blender-out')
    parser.add_argument('--preview', action='store_true', default=False)

    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])

    scenes = []

    sequence_scene = bpy.data.scenes['Sequence']

    for scene in bpy.data.scenes:
        if 'Video' in scene.name:
            scene.render.filepath = "/tmp/{}.mp4".format(scene.name)
            scene.render.image_settings.file_format = 'FFMPEG'
            scene.render.ffmpeg.format = 'MPEG4'  # Matroska?
            scene.render.ffmpeg.audio_codec = 'NONE'
            scene.eevee.taa_render_samples = 32

            scenes.append(scene)

    # if args.preview:
    #     video_scene = bpy.data.scenes['Video']
    #     video_scene.render.resolution_percentage = 50
    #     video_scene.eevee.taa_render_samples = 16

    bpy.context.window.scene = sequence_scene
    sequence_scene.render.ffmpeg.audio_codec = 'AAC'
    bpy.ops.sound.mixdown(filepath="{}.mp3".format(
        args.output))

    for video_scene in scenes:
        bpy.ops.render.render(animation=True, scene=video_scene.name)

    file_args = []

    for scene in scenes:
        file_args.append('-i')
        file_args.append(scene.render.filepath)

    # combine audio and video
    subprocess.run([
        'ffmpeg',
    ] + file_args + [
        '-i', '{}.mp3'.format(args.output),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-y',
        '{}'.format(args.output)
    ])

    print('render complete, cleaning up')

    os.remove('{}.mp3'.format(args.output))

    for scene in scenes:
        os.remove(scene.render.filepath)

    print('done')
