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
# --- (前面初始化與資料讀取維持不變) ---

# 4. 執行搜尋運算
search_button = st.button("🔍 開始搜尋", type="primary")

if (search_button or st.session_state['voice_output']) and query:
    with st.spinner('🤖 AI 正在思考中...'):
        try:
            # 取得 AI 提取的關鍵字
            res_text = get_ai_keywords(query)
            ai_keywords = [k.strip().replace("。", "") for k in res_text.split(',')]
            
            # 【保留 AI 思考】將關鍵字存入 state 供下方顯示
            st.session_state['ai_keywords_display'] = ai_keywords
            
            temp_df = df.copy()
            user_query_lower = query.lower()

            # 權重媒合邏輯
            def calculate_score(row):
                score = 0
                # [權重 A]：歌手名稱命中 (+50)
                if str(row['artist']).lower() in user_query_lower: score += 50 
                # [權重 B]：歌曲名稱命中 (+50)
                if str(row['song']).lower() in user_query_lower: score += 50
                # [權重 C]：AI 標籤命中 (每個 +10)
                tag_matches = sum(1 for k in ai_keywords if k.lower() in str(row['AI_Keywords']).lower())
                score += tag_matches * 10
                return score

            temp_df['match_score'] = temp_df.apply(calculate_score, axis=1)
            
            # 存入記憶抽屜
            st.session_state['search_results'] = temp_df[temp_df['match_score'] > 0].sort_values(by='match_score', ascending=False)
            st.session_state['voice_output'] = "" # 清空語音暫存
            
        except Exception as e:
            st.error(f"發生錯誤：{e}")

# --- 5. 顯示結果 (這裡把 AI 思考過程加回來) ---
if st.session_state['search_results'] is not None:
    # 💡 顯示 AI 解析到的關鍵字
    if 'ai_keywords_display' in st.session_state:
        st.write(f"💡 AI 解析關鍵字：`{', '.join(st.session_state['ai_keywords_display'])}`")
    
    results = st.session_state['search_results']
    
    if not results.empty:
        st.success(f"🔍 為妳精選了 {len(results)} 首歌曲（已按契合度排序）：")
        
        for _, row in results.iterrows():
            with st.container():
                c1, c2 = st.columns([1, 2])
                with c1:
                    # 判斷是精確命中還是標籤命中
                    is_exact = row['match_score'] >= 50
                    st.subheader(f"🎯 {row['song']}" if is_exact else row['song'])
                    st.write(f"🎤 {row['artist']}")
                    
                    # 顯示具體命中哪些標籤
                    ai_k = st.session_state.get('ai_keywords_display', [])
                    matched_tags = [k for k in ai_k if k.lower() in str(row['AI_Keywords']).lower()]
                    
                    if matched_tags:
                        st.info(f"✨ 標籤命中：{', '.join(matched_tags)}")
                    
                    if is_exact:
                        st.caption("✅ 偵測到歌手或歌名精確匹配")
                    
                    # 權重分數展示 (妳可以用這個來 debug)
                    st.caption(f"契合分數：{int(row['match_score'])}")
                    
                with c2:
                    st.video(f"https://www.youtube.com/watch?v={row['youtube_id']}")
                st.divider()
    else:
        st.warning("💔 沒找到符合的歌曲")
    st.info(f"目前資料庫共有 {len(df)} 首歌。")
