import streamlit as st
from streamlit_mic_recorder import speech_to_text
import pandas as pd
import google.generativeai as genai
import os

# --- STEP 1: 初始化 Session State (記憶抽屜) ---
# 這些變數確保網頁重整時，搜尋結果與文字不會消失
if 'voice_output' not in st.session_state:
    st.session_state['voice_output'] = ""
if 'search_results' not in st.session_state:
    st.session_state['search_results'] = None
if 'ai_keywords_display' not in st.session_state:
    st.session_state['ai_keywords_display'] = []

# 設定網頁標題與圖示
st.set_page_config(page_title="智能點歌台", page_icon="🎵")
st.title("智能點歌台 🎵")

# --- STEP 2: AI 配置與快取函式 ---
# 使用 st.secrets 安全讀取 Key
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
# 使用最新的 Flash 模型確保速度與準確度
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

@st.cache_data(show_spinner=False)
def get_ai_keywords(user_query):
    """
    透過 AI 提取關鍵字，並加入快取機制避免重複消耗額度。
    強化 Prompt，確保針對歌手搜尋時能提取其靈魂特徵（如：空靈）。
    """
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

# --- STEP 3: 讀取資料庫 ---
@st.cache_data
def load_data():
    file_path = "songs_with_tags.csv"
    if os.path.exists(file_path):
        df = pd.read_csv(file_path, encoding='utf-8-sig')
        df.columns = df.columns.str.strip() # 清洗欄位空格
        return df
    return None

df = load_data()

# --- STEP 4: 搜尋介面佈局 (語音與文字整合) ---
col1, col2 = st.columns([9, 1])

with col1:
    # 接收文字輸入或語音轉譯的結果
    query = st.text_input(
        "搜尋框", 
        value=st.session_state['voice_output'], 
        placeholder="搜尋歌手、歌名或心情 (例如：王菲 空靈)...",
        label_visibility="collapsed"
    )

with col2:
    # 語音按鈕：辨識完後會存入變數並觸發 rerun 以填入輸入框
    voice_text = speech_to_text(
        language='zh-TW', 
        start_prompt="🎤", 
        stop_prompt="✅", 
        key='mic_icon'
    )
    if voice_text and voice_text != st.session_state['voice_output']:
        st.session_state['voice_output'] = voice_text
        st.rerun()

# 搜尋按鈕
search_button = st.button("🔍 開始搜尋", type="primary", use_container_width=True)

# --- STEP 5: 核心搜尋與權重運算邏輯 ---
# 觸發條件：點擊按鈕 或 語音剛結束且框內有字
if (search_button or (voice_text and voice_text != "")) and query:
    if df is not None:
        with st.spinner('🤖 AI 正在精準媒合中...'):
            try:
                # 1. AI 關鍵字分析
                res_text = get_ai_keywords(query)
                ai_keywords = [k.strip().replace("。", "") for k in res_text.split(',')]
                st.session_state['ai_keywords_display'] = ai_keywords
                
                # 2. 權重媒合運算
                temp_df = df.copy()
                user_query_lower = query.lower().strip()

                def calculate_score(row):
                    score = 0
                    artist_val = str(row['artist']).lower()
                    song_val = str(row['song']).lower()
                    tag_val = str(row['AI_Keywords']).lower()
                    
                    # [權重 A]：歌手/歌名精確命中 (基礎分 50)
                    if artist_val in user_query_lower or user_query_lower in artist_val:
                        score += 50 
                    if song_val in user_query_lower:
                        score += 50
                    
                    # [權重 B]：AI 標籤命中 (每個加 30 分，確保風格優先)
                    tag_matches = 0
                    for k in ai_keywords:
                        if k.lower() in tag_val:
                            tag_matches += 1
                            score += 30
                    
                    # [權重 C]：複合加分 (同時符合歌手與標籤)
                    if score >= 50 and tag_matches > 0:
                        score += 20 
                    
                    return score

                temp_df['match_score'] = temp_df.apply(calculate_score, axis=1)
                
                # 3. 儲存結果至 Session State (防止重整消失)
                final_results = temp_df[temp_df['match_score'] > 0].sort_values(by='match_score', ascending=False)
                st.session_state['search_results'] = final_results
                
                # 搜尋完畢後，重置語音狀態以防循環
                st.session_state['voice_output'] = query 

            except Exception as e:
                st.error(f"搜尋過程中發生錯誤：{e}")
    else:
        st.error("找不到歌曲資料庫 (CSV)，請檢查檔案路徑。")

# --- STEP 6: 穩定結果顯示區 ---
# 只要記憶抽屜裡有資料，就會持續顯示，不會因為點擊或重整而消失
if st.session_state['search_results'] is not None:
    # 顯示 AI 解析到的關鍵字
    if st.session_state['ai_keywords_display']:
        st.write(f"💡 AI 解析關鍵字：`{', '.join(st.session_state['ai_keywords_display'])}`")
    
    results = st.session_state['search_results']
    
    if not results.empty:
        st.success(f"🔍 為妳精選了 {len(results)} 首歌曲（已按契合度排序）：")
        
        # 安全模式：僅顯示前 50 筆，並使用連結按鈕避免 YouTube 哭臉錯誤
        for _, row in results.head(50).iterrows():
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    is_exact = row['match_score'] >= 50
                    st.subheader(f"🎯 {row['song']}" if is_exact else row['song'])
                    st.write(f"🎤 {row['artist']}")
                    
                    # 顯示具體命中的標籤
                    ai_k = st.session_state['ai_keywords_display']
                    matched_tags = [k for k in ai_k if k.lower() in str(row['AI_Keywords']).lower()]
                    if matched_tags:
                        st.info(f"✨ 標籤命中：{', '.join(matched_tags)}")
                    
                    st.caption(f"契合分數：{int(row['match_score'])}")
                
                with c2:
                    # 使用 Link Button 解決嵌入影片導致的崩潰問題
                    st.write(" ") 
                    yt_url = f"https://www.youtube.com/watch?v={row['youtube_id']}"
                    st.link_button("▶️ 播放影片", yt_url, use_container_width=True)
            
            st.divider()
    else:
        st.warning("💔 沒找到符合的歌曲，換個關鍵字試試看？")

elif df is not None:
    # 初始狀態顯示資料庫規模
    st.info(f"目前資料庫共有 {len(df)} 首歌。請輸入心情或歌手開始點歌！")
