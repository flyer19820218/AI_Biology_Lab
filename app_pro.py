import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端自動截圖
import re
import base64
from PIL import Image

# --- 1. 頁面配置 (行動/平版雙模適配 + 深度白晝協議) ---
st.set_page_config(page_title="生物 AI 生命真理研究室", layout="wide")

st.markdown("""
    <style>
    /* A. 全域白晝協議：強制所有載具背景為白色，文字為全黑 */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stToolbar"], .stMain {
        background-color: #ffffff !important;
    }
    html, body, [class*="css"], .stMarkdown, p, span, label, li {
        color: #000000 !important;
        font-family: 'HanziPen SC', '翩翩體', 'PingFang TC', 'Heiti TC', 'Microsoft JhengHei', sans-serif !important;
    }

    /* B. 雙模適配：行動端自動縮減邊距，確保講義圖片最大化 */
    [data-testid="stAppViewBlockContainer"] {
        padding: 1.5rem 1rem !important;
    }
    
    /* 標題字體隨螢幕寬度彈性縮放 */
    h1 { font-size: calc(1.4rem + 1.2vw) !important; text-align: center; }
    h3 { font-size: calc(1.1rem + 0.5vw) !important; }

    /* C. 終極解鎖：針對蘋果手機「拉把 (Selectbox)」彈出選單的黑底修正 */
    div[data-baseweb="popover"], div[data-baseweb="listbox"], ul[role="listbox"], li[role="option"] {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    li[role="option"] div, li[role="option"] span {
        color: #000000 !important;
        background-color: #ffffff !important;
    }

    /* D. 組件鎖定：打字區與下拉選單本體 (白底黑字) */
    div[data-testid="stTextInput"] input, div[data-baseweb="select"], div[data-baseweb="select"] > div {
        background-color: #ffffff !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        border: 2px solid #000000 !important;
    }

    /* E. 拍照截圖區：中文化與白晝鎖定 */
    [data-testid="stFileUploader"] section { background-color: #ffffff !important; border: 2px dashed #000000 !important; }
    [data-testid="stFileUploader"] button { background-color: #ffffff !important; color: #000000 !important; border: 1px solid #000000 !important; }
    [data-testid="stFileUploader"] button div span { font-size: 0 !important; }
    [data-testid="stFileUploader"] button div span::before { content: "瀏覽檔案" !important; font-size: 1rem !important; color: #000000 !important; }

    /* F. 您原本的黃色導覽框鎖定 */
    .guide-box {
        background-color: #fff9c4 !important;
        color: #000000 !important;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #fbc02d;
        margin-bottom: 20px;
    }

    /* G. 按鈕行動優化：寬度 100% 方便操作 */
    div.stButton > button {
        background-color: #e1f5fe !important; 
        color: #000000 !important;
        border: 2px solid #01579b !important;
        border-radius: 12px !important;
        width: 100% !important;
        height: 3.5rem !important;
        font-weight: bold !important;
    }

    /* H. LaTeX 顏色鎖定與暗色模式覆蓋 */
    .katex { color: #000000 !important; }
    @media (prefers-color-scheme: dark) {
        .stApp, div[data-testid="stTextInput"] input, section[data-testid="stFileUploader"], [data-testid="stFileUploader"] button, div[data-baseweb="popover"] {
            background-color: #ffffff !important;
            color: #000000 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心助教語音 (iPad 專用 Base64 強效封裝) ---
async def generate_voice_base64(text):
    clean_text = re.sub(r'\$+', '', text)
    clean_text = clean_text.replace('\\%', '百分之').replace('%', '百分之')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('\n', ' ')
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-3%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    b64 = base64.b64encode(audio_data).decode()
    return f'<audio controls autoplay style="width:100%"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# --- 3. 雲端截圖功能 ---
def get_pdf_page_image(pdf_path, page_index):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    return img_data

# --- 4. 生物講義 26 頁熱血中二標題 ---
page_titles = {
    1: "【視覺的覺醒——顯微鏡的物理法則】", 
    2: "【影像的禁忌與雙重存在——複式 vs 解剖】", 
    3: "【生命的架構師——動植物細胞的對稱與偏執】",
    4: "【絕對領域的海關——細胞膜與滲透律法】", 
    5: "【生命的鍊金術——酵素的專一與禁忌】", 
    6: "【靈魂的煉金爐——消化道的長征】",
    7: "【消失的鍊金配方——透明液體的真偽】", 
    8: "素養探究：【失落的太陽碎片——光合作用變因破解(上)】", 
    9: "素養探究：【失落的太陽碎片——光合作用變因破解(下)】", 
    10: "【生命之脈——維管束的昇華與循環】", 
    11: "【生命之流的律法——血管動力與物質交換】", 
    12: "【生命的隱形絲線——內分泌與激素的律法】",
    13: "【靈魂的傳導律法——神經網路與反射弧】", 
    14: "【沈默的位移——植物的向性律法】", 
    15: "【生命的複寫律法——細胞分裂與減數分裂】",
    16: "【血緣的排列組合——ABO 血型律法】", 
    17: "【性別的遺傳烙印——性聯遺傳律法】", 
    18: "【家族的真相——譜系判讀律法】",
    19: "【萬物的真名——二名法與分類階層】", 
    20: "【微觀的混亂——五界分類律法（上）】", 
    21: "【綠色的聖域——植物界的二分律法】",
    22: "【無脊骨的禁軍——無脊椎動物】", 
    23: "【龍骨的傳承——脊椎動物】", 
    24: "【因果的交織網路——直視生物圈底層的生存規律】",
    25: "【吞噬命運的連鎖——階級頂端的毒素聖餐】", 
    26: "【萬物的繁星——在崩解邊緣編織的多樣性之網】"
}

# --- 5. 初始化 Session ---
if 'audio_html' not in st.session_state: st.session_state.audio_html = None

# --- 6. 核心 API 通行證指南 ---
st.title("🔬 生物 AI 生命真理研究室 (助教版)")
st.markdown("""
<div class="guide-box">
    <b>📖 學生快速通行指南：</b><br>
    1. 點擊連結：<a href="https://aistudio.google.com/app/apikey" target="_blank">Google AI Studio</a> 並登入。<br>
    2. 點擊左側 <b>Create API key</b>。<br>
    3. <b>⚠️ 重點：務必勾選兩次同意條款</b>，然後按產生。<br>
    4. 複製那一串英文金鑰，貼回下方「通行證」欄位按 Enter 即可啟動助教。
</div>
""", unsafe_allow_html=True)

user_key = st.text_input("🔑 通行證輸入區：", type="password")
st.divider()

# --- 7. 學生提問區 ---
st.subheader("💬 生命真理提問區")
col_q, col_up = st.columns([1, 1])
with col_q: student_q = st.text_input("打字問助教：", placeholder="例如：酵素的成份是什麼？")
with col_up: uploaded_file = st.file_uploader("拍照或截圖：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("正在調製波霸奶茶並思考答案..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            parts = ["你是資深生物 AI 助教。請用雞排配大杯珍奶解釋。公式必須使用 LaTeX。"]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if student_q: parts.append(student_q)
            res = model.generate_content(parts)
            st.info(f"💡 助教解答：\n\n{res.text}")
        except Exception as e: st.error(f"思考失敗：{e}")

st.divider()

# --- 8. 生命四大門雙選單 ---
st.subheader("📖 翻開真理之書：選擇學習單元")
parts_list = ["【第一門：微觀與鍊金】", "【二：循環與訊息】", "【三：遺傳與複寫】", "【四：分類與生態】"]
part_choice = st.selectbox("第一步：選擇大章節", parts_list)

if "第一門" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 19)
else: r = range(19, 27)

options = [f"第 {p} 頁：{page_titles.get(p, '單元內容')}" for p in r]
selected_page_str = st.selectbox("第二步：選擇精確單元名稱", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

# --- 9. 核心導讀按鈕 ---
if st.button(f"🚀 啟動【第 {target_page} 頁】圖文導讀"):
    if not user_key:
        st.warning("請先輸入金鑰。")
    else:
        genai.configure(api_key=user_key)
        path_finals = os.path.join(os.getcwd(), "data", "Biologyforfinals.pdf")
        with st.spinner("正在調製波霸奶茶..."):
            try:
                # 1. 雲端截圖顯示
                page_img = get_pdf_page_image(path_finals, target_page - 1)
                st.image(page_img, caption=f"講義：{page_titles[target_page]}", use_column_width=True)
                
                # 2. AI 講解
                file_obj = genai.upload_file(path=path_finals)
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = [
                    file_obj, 
                    f"你是資深生物 AI 助教。1. 請針對講義第 {target_page} 頁內容進行精確導讀。"
                    f"2. **【唯一重點】**：只講解第 {target_page} 頁看到的圖表與文字，還有練習題的詳細解說。"
                    "3. 開場白請生活化，一定要提到雞排配大杯珍奶。說各位同學好！今天助教感冒沙啞。"
                    "4. 化學式如 $$C_6H_{12}O_6$$ 必須嚴格使用 LaTeX。5. 最後做重點整理並且提醒學生容易出錯的觀念。"
                ]
                res = model.generate_content(prompt)
                st.markdown(res.text)
                
                # 3. 音訊封裝
                st.session_state.audio_html = asyncio.run(generate_voice_base64(res.text))
                st.balloons()
            except Exception as e: st.error(f"導讀失敗：{e}")

# --- 10. iPad/手機音訊播放區 ---
if st.session_state.audio_html:
    st.markdown("---")
    st.info("🔊 **平板/手機提醒**：請點擊播放鈕聽助教導讀。")
    st.markdown(st.session_state.audio_html, unsafe_allow_html=True)
