import bpy
import sys
import argparse
import subprocess
import os
import sentry_sdk


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

    video_scene = bpy.data.scenes['Video']
    video_scene.render.ffmpeg.audio_codec = 'AAC'

    bpy.ops.sound.mixdown(filepath="{}.mp3".format(args.output))

    video_scene.render.filepath = "{}.mp4".format(args.output)
    video_scene.render.image_settings.file_format = 'FFMPEG'
    video_scene.render.ffmpeg.format = 'MPEG4'  # Matroska?
    video_scene.render.ffmpeg.audio_codec = 'NONE'
    video_scene.eevee.taa_render_samples = 32

    if args.preview:
        video_scene = bpy.data.scenes['Video']
        video_scene.render.resolution_percentage = 50
        video_scene.eevee.taa_render_samples = 16

    bpy.ops.render.render(animation=True, scene=video_scene.name)

    # combine audio and video
    subprocess.run([
        'ffmpeg',
        '-i', '{}.mp4'.format(args.output),
        '-i', '{}.mp3'.format(args.output),
        '-c:v', 'copy',
        '-c:a', 'aac',
        '-y',
        '{}'.format(args.output)
    ])

    print('render complete, cleaning up')

    os.remove('{}.mp3'.format(args.output))
    os.remove('{}.mp4'.format(args.output))

    print('done')
