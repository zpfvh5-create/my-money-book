import streamlit as st
import pandas as pd
import os
from streamlit_calendar import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 (최상단 배치) ---
st.set_page_config(page_title="가계부", layout="wide")

# CSS: 초록색 메시지창, 메뉴, 헤더 등을 완전히 숨기고 달력 크기 고정
st.markdown("""
    <style>
    /* 상단 로딩바 및 상태 메시지 완전 차단 */
    [data-testid="stStatusWidget"], .stStatusWidget {display: none !important;}
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* 달력 크기 시원하게 조절 */
    iframe { min-height: 850px !important; }
    .main .block-container {padding: 1rem 2rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# 1초 동안만 데이터를 기억하게 하여 속도와 정확도를 동시에 잡음
@st.cache_data(ttl=1)
def load_data():
    try:
        df = conn.read(spreadsheet=SHEET_URL, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        df['id'] = df['id'].astype(str)
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    conn.update(spreadsheet=SHEET_URL, data=df)
    st.cache_data.clear() # 저장 후 즉시 캐시 삭제하여 반영

# --- 3. [팝업창] 내역 관리 ---
@st.dialog("가계부 기록")
def manage_date_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", ""))
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    
    with st.container(border=True):
        c1, c2, c3 = st.columns([3, 4, 3])
        t = c1.selectbox("구분", ["지출", "수입"])
        c = c2.text_input("내용", key="in_c")
        a = c3.number_input("금액", min_value=0, step=100, key="in_a")
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
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

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
    
    user_df_all = load_data()
    user_df = user_df_all[user_df_all['id'].str.startswith(str(st.session_state.user_id), na=False)]
    
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

    # 달력 크기 비율 최적화
    state = calendar(events=events, options={"initialView": "dayGridMonth", "selectable": True, "aspectRatio": 1.1, "locale": "ko"}, key="v11")

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
