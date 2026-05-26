import schedule
import time
import subprocess

def daily_job():
    print("⏰ 朝7時になりました。自動化処理を開始します！")
    
    # 1. まず動画を自動生成する
    print("🎬 動画を自動生成中...")
    subprocess.run(["python", "app/create_video.py"])
    
    # 2. 生成された動画をTikTokに投稿する
    print("🚀 TikTokへ投稿中...")
    subprocess.run(["python", "app/post_to_tiktok.py"])
    
    print("✨ 今日の投稿がすべて完了しました！")

# 毎日「朝の07:00」に daily_job を実行する設定
schedule.every().day.at("07:00").do(daily_job)

print("📡 スケジューラーが起動しました。24時間監視を開始します...")

while True:
    schedule.run_pending()
    time.sleep(1) # 💡 1秒ごとにチェックするのが確実で安全です