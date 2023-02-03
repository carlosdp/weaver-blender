import os
import sys
import subprocess
import runpod
from runpod.serverless.utils import validator
import requests


BLENDER_BIN = "/bin/blender" if sys.platform == "linux" else "/Applications/Blender.app/Contents/MacOS/Blender"

supabase_url = os.environ["SUPABASE_URL"]
service_role_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
asset_workspace = os.environ.get('ASSET_WORKSPACE', '/tmp')


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


def upload_storage_object(bucket, storage_key, filepath, content_type, upsert=False):
    with open(filepath, "rb") as output_blend:
        with requests.post(
            "{}/storage/v1/object/{}/{}".format(
                supabase_url,
                bucket,
                storage_key
            ),
            headers={
                'Authorization': 'Bearer {}'.format(service_role_key),
                'Content-Type': content_type,
                'X-Upsert': str(upsert).lower(),
            },
            data=output_blend.read()
        ) as response:
            if not response.ok:
                print("error uploading asset")
                print(response.text)
                raise Exception(
                    "error uploading asset: {}".format(response.text))


def handler(event):
    input = event["input"]

    story = input["story"]
    id = input["id"]
    user_id = input["user_id"]

    with open('./story.json', 'w') as f:
        f.write(story)

    blend_proc = subprocess.run([BLENDER_BIN, "--background", "--python-exit-code", "1",
                                 "--python", "generate_scene.py", "--", "--library", "{}.blend".format(
                                     'common'),
                                "--story", './story.json', "--output", "{}/output.blend".format(asset_workspace)])

    if blend_proc.returncode != 0:
        print("error generating {}".format(id))
        raise Exception("error generating {}".format(id))

    blend_storage_key = "{}/{}.blend".format(user_id, id)

    upload_storage_object("blend-assets", blend_storage_key,
                          "{}/output.blend".format(asset_workspace), "application/blender", upsert=True)

    render_proc = subprocess.run([BLENDER_BIN, "--background", "{}/output.blend".format(asset_workspace), "--python-exit-code", "1",
                                  "--python", "render_story.py", "--",
                                  "--output", "{}/output.mp4".format(asset_workspace), "--preview"])

    if render_proc.returncode != 0:
        print("error rendering {}".format(id))
        raise Exception("error rendering {}".format(id))

    storage_key = "{}/{}.mp4".format(user_id, id)

    upload_storage_object("video-assets", storage_key,
                          "{}/output.mp4".format(asset_workspace), "video/mp4", upsert=True)

    return {"result": storage_key, "blend_file": blend_storage_key}


runpod.serverless.start({
    "handler": handler
})
