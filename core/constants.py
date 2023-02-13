import pymel.core as pm

AXES = ["X", "Y", "Z"]
TRNSFRMATTRS = ["translate", "rotate", "scale"]
FROZENMTRX = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
ROTATEORDER = ["xyz", "yzx", "zxy", "xzy", "yxz", "zyx"]


def get_axis_index(axis):
    for i, a in enumerate(AXES):
        if a == axis.upper():
            return i
    return 0


def get_axis_matrix_range(axis):
    if axis.upper() == "Y":
        return [4, 7]
    elif axis.upper() == "Z":
        return [8, 11]
    else:
        return [0, 3]


def get_axis_vector(axis, invert=False):
    vector_list = [0.0, 0.0, 0.0]
    vector_list[get_axis_index(axis)] = 1.0
    if invert:
        return [-vector for vector in vector_list]
    return vector_list


def get_constrain_attrs(const_type):
    if const_type == "parent":
        attrs = ["_pos", "_rot"]
    elif const_type == "point":
        attrs = ["_pos"]
    elif const_type == "orient":
        attrs = ["_rot"]
    elif const_type == "scale":
        attrs = ["_scl"]
    else:
        attrs = ["_pos", "_rot", "_scl"]
    return attrs


def get_span(i, chain_len, base_tip=0):
    if i == 0:
        span = ["upper", "base"]
    elif i == chain_len - 1:
        span = ["lower", "tip"]
    elif i == 1 and chain_len == 3:
        span = ["mid", "mid"]
    else:
        span = [f"mid{str(i + 1).zfill(2)}", f"mid{str(i + 1).zfill(2)}"]
    return span[base_tip]


def get_vector_from_axis(axis="X", mirror=False):
    vector = get_axis_vector(axis)
    if mirror:
        vector = [-v for v in vector]
    return vector


def is_positive(n):
    if not n > 0:
        return False
    return True


def is_straight_line(vectors):
    if len(vectors) < 3 or [v for v in vectors if type(v) != list]:
        pm.warning("Three vectors are needed to properly calculate. Function returns True")
        return True
    ab_len = round(((vectors[0][0] - vectors[1][0]) ** 2 + (vectors[0][1] - vectors[1][1]) ** 2 + (
                vectors[0][2] - vectors[1][2]) ** 2) ** 0.5, 3)
    bc_len = round(((vectors[1][0] - vectors[2][0]) ** 2 + (vectors[1][1] - vectors[2][1]) ** 2 + (
                vectors[1][2] - vectors[2][2]) ** 2) ** 0.5, 3)
    ac_len = round(((vectors[0][0] - vectors[2][0]) ** 2 + (vectors[0][1] - vectors[2][1]) ** 2 + (
                vectors[0][2] - vectors[2][2]) ** 2) ** 0.5, 3)
    if ac_len < ab_len + bc_len:
        return False
    return True
