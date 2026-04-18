import streamlit as st
from PIL import Image
from googletrans import Translator
import re
import os
import json

# --- 기본 설정 ---
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

@st.cache_resource
def get_translator():
    return Translator()

translator = get_translator()

st.set_page_config(page_title="윱늅이 번역기 V2", layout="wide")

# --- 문맥 다듬기 (자연스럽게 모드용) ---
def polish_context(text):
    # 로컬라이징 시 자주 쓰이는 어투 교정 사전
    replacements = {
        "씨": "님",        # 마녀씨 -> 마녀님
        "당신": "너",      # 상황에 따라 다르지만 보통 서브컬처에선 '너'가 자연스러움
        "그녀": "그 애",
        "그들": "그 사람들",
        "~라고 생각한다": "~인 것 같아", # 문어체를 구어체로
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

# --- 번역 핵심 로직 ---
def smart_translate(text, mode, target_lang, is_natural):
    if not text or not str(text).strip(): return text
    patterns = {"일본어 전체": r'[ぁ-んァ-ヶー一-龠]', "한국어 전체": r'[가-힣]', "영어 전체": r'[a-zA-Z]'}
    
    if re.search(patterns.get(mode, r'.'), str(text)):
        try:
            res = translator.translate(str(text), dest=target_lang)
            translated = res.text
            
            # '자연스럽게' 모드가 켜져 있다면 추가 가공
            if is_natural:
                translated = polish_context(translated)
            
            return translated
        except:
            return text
    return text

# --- JSON 전용 번역 (재귀 함수) ---
def translate_json(data, mode, target_lang, is_natural):
    if isinstance(data, dict):
        return {k: translate_json(v, mode, target_lang, is_natural) for k, v in data.items()}
    elif isinstance(data, list):
        return [translate_json(i, mode, target_lang, is_natural) for i in data]
    elif isinstance(data, str):
        return smart_translate(data, mode, target_lang, is_natural)
    else:
        return data

# --- 사이드바 ---
st.sidebar.title("⚙️ 번역 설정")
source_mode = st.sidebar.selectbox("추출할 언어 필터", ["일본어 전체", "한국어 전체", "영어 전체"])
target_lang_name = st.sidebar.selectbox("결과 언어", ["한국어", "일본어", "영어"])
lang_map = {"한국어": "ko", "일본어": "ja", "영어": "en"}

st.sidebar.divider()
# 번역 모드 선택 추가
st.sidebar.subheader("💎 번역 스타일")
style_mode = st.sidebar.radio("스타일을 선택하세요", ["기본 번역", "자연스럽게 (로컬라이징)"])
is_natural = (style_mode == "자연스럽게 (로컬라이징)")

st.sidebar.divider()
st.sidebar.info("💡 **자연스럽게** 모드는 '~씨'를 '~님'으로 바꾸는 등 한국어 구어체에 맞게 문장을 다듬습니다.")

# --- 메인 메뉴 ---
tabs = st.tabs(["🏠 홈 화면", "📝 텍스트 번역", "📂 파일 번역 (JSON/TXT)"])

# 1. 홈 화면
with tabs[0]:
    st.title("🌍 윱늅이 정밀 번역기에 오신 걸 환영합니다!")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image('mascot.png', use_container_width=True, caption="윱늅님의 전용 마스코트")
        except:
            st.warning("'mascot.png' 파일을 찾을 수 없습니다.")

# 2. 텍스트 번역
with tabs[1]:
    st.header("📝 텍스트 직접 번역")
    input_text = st.text_area("번역할 대사를 입력하세요", height=200)
    if st.button("즉시 번역 시작 ✨"):
        if input_text:
            result = smart_translate(input_text, source_mode, lang_map[target_lang_name], is_natural)
            st.success(result)

# 3. 파일 번역 (JSON/TXT)
with tabs[2]:
    st.header("📂 파일 일괄 번역")
    uploaded_file = st.file_uploader("파일을 선택해주세요", type=['txt', 'json', 'csv', 'log'])
    
    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        
        if st.button(f"{uploaded_file.name} 번역 실행 🚀"):
            with st.spinner("정밀 번역 중..."):
                try:
                    if file_ext == 'json':
                        json_data = json.load(uploaded_file)
                        translated_data = translate_json(json_data, source_mode, lang_map[target_lang_name], is_natural)
                        final_output = json.dumps(translated_data, ensure_ascii=False, indent=4)
                    else:
                        content = uploaded_file.read().decode("utf-8")
                        lines = content.splitlines()
                        translated_lines = [smart_translate(l, source_mode, lang_map[target_lang_name], is_natural) for l in lines]
                        final_output = "\n".join(translated_lines)
                    
                    st.divider()
                    st.text_area("번역 결과 미리보기", final_output, height=200)
                    st.download_button(
                        label="번역된 파일 다운로드 💾",
                        data=final_output,
                        file_name=f"fixed_{uploaded_file.name}",
                        mime="text/plain" if file_ext != 'json' else "application/json"
                    )
                except Exception as e:
                    st.error(f"파일 처리 중 오류 발생: {e}")