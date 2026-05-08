import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# 1. 基礎配置
st.set_page_config(page_title="AI 音樂搜尋助理", page_icon="🎵")
st.title("🎵 我的專屬 AI 音樂助理")
st.markdown("輸入妳的心情或想聽的風格，讓 AI 幫妳從資料庫中翻找！")

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
        你是一個專業的華語流行音樂導覽員。用戶說：'{query}'。
        注意：我的資料庫主要是「80-90 年代經典金曲」與「華語抒情流行」。
        
        請根據語意提取 3-5 個關鍵字，並務必包含 1-2 個較通用的標籤（如：抒情、經典、流行、悲傷、溫柔）。
        不要使用 Lo-fi、Jazz、藍調等資料庫可能沒有的術語。
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
            mask = df['AI_Keywords'].apply(lambda x: any(str(k).lower() in str(x).lower() or str(x).lower() in str(k).lower() for k in ai_keywords))
            results = df[mask]

            if not results.empty:
                st.success(f"🔍 找到 {len(results)} 首歌曲：")
                for _, row in results.iterrows():
                    with st.container():
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            # 這裡可以放妳的 YouTube ID 產生的連結
                            st.subheader(row['song'])
                            st.write(f"🎤 {row['artist']}")
                        with col2:
                            url = f"https://www.youtube.com/watch?v={row['youtube_id']}"
                            st.video(url) # 直接在網頁內嵌播放器！
                        st.divider()
            else:
                st.warning("💔 沒找到符合的歌曲，換個說法試試？")
        except Exception as e:
            st.error(f"發生錯誤：{e}")
elif df is not None:
    st.info(f"目前資料庫共有 {len(df)} 首歌。")
