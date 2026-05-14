import streamlit as st
from streamlit_mic_recorder import speech_to_text
import pandas as pd
import google.generativeai as genai
import os

# 1. 初始化 session_state
if 'voice_output' not in st.session_state:
    st.session_state['voice_output'] = ""

st.markdown("### 智能點歌台🎵")

# 2. 建立並排佈局
col1, col2 = st.columns([9, 1])

with col1:
    query = st.text_input(
        "search", 
        value=st.session_state['voice_output'], 
        placeholder="直接輸入，或按右側麥克風...",
        label_visibility="collapsed"
    )

with col2:
    voice_text = speech_to_text(
        language='zh-TW', 
        start_prompt="🎤", 
        stop_prompt="✅", 
        key='mic_icon'
    )
    
    if voice_text and voice_text != st.session_state['voice_output']:
        st.session_state['voice_output'] = voice_text
        st.rerun()

# --- AI 配置與快取函式 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

@st.cache_data
def get_ai_keywords(user_query):
    """
    這個函式加了 cache，同樣的關鍵字搜尋第二次時，
    會直接從記憶體抓結果，不會再打 API 扣錢。
    """
    prompt = f"""
    你是一個音樂標籤提取器。用戶說：'{user_query}'。
    請提取 2-3 個最核心、最具代表性的關鍵字。
    注意：
    1. 除非用戶明確要求，否則禁止使用「流行」、「經典」、「音樂」、「歌曲」這類過於廣泛的詞。
    2. 盡量提取具體的風格（如：搖滾、民謠）或具體的情緒。
    只回傳關鍵字並用逗號隔開。
    """
    response = model.generate_content(prompt)
    return response.text

# --- 讀取資料 ---
@st.cache_data
def load_data():
    file_path = "songs_with_tags.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        return df
    return None

df = load_data()

# --- 核心搜尋邏輯 ---
# 加上一個手動按鈕當作「保險栓」
search_trigger = st.button("🔍 開始搜尋", type="primary")

# 只有在按下按鈕，或是語音輸入剛完成時才觸發
# --- 核心搜尋邏輯升級版 ---
if (search_trigger or st.session_state['voice_output']) and query:
    with st.spinner('🤖 AI 正在思考中...'):
        try:
            # 1. 取得 AI 關鍵字（維持原有的快取函式）
            res_text = get_ai_keywords(query)
            ai_keywords = [k.strip().replace("。", "") for k in res_text.split(',')]
            
            # 2. 建立一個複製品來計算分數
            temp_df = df.copy()

            # 3. 計算權重分數
            def calculate_score(row):
                score = 0
                user_query_lower = query.lower()
                
                # [權重 A]：歌手名稱完全命中 (最高優先)
                if str(row['artist']).lower() in user_query_lower:
                    score += 50 
                
                # [權重 B]：歌曲名稱完全命中
                if str(row['song']).lower() in user_query_lower:
                    score += 50
                
                # [權重 C]：AI 標籤命中 (每個標籤 +10 分)
                tag_matches = sum(1 for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower())
                score += tag_matches * 10
                
                return score

            temp_df['match_score'] = temp_df.apply(calculate_score, axis=1)

            # 4. 只篩選出分數大於 0 的結果
            results = temp_df[temp_df['match_score'] > 0].sort_values(by='match_score', ascending=False)

            if not results.empty:
                st.success(f"🔍 找到 {len(results)} 首相關歌曲：")
                
                for _, row in results.iterrows():
                    with st.container():
                        c1, c2 = st.columns([1, 2])
                        with c1:
                            # 如果分數很高，顯示「精確命中」
                            if row['match_score'] >= 50:
                                st.subheader(f"🎯 {row['song']}")
                            else:
                                st.subheader(row['song'])
                                
                            st.write(f"🎤 {row['artist']}")
                            
                            # 顯示命中原因
                            matched_tags = [k for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower()]
                            if matched_tags:
                                st.info(f"✨ 標籤命中：{', '.join(matched_tags)}")
                            if str(row['artist']).lower() in user_query_lower:
                                st.write("✅ 歌手精確匹配")
                        
                        with c2:
                            url = f"https://www.youtube.com/watch?v={row['youtube_id']}"
                            st.video(url)
                        st.divider()
            else:
                st.warning("💔 沒找到符合的歌曲，換個說法試試？")
        except Exception as e:
            st.error(f"發生錯誤：{e}")

elif df is not None:
    st.info(f"目前資料庫共有 {len(df)} 首歌。")
