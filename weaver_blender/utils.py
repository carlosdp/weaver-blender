import math
from mathutils import geometry, Vector


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
