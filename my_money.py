import streamlit as st
import pandas as pd
import datetime
import os

# --- 비밀번호 설정 (여기를 수정하세요!) ---
USER_PASSWORD = "1234"  # <--- 원하시는 비밀번호로 바꾸세요!

# --- 데이터 로드/저장 함수 ---
def load_data():
    if os.path.exists('data.json'):
        try: return pd.read_json('data.json', encoding='utf-8')
        except: pass
    return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(df):
    df.to_json('data.json', orient='records', force_ascii=False, indent=4)

# --- 페이지 설정 ---
st.set_page_config(page_title="나의 보안 가계부", layout="wide")

# --- 로그인 체크 ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔒 보안 로그인")
    password_input = st.text_input("비밀번호를 입력하세요", type="password")
    if st.button("로그인"):
        if password_input == USER_PASSWORD:
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("비밀번호가 틀렸습니다.")
    st.stop() # 로그인 안 되면 여기서 멈춤

# --- 로그인 성공 시 가계부 화면 ---
st.title("💰 초간단 스마트 가계부")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 입력 폼
with st.form("input_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([2, 2, 3, 2])
    d = col1.date_input("날짜", datetime.date.today())
    t = col2.selectbox("구분", ["지출", "수입"])
    c = col3.text_input("내용")
    a = col4.number_input("금액", min_value=0, step=100)
    
    if st.form_submit_button("저장하기"):
        new_row = pd.DataFrame({'날짜': [str(d)], '구분': [t], '내용': [c], '금액': [a]})
        st.session_state.df = pd.concat([st.session_state.df, new_row], ignore_index=True)
        save_data(st.session_state.df)
        st.success("저장 완료!")
        st.rerun()

st.divider()

# 통계 및 내역
df = st.session_state.df
if not df.empty:
    inc = df[df['구분'] == '수입']['금액'].sum()
    exp = df[df['구분'] == '지출']['금액'].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("총 수입", f"{inc:,}원")
    c2.metric("총 지출", f"{exp:,}원")
    c3.metric("현재 잔액", f"{(inc-exp):,}원")

    st.subheader("📊 전체 내역")
    st.dataframe(df.iloc[::-1], use_container_width=True)

# 로그아웃 버튼
if st.sidebar.button("로그아웃"):
    st.session_state.logged_in = False
    st.rerun()
