import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection
from cookies_manager import EncryptedCookieManager # 쿠키 관리자 추가

# --- 1. 쿠키 관리자 설정 ---
# 암호화 키는 아무 문자나 길게 입력하시면 됩니다.
cookies = EncryptedCookieManager(password="가계부_비밀_비밀번호_12345")
if not cookies.ready():
    st.stop()

# --- 2. 구글 시트 연결 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        df['id'] = df['id'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    conn.update(spreadsheet=SHEET_URL, data=df)

# --- 3. 사용자 관리 ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="자동 로그인 가계부", layout="wide")

# 쿠키에서 저장된 user_id 가져오기
saved_user_id = cookies.get("saved_user_id")

if 'user_id' not in st.session_state:
    st.session_state.user_id = saved_user_id # 쿠키 값이 있으면 자동으로 세션에 할당

if 'login_page' not in st.session_state:
    st.session_state.login_page = 'login'

# --- 4. [팝업창] 내역 관리 (기존과 동일) ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    all_df = load_data()
    user_day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(str(st.session_state.user_id), na=False))]
    
    with st.container(border=True):
        st.markdown("**➕ 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="in_t")
        c = c2.text_input("내용", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
        if st.button("구글 시트에 저장", use_container_width=True):
            new_id = f"{st.session_state.user_id}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c if c else ""], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    st.markdown("**📑 기존 기록**")
    if not user_day_df.empty:
        for _, row in user_day_df.iterrows():
            with st.expander(f"{row['구분']} | {int(row['금액']):,}원"):
                ec = st.text_input("내용", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("금액", value=int(row['금액']), key=f"e_a_{row['id']}")
                if st.button("수정", key=f"btn_e_{row['id']}"):
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액']] = [ec, ea]
                    save_data(all_df); st.rerun()
                if st.button("삭제", key=f"btn_d_{row['id']}", type="primary"):
                    save_data(all_df[all_df['id'] != row['id']]); st.rerun()

# --- 5. 메인 로직 ---
if st.session_state.user_id is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.login_page == 'login':
            st.title("🔐 로그인")
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                users = load_users()
                if uid in users and users[uid] == upw:
                    st.session_state.user_id = uid
                    # 로그인 성공 시 쿠키에 30일 동안 아이디 저장
                    cookies["saved_user_id"] = uid
                    cookies.save()
                    st.rerun()
                else: st.error("정보가 틀립니다.")
            if st.button("회원가입"): st.session_state.login_page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("아이디")
            npw = st.text_input("비밀번호", type="password")
            if st.button("가입"):
                u = load_users(); u[nid] = npw; save_users(u)
                st.session_state.login_page = 'login'; st.rerun()
else:
    # 가계부 화면
    st.sidebar.write(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None
        # 로그아웃 시 쿠키 삭제
        if "saved_user_id" in cookies:
            del cookies["saved_user_id"]
            cookies.save()
        st.rerun()

    user_df_all = load_data()
    user_df = user_df_all[user_df_all['id'].astype(str).str.startswith(str(st.session_state.user_id), na=False)]
    
    st.title("💰 영구보관 가계부")
    events = []
    for _, r in user_df.iterrows():
        is_exp = r['구분'] == '지출'
        t = f"{'-' if is_exp else '+'} {int(r['금액']):,}"
        events.append({"id": str(r['id']), "title": t, "start": str(r['날짜']), "backgroundColor": "#FF4B4B" if is_exp else "#28A745"})

    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "aspectRatio": 1.2, "locale": "ko"}, key="cal_cookie")

    if state.get("dateClick"):
        raw = state["dateClick"]["date"]
        target_date = (datetime.strptime(raw.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f") + timedelta(hours=9)).strftime("%Y-%m-%d")
        manage_date_entry(target_date)
    elif state.get("eventClick"):
        target_date = state["eventClick"]["event"]["start"].split("T")[0]
        manage_date_entry(target_date)

    if not user_df.empty:
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입", f"{i:,}원"); c2.metric("지출", f"{e:,}원"); c3.metric("잔액", f"{(i-e):,}원")
