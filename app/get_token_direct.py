import os
import requests
from dotenv import load_dotenv

load_dotenv()
CLIENT_KEY = os.getenv("CLIENT_KEY")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CODE = os.getenv("CODE")

def exchange_user_token():
    url = "https://open.tiktokapis.com/v2/oauth/token/"
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    # 投稿用トークンをもらうための正しい設定
    data = {
        "client_key": CLIENT_KEY,
        "client_secret": CLIENT_SECRET,
        "code": CODE,
        "grant_type": "authorization_code",
        "redirect_uri": "https://www.example.com/"
    }
    
    print("🔄 動画投稿用の「本物のユーザートークン」に最終変換中...")
    response = requests.post(url, headers=headers, data=data)
    res_data = response.json()
    
    if "access_token" in res_data:
        token = res_data["access_token"]
        print("\n🎉 大成功！！！トークンを取得できました：")
        print(f"----------------------------------------\n{token}\n----------------------------------------")
        print("\n上記の文字列を丸ごとコピーして、.envの TIKTOK_ACCESS_TOKEN= に上書き貼り付けしてください。")
    else:
        print("\n❌ エラーが発生しました。")
        print(f"レスポンス内容: {res_data}")

if __name__ == "__main__":
    exchange_user_token()