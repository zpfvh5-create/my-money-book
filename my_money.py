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
                df['id'] = df['id'].astype(str) # ID를 문자열로 통일하여 키에러 방지
            return df
        except: pass
    return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)

# --- 화면 설정 ---
st.set_page_config(page_title="완성형 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.info("로그인 후 이용해주세요.")
    st.stop()

# 최신 데이터 불러오기
user_df = load_data(st.session_state.user_id)

# --- [팝업창] 내역 관리 도구 ---
@st.dialog("내역 상세 관리")
def manage_date_entry(date_str):
    st.subheader(f"📍 {date_str}")
    
    # 1. 새 내역 추가
    with st.container(border=True):
        st.markdown("**➕ 새 내역 추가**")
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"], key="input_type")
        c = c2.text_input("내용", key="input_content")
        a = c3.number_input("금액", min_value=0, step=100, key="input_amount")
        
        if st.button("저장하기", use_container_width=True):
            if c:
                new_id = str(datetime.now().timestamp())
                new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [a]})
                # 실시간 데이터 병합 및 저장
                current_df = load_data(st.session_state.user_id)
                updated_df = pd.concat([current_df, new_row], ignore_index=True)
                save_data(st.session_state.user_id, updated_df)
                st.rerun()
            else:
                st.error("내용을 입력해주세요.")

    st.write("")
    st.markdown("**📑 기존 내역 수정/삭제**")
    
    # 해당 날짜 데이터만 필터링
    day_df = user_df[user_df['날짜'] == date_str]
    
    if day_df.empty:
        st.info("이 날짜에 등록된 내역이 없습니다.")
    else:
        for _, row in day_df.iterrows():
            with st.expander(f"{row['구분']} | {row['내용']} ({row['금액']:,}원)"):
                # 수정용 입력창
                edit_c = st.text_input("내용 수정", value=row['내용'], key=f"ec_{row['id']}")
                edit_a = st.number_input("금액 수정", value=int(row['금액']), key=f"ea_{row['id']}")
                edit_t = st.selectbox("구분 수정", ["지출", "수입"], index=0 if row['구분'] == '지출' else 1, key=f"et_{row['id']}")
                
                col_edit, col_del = st.columns(2)
                
                # 수정 로직
                if col_edit.button("수정 완료", key=f"btn_e_{row['id']}", use_container_width=True):
                    all_df = load_data(st.session_state.user_id)
                    all_df.loc[all_df['id'] == row['id'], ['내용', '금액', '구분']] = [edit_c, edit_a, edit_t]
                    save_data(st.session_state.user_id, all_df)
                    st.success("수정되었습니다!")
                    st.rerun()
                
                # 삭제 로직
                if col_del.button("삭제하기", key=f"btn_d_{row['id']}", use_container_width=True, type="primary"):
                    all_df = load_data(st.session_state.user_id)
                    all_df = all_df[all_df['id'] != row['id']]
                    save_data(st.session_state.user_id, all_df)
                    st.warning("삭제되었습니다.")
                    st.rerun()

# --- 메인 달력 화면 ---
st.title("💰 스마트 달력 가계부")

events = []
for _, r in user_df.iterrows():
    color = "#FF4B4B" if r['구분'] == '지출' else "#28A745"
    events.append({
        "title": f"{r['내용']}({int(r['금액']/1000)}k)", 
        "start": r['날짜'], 
        "backgroundColor": color,
        "borderColor": color
    })

calendar_options = {
    "headerToolbar": {"left": "prev,next today", "center": "title", "right": ""},
    "initialView": "dayGridMonth",
    "selectable": True,
    "aspectRatio": 1.0,
    "height": "auto",
    "locale": "ko"
}

state = calendar(events=events, options=calendar_options, key="calendar_v3")

# 날짜 클릭 시 동작 (한국 시간 보정 포함)
if state.get("dateClick"):
    raw_date = state["dateClick"]["date"]
    try:
        dt = datetime.strptime(raw_date.replace("Z", ""), "%Y-%m-%dT%H:%M:%S.%f")
        correct_dt = dt + timedelta(hours=9)
        clicked_date = correct_dt.strftime("%Y-%m-%d")
    except:
        clicked_date = raw_date.split("T")[0]
    
    manage_date_entry(clicked_date)

# 하단 요약 통계
st.write("---")
if not user_df.empty:
    inc = user_df[user_df['구분'] == '수입']['금액'].sum()
    exp = user_df[user_df['구분'] == '지출']['금액'].sum()
    m1, m2, m3 = st.columns(3)
    m1.metric("총 수입", f"{inc:,}원")
    m2.metric("총 지출", f"{exp:,}원")
    m3.metric("현재 잔액", f"{(inc-exp):,}원")
