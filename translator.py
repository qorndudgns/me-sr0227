import streamlit as st
from PIL import Image
from googletrans import Translator
import re
import os
import json

# --- 1. 초기 시스템 및 경로 설정 ---
# 서버 환경에서 경로 오류를 방지하기 위해 실행 파일 기준으로 경로를 고정합니다.
try:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    os.chdir(BASE_DIR)
except:
    BASE_DIR = os.getcwd()

@st.cache_resource
def get_translator():
    return Translator()

translator = get_translator()

# 페이지 설정
st.set_page_config(page_title="윱늅이 번역기 V2", layout="wide", page_icon="🌍")

# --- 2. 번역 및 텍스트 가공 로직 ---
def polish_context(text):
    """로컬라이징 시 자연스러운 한국어 구어체로 교정 (딕셔너리 기반)"""
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
    """핵심 번역 함수 (언어 필터링 및 에러 방지 포함)"""
    if not text or not str(text).strip():
        return text
    
    # 언어별 정규식 패턴
    patterns = {
        "일본어 전체": r'[ぁ-んァ-ヶー一-龠]',
        "한국어 전체": r'[가-힣]',
        "영어 전체": r'[a-zA-Z]'
    }
    
    # 해당 언어가 포함된 경우에만 번역 시도
    if re.search(patterns.get(mode, r'.'), str(text)):
        try:
            res = translator.translate(str(text), dest=target_lang)
            translated = res.text
            if is_natural:
                translated = polish_context(translated)
            return translated
        except Exception:
            # 번역 API 오류 시 원문 그대로 반환하여 앱 중단 방지
            return text
    return text

def translate_json(data, mode, target_lang, is_natural):
    """JSON 구조를 유지하며 내용만 번역 (재귀 함수)"""
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
tabs = st.tabs(["🏠 홈 화면", "📝 텍스트 번역", "📂 서버 파일 탐색기"])

# [탭 1] 홈 화면
with tabs[0]:
    st.title("🌍 윱늅이 정밀 번역기")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # mascot.png 파일이 없을 때 빨간 에러 화면이 뜨는 것을 방지
        if os.path.exists('mascot.png'):
            try:
                st.image('mascot.png', use_container_width=True, caption="윱늅님의 전용 마스코트")
            except Exception as e:
                st.warning("이미지를 불러오는 중 문제가 발생했습니다.")
        else:
            st.info("💡 'mascot.png' 파일을 찾을 수 없습니다. 이미지를 보고 싶다면 깃허브에 업로드해 주세요!")

# [탭 2] 텍스트 번역
with tabs[1]:
    st.header("📝 텍스트 직접 번역")
    # key 값을 지정하여 상태 유지를 돕습니다.
    input_text = st.text_area("번역할 대사를 입력하세요", height=250, key="text_input_area")
    
    if st.button("즉시 번역 시작 ✨"):
        if input_text.strip():
            with st.spinner("번역 엔진 가동 중..."):
                result = smart_translate(input_text, source_mode, lang_map[target_lang_name], is_natural)
                st.success("✅ 번역이 완료되었습니다!")
                st.text_area("번역 결과", result, height=250, key="text_output_area")
        else:
            st.warning("내용을 입력해 주세요.")
            # [탭 3] 서버 파일 탐색기 (파일 관리자 스타일)
with tabs[2]:
    st.header("📂 서버 파일 탐색기")

    # 1. 경로 및 세션 변수 초기화 (에러 방지용)
    if 'current_path' not in st.session_state:
        st.session_state.current_path = BASE_DIR
    if 'file_content' not in st.session_state:
        st.session_state.file_content = None
    if 'target_name' not in st.session_state:
        st.session_state.target_name = ""

    # 2. 경로 내비게이션 UI
    # 루트 경로와 현재 경로를 비교하여 현재 위치를 표시합니다.
    try:
        rel_display = os.path.relpath(st.session_state.current_path, BASE_DIR)
    except:
        rel_display = "."
    
    display_name = "루트(🏠)" if rel_display == "." else rel_display
    st.write(f"📁 **현재 위치:** `{display_name}`")

    # 상위 폴더 이동 버튼
    if st.session_state.current_path != BASE_DIR:
        if st.button("⬅️ 상위 폴더로 이동"):
            st.session_state.current_path = os.path.dirname(st.session_state.current_path)
            st.rerun()

    st.divider()

    # 3. 폴더 및 파일 리스트업 (시스템 파일 제외)
    try:
        all_items = os.listdir(st.session_state.current_path)
        # 점(.)으로 시작하는 설정 파일이나 시스템 폴더는 제외
        valid_items = [i for i in all_items if not i.startswith(('.', '__'))]
        
        folders = sorted([i for i in valid_items if os.path.isdir(os.path.join(st.session_state.current_path, i))])
        # 번역 가능한 확장자만 필터링
        target_exts = ('.txt', '.json', '.csv', '.xlsx')
        files = sorted([i for i in valid_items if os.path.isfile(os.path.join(st.session_state.current_path, i)) and i.lower().endswith(target_exts)])
    except Exception as e:
        st.error(f"디렉토리를 읽는 중 오류가 발생했습니다: {e}")
        folders, files = [], []

    # 4. 탐색기 목록 표시
    if not folders and not files:
        st.info("이 위치에는 번역 가능한 파일이 없습니다.")

    # 폴더 버튼 (클릭 시 이동)
    for folder in folders:
        if st.button(f"📁 {folder}/", key=f"dir_{folder}", use_container_width=True):
            st.session_state.current_path = os.path.join(st.session_state.current_path, folder)
            st.rerun()

    # 파일 버튼 (클릭 시 선택)
    for file in files:
        if st.button(f"📄 {file}", key=f"file_{file}", use_container_width=True):
            full_path = os.path.join(st.session_state.current_path, file)
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    st.session_state.file_content = f.read()
                st.session_state.target_name = os.path.relpath(full_path, BASE_DIR)
                st.success(f"✅ 선택된 파일: {file}")
            except Exception as e:
                st.error(f"파일을 읽을 수 없습니다: {e}")

    # 5. 번역 실행 섹션
    if st.session_state.file_content:
        st.divider()
        st.subheader(f"🎯 번역 대상: {os.path.basename(st.session_state.target_name)}")
        
        if st.button("🚀 이 파일 번역 시작", type="primary", use_container_width=True):
            with st.spinner("로컬라이징 작업 중..."):
                try:
                    ext = st.session_state.target_name.split('.')[-1].lower()
                    if ext == 'json':
                        data = json.loads(st.session_state.file_content)
                        res = translate_json(data, source_mode, lang_map[target_lang_name], is_natural)
                        res_text = json.dumps(res, ensure_ascii=False, indent=4)
                    else:
                        lines = st.session_state.file_content.splitlines()
                        t_lines = [smart_translate(l, source_mode, lang_map[target_lang_name], is_natural) for l in lines]
                        res_text = "\n".join(t_lines)
                    
                    st.success("✨ 번역이 완료되었습니다!")
                    st.text_area("미리보기", res_text, height=300)
                    st.download_button(
                        label="번역 결과 다운로드 📥",
                        data=res_text,
                        file_name=f"translated_{os.path.basename(st.session_state.target_name)}",
                        use_container_width=True
                    )
                except Exception as e:
                    st.error(f"번역 중 오류가 발생했습니다: {e}")