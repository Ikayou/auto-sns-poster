import os
import json
import random
import textwrap
import base64
from openai import OpenAI
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import ImageClip, AudioFileClip

api_key = os.getenv("OPENAI_API_KEY")
print(f"🔑 現在読み込まれているAPIキーの下4桁: ...{api_key[-4:] if api_key else '見つかりません'}")
# 環境変数からOpenAIのAPIキーを読み込む
client = OpenAI(api_key=api_key)

def generate_daily_content():
    """1. AIで今日のバズる台本と画像プロンプト、キャプションを考える"""
    print("🤖 AIが今日の投稿内容とキャプションを考えています...")
    
    # 💡 Python側で今日のジャンルをランダムに1つ強制決定する
    genres = [
        "すぐに使える心理学の裏ワザ",
        "知らなきゃ損する生活の知恵 / ライフハック",
        "Z世代の最新あるある / 人間関係のリアル",
        "ちょっと怖い雑学 / 都市伝説",
        "明日誰かに話したくなる面白い科学の雑学"
    ]
    today_genre = random.choice(genres)
    print(f"🎯 今日の選ばれたジャンル: {today_genre}")

    # プロンプトの中に {today_genre} を埋め込む
    prompt = f"""
    あなたはZ世代のトレンドとSNSのアルゴリズムを完全に把握している、超一流のTikTokショート動画プロデューサーです。
    今日のTikTokで確実にバズる、視聴者が「え、まじ！？」「わかる！」と共感・驚愕するようなショート動画のコンテンツを生成してください。

    【本日の必須テーマ】
    必ず以下のジャンルでコンテンツを作成してください。
    ジャンル: {today_genre}

    【ルール】
    1. ナレーションは最初の2秒（1文目）で強烈な「フック（惹きつけ）」を作ること。
    2. キャプションには、視聴者が自分の意見や経験を思わずコメントしたくなるような「議論を生む質問」を入れること。
    3. 出力は必ず以下のJSON形式のみとし、余計な文章は一切含めないでください。

    {{
        "title": "目を引く短いタイトル(フックになる言葉。15文字以内)",
        "narration": "音声読み上げ用のテキスト。最初の1文で強烈に惹きつけ、中盤でしっかりオチ（意外な事実や共感できる結論）をつけ、最後は必ず視聴者に問いかける疑問形（「〜だよね？」「〜どう思う？」など『？』を使った文章）で締めくくること。全体で60〜100文字程度にまとめる。",
        "image_prompt": "背景画像の画像生成プロンプト(英語)。シネマティック、エモい雰囲気など。テキストや文字は含めない。",
        "caption": "視聴者に質問を投げかけ、コメント欄の熱量を上げる概要欄テキスト",
        "hashtags": ["#トレンド", "#タグ1", "#タグ2", "#タグ3", "#タグ4"]
    }}
    """
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    content = json.loads(response.choices[0].message.content)
    
    # JSONとして保存
    with open("assets/content.json", "w", encoding="utf-8") as f:
        json.dump(content, f, ensure_ascii=False, indent=2)
        
    return content

def generate_background_image(image_prompt: str, bg_path: str):
    """2. AIで背景画像を生成する"""
    print("🎨 AIが背景画像を描画しています...")

    # プロンプトの末尾に、TikTok向けのシネマティックな指定と「文字なし」の念押しを追加
    optimized_prompt = f"{image_prompt}, vertical 9:16 TikTok aesthetic background, cinematic lighting, ultra-detailed, completely empty with NO text and NO words."

    response = client.images.generate(
        model="gpt-image-1-mini",
        prompt=optimized_prompt,
        size="1024x1536",
        n=1,
    )

    image_b64 = response.data[0].b64_json

    if not image_b64:
        raise ValueError(f"画像データが返ってきませんでした: {response.data[0]}")

    img_data = base64.b64decode(image_b64)

    with open(bg_path, "wb") as handler:
        handler.write(img_data)

    return bg_path

