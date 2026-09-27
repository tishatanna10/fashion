"""Image analysis helpers for wardrobe uploads."""

from logging import getLogger
from pathlib import Path
from threading import Lock
from time import perf_counter

import matplotlib.colors as mpl_colors
import numpy as np
import torch
from PIL import Image
from rembg import new_session, remove
from rembg.sessions.bria_rmbg import BriaRmBgSession
from transformers import AutoModelForZeroShotImageClassification, AutoProcessor


logger = getLogger(__name__)
_rembg_session = None
_rembg_session_lock = Lock()


def initialize_background_removal():
    """Load the rembg ONNX session once, preferably during FastAPI startup."""
    global _rembg_session
    if _rembg_session is not None:
        return _rembg_session

    with _rembg_session_lock:
        if _rembg_session is not None:
            return _rembg_session

        model_path = Path(BriaRmBgSession.model_dir()) / "bria-rmbg.onnx"
        start = perf_counter()
        if model_path.is_file():
            logger.info(
                "Loading cached rembg bria-rmbg model from %s (%d MB)",
                model_path,
                model_path.stat().st_size // (1024 * 1024),
            )
        else:
            logger.info(
                "rembg bria-rmbg model is missing at %s; downloading it during startup. "
                "The rembg/pooch progress bar will show download progress.",
                model_path,
            )
        try:
            _rembg_session = new_session("bria-rmbg")
        except Exception:
            logger.exception(
                "Failed to initialize rembg bria-rmbg after %.2f seconds",
                perf_counter() - start,
            )
            raise
        logger.info(
            "rembg bria-rmbg session ready in %.2f seconds",
            perf_counter() - start,
        )
        return _rembg_session


def _log_stage_time(stage: str, started_at: float) -> None:
    logger.info("wardrobe analysis stage=%s elapsed_s=%.2f", stage, perf_counter() - started_at)

# Specific item labels are grouped only to populate the existing broad category
# column. CLIP still compares against every specific item prompt.
CATEGORY_GROUPS = {
    "top": [
        "t-shirt", "polo shirt", "henley", "button-down shirt", "dress shirt",
        "blouse", "tank top", "camisole", "tube top", "crop top", "halter top",
        "peplum top", "tunic", "sweater", "cardigan", "hoodie", "sweatshirt",
        "turtleneck", "vest", "bodysuit", "corset top", "jersey", "thermal top",
        "wrap top", "off-shoulder top", "one-shoulder top", "long-sleeve shirt",
        "short-sleeve shirt", "flannel shirt", "baseball shirt", "scrub top",
    ],
    "bottom": [
        "jeans", "trousers", "dress pants", "chinos", "cargo pants", "joggers",
        "leggings", "shorts", "bermuda shorts", "bike shorts", "sweatpants",
        "track pants", "wide-leg pants", "culottes", "capri pants", "palazzo pants",
        "skirt", "mini skirt", "midi skirt", "maxi skirt", "pencil skirt",
        "pleated skirt", "denim skirt", "short skirt", "A-line skirt",
        "tights", "bicycle tights", "swim trunks", "board shorts",
    ],
    "dress": [
        "dress", "sundress", "maxi dress", "midi dress", "mini dress", "shirt dress",
        "wrap dress", "cocktail dress", "evening gown", "wedding dress", "slip dress",
        "bodycon dress", "sweater dress", "little black dress", "shift dress",
        "A-line dress", "formal gown", "kaftan dress", "tunic dress",
    ],
    "outerwear": [
        "jacket", "blazer", "suit jacket", "denim jacket", "leather jacket",
        "bomber jacket", "puffer jacket", "windbreaker", "rain jacket", "coat",
        "trench coat", "overcoat", "peacoat", "parka", "duffle coat", "fleece jacket",
        "vest jacket", "gilet", "kimono", "poncho", "cape", "shacket", "biker jacket",
        "varsity jacket", "anorak", "quilted jacket", "down coat", "raincoat",
    ],
    "shoes": [
        "sneakers", "running shoes", "trainers", "basketball shoes", "heels", "pumps",
        "flats", "ballet flats", "sandals", "flip-flops", "slides", "boots",
        "ankle boots", "knee-high boots", "Chelsea boots", "combat boots", "cowboy boots",
        "loafers", "oxford shoes", "derby shoes", "dress shoes", "mules", "clogs",
        "espadrilles", "wedges", "platform shoes", "hiking boots", "rain boots",
        "slippers", "slingback shoes", "mary jane shoes", "high-top sneakers",
    ],
    "accessory": [
        "bag", "tote bag", "backpack", "clutch", "handbag", "shoulder bag", "crossbody bag",
        "duffel bag", "messenger bag", "satchel", "wallet", "purse", "hat", "cap",
        "beanie", "sunhat", "bucket hat", "beret", "fedora", "visor", "jewellery",
        "necklace", "earrings", "bracelet", "ring", "brooch", "scarf", "belt",
        "sunglasses", "eyeglasses", "tie", "bow tie", "watch", "socks", "gloves",
        "mittens", "hairband", "hair clip", "headband", "bandana", "shawl", "pocket square",
        "suspenders", "umbrella", "keychain", "anklet", "cufflinks", "face mask",
    ],
}
CATEGORY_TYPES = [item for group in CATEGORY_GROUPS.values() for item in group]

