import os
import sys  # 💡 追加：ターミナルからのコマンドを受け取るための標準ライブラリ
import requests
from dotenv import load_dotenv

load_dotenv()

# TikTokアプリの認証情報
CLIENT_KEY = os.getenv("TIKTOK_CLIENT_KEY")
CLIENT_SECRET = os.getenv("TIKTOK_CLIENT_SECRET")
TIKTOK_ACCESS_TOKEN = os.getenv("TIKTOK_ACCESS_TOKEN", "YOUR_TEST_TOKEN")

def init_video_upload(video_path: str, caption: str):
    """
    ステップ1: TikTokのサーバーに『今からこのサイズの動画を投げるよ』と宣言し、
    アップロード用の専用URL（Upload URL）を発行してもらう
    """
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"
    
    headers = {
        "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
        "Content-Type": "application/json; charset=UTF-8"
    }
    
    video_size = os.path.getsize(video_path)
    
    payload = {
        "post_info": {
            "title": caption,
            "privacy_level": "SELF_ONLY", # 未審査アプリはSELF_ONLY必須
            "video_cover_timestamp_ms": 1000
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": video_size,
            "total_chunk_count": 1
        }
    }
    
    print(f"🚀 [TikTok] 動画アップロードの初期化リクエストを送信中... ({video_path})")
    response = requests.post(url, headers=headers, json=payload)
    res_data = response.json()
    
    if response.status_code != 200 or res_data.get("error", {}).get("code") != "ok":
        print(f"❌ 初期化に失敗しました。トークンが未設定か無効です。")
        print(f"レスポンス: {res_data}")
        return None
        
    return res_data.get("data", {}).get("upload_url")

def upload_video_binary(upload_url: str, video_path: str):
    """
    ステップ2: 発行されたUpload URLに対して、ローカルのMP4ファイルを
    丸ごとバイナリデータとして直接流し込む
    """
    print("📤 [TikTok] 動画バイナリを直接アップロード中...")
    video_size = os.path.getsize(video_path)
    
    headers = {
        "Content-Type": "video/mp4",
        "Content-Length": str(video_size),
        "Content-Range": f"bytes 0-{video_size - 1}/{video_size}"
    }
    
    with open(video_path, "rb") as f:
        response = requests.put(upload_url, headers=headers, data=f)
        
    if response.status_code in [200, 201]:
        print("🎉 TikTokへの直接アップロードに成功しました！スマホアプリの『下書き』または『自分のみ公開』を確認してください。")
    else:
        print(f"❌ バイナリ送信でエラーが発生しました。ステータスコード: {response.status_code}")

if __name__ == "__main__":
    # ==========================================
    # 💡 変更点: ターミナルからの引数（指示）を受け取る
    # ==========================================
    
    # 引数が足りない（ファイル名やテキストが指定されていない）場合は使い方を教えて終了する
    if len(sys.argv) < 3:
        print("❌ エラー: 引数が足りません。")
        print("💡 使い方: python app/post_to_tiktok.py <動画ファイル名> <キャプション>")
        print("例: python app/post_to_tiktok.py tiktok_news.mp4 \"最新ニュース！ #IT\"")
        sys.exit(1)
        
    # sys.argv[1] が動画ファイル名、sys.argv[2] がキャプション
    video_file = sys.argv[1]
    text_caption = sys.argv[2]
    
    print(f"📁 ターゲット動画: {video_file}")
    print(f"📄 投稿テキスト: \n{text_caption}\n")
    
    if not os.path.exists(video_file):
        print(f"❌ エラー: {video_file} が見つかりません。")
    else:
        # トークンがまだテスト用のデフォルトの場合は、まず認証用URLを案内する
        if TIKTOK_ACCESS_TOKEN == "YOUR_TEST_TOKEN":
            print("🔒 [要認証] まだプログラム用の『鍵（Access Token）』が設定されていません。")
            print("以下のURLをご自身のブラウザで開き、アカウント連携を許可してトークンを取得してください：")
            
            redirect_uri = "https://ikayou.github.io/tiktok-api-legal/"
            auth_url = f"https://www.tiktok.com/v2/auth/authorize/?client_key={CLIENT_KEY}&scope=user.info.basic,video.publish,video.upload&response_type=code&redirect_uri={redirect_uri}"
            print(f"\n👉 {auth_url}\n")
        else:
            upload_url = init_video_upload(video_file, text_caption)
            if upload_url:
                upload_video_binary(upload_url, video_file)