def generate_audio(narration: str, audio_path: str):
    """3. AIでナレーション音声を生成する"""
    print("🗣️ AIがナレーションを録音しています...")
    response = client.audio.speech.create(
        model="tts-1",
        voice="nova", # nova: 説得力のある女性の声。トレンド系に相性抜群
        input=narration
    )
    response.write_to_file(audio_path)
    return audio_path

def add_text_to_image(bg_path, json_path, output_image_path):
    """4. TikTokのセーフゾーンに合わせて、字幕を中央揃えで焼き付ける"""
    with open(json_path, 'r', encoding='utf-8') as f:
        content = json.load(f)
    
    title = content.get("title", "タイトルなし")
    narration = content.get("narration", "テキストなし")

    img = Image.open(bg_path).convert("RGBA")
    draw = ImageDraw.Draw(img)
    
    # 画像の幅と高さを取得（中央揃えの計算用）
    W, H = img.size

    font_path = "assets/NotoSansJP-Bold.ttf" 
    if not os.path.exists(font_path):
        raise FileNotFoundError(f"フォントファイルが見つかりません。{font_path} に配置してください。")

    # フォントサイズを少し大きくしてインパクトを出す
    font_title = ImageFont.truetype(font_path, 80)  
    font_body = ImageFont.truetype(font_path, 55)   

    # 中央揃えで綺麗に表示されるように文字を改行（幅を調整）
    wrapped_title = textwrap.fill(title, width=12)
    wrapped_narration = textwrap.fill(narration, width=16)

    # 黒い太めの縁取り（Stroke）で、どんな背景色でも文字を読みやすくする
    stroke_width = 5
    stroke_color = "black"

    # --- タイトルの描画（画面上部 25% の位置） ---
    draw.multiline_text(
        (W / 2, H * 0.25), 
        wrapped_title, 
        font=font_title, 
        fill="#FFD700", # インパクトのあるゴールドイエロー
        stroke_width=stroke_width, 
        stroke_fill=stroke_color, 
        align="center",
        anchor="mm" # "mm" = 座標をテキストのド真ん中に合わせる設定
    )
    
    # --- ナレーションの描画（画面中央 55% の位置） ---
    draw.multiline_text(
        (W / 2, H * 0.55), 
        wrapped_narration, 
        font=font_body, 
        fill="white", 
        stroke_width=stroke_width, 
        stroke_fill=stroke_color, 
        align="center", 
        spacing=25, # 行間を広げて圧迫感をなくす
        anchor="mm"
    )

    # RGBに変換して保存
    img.convert("RGB").save(output_image_path)
    return output_image_path

def create_ai_video(image_path: str, audio_path: str, output_path: str):
    """5. 画像と音声を合成し、音声の長さに合わせた動画を書き出す"""
    print("🎬 最終動画をレンダリングしています...")
    audio_clip = AudioFileClip(audio_path)
    
    video_clip = ImageClip(image_path).set_duration(audio_clip.duration)
    video_clip = video_clip.set_audio(audio_clip)
    
    video_clip.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac"
    )
    print(f"✨ 完了！AI完全自動生成動画: {output_path}")

if __name__ == "__main__":
    os.makedirs("assets", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    input_bg = "assets/background.png"
    input_json = "assets/content.json"
    audio_file = "assets/audio.mp3"
    annotated_bg = "assets/annotated_background.png" 
    output_video = "output/reels.mp4"
    
    # ==========================================
    # 🚀 完全自動化プロセス
    # ==========================================
    content = generate_daily_content()
    generate_background_image(content["image_prompt"], input_bg)
    generate_audio(content["narration"], audio_file)
    
    print("📝 画像に字幕を合成しています...")
    add_text_to_image(input_bg, input_json, annotated_bg)
    
    create_ai_video(annotated_bg, audio_file, output_video)