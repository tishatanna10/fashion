"""Body shape classification from bust, waist, and hip measurements."""


def calculate_body_type(
    bust: float | None, waist: float | None, hip: float | None
) -> str | None:
    """Classify centimetre measurements using published inch-based thresholds.

    Priority: hourglass (bust/hip within 1 inch and waist at least 9 inches
    smaller than both), pear (hips at least 3.6 inches larger than bust),
    inverted triangle (bust at least 3.6 inches larger than hips), apple
    (waist/hip >= 0.85 when bust and hip are not clearly imbalanced), then
    rectangle.
    """
    if bust is None or waist is None or hip is None:
        return None
    if bust <= 0 or waist <= 0 or hip <= 0:
        return None

    bust_in = bust / 2.54
    waist_in = waist / 2.54
    hip_in = hip / 2.54
    waist_to_hip = waist / hip

    if (
        abs(bust_in - hip_in) <= 1.0
        and bust_in - waist_in >= 9.0
        and hip_in - waist_in >= 9.0
    ):
        return "hourglass"
    if hip_in - bust_in >= 3.6:
        return "pear"
    if bust_in - hip_in >= 3.6:
        return "inverted triangle"
    if waist_to_hip >= 0.85:
        return "apple"
    return "rectangle"
