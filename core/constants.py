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


def get_axis_vector(axis):
    vectorList = [0.0, 0.0, 0.0]
    vectorList[get_axis_index(axis)] = 1.0
    return vectorList


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
    elif i == chain_len + 1:
        span = ["lower", "tip"]
    elif i == 1 and chain_len == 3:
        span = ["mid", "mid"]
    else:
        span = [f"mid{str(i + 1).zfill(2)}_", f"mid{str(i + 1).zfill(2)}_"]
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
