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
    st.header("📂 파일 정밀 번역")
    
    # 1. 파일 출처 선택 (라디오 버튼)
    file_source = st.radio("파일을 어디서 가져올까요?", ["내 기기에서 업로드", "서버 저장소에서 선택"], horizontal=True)
    
    final_content = "" # 번역할 최종 텍스트가 담길 곳
    file_name_display = ""

    if file_source == "내 기기에서 업로드":
        uploaded_file = st.file_uploader("파일을 선택하세요", type=['txt', 'json', 'csv', 'xlsx'])
        if uploaded_file is not None:
            final_content = uploaded_file.read().decode("utf-8")
            file_name_display = uploaded_file.name
            st.success(f"✅ 업로드 완료: {file_name_display}")

    else: # 서버 저장소에서 선택 모드
        # 현재 폴더에서 파일 목록 가져오기
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_files = [f for f in os.listdir(current_dir) if f.endswith(('.txt', '.json', '.csv', '.xlsx'))]
        # 2. 번역 실행 (내용이 있을 때만 버튼이 나옵니다)
    if final_content:
        st.divider()
        st.info(f"현재 선택된 파일: **{file_name_display}**")
        
        if st.button("번역 실행하기 🚀"):
            with st.spinner("전문 번역 엔진 가동 중..."):
                try:
                    # 파일 확장자에 따라 번역 방식 결정
                    file_ext = file_name_display.split('.')[-1].lower()
                    
                    if file_ext == 'json':
                        import json
                        json_data = json.loads(final_content)
                        # 윱늅님의 JSON 번역 함수 호출
                        translated_data = translate_json(json_data, source_mode, lang_map[target_lang_name], is_natural)
                        result = json.dumps(translated_data, ensure_ascii=False, indent=4)
                    else:
                        # 일반 텍스트 번역 (한 줄씩 번역)
                        lines = final_content.splitlines()
                        translated_lines = [smart_translate(l, source_mode, lang_map[target_lang_name], is_natural) for l in lines]
                        result = "\n".join(translated_lines)
                    
                    st.success("✅ 번역이 완료되었습니다!")
                    st.text_area("번역 결과", result, height=400)
                    
                    # 결과물 다운로드 버튼
                    st.download_button(
                        label="번역 결과 다운로드 📥",
                        data=result,
                        file_name=f"translated_{file_name_display}",
                        mime="text/plain"
                    )
                
                except Exception as e:
                    st.error(f"번역 중 오류가 발생했습니다: {e}")