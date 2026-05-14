import streamlit as st
import pandas as pd
import os
import json

# --- 데이터 저장 설정 ---
if not os.path.exists('user_data'): os.makedirs('user_data')

def load_users():
    if os.path.exists('users.json'):
        with open('users.json', 'r', encoding='utf-8') as f: return json.load(f)
    return {}

def save_users(users):
    with open('users.json', 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

@st.cache_data(show_spinner=False)
def load_data_cached(userid):
    file_path = f'user_data/{userid}.json'
    if os.path.exists(file_path):
        try: return pd.read_json(file_path, encoding='utf-8')
        except: pass
    return pd.DataFrame(columns=['날짜', '구분', '내용', '금액'])

def save_data(userid, df):
    file_path = f'user_data/{userid}.json'
    df.to_json(file_path, orient='records', force_ascii=False, indent=4)
    st.cache_data.clear()

# --- 메인 로직 ---
st.set_page_config(page_title="스마트 가계부", layout="centered")

# 화면 전환을 위한 상태 관리 (로그인 vs 회원가입)
if 'page' not in st.session_state: st.session_state.page = 'login'
if 'user_id' not in st.session_state: st.session_state.user_id = None

# --- [1] 로그인 화면 ---
if st.session_state.user_id is None and st.session_state.page == 'login':
    st.title("🔐 로그인")
    user_id = st.text_input("아이디")
    user_pw = st.text_input("비밀번호", type="password")
    
    if st.button("로그인", use_container_width=True):
        users = load_users()
        if user_id in users and users[user_id] == user_pw:
            st.session_state.user_id = user_id
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 틀렸습니다.")
    
    st.write("---")
    st.write("아직 계정이 없으신가요?")
    if st.button("회원가입 하러가기"):
        st.session_state.page = 'signup'
        st.rerun()

# --- [2] 회원가입 화면 ---
elif st.session_state.user_id is None and st.session_state.page == 'signup':
    st.title("📝 회원가입")
    new_id = st.text_input("새 아이디")
    new_pw = st.text_input("새 비밀번호", type="password")
    confirm_pw = st.text_input("비밀번호 확인", type="password")
    
    if st.button("가입하기", use_container_width=True):
        users = load_users()
        if new_id in users:
            st.error("이미 사용 중인 아이디입니다.")
        elif new_pw != confirm_pw:
            st.error("비밀번호가 일치하지 않습니다.")
        elif new_id and new_pw:
            users[new_id] = new_pw
            save_users(users)
            st.success("가입 성공! 이제 로그인해주세요.")
            st.session_state.page = 'login'
            st.rerun()
        else:
            st.warning("모든 칸을 채워주세요.")
            
    if st.button("이미 계정이 있나요? 로그인으로 돌아가기"):
        st.session_state.page = 'login'
        st.rerun()

# --- [3] 가계부 메인 화면 (로그인 성공 시) ---
else:
    st.title(f"💰 {st.session_state.user_id}님의 가계부")
    
    if st.sidebar.button("로그아웃"):
        st.session_state.user_id = None
        st.session_state.page = 'login'
        st.rerun()

    user_df = load_data_cached(st.session_state.user_id)

    with st.form("input_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 2, 3, 2])
        d = c1.date_input("날짜")
        t = c2.selectbox("구분", ["지출", "수입"])
        content = c3.text_input("내용")
        amount = c4.number_input("금액", min_value=0, step=100)
        if st.form_submit_button("저장하기"):
            if content:
                new_row = pd.DataFrame({'날짜': [str(d)], '구분': [t], '내용': [content], '금액': [amount]})
                user_df = pd.concat([user_df, new_row], ignore_index=True)
                save_data(st.session_state.user_id, user_df)
                st.rerun()

    if not user_df.empty:
        inc = user_df[user_df['구분'] == '수입']['금액'].sum()
        exp = user_df[user_df['구분'] == '지출']['금액'].sum()
        col1, col2, col3 = st.columns(3)
        col1.metric("총 수입", f"{inc:,}원")
        col2.metric("총 지출", f"{exp:,}원")
        col3.metric("잔액", f"{(inc-exp):,}원")
        st.dataframe(user_df.iloc[::-1], use_container_width=True)
