import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# 1. 基礎配置
st.set_page_config(page_title="AI 音樂搜尋助理", page_icon="🎵")
st.title("🎵 我的專屬 AI 音樂助理")
st.markdown("輸入妳的心情或想聽的風格，讓 AI 幫妳從資料庫中翻找！")

# 2. AI 配置
# 2. AI 配置
API_KEY = "AIzaSyBuFEvxIZv3hNvt6289iSIG1frWZ0dZ4lE"
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

# 3. 讀取資料
@st.cache_data
def load_data():
    file_path = "songs_with_tags.csv"
    if os.path.exists(file_path):
        # 💡 加入 encoding 防止亂碼，並強力清洗欄位名稱
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip() # 👈 這行最重要，清掉所有空格
        return df
    return None

df = load_data()

# 4. 網頁介面 - 搜尋框
query = st.text_input("你想聽什麼樣的歌？", placeholder="例如：心情不好想聽熱血的...")

if query:
    with st.spinner('🤖 AI 正在思考中...'):
        # 1. 升級後的 Prompt：讓 AI 知道妳的歌單背景
        prompt = f"""
        你是一個音樂標籤提取器。用戶說：'{query}'。
        請提取 2-3 個最核心、最具代表性的關鍵字。
        注意：
        1. 除非用戶明確要求，否則禁止使用「流行」、「經典」、「音樂」、「歌曲」這類過於廣泛的詞。
        2. 盡量提取具體的風格（如：搖滾、民謠）或具體的情緒。
        只回傳關鍵字並用逗號隔開。
        """

        try:
            response = model.generate_content(prompt)
            # 2. 增加防呆：移除可能出現的句號或空白
            ai_keywords = [k.strip().replace("。", "") for k in response.text.split(',')]
            
            st.write(f"💡 AI 解析關鍵字：`{', '.join(ai_keywords)}`")

            # 3. 搜尋邏輯優化：模糊比對 (只要關鍵字有部分重疊就抓出來)
            mask = df['AI_Keywords'].apply(lambda x: any(
                str(k).lower() in str(x).lower() or str(x).lower() in str(k).lower() 
                for k in ai_keywords
            ))
            results = df[mask]

            # 搜尋邏輯
            # 搜尋邏輯 - 加上 str() 確保不會因為空值崩潰
            # 找到搜尋邏輯那一行，改為：
            # 1. 基礎搜尋：先找出有命中的歌曲
            mask = df['AI_Keywords'].apply(lambda x: any(k.lower() in str(x).lower() for k in ai_keywords))
            results = df[mask].copy()

            if not results.empty:
                # 2. 計算「命中分數」：這首歌中了幾個關鍵字？
                results['match_score'] = results['AI_Keywords'].apply(
                    lambda x: sum(1 for k in ai_keywords if k.lower() in str(x).lower())
                )

                # 3. 執行排序：分數高的排前面
                results = results.sort_values(by='match_score', ascending=False)

                st.success(f"🔍 為妳精選了 {len(results)} 首歌曲（已按契合度排序）：")
                
                # 4. 顯示歌曲 (這部分可以延用妳原本的 UI)
                for _, row in results.iterrows():
                    with st.container():
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.subheader(row['song'])
                            st.write(f"🎤 {row['artist']}")
                            
                            # 💡 增加一個小提示，顯示這首歌有多契合
                            match_percent = int((row['match_score'] / len(ai_keywords)) * 100)
                            st.caption(f"🎯 契合度：{match_percent}%")
                            
                            matched_tags = [k for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower()]
                            st.info(f"✨ 命中：{', '.join(matched_tags)}")
                        
                        with col2:
                            url = f"https://www.youtube.com/watch?v={row['youtube_id']}"
                            st.video(url)
                        st.divider()
            else:
                st.warning("💔 沒找到符合的歌曲，換個說法試試？")
        except Exception as e:
            st.error(f"發生錯誤：{e}")
elif df is not None:
    st.info(f"目前資料庫共有 {len(df)} 首歌。")
