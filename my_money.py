import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 데이터 관리 함수 ---
if not os.path.exists('user_data'): os.makedirs('user_data')

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

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
st.set_page_config(page_title="완벽한 달력 가계부", layout="wide")

# 스타일 수정: 모바일에서 달력이 짤리지 않게 강제 설정
st.markdown("""
    <style>
    .main .block-container { padding-top: 1rem; padding-bottom: 1rem; }
    iframe { min-height: 750px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.info("로그인이 필요합니다.")
    st.stop()

user_df = load_data(st.session_state.user_id)

# --- [팝업창 기능] 날짜별 관리 도구 ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    
    # 1. 새 내역 입력
    with st.container(border=True):
        st.markdown("**➕ 새 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="new_type")
        c = c2.text_input("내용", key="new_content")
        a = c3.number_input("금액", min_value=0, step=100, key="new_amount")
        
        if st.button("저장하기", use_container_width=True):
            if c:
                new_id = str(pd.Timestamp.now().timestamp())
                new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [a]})
                updated_df = pd.concat([load_data(st.session_state.user_id), new_row], ignore_index=True)
                save_data(st.session_state.user_id, updated_df)
                st.success("저장 완료!")
                st.rerun()
            else: st.error("내용을 입력해주세요.")

    # 2. 기존 내역 수정/삭제
    st.markdown("**📑 기존 내역**")
    current_date_df = user_df[user_df['날짜'] == date_str]
    
    if current_date_df.empty:
        st.info("기록이 없습니다.")
    else:
        for i, row in current_date_df.iterrows():
            with st.expander(f"{row['구분']} - {row['내용']} ({row['금액']:,}원)"):
                u_c = st.text_input("내용 수정", value=row['내용'], key=f"e_c_{row['id']}")
                u_a = st.number_input("금액 수정", value=int(row['금액']), step=100, key=f"e_a_{row['id']}")
                u_t = st.selectbox("구분 수정", ["지출", "수입"], index=0 if row['구분']=='지출' else 1, key=f"e_t_{row['id']}")
                
                c_save, c_del = st.columns(2)
                if c_save.button("수정 완료", key=f"b_e_{row['id']}", use_container_width=True):
                    user_df.loc[user_df['id'] == row['id'], ['내용', '금액', '구분']] = [u_c, u_a, u_t]
                    save_data(st.session_state.user_id, user_df)
                    st.rerun()
                if c_del.button("삭제", key=f"b_d_{row['id']}", use_container_width=True, type="primary"):
                    new_df = user_df[user_df['id'] != row['id']]
                    save_data(st.session_state.user_id, new_df)
                    st.rerun()

# --- 메인 달력 화면 ---
st.title("💰 스마트 달력 가계부")

calendar_events = []
for i, row in user_df.iterrows():
    color = "#FF4B4B" if row['구분'] == '지출' else "#28A745"
    calendar_events.append({
        "title": f"{row['내용']} ({row['금액']:,})",
        "start": row['날짜'],
        "backgroundColor": color,
        "borderColor": color
    })

calendar_options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
    "initialView": "dayGridMonth",
    "selectable": True,
    "height": 700, # 핸드폰에서 짤리지 않는 적당한 높이
}

state = calendar(events=calendar_events, options=calendar_options, key="main_calendar")

# --- 날짜 클릭 시 시간대 오차 해결 로직 ---
if state.get("dateClick"):
    # 시간대 오차 때문에 하루 밀리는 현상 방지
    raw_date = state["dateClick"]["date"]
    if "T" in raw_date:
        # ISO 형식(2026-05-14T00:00:00Z)일 경우 앞부분 날짜만 추출
        clicked_date = raw_date.split("T")[0]
    else:
        clicked_date = raw_date
    
    manage_date_entry(clicked_date)

# 통계 표시
st.divider()
inc = user_df[user_df['구분'] == '수입']['금액'].sum()
exp = user_df[user_df['구분'] == '지출']['금액'].sum()
c1, c2, c3 = st.columns(3)
c1.metric("총 수입", f"{inc:,}원")
c2.metric("총 지출", f"{exp:,}원")
c3.metric("현재 잔액", f"{(inc-exp):,}원")
