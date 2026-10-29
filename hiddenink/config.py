"""Every threshold lives here so it is easy to see (and to freeze before held-out testing).

FROZEN: these values were tuned on the main set (data/clean + data/manipulated) only.
The held-out set (data/heldout) was generated AFTER freezing and never used for tuning.
"""

# --- Visibility thresholds -------------------------------------------------
LOW_CONTRAST_RATIO = 1.5    # WCAG contrast below this = text blends into the background
TINY_FONT_PT = 2.0          # font size below this (points) = unreadable
OFF_PAGE_VISIBLE_FRAC = 0.5  # if less than this fraction of a span is on the page -> off-page
COVERED_INSIDE_FRAC = 0.8   # span must be this much inside a filled rectangle
ZERO_WIDTH_MIN = 3          # this many invisible Unicode chars in one span -> flag
ZERO_WIDTH_CHARS = "​‌‍⁠﻿"
METADATA_MAX_LEN = 150      # a metadata field longer than this is suspicious
METADATA_FIELDS = ("title", "author", "subject", "keywords", "comments")

# --- Intent thresholds -----------------------------------------------------
INTENT_THRESHOLD = 0.5      # classifier probability needed to call text an "instruction"
RULE_SCORE = 0.95           # score given when a regex rule matches
STUFFING_MIN_ITEMS = 6      # a hidden list of >= this many short items = keyword stuffing
STUFFING_MAX_WORDS_PER_ITEM = 3

# --- Risk scoring ----------------------------------------------------------
POINTS = {"instruction": 60, "keyword_stuffing": 30, "other": 15}
EXTRA_FINDING_WEIGHT = 0.25  # each additional finding adds this fraction of its points
MEDIUM_AT = 25
HIGH_AT = 60
