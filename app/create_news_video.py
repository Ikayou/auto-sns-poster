import os
import feedparser
from openai import OpenAI
from gtts import gTTS
from moviepy.editor import *
from dotenv import load_dotenv

# .env から APIキー を読み込む
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_top_news():
    """RSSからニュース見出しを3つ取得する"""
    print("🔄 ニュースを取得中...")
    feed = feedparser.parse("https://www.heise.de/newsticker/heise-atom.xml")
    return [entry.title for entry in feed.entries[:3]]

def generate_script(news_titles):
    """OpenAIでTikTok用の30秒台本を作成する"""
    print("🤖 OpenAIに台本を作らせています...")
    prompt = f"""
    以下の3つのドイツのテックニュースを元に、TikTok用のショート動画の台本を作成してください。
    条件：
    - 挨拶から始まり、3つのニュースをテンポよく紹介すること。
    - 全部で30秒以内（約150〜180文字）で読み切れる長さにすること。
    - 視聴者の興味を引くキャッチーで自然な日本語にすること。
    - 出力は【読み上げる音声用テキスト】のみ（余計な記号や「台本：」などの前置きは絶対に入れない）。

    ニュース:
    1. {news_titles[0]}
    2. {news_titles[1]}
    3. {news_titles[2]}
    """
    
    # 安くて速い gpt-4o-mini モデルを使用
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def create_video():
    # 1. ニュース取得と要約
    news_titles = get_top_news()
    script_text = generate_script(news_titles)
    print(f"\n📝 完成した台本:\n{script_text}\n")

    # 2. 音声の生成 (gTTS)
    print("🗣️ 音声を生成中...")
    audio_path = "news_audio.mp3"
    tts = gTTS(text=script_text, lang='ja', slow=False)
    tts.save(audio_path)

    # 3. 動画の生成 (MoviePy)
    print("🎬 動画を合成中...")
    audio_clip = AudioFileClip(audio_path)
    duration = audio_clip.duration

    # 背景（とりあえずシンプルなダークグレーの縦長動画）
    bg_clip = ColorClip(size=(720, 1280), color=(30, 30, 30)).set_duration(duration)

    # テロップ（今回はシンプルに画面中央に「今日のテックニュース」と表示）
    # ※本格的に一言ずつ文字起こしを連動させるのは少しコードが長くなるため、まずは固定テロップで作ります
    txt_clip = TextClip(
        "今日の最新\nテックニュース！\n\n音声でお楽しみください🎧", 
        fontsize=60, 
        color='white',
        font='Noto-Sans-CJK-JP', # 日本語フォントを指定
        size=(600, None), 
        method='caption'
    ).set_position('center').set_duration(duration)

    # 背景、テロップ、音声をガッチャンコする
    final_video = CompositeVideoClip([bg_clip, txt_clip]).set_audio(audio_clip)

    # MP4として書き出し
    output_path = "tiktok_news.mp4"
    final_video.write_videofile(output_path, fps=24, codec="libx264", audio_codec="aac")
    print(f"✨ 動画が完成しました: {output_path}")

if __name__ == "__main__":
    create_video()