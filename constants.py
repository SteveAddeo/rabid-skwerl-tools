VECTORS = ["X", "Y", "Z"]


def get_vector_matrix_range(vector):
    if vector.upper() == "Y":
        return [4, 7]
    elif vector.upper() == "Z":
        return [8, 11]
    else:
        return [0, 3]


def get_vector_index(vector):
    for i, v in enumerate(VECTORS):
        if v == vector.upper():
            return i
    return 0


def is_positive(n):
    if not n > 0:
        return False
    return True
