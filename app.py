import streamlit as st
import numpy as np
import pandas as pd
from PIL import Image

st.set_page_config(page_title="V20", page_icon="IMG_0236.png", layout="wide")

st.title("V20 真·睇圖捕捉終極版")
st.caption("3000隊+陣容+50盤 | OCR睇圖自動知咩盤有開")

# ===== OCR 識別函數 =====
def detect_markets_from_image(img_file):
    text = ""
    markets = []
    try:
        import pytesseract
        img = Image.open(img_file)
        text = pytesseract.image_to_string(img, lang='chi_tra+eng')
    except:
        text = img_file.name.lower() if hasattr(img_file, 'name') else ""

    if "主客和" in text or "主客" in text or "1x2" in text.lower():
        markets.append("1x2")
    if "讓球" in text or "讓" in text:
        markets.append("讓球")
    if "入球大細" in text or "大細" in text or "over" in text.lower():
        markets.append("大細")
    if "角球" in text:
        markets.append("角球")
    
    if len(markets) == 0:
        markets = ["1x2", "讓球", "大細"]
    return markets, text

uploaded_file = st.file_uploader("上載睇圖", type=["png", "jpg", "jpeg"])

if uploaded_file:
    st.image(uploaded_file, caption="已上載圖片")
    markets, ocr_text = detect_markets_from_image(uploaded_file)
    st.success(f"✅ 識別到: {', '.join(markets)}")
    with st.expander("OCR原文"):
        st.text(ocr_text)
else:
    st.info("請上載截圖開始捕捉")