STYLE_LABELS = [
    "casual", "formal", "business casual", "business formal", "athletic", "athleisure",
    "streetwear", "bohemian", "elegant", "edgy", "minimalist", "romantic", "preppy",
    "vintage", "retro", "grunge", "punk", "gothic", "Y2K", "cottagecore",
    "coastal grandma", "old money", "dark academia", "light academia", "indie", "hipster",
    "glam", "chic", "classic", "artsy", "avant-garde", "tomboy", "girly", "western",
    "tropical", "resort wear", "festival", "cyberpunk", "techwear", "normcore",
    "maximalist", "cozy loungewear", "quiet luxury", "street style", "skater", "surfer",
    "biker", "military", "utility", "workwear", "heritage", "preppy sporty",
    "French girl", "Parisian chic", "Italian chic", "Scandinavian", "Japanese streetwear",
    "Korean streetwear", "Harajuku", "Lolita", "whimsigoth", "fairycore",
    "dark romantic", "coquette", "balletcore", "royalcore", "regencycore", "grandpacore",
    "blokecore", "gorpcore",
    "clean girl", "mob wife", "office siren", "indie sleaze", "scene", "emo", "rocker",
    "glam rock", "boho chic", "Southwestern", "safari", "nautical", "preppy classic",
    "mod", "1960s mod", "1970s retro", "1980s power dressing", "1990s minimalism",
    "2000s pop", "pin-up", "rockabilly", "art deco", "new romantic", "swing",
    "carnival", "beachwear", "vacation", "urban", "contemporary", "eclectic", "understated",
    "refined classic", "soft girl", "e-girl", "e-boy", "dark alternative", "rom-com",
    "craftcore", "upcycled", "sustainable fashion", "deconstructed", "architectural",
    "avant garde", "gender-neutral", "androgynous", "masculine", "feminine", "modest",
    "monochrome", "colorful", "preppy collegiate", "equestrian", "tenniscore", "pilates style",
    "dancewear", "uniform-inspired", "romantic vintage", "bohemian festival", "coastal chic",
    "desert western", "tropical resort", "mountain outdoors", "techwear utility", "quiet luxury",
    "red carpet", "black tie", "cocktail", "smart casual", "relaxed tailoring", "street punk",
    "post-punk", "gothic romantic", "Victorian", "Edwardian", "medieval", "steampunk",
    "space age", "futuristic", "minimal streetwear", "luxury sportswear", "loungewear",
    "sleepwear", "functional", "rugged", "soft grunge", "dark grunge", "romantic goth",
    "pastel goth", "cyber goth", "neo-classical", "quiet outdoors", "urban prep",
]
STYLE_LABELS = list(dict.fromkeys(STYLE_LABELS))

