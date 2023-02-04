def fly_in(obj, asset_start_frame, asset_end_frame):
    point = obj.location
    outside_point = point + (point.normalized() * 20)

    obj.location = outside_point
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=asset_start_frame - 11)
    obj.hide_render = False
    obj.keyframe_insert("location", frame=asset_start_frame - 10)
    obj.keyframe_insert("hide_render", frame=asset_start_frame - 10)

    obj.location = point
    obj.keyframe_insert("location", frame=asset_start_frame)
    obj.keyframe_insert("location", frame=asset_end_frame)

    obj.location = outside_point
    obj.keyframe_insert("location", frame=asset_end_frame + 10)
    obj.keyframe_insert("hide_render", frame=asset_end_frame + 10)
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=asset_end_frame + 11)


def scale_up(obj, asset_start_frame, asset_end_frame):
    original_scale = (obj.scale.x, obj.scale.y, obj.scale.z)

    obj.scale = (0.01, 0.01, 0.01)
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=asset_start_frame - 21)
    obj.hide_render = False
    obj.keyframe_insert("scale", frame=asset_start_frame - 20)
    obj.keyframe_insert("hide_render", frame=asset_start_frame - 20)

    obj.scale = original_scale
    obj.keyframe_insert("scale", frame=asset_start_frame)
    obj.keyframe_insert("scale", frame=asset_end_frame)

    obj.scale = (0.01, 0.01, 0.01)
    obj.keyframe_insert("scale", frame=asset_end_frame + 10)
    obj.keyframe_insert("hide_render", frame=asset_end_frame + 10)
    obj.hide_render = True
    obj.keyframe_insert("hide_render", frame=asset_end_frame + 11)

    # make the scale in/out fcurves elastic interpolated
    for fcurve in obj.animation_data.action.fcurves:
        if fcurve.data_path == 'scale':
            for i, keyframe in enumerate(fcurve.keyframe_points):
                if i == 0:
                    # elastic interpolation
                    keyframe.interpolation = 'BOUNCE'
