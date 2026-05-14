import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # 데이터를 읽어올 때 캐시 없이(ttl=0) 신선한 데이터 로드
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        
        # 필수 컬럼이 하나라도 빠져있으면 에러 방지를 위해 기본 구조 생성
        required_cols = ['id', '날짜', '구분', '내용', '금액']
        for col in required_cols:
            if col not in df.columns:
                return pd.DataFrame(columns=required_cols)
        
        df['id'] = df['id'].astype(str)
        return df
    except Exception:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        conn.update(spreadsheet=SHEET_URL, data=df)
    except Exception as e:
        st.error(f"저장 중 오류 발생: {e}")

# --- 2. 사용자 관리 (기존 파일 방식 유지) ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- 3. 화면 설정 ---
st.set_page_config(page_title="스마트 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'login_page' not in st.session_state:
    st.session_state.login_page = 'login'

# --- 4. [팝업창] 상세 관리 ---
@st.dialog("내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    all_df = load_data()
    
    # 내 데이터만 필터링 (KeyError 방지를 위해 .get 사용 대신 직접 체크)
    user_id_str = str(st.session_state.user_id)
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(user_id_str, na=False))]
    
    with st.container(border=True):
        st.markdown("**➕ 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="in_t")
        c = c2.text_input("내용", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
        
        if st.button("저장하기", use_container_width=True):
            new_id = f"{user_id_str}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c if c else ""], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    st.markdown("**📑 기록**")
    if day_df.empty: st.info("기록 없음")
    else:
        for _, row in day_df.iterrows():
            with st.expander(f"{row['구분']} | {int(row['금액']):,}원 | {row['내용']}"):
                ec = st.text_input("수정 내용", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("수정 금액", value=int(row['금액']), key=f"e_a_{row['id']}")
                col_e, col_d = st.columns(2)
                if col_e.button("수정", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액']] = [ec, ea]
                    save_data(all_df); st.rerun()
                if col_d.button("삭제", key=f"btn_d_{row['id']}", use_container_width=True, type="primary"):
                    save_data(all_df[all_df['id'] != row['id']]); st.rerun()

# --- 5. 로그인 화면 및 메인 화면 분기 ---
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
                    st.session_state.user_id = uid; st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
            if st.button("회원가입 하러가기"): st.session_state.login_page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("새 아이디")
            npw = st.text_input("새 비밀번호", type="password")
            if st.button("가입하기"):
                if nid and npw:
                    u = load_users(); u[nid] = npw; save_users(u)
                    st.success("가입 완료! 로그인해주세요."); st.session_state.login_page = 'login'; st.rerun()
            if st.button("로그인으로 돌아가기"): st.session_state.login_page = 'login'; st.rerun()

else:
    # 로그인 된 상태
    st.sidebar.write(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"): st.session_state.user_id = None; st.rerun()

    current_data = load_data()
    user_id_str = str(st.session_state.user_id)
    user_df = current_data[current_data['id'].str.startswith(user_id_str, na=False)]
    
    st.title("💰 영구보관 가계부")
    
    events = []
    for _, r in user_df.iterrows():
        is_exp = r['구분'] == '지출'
        t = f"{'-' if is_exp else '+'} {int(r['금액']):,}"
        events.append({"id": r['id'], "title": t, "start": r['날짜'], "backgroundColor": "#FF4B4B" if is_exp else "#28A745"})

    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "locale": "ko"}, key="main_cal")

    # 클릭 처리
    target_date = None
    if state.get("dateClick"):
        raw = state["dateClick"]["date"]
        target_date = raw.split("T")[0] # 가장 안전한 날짜 추출 방식
    elif state.get("eventClick"):
        target_date = state["eventClick"]["event"]["start"].split("T")[0]

    if target_date:
        manage_date_entry(target_date)

    if not user_df.empty:
        st.divider()
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입", f"{i:,}원"); c2.metric("지출", f"{e:,}원"); c3.metric("잔액", f"{(i-e):,}원")
