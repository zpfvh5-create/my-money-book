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
        try:
            df = pd.read_json(file_path, encoding='utf-8')
            if not df.empty:
                df['id'] = df['id'].astype(str)
            return df
        except: pass
    return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)

# --- 화면 설정 ---
st.set_page_config(page_title="완성형 스마트 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.info("로그인 후 이용해주세요.")
    st.stop()

# 최신 데이터 로드
user_df = load_data(st.session_state.user_id)

# --- [팝업창] 내역 관리 ---
@st.dialog("날짜 내역 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    
    # 1. 추가 섹션
    with st.container(border=True):
        st.markdown("**➕ 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="in_t")
        c = c2.text_input("내용 (미입력 가능)", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
        
        if st.button("저장하기", use_container_width=True):
            content_val = c if c else "내용 없음" # 공란일 경우 자동 채움
            new_id = str(datetime.now().timestamp())
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [content_val], '금액': [a]})
            save_data(st.session_state.user_id, pd.concat([load_data(st.session_state.user_id), new_row], ignore_index=True))
            st.rerun()

    # 2. 수정/삭제 섹션
    st.markdown("**📑 기존 기록**")
    day_df = user_df[user_df['날짜'] == date_str]
    
    if day_df.empty:
        st.info("기록이 없습니다.")
    else:
        for _, row in day_df.iterrows():
            with st.expander(f"{row['구분']} | {row['내용']} ({row['금액']:,}원)"):
                ec = st.text_input("내용", value=row['내용'], key=f"e_c_{row['id']}")
                ea = st.number_input("금액", value=int(row['금액']), key=f"e_a_{row['id']}")
                et = st.selectbox("구분", ["지출", "수입"], index=0 if row['구분']=='지출' else 1, key=f"e_t_{row['id']}")
                
                cs, cd = st.columns(2)
                if cs.button("수정", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df = load_data(st.session_state.user_id)
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액', '구분']] = [ec, ea, et]
                    save_data(st.session_state.user_id, all_df)
                    st.rerun()
                
                if cd.button("삭제", key=f"btn_d_{row['id']}", use_container_width=True, type="primary"):
                    all_df = load_data(st.session_state.user_id)
                    save_data(st.session_state.user_id, all_df[all_df['id'] != row['id']])
                    st.rerun()

# --- 메인 화면 ---
st.title("💰 나만의 스마트 가계부")

events = []
for _, r in user_df.iterrows():
    color = "#FF4B4B" if r['구분'] == '지출' else "#28A745"
    events.append({
        "id": r['id'],
        "title": f"{r['내용']}({int(r['금액']/1000)}k)", 
        "start": r['날짜'], 
        "backgroundColor": color,
        "borderColor": color
    })

options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
    "initialView": "dayGridMonth",
    "selectable": True,
    "aspectRatio": 1.0,
    "height": "auto",
    "locale": "ko"
}

# 달력 생성
state = calendar(events=events, options=options, key="final_calendar")

# --- 클릭 로직 (빈칸 클릭 + 글자 클릭 둘 다 지원) ---
target_date = None

# 1. 빈 칸 클릭 시
if state.get("dateClick"):
    raw_date = state["dateClick"]["date"]
    try:
        dt = datetime.strptime(raw_date.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
        target_date = (dt + timedelta(hours=9)).strftime("%Y-%m-%d")
    except:
        target_date = raw_date.split("T")[0]

# 2. 이미 있는 글자(이벤트) 클릭 시
elif state.get("eventClick"):
    target_date = state["eventClick"]["event"]["start"].split("T")[0]

# 팝업 띄우기
if target_date:
    manage_date_entry(target_date)

# 하단 요약
st.divider()
if not user_df.empty:
    inc, exp = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("총 수입", f"{inc:,}원")
    m2.metric("총 지출", f"{exp:,}원")
    m3.metric("현재 잔액", f"{(inc-exp):,}원")
