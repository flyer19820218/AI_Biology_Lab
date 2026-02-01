import streamlit as st
import google.generativeai as genai
import os
import asyncio
import edge_tts
import fitz  # 雲端自動截圖 (PyMuPDF)
import re
import base64
from PIL import Image

# --- 1. 頁面配置 (全黑翩翩體、全黑文字、適應行動端) ---
st.set_page_config(page_title="生物 AI 生命真理研究室", layout="wide")

st.markdown("""
    <style>
    html, body, [class*="css"], .stMarkdown, p, h1, h2, h3, span, label, li {
        color: #000000 !important;
        font-family: 'HanziPen SC', '翩翩體', 'KaiTi', sans-serif !important;
    }
    .guide-box {
        background-color: #e1f5fe;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #03a9f4;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #fce4ec !important;
        border-radius: 8px;
        font-weight: bold;
        width: 100%;
        height: 50px;
        font-size: 1.2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 核心助教語音 (iPad 專用 Base64 封裝) ---
async def generate_voice_base64(text):
    # 移除 LaTeX 與特殊字符，將 % 唸成「百分之」
    clean_text = re.sub(r'\$+', '', text)
    clean_text = clean_text.replace('\\%', '百分之').replace('%', '百分之')
    clean_text = clean_text.replace('*', '').replace('#', '').replace('\n', ' ')
    communicate = edge_tts.Communicate(clean_text, "zh-TW-HsiaoChenNeural", rate="-3%")
    audio_data = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data += chunk["data"]
    b64 = base64.b64encode(audio_data).decode()
    return f'<audio controls style="width:100%"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'

# --- 3. 雲端截圖功能 (穩定標準模式) ---
def get_pdf_page_image(pdf_path, page_index):
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_index)
    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
    img_data = pix.tobytes("png")
    doc.close()
    return img_data

# --- 4. 生物講義 26 頁熱血標題 (精確對位修正版) ---
page_titles = {
    1: "【視覺的覺醒：顯微鏡的物理法則】", 2: "【影像的禁忌與雙重存在：複式 vs 解剖】", 3: "【生命的架構師：細胞的對稱與偏執】",
    4: "【絕對領域的海關：細胞膜與滲透律法】", 5: "【生命的鍊金術：酵素的專一與禁忌】", 6: "【靈魂的煉金爐：消化道的長征】",
    7: "【消失的鍊金配方：透明液體的真偽】", 
    8: "【失落的太陽碎片：光合作用變因破解(上)】", 
    9: "【失落的太陽碎片：光合作用變因破解(下)】", 
    10: "【生命之脈：維管束的昇華與循環】", 11: "【生命之流律法：血管動力與物質交換】", 12: "【生命的隱形絲線：內分泌與激素】",
    13: "【靈魂傳導律法：神經網路與反射弧】", 14: "【沈默的位移：植物的向性律法】", 15: "【生命的複寫律法：分裂與減數】",
    16: "【血緣的排列組合：ABO 血型律法】", 17: "【性別的遺傳烙印：性聯遺傳律法】", 18: "【家族的真相：譜系判讀律法】",
    19: "【萬物的真名：二名法與分類階層】", 20: "【微觀的混亂：五界分類律法(上)】", 21: "【綠色的聖域：植物界的二分律法】",
    22: "【無脊骨的禁軍：無脊椎動物概論】", 23: "【龍骨的傳承：脊椎動物演化】", 24: "【因果交織網路：生物圈生存規律】",
    25: "【吞噬命運連鎖：階級頂端毒素聖餐】", 26: "【萬物的繁星：多樣性之網】"
}

# --- 5. 初始化 Session ---
if 'audio_html' not in st.session_state: st.session_state.audio_html = None

st.title("🔬 生物 AI 生命真理研究室 (助教版)")
st.markdown("""<div class="guide-box"><b>📖 快速指南：</b>貼上通行證後，選擇生命大門即可啟動。</div>""", unsafe_allow_html=True)
user_key = st.text_input("🔑 通行證：", type="password")

st.divider()

# --- 6. 學生提問專區 ---
st.subheader("💬 生命真理提問區")
student_q = st.text_input("打字問助教：")
uploaded_file = st.file_uploader("拍下觀察截圖：", type=["jpg", "png", "jpeg"])

if (student_q or uploaded_file) and user_key:
    with st.spinner("正在調製波霸奶茶並翻閱生命卷軸..."):
        try:
            genai.configure(api_key=user_key)
            model = genai.GenerativeModel('models/gemini-2.5-flash')
            parts = ["你是資深生物 AI 助教。用雞排配大杯珍奶解釋。公式使用 LaTeX。"]
            if uploaded_file: parts.append(Image.open(uploaded_file))
            if student_q: parts.append(student_q)
            res = model.generate_content(parts)
            st.info(f"💡 助教解答：\n\n{res.text}")
        except Exception as e: st.error(f"思考失敗：{e}")

st.divider()

# --- 7. 生命四大門雙選單 (26 頁不跳頁修正) ---
st.subheader("📖 翻開真理之書：選擇學習單元")
parts_list = ["【第一門：微觀與鍊金】", "【二：循環與訊息】", "【三：遺傳與複寫】", "【四：分類與生態】"]
part_choice = st.selectbox("第一層：選擇大章節", parts_list)

if "第一門" in part_choice: r = range(1, 8)
elif "二" in part_choice: r = range(8, 15)
elif "三" in part_choice: r = range(15, 19)
else: r = range(19, 27)

options = [f"第 {p} 頁：{page_titles.get(p, '單元內容')}" for p in r]
selected_page_str = st.selectbox("第二層：選擇精確單元名稱", options)
target_page = int(re.search(r"第 (\d+) 頁", selected_page_str).group(1))

# --- 8. 核心導讀按鈕 ---
if st.button(f"🚀 啟動【第 {target_page} 頁】圖文導讀"):
    if not user_key:
        st.warning("請先輸入金鑰。")
    else:
        path_finals = os.path.join(os.getcwd(), "data", "Biologyforfinals.pdf")
        with st.spinner("正在調製波霸奶茶..."):
            try:
                # 1. 雲端截圖
                page_img = get_pdf_page_image(path_finals, target_page - 1)
                st.image(page_img, caption=f"講義：{page_titles[target_page]}", use_column_width=True)
                
                # 2. AI 講解 (講義優先)
                genai.configure(api_key=user_key)
                file_obj = genai.upload_file(path=path_finals)
                model = genai.GenerativeModel('models/gemini-2.5-flash')
                prompt = [
                    file_obj, 
                    f"你是生物 AI 助教。詳細導讀講義第 {target_page} 頁。開場提到雞排配大杯珍奶。公式必須 LaTeX。絕對不准出測驗。"
                ]
                res = model.generate_content(prompt)
                st.markdown(res.text)
                
                # 3. iPad 音訊封裝
                st.session_state.audio_html = asyncio.run(generate_voice_base64(res.text))
                st.balloons()
            except Exception as e: st.error(f"解析失敗：{e}")

# --- 9. iPad 音訊解鎖區 ---
if st.session_state.audio_html:
    st.markdown("---")
    st.info("🔊 **平板導讀提醒**：請點擊播放鈕，聽取生命真理。")
    st.markdown(st.session_state.audio_html, unsafe_allow_html=True)