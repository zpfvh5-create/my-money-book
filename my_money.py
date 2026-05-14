import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 1. 데이터 관리 함수 ---
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
        try:
            df = pd.read_json(file_path, encoding='utf-8')
            if not df.empty:
                # 모든 ID를 문자열로 변환하여 KeyError 방지
                df['id'] = df['id'].astype(str)
                return df
        except: pass
    return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)

# --- 2. 페이지 설정 ---
st.set_page_config(page_title="스마트 가계부", layout="wide")

# 세션 상태 초기화
if 'user_id' not in st.session_state: st.session_state.user_id = None
if 'login_page' not in st.session_state: st.session_state.login_page = 'login'

# --- 3. [팝업창] 내역 관리 ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    current_df = load_data(st.session_state.user_id)
    
    # 내역 추가
    with st.container(border=True):
        st.markdown("**➕ 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="in_t")
        c = c2.text_input("내용", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
        if st.button("저장하기", use_container_width=True):
            new_id = str(datetime.now().timestamp())
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c if c else "항목 없음"], '금액': [a]})
            save_data(st.session_state.user_id, pd.concat([current_df, new_row], ignore_index=True))
            st.rerun()

    # 내역 수정/삭제
    st.markdown("**📑 기존 기록**")
    day_df = current_df[current_df['날짜'] == date_str]
    if day_df.empty: st.info("기록 없음")
    else:
        for _, row in day_df.iterrows():
            with st.expander(f"{row['구분']} | {row['내용']} ({row['금액']:,}원)"):
                ec = st.text_input("내용", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("금액", value=int(row['금액']), key=f"e_a_{row['id']}")
                cs, cd = st.columns(2)
                if cs.button("수정", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df = load_data(st.session_state.user_id)
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액']] = [ec, ea]
                    save_data(st.session_state.user_id, all_df); st.rerun()
                if cd.button("삭제", key=f"btn_d_{row['id']}", use_container_width=True, type="primary"):
                    all_df = load_data(st.session_state.user_id)
                    save_data(st.session_state.user_id, all_df[all_df['id'] != row['id']]); st.rerun()

# --- 4. 메인 로직 (화면 분기) ---

# [A] 로그인이 안 된 경우 (로그인/회원가입 화면)
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
                    st.rerun()
                else: st.error("정보가 틀렸습니다.")
            if st.button("회원가입 하러가기"):
                st.session_state.login_page = 'signup'; st.rerun()
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
                    st.success("가입 완료! 로그인 해주세요.")
                    st.session_state.login_page = 'login'; st.rerun()
            if st.button("이미 계정이 있나요?"):
                st.session_state.login_page = 'login'; st.rerun()

# [B] 로그인이 된 경우 (가계부 본체)
else:
    st.sidebar.title(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None; st.rerun()

    user_df = load_data(st.session_state.user_id)
    st.title("💰 나의 스마트 가계부")

    # 달력 이벤트
    events = []
    for _, r in user_df.iterrows():
        color = "#FF4B4B" if r['구분'] == '지출' else "#28A745"
        events.append({"id": r['id'], "title": f"{r['내용']}({int(r['금액']/1000)}k)", "start": r['날짜'], "backgroundColor": color})

    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "aspectRatio": 1.0, "locale": "ko"}, key="cal")

    # 클릭 감지
    target_date = None
    if state.get("dateClick"):
        raw = state["dateClick"]["date"]
        try: target_date = (datetime.strptime(raw.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f") + timedelta(hours=9)).strftime("%Y-%m-%d")
        except: target_date = raw.split("T")[0]
    elif state.get("eventClick"):
        target_date = state["eventClick"]["event"]["start"].split("T")[0]

    if target_date: manage_date_entry(target_date)

    # 하단 통계
    st.divider()
    if not user_df.empty:
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("총 수입", f"{i:,}원"); c2.metric("총 지출", f"{e:,}원"); c3.metric("현재 잔액", f"{(i-e):,}원")
