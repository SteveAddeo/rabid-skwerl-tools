AXES = ["X", "Y", "Z"]


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
    vectorList = [0, 0, 0]
    vectorList[get_axis_index(axis)] = 1
    return vectorList


def is_positive(n):
    if not n > 0:
        return False
    return True
