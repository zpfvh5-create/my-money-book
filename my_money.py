import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 (화면 꽉 차게) ---
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    /* 전체 화면 여백 제거 및 달력 크기 최적화 */
    .main .block-container {
        padding: 1rem 2rem !important;
        max-width: 100% !important;
    }
    /* 달력 높이 강제 지정 */
    .fc { 
        min-height: 700px !important; 
    }
    div[data-testid="stStatusWidget"] {display: none !important;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=0, show_spinner=False)
def load_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        # 데이터 형식 강제 변환
        df['id'] = df['id'].astype(str)
        df['날짜'] = df['날짜'].astype(str)
        df['구분'] = df['구분'].astype(str)
        df['내용'] = df['내용'].astype(str)
        df['금액'] = pd.to_numeric(df['금액']).fillna(0).astype(int)
        
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠️ 저장 실패 이유: {e}")
        return False

# --- 3. 입력 팝업 ---
@st.dialog("내역 관리")
def manage_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", "user"))
    
    # 입력 폼
    with st.form("entry_form", clear_on_submit=True):
        t = st.selectbox("구분", ["지출", "수입"])
        c = st.text_input("내용 (필수)")
        a = st.number_input("금액", min_value=0, step=100, value=0)
        submit = st.form_submit_button("저장하기", use_container_width=True)
        
        if submit:
            if c.strip(): # 내용이 비어있지 않은지 확인
                new_id = f"{uid}_{int(time.time())}"
                new_row = pd.DataFrame({
                    'id': [new_id], 
                    '날짜': [date_str], 
                    '구분': [t], 
                    '내용': [c.strip()], 
                    '금액': [int(a)]
                })
                combined_df = pd.concat([all_df, new_row], ignore_index=True)
                if save_data(combined_df):
                    st.success("저장 완료!")
                    time.sleep(0.5)
                    st.rerun()
            else:
                st.error("❗ '내용'을 반드시 입력해주세요.")

    # 하단 내역 리스트 (삭제용)
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col1, col2 = st.columns([4, 1])
            icon = "🔴" if row['구분']=="지출" else "🔵"
            col1.write(f"{icon} {int(row['금액']):,}원 | {row['내용']}")
            if col2.button("🗑️", key=f"del_{row['id']}"):
                new_df = all_df[all_df['id'] != row['id']]
                if save_data(new_df): st.rerun()

# --- 4. 메인 로직 (로그인 생략 버전) ---
if 'user_id' not in st.session_state: st.session_state.user_id = "user"

st.title("💰 내 가계부")
data = load_data()
my_data = data[data['id'].str.startswith(str(st.session_state.user_id), na=False)]

events = []
for _, r in my_data.iterrows():
    is_exp = r['구분'] == '지출'
    events.append({
        "id": r['id'], 
        "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
        "start": str(r['날짜']), 
        "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
        "display": "block"
    })

# 캘린더 높이 조절 옵션 추가
state = calendar(
    events=events, 
    options={
        "initialView": "dayGridMonth", 
        "locale": "ko",
        "height": "auto",
        "contentHeight": 650
    }, 
    key="calendar_v1"
)

if state.get("dateClick"):
    manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"):
    manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
