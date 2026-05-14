import streamlit as st
import pandas as pd
import os
import json
import time
from streamlit_calendar import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 ---
icon_url = "https://cdn-icons-png.flaticon.com/512/2454/2454282.png" 
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown(f"""
    <style>
    div[data-testid="stStatusWidget"] {{display: none !important;}}
    .stDeployButton {{display:none !important;}}
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    .main .block-container {{padding: 1rem !important;}}
    iframe {{ min-height: 800px !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 연결 및 관리 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# 로딩 속도와 정확도를 위해 ttl을 1초로 설정
@st.cache_data(ttl=1, show_spinner=False)
def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        # 컬럼 순서 및 타입 강제
        df.columns = ['id', '날짜', '구분', '내용', '금액']
        df = df.astype({'id': str, '날짜': str, '구분': str, '내용': str})
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        # 저장 전 데이터 정제
        df['id'] = df['id'].astype(str)
        df['날짜'] = df['날짜'].astype(str)
        df['금액'] = pd.to_numeric(df['금액']).astype(int)
        
        conn.update(spreadsheet=SHEET_URL, data=df)
        st.cache_data.clear() # 캐시 즉시 삭제
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

# --- 3. 입력 팝업 ---
@st.dialog("기록 관리")
def manage_entry(date_str):
    st.write(f"📅 **{date_str}**")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", ""))
    
    # 내역 입력 구역
    with st.container(border=True):
        t = st.selectbox("구분", ["지출", "수입"], key="sel_type")
        c = st.text_input("내용", key="txt_content")
        a = st.number_input("금액", min_value=0, step=100, key="num_amount")
        
        if st.button("저장하기", use_container_width=True, type="primary"):
            if uid:
                new_id = f"{uid}_{int(time.time())}"
                new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [int(a)]})
                updated_df = pd.concat([all_df, new_row], ignore_index=True)
                if save_data(updated_df):
                    st.success("저장되었습니다!")
                    time.sleep(0.5)
                    st.rerun()

    # 기존 내역 표시 및 삭제
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col_t, col_b = st.columns([4, 1])
            icon = "🔴" if row['구분']=="지출" else "🔵"
            col_t.write(f"{icon} {int(row['금액']):,}원 | {row['내용']}")
            if col_b.button("🗑️", key=f"del_{row['id']}"):
                if save_data(all_df[all_df['id'] != row['id']]):
                    st.rerun()

# --- 4. 메인 화면 ---
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'login_page' not in st.session_state: st.session_state.login_page = 'login'

if st.session_state.user_id is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.login_page == 'login':
            st.title("🔐 로그인")
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True, type="primary"):
                users = load_users()
                if uid in users and users[uid] == upw:
                    st.session_state.user_id = uid; st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
            if st.button("회원가입"): st.session_state.login_page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("새 아이디")
            npw = st.text_input("새 비밀번호", type="password")
            if st.button("가입 완료", use_container_width=True):
                if nid and npw:
                    u = load_users(); u[nid] = npw; save_users(u)
                    st.success("가입 성공! 로그인 해주세요.")
                    st.session_state.login_page = 'login'; st.rerun()
            if st.button("취소"): st.session_state.login_page = 'login'; st.rerun()
else:
    st.sidebar.write(f"👤 **{st.session_state.user_id}**님")
    if st.sidebar.button("로그아웃"): st.session_state.user_id = None; st.rerun()

    st.title("💰 가계부")
    data = load_data()
    my_data = data[data['id'].str.startswith(str(st.session_state.user_id), na=False)]
    
    events = []
    for _, r in my_data.iterrows():
        is_exp = r['구분'] == '지출'
        events.append({"id": r['id'], "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", "start": str(r['날짜']), "backgroundColor": "#FF4B4B" if is_exp else "#28A745", "borderColor": "transparent"})

    state = calendar(events=events, options={"initialView": "dayGridMonth", "aspectRatio": 1.1, "locale": "ko"}, key="v16")

    if state.get("dateClick"): manage_entry(state["dateClick"]["date"].split("T")[0])
    elif state.get("eventClick"): manage_entry(state["eventClick"]["event"]["start"].split("T")[0])

    if not my_data.empty:
        st.divider()
        i, e = my_data[my_data['구분'] == '수입']['금액'].sum(), my_data[my_data['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 수입", f"{i:,}원"); c2.metric("이번 달 지출", f"{e:,}원"); c3.metric("남은 잔액", f"{(i-e):,}원")
