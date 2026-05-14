import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 구글 시트 연결 설정 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 데이터를 읽어온 후 빈 값이나 컬럼 오류 방지
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        # 모든 컬럼이 문자열/숫자 형식이 맞는지 강제 변환
        df['id'] = df['id'].astype(str)
        return df
    except Exception:
        # 시트가 아예 비어있거나 접근이 안 될 때 기본 구조 반환
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        conn.update(spreadsheet=SHEET_URL, data=df)
    except Exception as e:
        st.error(f"구글 시트 저장 오류: {e}")

# --- 2. 사용자 관리 ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

st.set_page_config(page_title="영구보관 가계부", layout="wide")

if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'login_page' not in st.session_state: st.session_state.login_page = 'login'

# --- 3. [팝업창] 내역 관리 ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    all_df = load_data()
    
    # 안전하게 필터링 (id가 문자열인지 확인)
    user_day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(str(st.session_state.user_id), na=False))]
    
    with st.container(border=True):
        st.markdown("**➕ 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="in_t")
        c = c2.text_input("내용", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
        
        if st.button("구글 시트에 저장", use_container_width=True):
            new_id = f"{st.session_state.user_id}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({
                'id': [new_id], '날짜': [date_str], '구분': [t], 
                '내용': [c if c else ""], '금액': [a]
            })
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    st.markdown("**📑 기존 기록**")
    if user_day_df.empty: st.info("기록 없음")
    else:
        for _, row in user_day_df.iterrows():
            prefix = "🔴 -" if row['구분'] == '지출' else "🔵 +"
            label = f"{prefix} {int(row['금액']):,}" + (f" | {row['내용']}" if row['내용'] else "")
            with st.expander(label):
                ec = st.text_input("내용 수정", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("금액 수정", value=int(row['금액']), key=f"e_a_{row['id']}")
                if st.button("수정 완료", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액']] = [ec, ea]
                    save_data(all_df); st.rerun()
                if st.button("삭제하기", key=f"btn_d_{row['id']}", use_container_width=True, type="primary"):
                    save_data(all_df[all_df['id'] != row['id']]); st.rerun()

# --- 4. 메인 로직 ---
if st.session_state.user_id is None:
    # (로그인 로직은 동일)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.login_page == 'login':
            st.title("🔐 가계부 로그인")
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                users = load_users()
                if uid in users and users[uid] == upw:
                    st.session_state.user_id = uid; st.rerun()
                else: st.error("로그인 실패")
            if st.button("회원가입"): st.session_state.login_page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("아이디")
            npw = st.text_input("비밀번호", type="password")
            if st.button("가입"):
                u = load_users(); u[nid] = npw; save_users(u)
                st.session_state.login_page = 'login'; st.rerun()
else:
    # 가계부 본체
    user_df_all = load_data()
    # 내 데이터만 안전하게 가져오기
    user_df = user_df_all[user_df_all['id'].astype(str).str.startswith(str(st.session_state.user_id), na=False)]
    
    st.title("💰 영구보관 가계부")
    st.sidebar.write(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"): st.session_state.user_id = None; st.rerun()

    events = []
    for _, r in user_df.iterrows():
        is_exp = r['구분'] == '지출'
        t = f"{'-' if is_exp else '+'} {int(r['금액']):,}"
        events.append({"id": str(r['id']), "title": t, "start": str(r['날짜']), "backgroundColor": "#FF4B4B" if is_exp else "#28A745"})

    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "aspectRatio": 1.2, "locale": "ko"}, key="cal_final")

    # 클릭 감지
    target_date = None
    if state.get("dateClick"):
        raw = state["dateClick"]["date"]
        try: target_date = (datetime.strptime(raw.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f") + timedelta(hours=9)).strftime("%Y-%m-%d")
        except: target_date = raw.split("T")[0]
    elif state.get("eventClick"):
        target_date = state["eventClick"]["event"]["start"].split("T")[0]

    if target_date: manage_date_entry(target_date)

    st.divider()
    if not user_df.empty:
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입", f"{i:,}원"); c2.metric("지출", f"{e:,}원"); c3.metric("잔액", f"{(i-e):,}원")
