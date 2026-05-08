import google.generativeai as genai
import pandas as pd
import time
import os
import lyricsgenius # 新增：歌詞 API 工具

# 1. 配置 API Key
API_KEY = "AIzaSyBuFEvxIZv3hNvt6289iSIG1frWZ0dZ4lE" # 填入妳的 Gemini API Key
GENIUS_ACCESS_TOKEN = "pGKs3Mi_SPUSsCjBVKxKKGGTxeGMZ28ZXy_XxAmXJnhFbtkecAchsv__XnMZJeVXNaGFg1-5nq0X0u9IatkWdw" # 填入妳申請的 Genius Token
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('models/gemini-3.1-flash-lite-preview')

# 新增：初始化歌詞 API
genius = lyricsgenius.Genius(GENIUS_ACCESS_TOKEN)
genius.remove_section_headers = True 
genius.verbose = False 

def get_real_lyrics(song_name, artist):
    """新增：從 Genius 抓取真實歌詞，並過濾掉雜訊"""
    try:
        # 強制搜尋「歌名 歌手 歌詞」提高精準度
        search_query = f"{song_name} {artist} 歌詞"
        song = genius.search_song(search_query)
        if song:
            lines = [l.strip() for l in song.lyrics.split('\n') if l.strip()]
            # 尋找第一句包含中文且長度足夠的歌詞
            for line in lines:
                if any('\u4e00' <= char <= '\u9fff' for char in line) and len(line) > 5:
                    # 排除掉剛好是歌名的那一列
                    if song_name not in line or len(line) > len(song_name) + 2:
                        return line
        return ""
    except:
        return ""

def get_song_tags_with_lyrics(song_name, artist, yt_id):
    """讓 AI 產出包含關鍵字與重點歌詞的合體字串"""
    # 下方所有程式碼都必須比 def 往右縮排 4 個空格
    yt_context = f" (YouTube ID: {yt_id})" if pd.notna(yt_id) and str(yt_id).strip() != "" else ""
    
    prompt = f"""
    任務：針對歌曲 "{song_name}" (歌手: {artist}){yt_context} 提取具備專業音樂庫質感的深度標籤。
    
    【核心標籤策略】：
    1. **僅限當下專輯 (Single Album Only)**：只允許列出該首歌曲「實際收錄的正規專輯名稱」（中英對照），嚴禁聯想歌手的其他歷史專輯。
    2. **時間軸標籤 (Timeline)**：必須同時包含「發行年份」與中文的「年代」及英文「Decade」（例如：2016, 2010年代, 2010s）。
    3. **標誌性風格識別**：根據歌手地位加入專屬風格標籤（如：周氏情歌, Jay Chou Style）。
    4. **嚴格黑名單 (Blacklist)**：
       - 絕對禁止出現：輕節奏, Mid-tempo, 睡前音樂, Bedtime, 輕音樂, Easy Listening, 音樂庫, Stock Music。
       - 絕對禁止出現非專業或瑣碎形容詞（如：邊邊角角、羞澀、漫步、心兒摘下）。

    【標籤維度（量體適中且精確）】：
    - **專輯與時間**：所屬專輯名稱 (中英對照), 發行年份, 中文年代 (如 2010年代), 英文年代 (如 2010s), 地區。
    - **流派與技術**：華語流行 (Mandopop), 核心流派 (如 R&B, Pop Ballad), 聲音特質 (如 Clean Vocals, Airy Vocals), 製作器樂 (如 Piano, Acoustic Guitar, Groove)。
    - **歌單與場景**：婚禮 (Wedding), 約會 (Dating), 咖啡廳 (Cafe), 療癒 (Healing), 浪漫 (Romantic), 經典 (Classic)。
    - **事實歌詞**：第一句歌詞, 副歌第一句。

    【輸出示範】：
    周杰倫的床邊故事, Jay Chou's Bedtime Stories, 2016, 2010年代, 2010s, Taiwan, 華語流行, Mandopop, 周氏情歌, Jay Chou Style, R&B, 流行抒情, Pop Ballad, 輕快流行, Upbeat, 清澈嗓音, Clean Vocals, 氣聲唱法, Airy Vocals, 鋼琴伴奏, Piano, 吉他編曲, Acoustic Guitar, 浪漫氛圍, Romantic, 甜蜜, Sweet, 婚禮歌單, Wedding, 約會, Dating, 咖啡廳, Cafe, 療癒系, Healing, 經典, Classic, 塞納河畔左岸的咖啡, 親愛的愛上你從那天起

    【輸出規範】：
    - 僅回傳一串以「逗號」分隔的純文字。
    - **強制要求**：年代必須同時包含中文（如：2010年代）與英文（如：2010s）。
    - **強制要求**：專輯僅能列出該曲收錄的那一張，並採中英文對照。
    - **禁止** 分類標題、**禁止** 冒號、**禁止** 括號、**禁止** 出現黑名單內的任何廢詞。
    """
    
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            # 確保輸出是一整行文字
            return response.text.strip().replace('\n', ', ')
        return "AI 無法產出結果"
    except Exception as e:
        return f"API 錯誤: {str(e)}"
        
def main():
    file_name = "songs.csv"
    output_name = "songs_with_tags.csv"

    if not os.path.exists(file_name):
        print(f"❌ 找不到檔案：{file_name}")
        return

    try:
        df = pd.read_csv(file_name)
        df.columns = df.columns.str.strip()
        print(f"✅ 成功讀取檔案，共有 {len(df)} 首歌。")
    except Exception as e:
        print(f"❌ 讀取 CSV 失敗: {e}")
        return

    all_tags = []
    for index, row in df.iterrows():
        s_name = row.get('song', 'Unknown Song')
        s_artist = row.get('artist', 'Unknown Artist')
        s_ytid = row.get('youtube_id', "")

        print(f"[{index+1}/{len(df)}] 處理中: {s_name} - {s_artist}...")
        
        # 1. 先拿 AI 產出的那串排山倒海的標籤
        tags_from_ai = get_song_tags_with_lyrics(s_name, s_artist, s_ytid)
        
        # 2. 再拿 API 抓到的精確歌詞
        accurate_lyrics = get_real_lyrics(s_name, s_artist)
        
        # 3. 物理組合：標籤後面直接接正確歌詞，中間用逗號隔開
        if accurate_lyrics:
            # 如果 AI 已經產出過標籤了，我們就把 API 抓到的正確歌詞補在最後面
            final_entry = f"{tags_from_ai}, {accurate_lyrics}"
        else:
            final_entry = tags_from_ai
            
        all_tags.append(final_entry)
        
        time.sleep(4)

    # 4. 儲存結果
    df['AI_Keywords'] = all_tags
    df.to_csv(output_name, index=False, encoding="utf-8-sig")
    print("-" * 30)
    print(f"🎉 全部處理完成！結果已存至: {output_name}")

if __name__ == "__main__":
    main()