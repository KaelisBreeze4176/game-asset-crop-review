import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.game_assets import ModerationItem, enqueue_for_review


def test_review_queue_keeps_only_materialized_variants():
    items = [
        ModerationItem("a1", "1:1", "variant-1"),
        ModerationItem("a1", "16:9", ""),
        ModerationItem("a1", "9:16", "variant-3"),
    ]
    queued = enqueue_for_review(items)
    assert [item.aspect for item in queued] == ["1:1", "9:16"]
