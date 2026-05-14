import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 구글 시트 연결 (사용자님 주소 고정) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        required_cols = ['id', '날짜', '구분', '내용', '금액']
        for col in required_cols:
            if col not in df.columns: return pd.DataFrame(columns=required_cols)
        df['id'] = df['id'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        conn.update(spreadsheet=SHEET_URL, data=df)
    except Exception as e:
        st.error(f"저장 실패: {e}")

# --- 2. 사용자 관리 ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- 3. 화면 설정 (달력 크기 최적화) ---
st.set_page_config(page_title="내 손안의 가계부", layout="wide")

# CSS를 사용하여 달력 영역의 높이를 강제로 조절합니다.
st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    iframe { min-height: 700px !important; } 
    </style>
    """, unsafe_allow_html=True)

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'login_page' not in st.session_state: st.session_state.login_page = 'login'

# --- 4. [팝업창] 내역 관리 ---
@st.dialog("상세 내역")
def manage_date_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    user_id_str = str(st.session_state.user_id)
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(user_id_str, na=False))]
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"])
        c = c2.text_input("내용", placeholder="항목명")
        a = c3.number_input("금액", min_value=0, step=100)
        if st.button("내역 추가하기", use_container_width=True, type="primary"):
            new_id = f"{user_id_str}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c if c else ""], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            with st.expander(f"{row['구분']} | {int(row['금액']):,}원 | {row['내용']}"):
                ec = st.text_input("내용 수정", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("금액 수정", value=int(row['금액']), key=f"e_a_{row['id']}")
                col1, col2 = st.columns(2)
                if col1.button("수정", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액']] = [ec, ea]
                    save_data(all_df); st.rerun()
                if col2.button("삭제", key=f"btn_d_{row['id']}", use_container_width=True):
                    save_data(all_df[all_df['id'] != row['id']]); st.rerun()

# --- 5. 메인 로직 ---
if st.session_state.user_id is None:
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.session_state.login_page == 'login':
            st.title("🔐 로그인")
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True, type="primary"):
                users = load_users()
                if uid in users and users[uid] == upw:
                    st.session_state.user_id = uid; st.rerun()
                else: st.error("정보가 틀립니다.")
            if st.button("회원가입"): st.session_state.login_page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("아이디")
            npw = st.text_input("비밀번호", type="password")
            if st.button("가입 완료"):
                if nid and npw:
                    u = load_users(); u[nid] = npw; save_users(u)
                    st.session_state.login_page = 'login'; st.rerun()
            if st.button("취소"): st.session_state.login_page = 'login'; st.rerun()
else:
    # 로그인 상태: 사이드바에 정보 표시
    st.sidebar.subheader(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃", use_container_width=True): 
        st.session_state.user_id = None; st.rerun()

    current_data = load_data()
    user_id_str = str(st.session_state.user_id)
    user_df = current_data[current_data['id'].str.startswith(user_id_str, na=False)]
    
    st.title("💰 우리집 클라우드 가계부")
    
    events = []
    for _, r in user_df.iterrows():
        is_exp = r['구분'] == '지출'
        t = f"{'-' if is_exp else '+'} {int(r['금액']):,}"
        events.append({"id": r['id'], "title": t, "start": str(r['날짜']), "backgroundColor": "#FF4B4B" if is_exp else "#28A745"})

    # 달력 옵션: aspectRatio를 낮춰서 세로 길이를 더 길게 만듭니다.
    cal_options = {
        "initialView": "dayGridMonth",
        "selectable": True,
        "locale": "ko",
        "aspectRatio": 1.0, # 1.0에 가까울수록 달력이 정사각에 가깝고 커집니다.
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,dayGridWeek"},
    }
    
    state = calendar(events=events, options=cal_options, key="big_calendar")

    if state.get("dateClick"):
        manage_date_entry(state["dateClick"]["date"].split("T")[0])
    elif state.get("eventClick"):
        manage_date_entry(state["eventClick"]["event"]["start"].split("T")[0])

    if not user_df.empty:
        st.divider()
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입 합계", f"{i:,}원")
        c2.metric("지출 합계", f"{e:,}원")
        c3.metric("남은 잔액", f"{(i-e):,}원", delta_color="normal")
