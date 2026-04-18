import streamlit as st
from googletrans import Translator
import re
import time
import os
import glob

# --- 0. 페이지 설정 및 전역 스타일 ---
st.set_page_config(page_title="윱늅 번역기", layout="wide")

# 세션 상태 초기화
if 'history' not in st.session_state:
    st.session_state.history = []

# 네온 그린 테마 및 스타일 적용
def apply_custom_style(color):
    st.markdown(f"""
        <style>
        .stButton>button {{
            background-color: {color} !important;
            color: white !important;
            font-weight: bold;
            border-radius: 8px;
            border: none;
            transition: 0.3s;
            width: 100%;
        }}
        .stButton>button:hover {{
            box-shadow: 0 0 15px {color};
            transform: translateY(-2px);
        }}
        .status-card {{
            background-color: #1E1E1E;
            padding: 20px;
            border-radius: 15px;
            border-left: 5px solid {color};
            margin-bottom: 20px;
        }}
        .stTextArea textarea {{
            background-color: #0E1117;
            color: #E0E0E0;
            border: 1px solid #30363D;
        }}
        </style>
    """, unsafe_allow_html=True)

# --- 1. 사이드바 (고정 설정 영역) ---
st.sidebar.header("🎨 워크스테이션 설정")
theme_color = st.sidebar.color_picker("포인트 컬러 (마스코트 매칭)", "#00C853")
apply_custom_style(theme_color)

st.sidebar.divider()
st.sidebar.header("🌐 언어 엔진 (양방향)")
lang_map = {"한국어": "ko", "일본어": "ja", "영어": "en", "중국어": "zh-cn"}
source_name = st.sidebar.selectbox("원본 언어", list(lang_map.keys()), index=1)
target_name = st.sidebar.selectbox("결과 언어", list(lang_map.keys()), index=0)

st.sidebar.divider()
st.sidebar.subheader("🔮 교정 및 품질")
main_mode = st.sidebar.radio("번역 스타일", ["기본 번역", "자연스러운 번역"])
do_spell_check = st.sidebar.checkbox("지능형 맞춤법/문장 정제 활성화", value=True)

st.sidebar.divider()
st.sidebar.subheader("📱 모바일 전용 설정")
local_mode = st.sidebar.checkbox("로컬 경로 직접 접근 모드 (Pydroid용)")

user_dict = {}
selected_sub_mode = "없음"
if main_mode == "자연스러운 번역":
    selected_sub_mode = st.sidebar.radio("세부 교정", ["기본 교정", "자동 교정", "수동 교정"])
    if selected_sub_mode == "수동 교정":
        user_dict_input = st.sidebar.text_area("개별 사전 (씨:님)", "씨:님\n당신:너", height=100)
        for line in user_dict_input.split('\n'):
            if ':' in line:
                old, new = line.split(':'); user_dict[old.strip()] = new.strip()

# --- 2. 핵심 로직 (V25+ 스마트 복구 및 정제) ---
def is_translatable(text):
    return bool(re.search(r'[ぁ-んァ-ヶー一-龠]|[가-힣]|[\u4e00-\u9fff]', text))

def camouflage_text(text):
    brackets = None; prefix = ""; suffix = ""
    if text.startswith('「') and text.endswith('」'): brackets = ('「', '」'); text = text[1:-1]
    elif text.startswith('『') and text.endswith('』'): brackets = ('『', '』'); text = text[1:-1]
    m_lead = re.match(r'^([^ぁ-んァ-ヶー一-龠a-zA-Z0-9가-힣]+)', text)
    if m_lead: prefix = m_lead.group(1); text = text[len(prefix):]
    m_trail = re.search(r'([^ぁ-んァ-ヶー一-龠a-zA-Z0-9가-힣]+)$', text)
    if m_trail: suffix = m_trail.group(1); text = text[:-len(suffix)]
    tags = re.findall(r'\[.*?\]|\{.*?\}', text)
    protected_tags = []
    for i, tag in enumerate(tags):
        placeholder = f"<T{i}>"; protected_tags.append((placeholder, tag)); text = text.replace(tag, placeholder)
    orig_jp = re.findall(r'[ぁぃぅぇぉっゃゅょ～]+', text)
    return text.strip(), {'brackets': brackets, 'prefix': prefix, 'suffix': suffix, 'tags': protected_tags, 'orig_jp': orig_jp}

def reveal_text(text, info):
    broken = ['ㅀ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㅄ', 'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ', '～']
    for jp_char in info['orig_jp']:
        for p in broken:
            if p in text: text = text.replace(p, jp_char, 1); break
    for i, (placeholder, tag) in enumerate(info['tags']):
        text = re.sub(rf'<\s*T{i}\s*>', tag, text, flags=re.IGNORECASE)
    text = info['prefix'] + text + info['suffix']
    if info['brackets']: text = info['brackets'][0] + text + info['brackets'][1]
    text = text.replace('...', '……').replace('?', '？').replace('!', '！')
    if do_spell_check:
        text = text.replace("했읍니다", "했습니다").replace("않하고", "안 하고").replace("가십시요", "가십시오")
    return text.strip()