PATTERN_LABELS = ["solid", "striped", "printed", "checked", "floral"]

# CSS4 provides 148 standardized named colours with their reference hex/RGB
# values. The parent taxonomy keeps those precise names useful in the app.
COLOUR_RGB = {
    name.lower(): tuple(round(channel * 255) for channel in mpl_colors.to_rgb(hex_value))
    for name, hex_value in mpl_colors.CSS4_COLORS.items()
}
COLOUR_PARENTS = {
    "black", "white", "grey", "silver", "brown", "beige", "red", "orange",
    "yellow", "green", "teal", "cyan", "blue", "navy", "purple", "magenta",
    "pink", "maroon", "olive", "gold",
}


def _colour_parent(name: str, rgb: tuple[int, int, int]) -> str:
    if name in COLOUR_PARENTS:
        return name
    red, green, blue = (channel / 255 for channel in rgb)
    high, low = max(red, green, blue), min(red, green, blue)
    saturation = 0 if high == 0 else (high - low) / high
    if high < 0.15:
        return "black"
    if low > 0.88 and saturation < 0.14:
        return "white"
    if saturation < 0.16:
        return "grey"
    # rgb_to_hsv returns (hue, saturation, value); take its hue component.
    # The previous [0] indexed the red channel, which sent warm colours into
    # unrelated hue ranges (including teal/green).
    hue = float(mpl_colors.rgb_to_hsv(np.array(rgb, dtype=float) / 255.0)[0]) * 360
    if 5 <= hue < 45 and high < 0.65:
        return "brown"
    if hue < 12 or hue >= 345:
        return "red"
    if hue < 38:
        return "orange"
    if hue < 68:
        return "yellow"
    if hue < 155:
        return "green"
    if hue < 190:
        return "teal"
    if hue < 205:
        return "cyan"
    if hue < 255:
        return "blue"
    if hue < 285:
        return "purple"
    if hue < 320:
        return "magenta"
    return "pink"


COLOUR_PARENT_MAP = {
    name: _colour_parent(name, rgb) for name, rgb in COLOUR_RGB.items()
}

# Load FashionCLIP once. Its Hugging Face model card provides a Transformers
# zero-shot image classification model and processor for this checkpoint.
_device = "cuda" if torch.cuda.is_available() else "cpu"
_model_id = "patrickjohncyh/fashion-clip"
_model = AutoModelForZeroShotImageClassification.from_pretrained(_model_id)
_model = _model.to(_device).eval()
_processor = AutoProcessor.from_pretrained(_model_id)


def _classify(
    image: Image.Image,
    labels: list[str],
    prompt_template: str,
    top_k: int = 1,
    minimum_confidence: float | None = None,
) -> tuple[str, float, list[dict[str, float | str]]]:
    prompts = [prompt_template.format(label=label) for label in labels]
    inputs = _processor(
        text=prompts, images=image.convert("RGB"), return_tensors="pt", padding=True
    ).to(_device)
    with torch.inference_mode():
        probabilities = _model(**inputs).logits_per_image.softmax(dim=-1)[0]
    scores, indices = probabilities.topk(min(top_k, len(labels)))
    candidates = [
        {"label": labels[int(index)], "score": float(score)}
        for score, index in zip(scores.tolist(), indices.tolist())
    ]
    best_label = candidates[0]["label"]
    best_score = candidates[0]["score"]
    # A softmax score over 187+ category labels is naturally small. Decide
    # uncertainty from separation between candidates instead of an absolute
    # probability cutoff that those large label sets cannot meet.
    second_score = candidates[1]["score"] if len(candidates) > 1 else 0.0
    is_confident = (
        best_score >= minimum_confidence
        if minimum_confidence is not None
        else best_score >= second_score * 1.15
    )
    return (best_label if is_confident else "uncertain", best_score, candidates)


