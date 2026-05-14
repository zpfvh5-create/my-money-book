import streamlit as st
import pandas as pd
import os
import json
from streamlit_calendar import calendar

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
st.set_page_config(page_title="프리미엄 달력 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- 로그인 세션 ---
if st.session_state.user_id is None:
    st.info("로그인 후 이용 가능합니다.")
    st.stop()

# --- 데이터 로드 ---
user_df = load_data(st.session_state.user_id)

# --- 가계부 메인 화면 ---
st.title(f"📅 {st.session_state.user_id}님의 달력 가계부")

# 달력 이벤트 구성
calendar_events = []
for i, row in user_df.iterrows():
    color = "#FF4B4B" if row['구분'] == '지출' else "#28A745"
    calendar_events.append({
        "title": f"{row['내용']} ({row['금액']:,}원)",
        "start": row['날짜'],
        "backgroundColor": color,
        "borderColor": color
    })

# 달력 옵션 (높이 자동 조절 및 클릭 이벤트 추가)
calendar_options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth,listWeek"},
    "initialView": "dayGridMonth",
    "selectable": True,
    "height": "auto",  # 짤림 방지: 내용에 맞춰 높이 조절
}

# 달력 렌더링 및 클릭 감지
state = calendar(events=calendar_events, options=calendar_options, key="main_calendar")

# --- 달력 날짜 클릭 시 동작 (새 창처럼 작동) ---
if state.get("dateClick"):
    clicked_date = state["dateClick"]["date"].split("T")[0]
    
    # 클릭한 날짜를 위한 입력창 (사이드바 또는 중앙 하단에 띄움)
    st.divider()
    st.subheader(f"📍 {clicked_date} 내역 추가")
    with st.form("quick_add_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([2, 4, 2])
        t = col1.selectbox("구분", ["지출", "수입"])
        c = col2.text_input("내용 (예: 점심식사, 월급)")
        a = col3.number_input("금액", min_value=0, step=100)
        
        if st.form_submit_button("기록하기"):
            if c:
                new_id = str(pd.Timestamp.now().timestamp())
                new_row = pd.DataFrame({'id': [new_id], '날짜': [clicked_date], '구분': [t], '내용': [c], '금액': [a]})
                user_df = pd.concat([user_df, new_row], ignore_index=True)
                save_data(st.session_state.user_id, user_df)
                st.success("저장되었습니다!")
                st.rerun()
            else:
                st.warning("내용을 입력해주세요.")

st.divider()

# --- 상세 리스트 및 통계 ---
inc = user_df[user_df['구분'] == '수입']['금액'].sum()
exp = user_df[user_df['구분'] == '지출']['금액'].sum()

c1, c2, c3 = st.columns(3)
c1.metric("이번 달 수입", f"{inc:,}원")
c2.metric("이번 달 지출", f"{exp:,}원")
c3.metric("남은 잔액", f"{(inc-exp):,}원")

st.subheader("📑 내역 관리 (수정/삭제)")
if not user_df.empty:
    # 최신순 정렬
    display_df = user_df.iloc[::-1]
    
    # 고정 박스형 리스트
    for i, row in display_df.iterrows():
        with st.container():
            col_d, col_g, col_c, col_a, col_b = st.columns([2, 1, 3, 2, 1])
            col_d.write(row['날짜'])
            col_g.write(f"[{row['구분']}]")
            col_c.write(row['내용'])
            col_a.write(f"{row['금액']:,}원")
            if col_b.button("삭제", key=f"del_{row['id']}"):
                user_df = user_df[user_df['id'] != row['id']]
                save_data(st.session_state.user_id, user_df)
                st.rerun()
        st.write("") # 간격 조절
