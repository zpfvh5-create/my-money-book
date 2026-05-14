import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar

# --- 설정 및 데이터 관리 ---
if not os.path.exists('user_data'): os.makedirs('user_data')

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

def load_data(userid):
    file_path = f'user_data/{userid}.json'
    if os.path.exists(file_path):
        try: return pd.read_json(file_path, encoding='utf-8')
        except: pass
    return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)

# --- 메인 설정 ---
st.set_page_config(page_title="달력 스마트 가계부", layout="wide")

if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_id' not in st.session_state: st.session_state.user_id = None

# --- [1] 로그인/회원가입 화면 ---
if st.session_state.user_id is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.page == 'login':
            st.title("🔐 로그인")
            uid = st.text_input("아이디")
            upw = st.text_input("비밀번호", type="password")
            if st.button("로그인", use_container_width=True):
                users = load_users()
                if uid in users and users[uid] == upw:
                    st.session_state.user_id = uid
                    st.rerun()
                else: st.error("정보가 일치하지 않습니다.")
            if st.button("회원가입 하러가기"):
                st.session_state.page = 'signup'; st.rerun()
        else:
            st.title("📝 회원가입")
            nid = st.text_input("새 아이디")
            npw = st.text_input("새 비밀번호", type="password")
            if st.button("가입하기", use_container_width=True):
                users = load_users()
                if nid in users: st.error("이미 있는 아이디입니다.")
                elif nid and npw:
                    users[nid] = npw
                    save_users(users)
                    st.success("가입 완료!"); st.session_state.page = 'login'; st.rerun()
            if st.button("로그인으로 돌아가기"):
                st.session_state.page = 'login'; st.rerun()

# --- [2] 가계부 메인 화면 (달력 버전) ---
else:
    st.sidebar.title(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None; st.rerun()

    user_df = load_data(st.session_state.user_id)

    # 달력 이벤트 생성
    calendar_events = []
    for i, row in user_df.iterrows():
        color = "#FF4B4B" if row['구분'] == '지출' else "#28A745"
        calendar_events.append({
            "title": f"{row['내용']} ({row['금액']:,}원)",
            "start": row['날짜'],
            "color": color
        })

    st.title("📅 나의 달력 가계부")
    
    # 달력 표시
    calendar_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
        "initialView": "dayGridMonth",
    }
    calendar(events=calendar_events, options=calendar_options)

    st.divider()

    # 입력 폼
    with st.expander("➕ 새 내역 추가하기", expanded=True):
        with st.form("input_form", clear_on_submit=True):
            c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
            d = c1.date_input("날짜")
            t = c2.selectbox("구분", ["지출", "수입"])
            content = c3.text_input("내용")
            amount = c4.number_input("금액", min_value=0, step=100)
            if st.form_submit_button("저장하기"):
                if content:
                    new_id = str(pd.Timestamp.now().timestamp())
                    new_row = pd.DataFrame({'id': [new_id], '날짜': [str(d)], '구분': [t], '내용': [content], '금액': [amount]})
                    user_df = pd.concat([user_df, new_row], ignore_index=True)
                    save_data(st.session_state.user_id, user_df)
                    st.rerun()

    # 수정/삭제가 가능한 리스트
    st.subheader("📑 상세 내역 관리")
    if not user_df.empty:
        # 역순 정렬 (최신순)
        display_df = user_df.iloc[::-1]
        
        for i, row in display_df.iterrows():
            with st.container():
                cols = st.columns([2, 1, 3, 2, 1])
                cols[0].write(row['날짜'])
                cols[1].write(f"[{row['구분']}]")
                cols[2].write(row['내용'])
                cols[3].write(f"{row['금액']:,}원")
                if cols[4].button("삭제", key=f"del_{row['id']}"):
                    user_df = user_df[user_df['id'] != row['id']]
                    save_data(st.session_state.user_id, user_df)
                    st.rerun()
            st.divider()
