import streamlit as st
import pandas as pd
from streamlit_calendar import calendar
from datetime import datetime
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 및 로딩 메시지 강제 숨기기 ---
st.set_page_config(page_title="가계부", layout="wide")

st.markdown("""
    <style>
    /* 로딩 중 발생하는 모든 메시지와 애니메이션 숨기기 */
    div[data-testid="stStatusWidget"] {display: none !important;}
    .stDeployButton {display:none !important;}
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    /* 화면 여백 최적화 */
    .main .block-container {padding: 1rem !important;}
    iframe { min-height: 800px !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 구글 시트 연결 최적화 ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1HfaQLS2kQYeTVM3fnYdrPiIR_8uYCA9hYeDUL8-dB3E/edit?gid=0#gid=0"
conn = st.connection("gsheets", type=GSheetsConnection)

# 캐시 시간을 2초로 늘려 연속 클릭 시 부하를 줄임
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
    # 저장 시에만 잠깐 로딩이 보일 수 있으나 최대한 조용히 처리
    conn.update(spreadsheet=SHEET_URL, data=df)
    st.cache_data.clear()

# --- 3. [팝업창] 입력 관리 ---
@st.dialog("기록하기")
def manage_entry(date_str):
    st.write(f"📅 **{date_str}**")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", ""))
    
    with st.form("input_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        t = c1.selectbox("구분", ["지출", "수입"])
        a = c2.number_input("금액", min_value=0, step=100)
        c = st.text_input("내용")
        if st.form_submit_button("확인", use_container_width=True):
            new_id = f"{uid}_{datetime.now().timestamp()}"
            new_row = pd.DataFrame({'id': [new_id], '날짜': [date_str], '구분': [t], '내용': [c], '금액': [a]})
            save_data(pd.concat([all_df, new_row], ignore_index=True))
            st.rerun()

    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col_txt, col_btn = st.columns([4, 1])
            col_txt.write(f"{row['구분']} | {int(row['금액']):,}원 | {row['내용']}")
            if col_btn.button("🗑️", key=f"del_{row['id']}"):
                save_data(all_df[all_df['id'] != row['id']])
                st.rerun()

# --- 4. 메인 화면 ---
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

if st.session_state.user_id is None:
    st.title("🔐 로그인")
    uid = st.text_input("아이디")
    if st.button("시작하기", use_container_width=True):
        st.session_state.user_id = uid
        st.rerun()
else:
    st.sidebar.button("로그아웃", on_click=lambda: st.session_state.update(user_id=None))
    st.title("💰 가계부")
    
    # 데이터 가져오기 (초록 메시지 안 뜨게 처리)
    data = load_data()
    user_id = str(st.session_state.user_id)
    my_data = data[data['id'].str.startswith(user_id, na=False)]
    
    events = []
    for _, r in my_data.iterrows():
        is_exp = r['구분'] == '지출'
        events.append({
            "id": r['id'], "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
            "start": str(r['날짜']), "backgroundColor": "#FF4B4B" if is_exp else "#28A745"
        })

    state = calendar(events=events, options={"initialView": "dayGridMonth", "aspectRatio": 1.2, "locale": "ko"}, key="v12")

    if state.get("dateClick"):
        manage_entry(state["dateClick"]["date"].split("T")[0])
    elif state.get("eventClick"):
        manage_entry(state["eventClick"]["event"]["start"].split("T")[0])

    if not my_data.empty:
        st.divider()
        i, e = my_data[my_data['구분'] == '수입']['금액'].sum(), my_data[my_data['구분'] == '지출']['금액'].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("수입", f"{i:,}원"); c2.metric("지출", f"{e:,}원"); c3.metric("잔액", f"{(i-e):,}원")
