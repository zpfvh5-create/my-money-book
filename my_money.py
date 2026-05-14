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

# --- 화면 설정 ---
st.set_page_config(page_title="정사각형 가계부", layout="wide")

# CSS: 달력 컨테이너 크기 최적화
st.markdown("""
    <style>
    .main .block-container { padding: 1rem; }
    iframe { width: 100% !important; }
    </style>
    """, unsafe_allow_html=True)

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.info("로그인 후 이용해주세요.")
    st.stop()

user_df = load_data(st.session_state.user_id)

# --- [팝업창] 관리 도구 ---
@st.dialog("내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    
    with st.container(border=True):
        st.markdown("**➕ 새 내역**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="nt")
        c = c2.text_input("내용", key="nc")
        a = c3.number_input("금액", min_value=0, step=100, key="na")
        
        if st.button("저장하기", use_container_width=True):
            if c:
                new_id = str(pd.Timestamp.now().timestamp())
                new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [a]})
                save_data(st.session_state.user_id, pd.concat([load_data(st.session_state.user_id), new_row], ignore_index=True))
                st.rerun()

    st.markdown("**📑 기존 내역**")
    day_df = user_df[user_df['날짜'] == date_str]
    if day_df.empty:
        st.info("기록 없음")
    else:
        for i, row in day_df.iterrows():
            with st.expander(f"{row['내용']} ({row['금액']:,})"):
                uc = st.text_input("수정", value=row['내용'], key=f"ec_{row['id']}")
                ua = st.number_input("금액", value=int(row['금액']), key=f"ea_{row['id']}")
                cs, cd = st.columns(2)
                if cs.button("수정", key=f"be_{row['id']}", use_container_width=True):
                    user_df.loc[user_df['id'] == row['id'], ['내용', '금액']] = [uc, ua]
                    save_data(st.session_state.user_id, user_df); st.rerun()
                if cd.button("삭제", key=f"bd_{row['id']}", use_container_width=True, type="primary"):
                    save_data(st.session_state.user_id, user_df[user_df['id'] != row['id']]); st.rerun()

# --- 메인 달력 ---
st.title("💰 스마트 가계부")

events = []
for _, r in user_df.iterrows():
    color = "#FF4B4B" if r['구분'] == '지출' else "#28A745"
    events.append({"title": f"{r['내용']}({int(r['금액']/1000)}k)", "start": r['날짜'], "backgroundColor": color})

# 정사각형 비율(aspectRatio) 적용
options = {
    "headerToolbar": {"left": "prev,next", "center": "title", "right": "today"},
    "initialView": "dayGridMonth",
    "selectable": True,
    "aspectRatio": 1.0, # 정사각형에 가까운 비율로 설정
    "height": "auto",
    "locale": "ko"
}

state = calendar(events=events, options=options, key="calendar")

# --- ⭐ 날짜 밀림 현상 최종 해결 로직 ⭐ ---
if state.get("dateClick"):
    raw_date = state["dateClick"]["date"]
    
    try:
        # ISO 문자열(2026-05-14T00:00:00.000Z)을 파이썬 객체로 변환
        dt = datetime.strptime(raw_date.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
        # 부품이 UTC로 날짜를 주므로 한국 시간(+9시간)을 강제로 더함
        correct_dt = dt + timedelta(hours=9)
        clicked_date = correct_dt.strftime("%Y-%m-%d")
    except:
        # 만약 날짜 문자열만 들어오는 경우
        clicked_date = raw_date.split("T")[0]
    
    manage_date_entry(clicked_date)

# 하단 요약
st.write("---")
inc = user_df[user_df['구분'] == '수입']['금액'].sum()
exp = user_df[user_df['구분'] == '지출']['금액'].sum()
st.columns(3)[0].metric("수입", f"{inc:,}원")
st.columns(3)[1].metric("지출", f"{exp:,}원")
st.columns(3)[2].metric("잔액", f"{(inc-exp):,}원")
