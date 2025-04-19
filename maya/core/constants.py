import pymel.core as pm

AXES = ["X", "Y", "Z"]
TRNSFRMATTRS = ["translate", "rotate", "scale"]
FROZENMTRX = [1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0]
ROTATEORDER = ["xyz", "yzx", "zxy", "xzy", "yxz", "zyx"]


def get_attr_suffix(attr):
    """
    Returns the naming convention suffix for a defined attribute
    :param attr: str: attribute being queried
    :return: str: the standardized suffix of the defined attribute
    """
    if attr == "translate":
        return "_pos"
    elif attr == "rotate":
        return "_rot"
    else:
        return "_sca"


def get_axis_index(axis):
    """
    Returns the index number of a given axis
    :param axis: str: the axis being queried
    :return: int: The integer of the defined axis
    """
    for i, a in enumerate(AXES):
        if a == axis.upper():
            return i
    return 0


def get_axis_matrix_range(axis):
    """
    Returns the index range of a given axis with a standard matrix
    :param axis: str: axis being queried
    :return: list: the start and end indices of the range of the defined axis
    """
    if axis.upper() == "Y":
        return [4, 7]
    elif axis.upper() == "Z":
        return [8, 11]
    else:
        return [0, 3]


def get_axis_vector(axis, invert=False):
    """
    Returns the up vector for a defined axis and inverts it if told to
    :param axis: str: The axis being queried
    :param invert: bool: whether or not to invert the returned vector
    :return: vec: The up vector of the defined wearable
    """
    vector = [0.0, 0.0, 0.0]
    vector[get_axis_index(axis)] = 1.0
    if invert:
        return [-v for v in vector]
    return vector


def get_constrain_attrs(const_type):
    """
    Returns a list of suffixes for the attribute being constrained by a defined constraint
    :param const_type: str: the type of constraint being queried
    :return: list: suffixes being constrained
    """
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
    """
    Returns the naming convention of a given integer in a given chain length
    :param i: int: point being queried
    :param chain_len: int: defined length of the chain the integer is being compared with
    :param base_tip: bool: returns the base/tip convention within a span
    :return: str: the naming convention of the defined span
    """
    if i == 0:
        span = ["upper", "base"]
    elif i == chain_len - 1:
        span = ["lower", "tip"]
    elif i == 1 and chain_len == 3:
        span = ["mid", "mid"]
    else:
        span = [f"mid{str(i).zfill(2)}", f"mid{str(i).zfill(2)}"]
    return span[base_tip]


def is_positive(n):
    """
    Returns if a given number is positive
    :param n: float: number being queried
    :return: bool: if that number is positive
    """
    if not n > 0:
        return False
    return True


def is_straight_line(vectors):
    """
    Determines if a series of vectors fall along a straight line
    :param vectors: list: vectors being queried
    :return: bool: if the vectors exist on a straight line
    """
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
