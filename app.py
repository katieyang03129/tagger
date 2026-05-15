import streamlit as st
from streamlit_mic_recorder import speech_to_text
import pandas as pd
import google.generativeai as genai
import os

# --- STEP 1: 初始化 Session State (記憶抽屜) ---
if 'voice_output' not in st.session_state:
    st.session_state['voice_output'] = ""
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'ai_keywords_display' not in st.session_state:
    st.session_state['ai_keywords_display'] = []

st.set_page_config(page_title="智能點歌台", page_icon="🎵")
st.title("智能點歌台 🎵")

# --- STEP 2: AI 配置與資料庫讀取 ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

@st.cache_data(show_spinner=False)
def get_ai_keywords(user_query):
    prompt = f"""
    你是一個專業音樂評論家。當用戶搜尋內容：'{user_query}' 時：
    1. 提取 2-3 個核心關鍵字。
    2. 如果包含特定歌手，請務必提取該歌手最具代表性的音色特徵或情感氛圍（例如：空靈、懶散、冷冽等）。
    3. 嚴禁多餘描述，只回傳關鍵字並用逗號隔開。
    """
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return ""

@st.cache_data
def load_data():
    file_path = "songs_with_tags.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        return df
    return None

df = load_data()

# --- STEP 3: 搜尋介面佈局 (文字框 + 語音按鈕) ---
col1, col2 = st.columns([6, 4]) 

with col1:
    # 唯一的搜尋輸入框
    query = st.text_input(
        "search_input", 
        value=st.session_state['voice_output'], 
        placeholder="搜尋歌手、歌名或心情 (例如：王菲 空靈)...",
        label_visibility="collapsed"
    )

with col2:
    # 語音按鈕：文字會隨狀態切換
    voice_text = speech_to_text(
        language='zh-TW', 
        start_prompt="🎙️ 語音輸入", 
        stop_prompt="🛑 輸入中...完成請點我", 
        key='mic_recorder'
    )

# --- STEP 4: 處理語音輸入狀態與回傳 ---
# 1. 顯示「輸入中」狀態
if st.session_state.get('mic_recorder') is not None and not voice_text:
    st.markdown("💬 :red[語音輸入中...請開始說話]")

# 2. 錄音完成後的處理 (只填入框框，不自動搜尋)
if voice_text and voice_text != st.session_state['voice_output']:
    st.session_state['voice_output'] = voice_text
    st.rerun()

# 唯一的搜尋發動按鈕
search_trigger = st.button("🔍 開始搜尋", type="primary", use_container_width=True)

# --- STEP 5: 核心搜尋邏輯 (僅在按下「開始搜尋」時執行) ---
if search_trigger and query:
    if df is not None:
        with st.spinner('🤖 AI 正在精準媒合中...'):
            try:
                res_text = get_ai_keywords(query)
                ai_keywords = [k.strip().replace("。", "") for k in res_text.split(',')]
                st.session_state['ai_keywords_display'] = ai_keywords
                
                temp_df = df.copy()
                user_query_lower = query.lower().strip()

                def calculate_score(row):
                    score = 0
                    artist_val = str(row['artist']).lower()
                    song_val = str(row['song']).lower()
                    tag_val = str(row['AI_Keywords']).lower()
                    
                    # [權重 A]：歌手/歌名精確命中
                    if artist_val in user_query_lower or user_query_lower in artist_val: score += 50 
                    if song_val in user_query_lower: score += 50
                    
                    # [權重 B]：標籤命中
                    tag_matches = 0
                    for k in ai_keywords:
                        if k.lower() in tag_val:
                            tag_matches += 1
                            score += 30
                    
                    # [權重 C]：複合加分
                    if score >= 50 and tag_matches > 0: score += 20 
                    return score

                temp_df['match_score'] = temp_df.apply(calculate_score, axis=1)
                st.session_state['search_results'] = temp_df[temp_df['match_score'] > 0].sort_values(by='match_score', ascending=False)
                
            except Exception as e:
                st.error(f"搜尋過程中發生錯誤：{e}")
    else:
        st.error("找不到歌曲資料庫 (CSV)。")

# --- STEP 6: 結果顯示區 (穩定顯示) ---
if st.session_state['search_results'] is not None:
    if st.session_state['ai_keywords_display']:
        st.write(f"💡 AI 解析關鍵字：`{', '.join(st.session_state['ai_keywords_display'])}`")
    
    results = st.session_state['search_results']
    
    if not results.empty:
        st.success(f"🔍 為妳精選了 {len(results)} 首歌曲（僅顯示前 50 首）：")
        for _, row in results.head(50).iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    is_exact = row['match_score'] >= 50
                    st.subheader(f"🎯 {row['song']}" if is_exact else row['song'])
                    st.write(f"🎤 {row['artist']}")
                    
                    ai_k = st.session_state['ai_keywords_display']
                    matched_tags = [k for k in ai_k if k.lower() in str(row['AI_Keywords']).lower()]
                    if matched_tags:
                        st.info(f"✨ 標籤命中：{', '.join(matched_tags)}")
                    st.caption(f"契合分數：{int(row['match_score'])}")
                
                with c2:
                    st.write(" ") 
                    yt_url = f"https://www.youtube.com/watch?v={row['youtube_id']}"
                    st.link_button("▶️ 播放影片", yt_url, use_container_width=True)
            st.divider()
    else:
        st.warning("💔 沒找到符合的歌曲，換個關鍵字試試看？")
elif df is not None:
    st.info(f"目前資料庫共有 {len(df)} 首歌。請輸入心情或歌手開始點歌！")
