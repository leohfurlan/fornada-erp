def edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        diagonal = previous[0]
        previous[0] = row
        for column, right_char in enumerate(right, start=1):
            above = previous[column]
            previous[column] = min(
                previous[column] + 1,
                previous[column - 1] + 1,
                diagonal + (left_char != right_char),
            )
            diagonal = above
    return previous[-1]
