import os
import json
import requests
from dotenv import load_dotenv
from openai import OpenAI

# .envファイルから環境変数を読み込む
load_dotenv()

# OpenAIクライアントの初期化（APIキーは自動で読み込まれます）
client = OpenAI()

def generate_script_and_prompts(topic: str) -> dict:
    """
    GPT-4o-miniを使って、動画の台本と画像生成用プロンプトを生成する
    """
    system_prompt = """あなたはTikTokやInstagramリール向けの優秀なショート動画プロデューサーです。
    指定されたテーマで、15秒程度の動画の台本（ナレーション）と、
    その動画の背景として使う縦型画像の生成プロンプト（英語）を作成してください。
    必ず以下のキーを持つJSON形式で出力してください。
    - title: 動画のタイトル
    - narration: ナレーションのテキスト
    - image_prompt: 背景画像の生成プロンプト（英語で詳細に記述。例: "A futuristic server room with glowing blue lights..."）
    """

    user_prompt = f"テーマ: {topic}"

    # JSON形式での出力を強制（response_formatを使用）
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    )
    
    # 返ってきたJSON文字列をPythonの辞書に変換
    return json.loads(response.choices[0].message.content)

def generate_and_download_image(prompt: str, save_path: str):
    """
    DALL-Eの権限反映待ちのため、一時的にフリー画像APIからダミーの縦長画像を取得する
    """
    print(f"※ DALL-Eの代わりにダミー画像を取得します...")
    
    # 高画質なランダム画像を取得できる開発者用API（Lorem Picsum）
    # DALL-E 3と同じ 1024x1792 の縦長サイズを指定
    image_url = "https://picsum.photos/1024/1792"
    
    # 画像データをダウンロード
    response = requests.get(image_url)
    img_data = response.content
    
    # ファイルに書き込む
    with open(save_path, 'wb') as handler:
        handler.write(img_data)
        
    return save_path

if __name__ == "__main__":
    # assetsディレクトリが存在しない場合は作成
    os.makedirs("assets", exist_ok=True)

    # 1. テーマを決めてAIに台本を生成させる
    # ※ここはITインフラエンジニアらしく、技術系のテーマにしています！
    target_topic = "Dockerとコンテナ技術の超基礎"
    
    print(f"1. 「{target_topic}」の台本と画像プロンプトを生成中...")
    content_data = generate_script_and_prompts(target_topic)
    
    print("\n--- 生成されたデータ ---")
    print(json.dumps(content_data, ensure_ascii=False, indent=2))
    
    # 次の動画生成ステップ(create_video.py)で使い回せるようにJSONとして保存しておく
    with open("assets/content.json", "w", encoding="utf-8") as f:
        json.dump(content_data, f, ensure_ascii=False, indent=2)
    
    # 2. 生成された英語プロンプトを使って背景画像を生成
    print("\n2. 背景画像を生成中... (DALL-E 3)")
    image_file_path = "assets/background.png"
    generate_and_download_image(content_data["image_prompt"], image_file_path)
    
    print(f"\n完了！画像を保存しました: {image_file_path}")