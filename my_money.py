import streamlit as st
import pandas as pd
import datetime
import os
import json

# --- 데이터 로드/저장 ---
def load_data():
    if os.path.exists('data.json'):
        try: return pd.read_json('data.json', encoding='utf-8')
        except: pass
    return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(df):
    df.to_json('data.json', orient='records', force_ascii=False, indent=4)

# --- 메인 화면 ---
st.set_page_config(page_title="나의 가계부", layout="wide")
st.title("💰 초간단 스마트 가계부")

if 'df' not in st.session_state:
    st.session_state.df = load_data()

# 입력 폼
with st.form("input_form", clear_on_submit=True):
    col1, col2, col3, col4 = st.columns([2, 2, 3, 2])
    d = col1.date_input("날짜", datetime.date.today())
    t = col2.selectbox("구분", ["지출", "수입"])
    c = col3.text_input("내용 (예: 점심 식사)")
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
    c3.metric("현재 잔액", f"{(inc-exp):,}원", delta_color="normal")

    st.subheader("📊 전체 내역")
    st.dataframe(df.iloc[::-1], use_container_width=True)
else:
    st.info("아직 입력된 내역이 없습니다. 위 양식을 작성해 보세요!")
