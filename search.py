import pandas as pd
import os
import google.generativeai as genai

# 1. 配置妳的 AI Key (直接用妳產標籤那組)
API_KEY = "AIzaSyBuFEvxIZv3hNvt6289iSIG1frWZ0dZ4lE"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

def start_search_assistant():
    # 自動獲取檔案路徑
    base_path = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(base_path, "songs_with_tags.csv")

    if not os.path.exists(file_path):
        print(f"❌ 找不到資料檔：{file_path}")
        return

    try:
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
    except Exception as e:
        print(f"❌ 讀取 CSV 失敗: {e}")
        return

    print(f"✅ 成功載入 {len(df)} 首歌。")
    print("🎵 AI 語意搜尋助理已啟動！(輸入 'quit' 結束)")
    print("-" * 40)

    while True:
        user_input = input("\n你想聽什麼樣的歌？(例如：心情不好想聽熱血的)：").strip()
        
        if not user_input: continue
        if user_input.lower() == 'quit': break

        print("🤖 AI 正在分析您的需求...")

        # 這裡就是讓 AI 幫妳「翻譯」關鍵字的秘訣
        prompt = f"""
        你是一個音樂庫導覽員。用戶說："{user_input}"
        請從這句話中提取 2-3 個適合搜尋音樂標籤的關鍵字。
        只回傳關鍵字，用逗號隔開。
        範例：搖滾, 熱血, 電吉他
        """

        try:
            response = model.generate_content(prompt)
            # 把 AI 產出的字串變成清單：['搖滾', '熱血']
            ai_keywords = [k.strip() for k in response.text.split(',')]
            print(f"💡 AI 搜尋標籤：{', '.join(ai_keywords)}")

            # 搜尋邏輯：只要命中 AI 給的任何一個字就列出來
            mask = df['AI_Keywords'].apply(lambda x: any(k.lower() in str(x).lower() for k in ai_keywords))
            results = df[mask]

            if not results.empty:
                print(f"🔍 幫您找到以下歌曲：")
                for _, row in results.iterrows():
                    print(f"✨ {row.get('artist')} - {row.get('song')}")
                    print(f"   📺 https://www.youtube.com/watch?v={row.get('youtube_id')}")
            else:
                print("💔 找不到符合的歌，換個說法試試看？")

        except Exception as e:
            print(f"❌ AI 處理失敗: {e}")

if __name__ == "__main__":
    start_search_assistant()