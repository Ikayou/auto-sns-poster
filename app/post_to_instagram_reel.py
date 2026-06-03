"""
Backward-compatible entry point.

Instagram posting now uses PNG slides as a carousel instead of publishing the
generated MP4.

Run:
  python app/post_to_instagram_reel.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.post_to_instagram_carousel import post_instagram_carousel


if __name__ == "__main__":
    post_instagram_carousel()
