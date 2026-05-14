import streamlit as st
import pandas as pd
import os
import json

# --- 데이터 저장 폴더 생성 ---
if not os.path.exists('user_data'):
    os.makedirs('user_data')

# --- 회원 정보 관리 함수 ---
def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- 사용자별 가계부 데이터 로드/저장 ---
def load_data(userid):
    file_path = f'user_data/{userid}.json'
    if os.path.exists(file_path):
        return pd.read_json(file_path, encoding='utf-8')
    return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)

# --- 메인 로직 ---
st.set_page_config(page_title="모두의 가계부", layout="wide")

if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# --- 로그인/회원가입 화면 ---
if st.session_state.user_id is None:
    menu = ["로그인", "회원가입"]
    choice = st.sidebar.selectbox("메뉴", menu)

    if choice == "회원가입":
        st.subheader("📝 새로운 계정 만들기")
        new_user = st.text_input("아이디 결정")
        new_pw = st.text_input("비밀번호 결정", type='password')
        if st.button("가입하기"):
            users = load_users()
            if new_user in users:
                st.error("이미 존재하는 아이디입니다.")
            elif new_user and new_pw:
                users[new_user] = new_pw
                save_users(users)
                st.success("회원가입 완료! 로그인을 해주세요.")
            else:
                st.warning("아이디와 비밀번호를 입력하세요.")

    else:
        st.subheader("🔑 로그인")
        username = st.text_input("아이디")
        password = st.text_input("비밀번호", type='password')
        if st.button("접속"):
            users = load_users()
            if username in users and users[username] == password:
                st.session_state.user_id = username
                st.rerun()
            else:
                st.error("아이디 또는 비밀번호가 틀렸습니다.")

# --- 가계부 메인 화면 (로그인 성공 시) ---
else:
    st.sidebar.write(f"👤 **{st.session_state.user_id}**님 환영합니다!")
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None
        st.rerun()

    st.title("💰 개인별 스마트 가계부")
    
    # 해당 유저의 데이터만 불러오기
    user_df = load_data(st.session_state.user_id)

    with st.form("input_form", clear_on_submit=True):
        col1, col2, col3, col4 = st.columns([2, 2, 3, 2])
        d = col1.date_input("날짜")
        t = col2.selectbox("구분", ["지출", "수입"])
        c = col3.text_input("내용")
        a = col4.number_input("금액", min_value=0, step=100)
        
        if st.form_submit_button("기록 저장"):
            new_row = pd.DataFrame({'날짜': [str(d)], '구분': [t], '내용': [c], '금액': [a]})
            user_df = pd.concat([user_df, new_row], ignore_index=True)
            save_data(st.session_state.user_id, user_df)
            st.success("저장되었습니다!")
            st.rerun()

    st.divider()

    if not user_df.empty:
        inc = user_df[user_df['구분'] == '수입']['금액'].sum()
        exp = user_df[user_df['구분'] == '지출']['금액'].sum()
        
        c1, c2, c3 = st.columns(3)
        c1.metric("내 총 수입", f"{inc:,}원")
        c2.metric("내 총 지출", f"{exp:,}원")
        c3.metric("내 잔액", f"{(inc-exp):,}원")

        st.subheader(f"📊 {st.session_state.user_id}님의 내역")
        st.dataframe(user_df.iloc[::-1], use_container_width=True)
    else:
        st.info("기록이 없습니다. 첫 지출/수입을 입력해 보세요!")
