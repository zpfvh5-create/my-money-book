import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 전용 아이콘 설정 ---
# 아래 icon_url이 핸드폰 바탕화면 아이콘이 됩니다.
icon_url = "https://cdn-icons-png.flaticon.com/512/2454/2454282.png" 

st.set_page_config(
    page_title="가계부",
    page_icon="💰",
    layout="wide"
)

# 폰 홈 화면 추가 시 앱처럼 보이게 하는 메타 설정
st.markdown(f"""
    <link rel="apple-touch-icon" href="{icon_url}">
    <link rel="icon" href="{icon_url}">
    <style>
    /* 로딩 메시지 및 불필요한 UI 숨기기 */
    div[data-testid="stStatusWidget"] {{display: none !important;}}
    .stDeployButton {{display:none !important;}}
    #MainMenu {{visibility: hidden;}}
    header {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    /* 화면 여백 및 달력 크기 최적화 */
    .main .block-container {{padding: 1rem !important;}}
    iframe {{ min-height: 800px !important; }}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=2, show_spinner=False)
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
    st.cache_data.clear()

# --- 3. [팝업창] 입력 및 관리 ---
@st.dialog("기록 관리")
def manage_entry(date_str):
    st.write(f"📅 **{date_str}**")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", ""))
    
    # 입력 폼
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t = c1.selectbox("구분", ["지출", "수입"])
        a = c2.number_input("금액", min_value=0, step=100)
        c = st.text_input("내용 (선택)")
        if st.form_submit_button("저장하기", use_container_width=True):
            new_id = f"{uid}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    # 기존 내역 확인 및 삭제
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col_txt, col_btn = st.columns([4, 1])
            color = "🔴" if row['구분'] == "지출" else "🔵"
            col_txt.write(f"{color} {int(row['금액']):,}원 ({row['내용']})")
            if col_btn.button("🗑️", key=f"del_{row['id']}"):
                save_data(all_df[all_df['id'] != row['id']])
                st.rerun()

# --- 4. 메인 로직 ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.title("🔐 가계부 로그인")
    uid = st.text_input("아이디를 입력하세요")
    if st.button("시작하기", use_container_width=True, type="primary"):
        if uid:
            st.session_state.user_id = uid
            st.rerun()
else:
    # 사이드바 설정
    st.sidebar.write(f"👤 **{st.session_state.user_id}**님")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()

    st.title("💰 가계부")
    
    # 데이터 로드
    data = load_data()
    uid_str = str(st.session_state.user_id)
    my_data = data[data['id'].str.startswith(uid_str, na=False)]
    
    # 달력 이벤트 생성
    events = []
    for _, r in my_data.iterrows():
        is_exp = r['구분'] == '지출'
        events.append({
            "id": r['id'], 
            "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
            "start": str(r['날짜']), 
            "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
            "borderColor": "#FF4B4B" if is_exp else "#28A745"
        })

    # 달력 표시
    state = calendar(
        events=events, 
        options={
            "initialView": "dayGridMonth", 
            "aspectRatio": 1.1, 
            "locale": "ko",
            "headerToolbar": {"left": "prev,next", "center": "title", "right": "today"}
        }, 
        key="v13"
    )

    # 클릭 감지
    if state.get("dateClick"):
        manage_entry(state["dateClick"]["date"].split("T")[0])
    elif state.get("eventClick"):
        manage_entry(state["eventClick"]["event"]["start"].split("T")[0])

    # 하단 요약
    if not my_data.empty:
        st.divider()
        i, e = my_data[my_data['구분'] == '수입']['금액'].sum(), my_data[my_data['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("이번 달 수입", f"{i:,}원")
        c2.metric("이번 달 지출", f"{e:,}원")
        c3.metric("남은 잔액", f"{(i-e):,}원")
