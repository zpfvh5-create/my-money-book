import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar
from datetime import datetime, timedelta

# --- 데이터 관리 ---
if not os.path.exists('user_data'): os.makedirs('user_data')

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
st.set_page_config(page_title="완전판 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.info("로그인이 필요합니다.")
    st.stop()

user_df = load_data(st.session_state.user_id)

# --- [팝업창] 날짜별 관리 ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    
    # 새 내역 입력
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
                st.rerun()

    # 기존 내역 관리
    st.markdown("**📑 등록된 내역**")
    current_date_df = user_df[user_df['날짜'] == date_str]
    if current_date_df.empty:
        st.info("기록이 없습니다.")
    else:
        for i, row in current_date_df.iterrows():
            with st.expander(f"{row['구분']} - {row['내용']} ({row['금액']:,}원)"):
                u_c = st.text_input("내용 수정", value=row['내용'], key=f"e_c_{row['id']}")
                u_a = st.number_input("금액 수정", value=int(row['금액']), step=100, key=f"e_a_{row['id']}")
                if st.button("수정 완료", key=f"b_e_{row['id']}", use_container_width=True):
                    user_df.loc[user_df['id'] == row['id'], ['내용', '금액']] = [u_c, u_a]
                    save_data(st.session_state.user_id, user_df); st.rerun()
                if st.button("삭제", key=f"b_d_{row['id']}", use_container_width=True, type="primary"):
                    new_df = user_df[user_df['id'] != row['id']]
                    save_data(st.session_state.user_id, new_df); st.rerun()

# --- 메인 달력 화면 ---
st.title("💰 스마트 가계부 (오차 수정됨)")

calendar_events = []
for i, row in user_df.iterrows():
    color = "#FF4B4B" if row['구분'] == '지출' else "#28A745"
    calendar_events.append({"title": f"{row['내용']} ({row['금액']:,})", "start": row['날짜'], "backgroundColor": color})

calendar_options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
    "initialView": "dayGridMonth",
    "selectable": True,
    "height": 650, # 짤림 방지를 위해 약간 더 작게 조절
}

state = calendar(events=calendar_events, options=calendar_options, key="main_calendar")

# --- ⭐ 날짜 밀림 해결 핵심 로직 ⭐ ---
if state.get("dateClick"):
    date_val = state["dateClick"]["date"]
    
    # 1. ISO 형식 확인 (T가 포함된 경우)
    if "T" in date_val:
        # 시간 정보가 포함되어 있으면 날짜가 밀릴 수 있으므로 9시간을 더해 한국 시간으로 보정
        dt_obj = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
        # 시간대가 00:00:00으로 들어오면 UTC 기준이라 한국에선 전날로 보일 수 있음
        # 날짜만 정확히 추출하기 위해 시간 정보를 버리고 날짜 문자열만 취함
        clicked_date = dt_obj.strftime('%Y-%m-%d')
    else:
        clicked_date = date_val
    
    manage_date_entry(clicked_date)

# 통계
st.divider()
inc = user_df[user_df['구분'] == '수입']['금액'].sum()
exp = user_df[user_df['구분'] == '지출']['금액'].sum()
st.columns(3)[0].metric("총 수입", f"{inc:,}원")
st.columns(3)[1].metric("총 지출", f"{exp:,}원")
st.columns(3)[2].metric("잔액", f"{(inc-exp):,}원")
