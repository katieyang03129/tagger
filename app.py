import streamlit as st
from streamlit_mic_recorder import speech_to_text
import pandas as pd
import google.generativeai as genai
import os

# --- 1. 初始化所有記憶抽屜 ---
if 'voice_output' not in st.session_state:
    st.session_state['voice_output'] = ""
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None

st.markdown("### 智能點歌台🎵")

# --- 2. 輸入佈局 ---
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

# --- 3. 配置與資料讀取 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

@st.cache_data
def get_ai_keywords(user_query):
    prompt = f"你是一個音樂標籤提取器。用戶說：'{user_query}'。請提取 2-3 個核心關鍵字，用逗號隔開。"
    response = model.generate_content(prompt)
    return response.text

@st.cache_data
def load_data():
    file_path = "songs_with_tags.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        return df
    return None

df = load_data()

# --- 4. 觸發搜尋動作 (這裡只負責「運算」並「存入記憶」) ---
search_button = st.button("🔍 開始搜尋", type="primary")

if (search_button or st.session_state['voice_output']) and query:
    with st.spinner('🤖 AI 正在思考中...'):
        try:
            res_text = get_ai_keywords(query)
            ai_keywords = [k.strip().replace("。", "") for k in res_text.split(',')]
            
            temp_df = df.copy()
            user_query_lower = query.lower()

            def calculate_score(row):
                score = 0
                if str(row['artist']).lower() in user_query_lower: score += 50 
                if str(row['song']).lower() in user_query_lower: score += 50
                tag_matches = sum(1 for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower())
                score += tag_matches * 10
                return score

            temp_df['match_score'] = temp_df.apply(calculate_score, axis=1)
            # 【關鍵】: 把過濾後的結果存進 session_state
            st.session_state['search_results'] = temp_df[temp_df['match_score'] > 0].sort_values(by='match_score', ascending=False)
            
            # 搜尋完就清空語音暫存，避免循環
            st.session_state['voice_output'] = ""
            
        except Exception as e:
            st.error(f"發生錯誤：{e}")

# --- 5. 顯示結果 (這段在最外層，只要記憶裡有東西，重整就不會消失) ---
if st.session_state['search_results'] is not None:
    results = st.session_state['search_results']
    if not results.empty:
        st.success(f"🔍 為妳精選了 {len(results)} 首歌曲：")
        for _, row in results.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.subheader(f"🎯 {row['song']}" if row['match_score'] >= 50 else f"{row['song']}")
                    st.write(f"🎤 {row['artist']}")
                    matched_tags = [k for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower()] if 'ai_keywords' in locals() else []
                    if matched_tags: st.info(f"✨ 標籤命中：{', '.join(matched_tags)}")
                with c2:
                    st.video(f"https://www.youtube.com/watch?v={row['youtube_id']}")
                st.divider()
    else:
        st.warning("💔 沒找到符合的歌曲")
elif df is not None:
    st.info(f"目前資料庫共有 {len(df)} 首歌。")
