import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding: 1rem 3% !important; }
    .fc { max-height: 600px !important; } 
    header, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# 2. 서비스 계정 인증 정보 재구성 (저장 권한 확보용)
PK = st.secrets["private_key"].replace("\\n", "\n")
creds = {
    "type": "service_account",
    "project_id": "my-money-book-496306",
    "private_key_id": st.secrets["key_id"],
    "private_key": PK,
    "client_email": "money-key@my-money-book-496306.iam.gserviceaccount.com",
    "client_id": "115839050069906584502",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/money-key%40my-money-book-496306.iam.gserviceaccount.com"
}

# 인증 정보를 명시적으로 전달하여 연결 생성
conn = st.connection("gsheets", type=GSheetsConnection, **creds)
url = st.secrets["spreadsheet"]

def load_data():
    try:
        # 인증된 연결로 읽기
        df = conn.read(spreadsheet=url, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])
        return df
    except:
        return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        # 데이터 정리 후 인증된 연결로 업데이트
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        conn.update(spreadsheet=url, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        # 에러 메시지를 더 자세히 표시
        st.error(f"⚠️ 저장 실패: {e}")
        return False

# 3. 입력 창
@st.dialog("내역 관리")
def manage_entry(date_str):
    st.write(f"📅 **{date_str}**")
    all_df = load_data()
    
    col1, col2 = st.columns(2)
    with col1: t = st.selectbox("구분", ["지출", "수입"])
    with col2: a = st.number_input("금액", min_value=0, step=100)
    c = st.text_input("내용", placeholder="기록 없음")
    
    if st.button("💾 저장하기", use_container_width=True, type="primary"):
        new_row = pd.DataFrame({
            '날짜': [date_str],
            '구분': [t],
            '내용': [c.strip() if c.strip() else "기록 없음"],
            '금액': [int(a)]
        })
        if save_data(pd.concat([all_df, new_row], ignore_index=True)):
            st.success("성공!")
            time.sleep(1)
            st.rerun()

# 4. 메인 화면
st.title("💰 가계부")
data = load_data()

events = []
for _, r in data.iterrows():
    try:
        is_exp = r['구분'] == '지출'
        events.append({
            "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
            "start": str(r['날짜']), 
            "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
            "borderColor": "transparent"
        })
    except: continue

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": 600}, key="calendar_v8")

if state.get("dateClick"): 
    manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): 
    manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
