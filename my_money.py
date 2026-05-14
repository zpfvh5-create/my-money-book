import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 ---
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
    .fc { min-height: 750px !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 서비스 계정 정보 (직접 입력 방식) ---
# TypeError 방지를 위해 딕셔너리 구조를 명확히 정의합니다.
creds = {
    "type": "service_account",
    "project_id": "my-money-book-496306",
    "private_key_id": "5c18f0f54fccb507412e7f097a88f1ccb4e8e1f3",
    "private_key": st.secrets.get("private_key", "").replace("\\n", "\n") if "private_key" in st.secrets else "",
    "client_email": "money-key@my-money-book-496306.iam.gserviceaccount.com",
    "client_id": "115839050069906584502",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/money-key%40my-money-book-496306.iam.gserviceaccount.com"
}

# 연결 설정 (가장 안정적인 호출 방식)
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        url = st.secrets["spreadsheet"]
        # credentials 매개변수 대신 설정된 연결을 통해 읽어옵니다.
        df = conn.read(spreadsheet=url, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        df.columns = ['id', '날짜', '구분', '내용', '금액']
        return df
    except Exception as e:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        url = st.secrets["spreadsheet"]
        # 금액 데이터 형식 강제 변환 (오류 방지)
        df['금액'] = pd.to_numeric(df['금액']).fillna(0).astype(int)
        conn.update(spreadsheet=url, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ 저장 중 오류 발생: {e}")
        return False

# --- 3. 입력 창 ---
@st.dialog("내역 관리")
def manage_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    
    t = st.selectbox("구분", ["지출", "수입"])
    c = st.text_input("내용", placeholder="기록 없음")
    a = st.number_input("금액 (원)", min_value=0, step=100)
    
    if st.button("💾 저장하기", use_container_width=True, type="primary"):
        final_content = c.strip() if c.strip() else "기록 없음"
        new_row = pd.DataFrame({
            'id': [f"user_{int(time.time())}"],
            '날짜': [date_str],
            '구분': [t],
            '내용': [final_content],
            '금액': [int(a)]
        })
        # 데이터 합치기 및 저장
        combined_df = pd.concat([all_df, new_row], ignore_index=True)
        if save_data(combined_df):
            st.success("성공적으로 저장되었습니다!")
            time.sleep(1)
            st.rerun()

# --- 4. 메인 화면 ---
st.title("💰 내 가계부")
data = load_data()

events = []
for _, r in data.iterrows():
    try:
        is_exp = r['구분'] == '지출'
        events.append({
            "id": str(r.get('id', time.time())), 
            "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
            "start": str(r['날짜']), 
            "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
            "borderColor": "transparent"
        })
    except:
        continue

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": 700}, key="final_v5")

if state.get("dateClick"): 
    manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): 
    manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
