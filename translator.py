import streamlit as st
from PIL import Image
from googletrans import Translator
import re
import os
import json

# --- 1. 초기 시스템 설정 ---
try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

@st.cache_resource
def get_translator():
    return Translator()

translator = get_translator()

st.set_page_config(page_title="윱늅이 번역기 V2", layout="wide")

# --- 2. 번역 가공 로직 ---
def polish_context(text):
    """로컬라이징 시 자연스러운 한국어 구어체로 교정"""
    replacements = {
        "씨": "님",
        "당신": "너",
        "그녀": "그 애",
        "그들": "그 사람들",
        "~라고 생각한다": "~인 것 같아",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def smart_translate(text, mode, target_lang, is_natural):
    """핵심 번역 함수 (언어 필터링 포함)"""
    if not text or not str(text).strip(): return text
    
    # 언어별 정규식 패턴
    patterns = {
        "일본어 전체": r'[ぁ-んァ-ヶー一-龠]',
        "한국어 전체": r'[가-힣]',
        "영어 전체": r'[a-zA-Z]'
    }
    
    # 선택된 모드의 글자가 포함되어 있을 때만 번역 실행
    if re.search(patterns.get(mode, r'.'), str(text)):
        try:
            res = translator.translate(str(text), dest=target_lang)
            translated = res.text
            if is_natural:
                translated = polish_context(translated)
            return translated
        except:
            return text
    return text

def translate_json(data, mode, target_lang, is_natural):
    """JSON 데이터를 재귀적으로 뒤지며 번역"""
    if isinstance(data, dict):
        return {k: translate_json(v, mode, target_lang, is_natural) for k, v in data.items()}
    elif isinstance(data, list):
        return [translate_json(i, mode, target_lang, is_natural) for i in data]
    elif isinstance(data, str):
        return smart_translate(data, mode, target_lang, is_natural)
    else:
        return data

# --- 3. 사이드바 UI (설정) ---
st.sidebar.title("⚙️ 번역 설정")
source_mode = st.sidebar.selectbox("추출할 언어 필터", ["일본어 전체", "한국어 전체", "영어 전체"])
target_lang_name = st.sidebar.selectbox("결과 언어", ["한국어", "일본어", "영어"])
lang_map = {"한국어": "ko", "일본어": "ja", "영어": "en"}

st.sidebar.divider()
st.sidebar.subheader("💎 번역 스타일")
style_mode = st.sidebar.radio("스타일을 선택하세요", ["기본 번역", "자연스럽게 (로컬라이징)"])
is_natural = (style_mode == "자연스럽게 (로컬라이징)")

st.sidebar.divider()
st.sidebar.info("💡 **자연스럽게** 모드는 구어체 교정 기능을 포함합니다.")

# --- 4. 메인 메뉴 (탭 구성) ---
tabs = st.tabs(["🏠 홈 화면", "📝 텍스트 번역", "📂 파일 번역 (JSON/TXT)"])
# --- 5. 탭별 상세 내용 ---

# [탭 1] 홈 화면
with tabs[0]:
    st.title("🏠 홈 화면")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            st.image('mascot.png', use_container_width=True, caption="윱늅님의 전용 마스코트")
        except:
            st.warning("'mascot.png' 파일을 찾을 수 없습니다. 깃허브에 이미지가 있는지 확인해 주세요.")
    st.info("왼쪽 사이드바에서 언어 필터와 번역 스타일을 먼저 설정해 주세요!")

# [탭 2] 텍스트 번역
with tabs[1]:
    st.header("📝 텍스트 직접 번역")
    input_text = st.text_area("번역할 대사를 입력하세요", height=250, placeholder="여기에 내용을 붙여넣으세요...")
    
    if st.button("즉시 번역 시작 ✨"):
        if input_text.strip():
            with st.spinner("번역 엔진 가동 중..."):
                result = smart_translate(input_text, source_mode, lang_map[target_lang_name], is_natural)
                st.success("✅ 번역이 완료되었습니다!")
                st.text_area("번역 결과", result, height=250)
        else:
            st.warning("번역할 내용을 입력해 주세요.")

# [탭 3] 파일 번역 (핵심: 세션 상태 유지)
with tabs[2]:
    st.header("📂 파일 정밀 번역")

    # 세션 상태(기억 저장소) 초기화
    if 'file_content' not in st.session_state:
        st.session_state.file_content = None
    if 'target_name' not in st.session_state:
        st.session_state.target_name = ""

    file_source = st.radio("파일 출처를 선택하세요", ["내 기기에서 업로드", "서버 저장소"], horizontal=True)

    if file_source == "내 기기에서 업로드":
        uploaded_file = st.file_uploader("파일 선택 (txt, json, csv, xlsx)", type=['txt', 'json', 'csv', 'xlsx'])
        if uploaded_file:
            st.session_state.file_content = uploaded_file.read().decode("utf-8")
            st.session_state.target_name = uploaded_file.name
            st.success(f"✅ {st.session_state.target_name} 준비 완료!")

    else: # 서버 저장소 모드
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_files = []
        # 하위 폴더까지 탐색
        for root, dirs, files in os.walk(current_dir):
            if '.git' in root or '.streamlit' in root: continue
            for f in files:
                if f.endswith(('.txt', '.json', '.csv', '.xlsx')):
                    rel_path = os.path.relpath(os.path.join(root, f), current_dir)
                    server_files.append(rel_path)
        server_files.sort()

        if server_files:
            target_file = st.selectbox("번역할 서버 파일을 선택하세요", server_files)
            if st.button("파일 불러오기"):
                full_path = os.path.join(current_dir, target_file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    st.session_state.file_content = f.read()
                st.session_state.target_name = target_file
                st.success(f"✅ '{target_file}' 로드 성공!")
        else:
            st.warning("서버에 번역 가능한 파일이 없습니다.")

    # 파일이 불러와진 상태에서만 번역 실행 버튼 노출
    if st.session_state.file_content:
        st.divider()
        st.info(f"현재 선택된 파일: **{st.session_state.target_name}**")
        
        if st.button("번역 실행하기 🚀"):
            with st.spinner("전문 번역 엔진 가동 중... 잠시만 기다려 주세요."):
                try:
                    f_ext = st.session_state.target_name.split('.')[-1].lower()
                    
                    if f_ext == 'json':
                        data = json.loads(st.session_state.file_content)
                        translated_res = translate_json(data, source_mode, lang_map[target_lang_name], is_natural)
                        final_res = json.dumps(translated_res, ensure_ascii=False, indent=4)
                    else:
                        lines = st.session_state.file_content.splitlines()
                        translated_lines = [smart_translate(l, source_mode, lang_map[target_lang_name], is_natural) for l in lines]
                        final_res = "\n".join(translated_lines)
                    
                    st.success("✅ 파일 전체 번역 완료!")
                    st.text_area("번역 결과 미리보기", final_res, height=350)
                    
                    # 다운로드 버튼 생성
                    st.download_button(
                        label="번역 결과 파일로 저장 📥",
                        data=final_res,
                        file_name=f"translated_{st.session_state.target_name}",
                        mime="text/plain"
                    )
                except Exception as e:
                    st.error(f"번역 도중 오류가 발생했습니다: {e}")