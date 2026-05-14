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

# --- 2. 서비스 계정 정보 직접 설정 (Secrets 오류 방지) ---
google_secrets = {
    "type": "service_account",
    "project_id": "my-money-book-496306",
    "private_key_id": "5c18f0f54fccb507412e7f097a88f1ccb4e8e1f3",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC9vt+E/N34kY8a\nIZKQ+mJYkNZR9X6sEFNf+ppEpsgAYtDzmg++5uubxU6zSkb14/VBUqlWy4Qf8wvp\nwSk73o9nLJEo3EMlUy2GJaEhnkZKfWUTu34CY9FC1htS01KTtIR3I8r0m3WhKzv/\nt0M9M5UNF9qFwABjvAWE2vctNM5cYyYfTLD/IZuPgl+qgRu09oK5GcrfxXBKy1CO\nS5v0KSH7obt50bXVavIW2lj+7oG6chU2mmPwuXZyoY5vZIkMv29AcBrgqgY92QZT\nICoxcKgtBO16MPgUIbgFrdW2Hc4+l0br2cw0b6BPNFsiVH4cEmm+q0Yp6nOCjUDz\nY5pnn5qPAgMBAAECggEABGAseL1Ow8wHiCC8vTR+TsXi9gzlQ5k0yFfXyubVtzyQ\nI63/2EqBpcaiY/wTMC8g7sVgkQHXJYLOBDFSKXFJI/tLywIZV6Otab81vLgRAugV\nYU5yP3fcfDVtIoyBBlWkCw37ljHSP/SRSPpe8JW0mugGlWMHdJqsvehBdFIYGC/0\nStBoPQwCqtpHNkt7HRjS+HsdsD15/gnOUKJaawQtPDMe9Eq2hyJihGMr8WHGmucl\nZ1UIroZxIS236f/fs44tgBVk/ZSHECofP98w4eUK5CxpvkHdatpBMg8XDyEiXJp2\noeRYIoA+iiczeY6CjgVG3+UsfO5c1nJ6iLGVkpOC8QKBgQDtkzg2U9jWFNFJbeuL\nP5VaXsk8YdULH2KpGDJGhf8xsV1UvVMATrLmXTDthlOwJmTaxGVTbBzP2Pta4jzO\nd22rX+qQJfPvgVTx0ex2h/sEGbsR5Itc0iiVrGpFD5jvof5ThYSGu6/jaoQG1JZ0\nDCOGXZssxBjsUfDhFGiuT7677QKBgQDMdg3dO1V3pBZ7btTKEKlOEwtrB59jjtEM\nrhv6hRmFoCR5WvwHiQx1oW+L5k1ax5ZhNg6q9ekowOqPvuC//Mdd3KTAxJ4KMowV\haTzR8rg9iisCu3SBHweV9xGiOZo4DZiWCo+GfDo3dgkS5lu0GKY4FIYXReUmol2\ne7MOnvp46wKBgEGXedeWArHogXfSf0usvGF89fZT1GwDuEuTQJ4z9KcVnvz8YGQf\nVkk/xXhus8BYeVPlEUyc9r9z2sHW4I7obkD4dFxj/htMC9XP7Yc0N9uD9yATh16T\nL11TguuaSNEwWnVY0aQZQZB6IgV4wCk+CLjaMzOC2Ja2cNjTt6sYnUJpAoGBALjO\neEegiuciXOPi0Nl35+BXHHn4oNwXSeOhOE7foasDjhRW5flVqfplGfMlDoRgZQ+n\nEej7b21TunCFgpZmQDoZ5p0K2yKyf6Ywb2EqYjmmpiqjkkTDowC2P7dNpJ3lE6Me\nt8f8IKILa4ObBauBFa3DDNFSy66ZZGjA9J7hmdpTAoGBALmAFSeqob4GjMmplwX6\narb/zCdy0JVZHE7xaD90RWuSq/pRyem8kOVHAw0jM983qdH9j03mAT2H8KS1Z7I5\njfSi9xaQ/vWaqU9v76TpswLZqCon6dUk859Bk7sV0DBSp7YUIXiIJ3G783jCi6Y6\njVSJX1XGyMLqJQcZ0rWrV5G3\n-----END PRIVATE KEY-----\n",
    "client_email": "money-key@my-money-book-496306.iam.gserviceaccount.com",
    "client_id": "115839050069906584502",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/money-key%40my-money-book-496306.iam.gserviceaccount.com"
}

# 연결 설정
conn = st.connection("gsheets", type=GSheetsConnection, **google_secrets)

def load_data():
    try:
        url = st.secrets["spreadsheet"]
        df = conn.read(spreadsheet=url, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        df.columns = ['id', '날짜', '구분', '내용', '금액']
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        url = st.secrets["spreadsheet"]
        df['금액'] = pd.to_numeric(df['금액']).fillna(0).astype(int)
        conn.update(spreadsheet=url, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"❌ 오류 발생: {e}")
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
        if save_data(pd.concat([all_df, new_row], ignore_index=True)):
            st.success("성공!")
            time.sleep(1)
            st.rerun()

# --- 4. 메인 화면 ---
st.title("💰 내 가계부")
data = load_data()

events = []
for _, r in data.iterrows():
    is_exp = r['구분'] == '지출'
    events.append({
        "id": str(r['id']), 
        "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
        "start": str(r['날짜']), 
        "backgroundColor": "#FF4B4B" if is_exp else "#28A745",
        "borderColor": "transparent"
    })

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": 700}, key="final_v4")

if state.get("dateClick"): manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
