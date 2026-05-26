"""
Canva カルーセルパイプライン — コンテンツ生成フェーズ

このスクリプトは:
  1. RSS から記事を取得
  2. GPT-4o-mini でカルーセルコンテンツ(JSON)を生成
  3. assets/carousel_content.json に保存

スライド画像の生成は Claude Code の /make-canva-slides コマンドで行う:
  → Claude Code を開いて  /make-canva-slides  と入力するだけ

使用テンプレートID（Canva）:
  タイトル  : DAHKwLcEEmA
  コンテンツ: DAHKwGZP6uw
  CTA      : DAHKwHaO_so
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from app.fetch_content import fetch_articles
from app.create_carousel import generate_carousel_content

load_dotenv()

ROOT_DIR   = Path(__file__).parent.parent
ASSETS_DIR = ROOT_DIR / "assets"
OUTPUT_DIR = ROOT_DIR / "output" / "carousel"


def run() -> dict:
    print("📰 RSSフィードから記事を取得中...")
    articles = fetch_articles()

    print("\n🤖 AIがカルーセルコンテンツを生成中...")
    content = generate_carousel_content(articles)

    ASSETS_DIR.mkdir(exist_ok=True)
    content_path = ASSETS_DIR / "carousel_content.json"
    with open(content_path, "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)

    print("\n--- 生成されたコンテンツ ---")
    print(json.dumps(content, ensure_ascii=False, indent=2))
    print(f"\n✅ {content_path} に保存しました")

    slides_count = len(content["slides"]) + 2  # タイトル + コンテンツ + CTA
    print(f"\n🎨 次のステップ: Claude Code で以下を実行してください")
    print(f"   /make-canva-slides")
    print(f"   → Canvaで {slides_count} 枚のスライドを自動生成して output/carousel/ に保存します")

    return content


if __name__ == "__main__":
    run()