def _dominant_colour(image: Image.Image) -> tuple[str, str]:
    if not isinstance(image, Image.Image):
        image = Image.fromarray(np.asarray(image))
    # rembg returns PNG bytes (or a PIL image), so decoding with Pillow gives
    # RGBA in RGB channel order; keep the first three channels as RGB.
    rgba = np.asarray(image.convert("RGBA"))
    logger.info("Colour detection image array shape: %s", rgba.shape)
    pixels = rgba[rgba[:, :, 3] > 0, :3]
    if pixels.size == 0:
        raise ValueError("Background removal produced no visible pixels")
    if len(pixels) > 10_000:
        indices = np.linspace(0, len(pixels) - 1, 10_000, dtype=int)
        pixels = pixels[indices]

    bins = pixels.astype(np.int32) // 16
    bin_ids = bins[:, 0] * 256 + bins[:, 1] * 16 + bins[:, 2]
    counts = np.bincount(bin_ids, minlength=4096)
    dominant_pixels = pixels[bin_ids == int(counts.argmax())]
    rgb = dominant_pixels.mean(axis=0)
    detailed = min(
        COLOUR_RGB,
        key=lambda name: sum((float(rgb[i]) - COLOUR_RGB[name][i]) ** 2 for i in range(3)),
    )
    parent = _colour_parent(detailed, tuple(int(round(channel)) for channel in rgb))
    # Very dark brown fabric can be closer in raw RGB distance to a CSS gray
    # swatch; retain the useful brown name when its measured hue is brown.
    if parent == "brown" and detailed not in COLOUR_PARENTS:
        detailed = "brown"
    return parent, detailed


def analyze_clothing_image(image_path: str) -> dict:
    """Remove an image background and predict clothing attributes with CLIP."""
    analysis_started_at = perf_counter()
    original_path = Path(image_path)
    cleaned_path = original_path.with_name(f"{original_path.stem}_nobg.png")
    stage_started_at = perf_counter()
    with original_path.open("rb") as image_file:
        cleaned = remove(image_file.read(), session=initialize_background_removal())
    if isinstance(cleaned, Image.Image):
        cleaned_image = cleaned.convert("RGBA")
    else:
        from io import BytesIO

        cleaned_image = Image.open(BytesIO(cleaned)).convert("RGBA")
    cleaned_image.save(cleaned_path, format="PNG")
    _log_stage_time("background_removal", stage_started_at)

    stage_started_at = perf_counter()
    specific_type, category_confidence, category_candidates = _classify(
        cleaned_image,
        CATEGORY_TYPES,
        "a clear product photo of a {label} clothing or fashion accessory",
        top_k=3,
    )
    _log_stage_time("category_classification", stage_started_at)
    broad_category = next(
        (group for group, items in CATEGORY_GROUPS.items() if specific_type in items),
        "uncertain",
    )
    if specific_type == "uncertain":
        broad_category = "uncertain"
        specific_type = "uncertain"

    stage_started_at = perf_counter()
    style, style_confidence, style_candidates = _classify(
        cleaned_image,
        STYLE_LABELS,
        "a person wearing an outfit in the {label} fashion aesthetic",
        top_k=3,
        minimum_confidence=0.65,
    )
    _log_stage_time("style_classification", stage_started_at)
    stage_started_at = perf_counter()
    pattern, pattern_confidence, _ = _classify(
        cleaned_image,
        PATTERN_LABELS,
        "a photo of a clothing item with a {label} pattern",
    )
    _log_stage_time("pattern_classification", stage_started_at)
    stage_started_at = perf_counter()
    colour, colour_detailed = _dominant_colour(cleaned_image)
    _log_stage_time("colour_detection", stage_started_at)
    _log_stage_time("total_analysis", analysis_started_at)

    return {
        "category": broad_category,
        "subcategory": specific_type,
        "style": style,
        "pattern": pattern,
        "colour": colour,
        "colour_detailed": colour_detailed,
        "confidence": {
            "category": category_confidence,
            "style": style_confidence,
            "pattern": pattern_confidence,
        },
        "category_candidates": category_candidates,
        "style_candidates": style_candidates,
    }