def apply_correction(text, main_m, sub_m, u_dict):
    if main_m == "자연스러운 번역":
        rules = {"당신": "너", "그녀": "그 애", "녀석": "아이", "하였습니다": "했어", "씨": "님"} if sub_m == "자동 교정" else {"씨": "님"}
        target_dict = u_dict if sub_m == "수동 교정" else rules
        for old, new in target_dict.items(): text = text.replace(old, new)
    return text

def translate_body(content, translator):
    lines = content.split('\n')
    targets = set([re.search(r'"Literal":\s*"(.*?)"', l).group(1) for l in lines if re.search(r'"Literal":\s*"(.*?)"', l)])
    targets = [t for t in targets if is_translatable(t)]
    translated_map = {}
    for t in targets:
        try:
            pt, info = camouflage_text(t)
            res = translator.translate(pt, src=lang_map[source_name], dest=lang_map[target_name]).text
            translated_map[t] = apply_correction(reveal_text(res, info), main_mode, selected_sub_mode, user_dict)
            time.sleep(0.02)
        except: translated_map[t] = t
    final_output = []
    for line in lines:
        match = re.search(r'"Literal":\s*"(.*?)"', line)
        if match and match.group(1) in translated_map:
            line = line.replace(f'"{match.group(1)}"', f'"{translated_map[match.group(1)]}"')
        final_output.append(line)
    return '\n'.join(final_output)

# --- 3. 메인 화면 구성 ---
st.markdown(f"### 윱늅이의 이상한 야매 번역기")
tab_home, tab_file, tab_text = st.tabs(["🏠 홈", "📂 파일 번역 모드", "📝 텍스트 전용 모드"])

with tab_home:
    col1, col2 = st.columns([1, 2])
    with col1:
        if os.path.exists("mascot.png"):
            st.image("mascot.png", use_container_width=True)
        else:
            st.info("🎨 mascot.png 파일을 올려주세요.")
    with col2:
        st.title("Welcome, Master.")
        st.markdown(f"""
            <div class="status-card">
                <h3>"윱늅이의 야매 번역기"</h3>
                <p>코딩은 처음이라 버그가 있을 수도 있어요. 그래도 기본적인 기능은<br>
                제없이 잘 작동할 거예요. 앞으로 계속 보강해 나갈게요.</p>
            </div>
        """, unsafe_allow_html=True)

with tab_file:
    st.header("📂 JSON 무결점 파일 번역기")
    if local_mode:
        local_path = st.text_input("게임 데이터 폴더 경로 입력", "")
        if st.button("🚀 폴더 내 모든 JSON 번역 시작") and local_path:
            json_files = glob.glob(os.path.join(local_path, "*.json"))
            if not json_files: st.error("해당 경로에 JSON 파일이 없습니다.")
            else:
                translator = Translator()
                for file_path in json_files:
                    with st.status(f"파일 처리 중: {os.path.basename(file_path)}"):
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            body = f.read()
                        result = translate_body(body, translator)
                        with open(file_path, 'w', encoding='utf-8') as f:
                            f.write(result)
                st.success("✅ 모든 파일이 번역되어 덮어쓰기 완료되었습니다!")
    else:
        uploaded_files = st.file_uploader("JSON 파일들을 업로드하세요", accept_multiple_files=True)
        if uploaded_files and st.button("🚀 일괄 번역 시작"):
            translator = Translator()
            for up_file in uploaded_files:
                with st.status(f"'{up_file.name}' 가공 중..."):
                    body = up_file.read().decode('utf-8', errors='ignore')
                    result = translate_body(body, translator)
                    st.download_button(f"📥 {up_file.name} 저장", result, f"ko_{up_file.name}")

with tab_text:
    st.header("📝 전문가용 텍스트 워크스테이션")
    col_in, col_out = st.columns(2)
    with col_in:
        raw_input = st.text_area("원본 입력", height=300)
        trans_opt = st.radio("방식", ["한 줄씩 번역", "통째로 번역"], horizontal=True)
    with col_out:
        res_area = st.empty()
    if st.button("🚀 번역 실행"):
        if raw_input.strip():
            translator = Translator()
            if trans_opt == "한 줄씩 번역":
                results = []
                for l in raw_input.split('\n'):
                    if not l.strip(): results.append(""); continue
                    pt, info = camouflage_text(l)
                    res = translator.translate(pt, src=lang_map[source_name], dest=lang_map[target_name]).text
                    results.append(apply_correction(reveal_text(res, info), main_mode, selected_sub_mode, user_dict))
                final_text = "\n".join(results)
            else:
                pt, info = camouflage_text(raw_input)
                res = translator.translate(pt, src=lang_map[source_name], dest=lang_map[target_name]).text
                final_text = apply_correction(reveal_text(res, info), main_mode, selected_sub_mode, user_dict)
            res_area.text_area("번역 결과", final_text, height=300)
            st.session_state.history.insert(0, {"time": time.strftime("%H:%M:%S"), "in": raw_input[:30], "out": final_text})
            st.toast("✅ 히스토리에 저장되었습니다!", icon="🛡️")

    if st.session_state.history:
        st.divider()
        for h in st.session_state.history:
            with st.expander(f"[{h['time']}] {h['in']}..."): st.write(h['out'])
