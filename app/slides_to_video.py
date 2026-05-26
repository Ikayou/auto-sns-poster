"""
カルーセルスライドPNG → スライドショーMP4 変換

output/carousel/slide_*.png を読み込み、
各スライドを一定秒数表示する動画を生成する。
生成後は既存の TikTok 動画投稿 API でそのまま投稿可能。

実行:
  python app/slides_to_video.py
"""

import os
import sys
from pathlib import Path

from moviepy.editor import ImageClip, concatenate_videoclips, AudioFileClip
from dotenv import load_dotenv

load_dotenv()

ROOT_DIR    = Path(__file__).parent.parent
CAROUSEL_DIR = ROOT_DIR / "output" / "carousel"
OUTPUT_PATH  = ROOT_DIR / "output" / "carousel_video.mp4"

# 1枚あたりの表示秒数（合計 = スライド枚数 × この値）
SECONDS_PER_SLIDE = float(os.getenv("SECONDS_PER_SLIDE", "8.0"))


def slides_to_video(
    slide_dir: Path = CAROUSEL_DIR,
    output_path: Path = OUTPUT_PATH,
    seconds_per_slide: float = SECONDS_PER_SLIDE,
    audio_path: Path | None = None,
) -> Path:
    slides = sorted(slide_dir.glob("slide_*.png"))
    if not slides:
        raise FileNotFoundError(f"スライドが見つかりません: {slide_dir}")

    print(f"🎬 {len(slides)} 枚のスライドを動画に変換中...")
    print(f"   1枚あたり {seconds_per_slide} 秒 / 合計 {len(slides) * seconds_per_slide:.1f} 秒")

    clips = [
        ImageClip(str(p)).set_duration(seconds_per_slide)
        for p in slides
    ]
    video = concatenate_videoclips(clips, method="compose")

    # BGM がある場合は合成（動画の長さに合わせてループ or トリム）
    if audio_path and Path(audio_path).exists():
        audio = AudioFileClip(str(audio_path))
        # 動画より長いBGMはトリム、短い場合はそのまま
        if audio.duration > video.duration:
            audio = audio.subclip(0, video.duration)
        video = video.set_audio(audio)
        print(f"   BGMを追加: {audio_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    video.write_videofile(
        str(output_path),
        fps=30,
        codec="libx264",
        audio_codec="aac",
    )

    print(f"✅ 動画を保存しました: {output_path}")
    return output_path


if __name__ == "__main__":
    result = slides_to_video(audio_path=None)
    print(f"\n次のステップ: python app/upload_to_tiktok_draft.py")
