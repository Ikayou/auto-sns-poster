import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# 環境変数の読み込み
ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
BUSINESS_ACCOUNT_ID = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
API_VERSION = "v19.0"  # Meta APIのバージョン
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

def create_media_container(video_url: str, caption: str) -> str:
    """ステップ1: Metaのサーバーに動画URLを伝え、メディアコンテナ（箱）を作成する"""
    url = f"{BASE_URL}/{BUSINESS_ACCOUNT_ID}/media"
    payload = {
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "access_token": ACCESS_TOKEN
    }
    
    print("🚀 [Step 1/3] Metaサーバーへ動画URLを送信中...")
    response = requests.post(url, data=payload)
    res_data = response.json()
    
    if "id" not in res_data:
        raise Exception(f"コンテナ作成に失敗しました: {res_data}")
        
    container_id = res_data["id"]
    print(f"✅ コンテナが作成されました。ID: {container_id}")
    return container_id

def wait_for_processing(container_id: str, timeout_sec: int = 300) -> bool:
    """ステップ2: Meta側での動画エンコード処理が完了するのを待つ"""
    url = f"{BASE_URL}/{container_id}"
    params = {
        "fields": "status_code",
        "access_token": ACCESS_TOKEN
    }
    
    print("⏳ [Step 2/3] Meta側での動画処理を待機しています（これには1〜2分かかります）...")
    start_time = time.time()
    
    while time.time() - start_time < timeout_sec:
        response = requests.get(url, params=params)
        res_data = response.json()
        status_code = res_data.get("status_code")
        
        if status_code == "FINISHED":
            print("✅ 動画の処理が完了しました！投稿可能な状態です。")
            return True
        elif status_code == "ERROR":
            raise Exception(f"Meta側での動画処理中にエラーが発生しました: {res_data}")
            
        # 20秒待って再確認（ポーリング）
        time.sleep(20)
        
    raise TimeoutError("Meta側の動画処理がタイムアウトしました。")

def publish_media(container_id: str) -> str:
    """ステップ3: 処理が終わったコンテナを、実際のReelsとしてタイムラインに公開する"""
    url = f"{BASE_URL}/{BUSINESS_ACCOUNT_ID}/media_publish"
    payload = {
        "creation_id": container_id,
        "access_token": ACCESS_TOKEN
    }
    
    print("📢 [Step 3/3] Instagramへの公開リクエストを送信中...")
    response = requests.post(url, data=payload)
    res_data = response.json()
    
    if "id" not in res_data:
        raise Exception(f"公開に失敗しました: {res_data}")
        
    post_id = res_data["id"]
    print(f"🎉 完全に自動投稿されました！ポストID: {post_id}")
    return post_id

if __name__ == "__main__":
    # テスト用の設定
    # ⚠️ 実際に動かす際は、ここにインターネット上の公開動画URLを入力します
    TEST_VIDEO_URL = "https://your-public-server.com/output/reels.mp4" 
    TEST_CAPTION = "Dockerコンテナの基礎知識！ #Docker #DevOps #プログラミング"

    try:
        # 1. 箱を作る
        c_id = create_media_container(TEST_VIDEO_URL, TEST_CAPTION)
        
        # 2. Metaの処理を待つ
        if wait_for_processing(c_id):
            # 3. 世の中に公開！
            publish_media(c_id)
            
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")