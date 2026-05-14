import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# 1. 페이지 설정 (달력 크기 최적화)
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding: 1rem 3% !important; }
    .fc { max-height: 600px !important; } 
    header, footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# 2. 서비스 계정 정보 및 연결 (TypeError 방지용 구성)
PK = "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC9vt+E/N34kY8a\nIZKQ+mJYkNZR9X6sEFNf+ppEpsgAYtDzmg++5uubxU6zSkb14/VBUqlWy4Qf8wvp\nwSk73o9nLJEo3EMlUy2GJaEhnkZKfWUTu34CY9FC1htS01KTtIR3I8r0m3WhKzv/\nt0M9M5UNF9qFwABjvAWE2vctNM5cYyYfTLD/IZuPgl+qgRu09oK5GcrfxXBKy1CO\nS5v0KSH7obt50bXVavIW2lj+7oG6chU2mmPwuXZyoY5vZIkMv29AcBrgqgY92QZT\nICoxcKgtBO16MPgUIbgFrdW2Hc4+l0br2cw0b6BPNFsiVH4cEmm+q0Yp6nOCjUDz\nY5pnn5qPAgMBAAECggEABGAseL1Ow8wHiCC8vTR+TsXi9gzlQ5k0yFfXyubVtzyQ\nI63/2EqBpcaiY/wTMC8g7sVgkQHXJYLOBDFSKXFJI/tLywIZV6Otab81vLgRAugV\nYU5yP3fcfDVtIoyBBlWkCw37ljHSP/SRSPpe8JW0mugGlWMHdJqsvehBdFIYGC/0\nStBoPQwCqtpHNkt7HRjS+HsdsD15/gnOUKJaawQtPDMe9Eq2hyJihGMr8WHGmucl\nZ1UIroZxIS236f/fs44tgBVk/ZSHECofP98w4eUK5CxpvkHdatpBMg8XDyEiXJp2\noeRYIoA+iiczeY6CjgVG3+UsfO5c1nJ6iLGVkpOC8QKBgQDtkzg2U9jWFNFJbeuL\nP5VaXsk8YdULH2KpGDJGhf8xsV1UvVMATrLmXTDthlOwJmTaxGVTbBzP2Pta4jzO\nd22rX+qQJfPvgVTx0ex2h/sEGbsR5Itc0iiVrGpFD5jvof5ThYSGu6/jaoQG1JZ0\nDCOGXZssxBjsUfDhFGiuT7677QKBgQDMdg3dO1V3pBZ7btTKEKlOEwtrB59jjtEM\rhv6hRmFoCR5WvwHiQx1oW+L5k1ax5ZhNg6q9ekowOqPvuC//Mdd3KTAxJ4KMowV\haTzR8rg9iisCu3SBHweV9xGiOZo4DZiWCo+GfDo3dgkS5lu0GKY4FIYXReUmol2\ne7MOnvp46wKBgEGXedeWArHogXfSf0usvGF89fZT1GwDuEuTQJ4z9KcVnvz8YGQf\nVkk/xXhus8BYeVPlEUyc9r9z2sHW4I7obkD4dFxj/htMC9XP7Yc0N9uD9yATh16T\nL11TguuaSNEwWnVY0aQZQZB6IgV4wCk+CLjaMzOC2Ja2cNjTt6sYnUJpAoGBALjO\neEegiuciXOPi0Nl35+BXHHn4oNwXSeOhOE7foasDjhRW5flVqfplGfMlDoRgZQ+n\nEej7b21TunCFgpZmQDoZ5p0K2yKyf6Ywb2EqYjmmpiqjkkTDowC2P7dNpJ3lE6Me\nt8f8IKILa4ObBauBFa3DDNFSy66ZZGjA9J7hmdpTAoGBALmAFSeqob4GjMmplwX6\narb/zCdy0JVZHE7xaD90RWuSq/pRyem8kOVHAw0jM983qdH9j03mAT2H8KS1Z7I5\njfSi9xaQ/vWaqU9v76TpswLZqCon6dUk859Bk7sV0DBSp7YUIXiIJ3G783jCi6Y6\njVSJX1XGyMLqJQcZ0rWrV5G3\n-----END PRIVATE KEY-----\n"

# st.connection에 직접 자격 증명을 전달하지 않고 st.secrets의 형식을 맞춥니다.
conn = st.connection("gsheets", type=GSheetsConnection)
url = st.secrets["spreadsheet"]

def load_data():
    try:
        # 'private_key'와 'key_id'를 코드 내에서 조합하여 인증 처리
        df = conn.read(spreadsheet=url, ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])
        return df
    except:
        return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        # 숫자 형식 강제 변환
        df['금액'] = pd.to_numeric(df['금액'], errors='coerce').fillna(0).astype(int)
        conn.update(spreadsheet=url, data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"⚠️ 저장 중 문제 발생: {e}")
        return False

# 3. 입력 창 (다이얼로그)
@st.dialog("내역 입력")
def manage_entry(date_str):
    st.write(f"📅 **{date_str}**")
    all_df = load_data()
    
    col1, col2 = st.columns(2)
    with col1: t = st.selectbox("구분", ["지출", "수입"])
    with col2: a = st.number_input("금액", min_value=0, step=100)
    c = st.text_input("내용 (선택사항)", placeholder="기록 없음")
    
    if st.button("💾 저장하기", use_container_width=True, type="primary"):
        new_row = pd.DataFrame({
            '날짜': [date_str],
            '구분': [t],
            '내용': [c.strip() if c.strip() else "기록 없음"],
            '금액': [int(a)]
        })
        if save_data(pd.concat([all_df, new_row], ignore_index=True)):
            st.success("저장 완료!")
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

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": 600}, key="calendar_final")

if state.get("dateClick"): 
    manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): 
    manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
