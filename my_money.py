import streamlit as st
import pandas as pd
import os
from streamlit_calendar import calendar
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection

# --- 1. 구글 시트 연결 (사용자님 주소) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"

# 속도 개선을 위한 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        # ttl=0을 유지하되, 불필요한 로그 출력을 줄이기 위해 시트 데이터만 추출
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        df['id'] = df['id'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    # 저장 시 발생하는 메시지를 최소화
    conn.update(spreadsheet=SHEET_URL, data=df)

# --- 2. 페이지 설정 ---
st.set_page_config(page_title="가계부", layout="wide")

# CSS: 상단 로딩 바 및 초록색 메시지 숨기기 시도 + 달력 크기 조절
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* 로딩 중 뜨는 메시지 박스 스타일 숨기기 */
    .stStatusWidget {display: none;}
    iframe { min-height: 800px !important; }
    </style>
    """, unsafe_allow_html=True)

if 'user_id' not in st.session_state: st.session_state.user_id = None

# --- 3. [팝업창] 내역 관리 ---
@st.dialog("가계부 기록")
def manage_date_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    uid = str(st.session_state.user_id)
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"])
        c = c2.text_input("내용", key="input_content")
        a = c3.number_input("금액", min_value=0, step=100, key="input_amount")
        if st.button("저장", use_container_width=True, type="primary"):
            new_id = f"{uid}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c if c else ""], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    for _, row in day_df.iterrows():
        with st.expander(f"{row['구분']} | {int(row['금액']):,}원 | {row['내용']}"):
            if st.button("삭제", key=f"del_{row['id']}", use_container_width=True):
                save_data(all_df[all_df['id'] != row['id']])
                st.rerun()

# --- 4. 메인 로직 ---
if st.session_state.user_id is None:
    st.title("🔐 가계부 로그인")
    uid = st.text_input("아이디")
    if st.button("들어가기", use_container_width=True):
        st.session_state.user_id = uid
        st.rerun()
else:
    st.sidebar.write(f"👤 {st.session_state.user_id}님")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()

    st.title("💰 가계부")
    
    # 데이터 로드 시 로딩바 숨기기 위해 빈 공간 활용
    with st.empty():
        user_df = load_data()
        user_df = user_df[user_df['id'].str.startswith(str(st.session_state.user_id), na=False)]
    
    events = []
    for _, r in user_df.iterrows():
        is_exp = r['구분'] == '지출'
        events.append({
            "id": r['id'], 
            "title": f"{'-' if is_exp else '+'} {int(r['금액']):,}", 
            "start": str(r['날짜']), 
            "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
            "borderColor": "#FF4B4B" if is_exp else "#28A745"
        })

    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "aspectRatio": 1.0, "locale": "ko"}, key="v10")

    # 날짜 클릭 시 반응 최적화
    if state.get("dateClick"):
        manage_date_entry(state["dateClick"]["date"].split("T")[0])
    elif state.get("eventClick"):
        manage_date_entry(state["eventClick"]["event"]["start"].split("T")[0])

    if not user_df.empty:
        st.divider()
        i, e = user_df[user_df['구분'] == '수입']['금액'].sum(), user_df[user_df['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입", f"{i:,}원")
        c2.metric("지출", f"{e:,}원")
        c3.metric("잔액", f"{(i-e):,}원")
