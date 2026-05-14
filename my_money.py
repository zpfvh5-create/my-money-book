import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 (화면 크기 복구) ---
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
    .fc { min-height: 750px !important; } /* 달력 크기 강제 확대 */
    div[data-testid="stStatusWidget"] { display: none !important; }
    header { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        df = conn.read(ttl=0)
        if df is None or df.empty:
            return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])
        # 컬럼 이름 강제 맞춤 (오류 방지)
        df.columns = ['id', '날짜', '구분', '내용', '금액']
        return df
    except:
        return pd.DataFrame(columns=['id', '날짜', '구분', '내용', '금액'])

def save_data(df):
    try:
        # 시트 저장 전 데이터 정제
        df['금액'] = pd.to_numeric(df['금액']).fillna(0).astype(int)
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        # 실패 시 구체적인 이유를 화면에 띄움
        st.error(f"❌ 저장 실패! 이유: {e}")
        return False

# --- 3. 입력 창 (더 직관적으로 수정) ---
@st.dialog("내역 관리")
def manage_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    uid = str(st.session_state.get("user_id", "user"))
    
    # 폼 없이 직접 입력 방식으로 변경 (입력 누락 방지)
    t = st.selectbox("구분", ["지출", "수입"])
    c = st.text_input("무엇을 하셨나요? (내용)")
    a = st.number_input("금액 (원)", min_value=0, step=100)
    
    if st.button("💾 이 내역 저장하기", use_container_width=True, type="primary"):
        if c.strip():
            new_row = pd.DataFrame({
                'id': [f"{uid}_{int(time.time())}"],
                '날짜': [date_str],
                '구분': [t],
                '내용': [c.strip()],
                '금액': [int(a)]
            })
            if save_data(pd.concat([all_df, new_row], ignore_index=True)):
                st.balloons()
                st.success("저장되었습니다!")
                time.sleep(1)
                st.rerun()
        else:
            st.warning("⚠️ 내용을 입력해야 저장이 가능합니다.")

    # 삭제 리스트
    day_df = all_df[(all_df['날짜'] == date_str) & (all_df['id'].str.startswith(uid, na=False))]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"{'🔴' if row['구분']=='지출' else '🔵'} {int(row['금액']):,}원 | {row['내용']}")
            if col2.button("🗑️", key=f"del_{row['id']}"):
                if save_data(all_df[all_df['id'] != row['id']]): st.rerun()

# --- 4. 메인 화면 ---
if 'user_id' not in st.session_state: st.session_state.user_id = "user"

st.title("💰 스마트 가계부")
data = load_data()
my_data = data[data['id'].str.startswith(st.session_state.user_id, na=False)]

events = []
for _, r in my_data.iterrows():
    is_exp = r['구분'] == '지출'
    events.append({
        "id": r['id'], 
        "title": f"{'-' if is_exp else '+'}{int(r['금액']):,}", 
        "start": str(r['날짜']), 
        "backgroundColor": "#FF4B4B" if is_exp else "#28A745"
    })

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": 700}, key="calendar_final")

if state.get("dateClick"): manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
