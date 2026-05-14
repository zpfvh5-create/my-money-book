import streamlit as st
import pandas as pd
import time
from streamlit_calendar import calendar
from streamlit_gsheets import GSheetsConnection

# --- 1. 페이지 설정 (달력 크기 확대) ---
st.set_page_config(page_title="가계부", page_icon="💰", layout="wide")

st.markdown("""
    <style>
    .main .block-container { padding: 1rem 2rem !important; max-width: 100% !important; }
    .fc { min-height: 800px !important; } 
    div[data-testid="stStatusWidget"] { display: none !important; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 연결 ---
conn = st.connection("gsheets", type=GSheetsConnection)

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
        # 데이터 형식 최종 정리
        df['금액'] = pd.to_numeric(df['금액']).fillna(0).astype(int)
        # 구글 시트에 업데이트
        conn.update(data=df)
        st.cache_data.clear()
        return True
    except Exception as e:
        # 여기에 뜨는 영문 메시지가 해결의 핵심입니다!
        st.error(f"❌ 저장 실패 원인: {e}")
        st.info("💡 팁: 구글 시트 우측 상단 '공유'에 서비스 계정 이메일이 '편집자'로 있는지 확인해 보세요.")
        return False

# --- 3. 입력 창 (내용 미입력 허용) ---
@st.dialog("내역 관리")
def manage_entry(date_str):
    st.subheader(f"📅 {date_str}")
    all_df = load_data()
    uid = "user"
    
    t = st.selectbox("구분", ["지출", "수입"])
    c = st.text_input("내용 (안 써도 됨)", placeholder="기록 없음")
    a = st.number_input("금액 (원)", min_value=0, step=100)
    
    if st.button("💾 저장하기", use_container_width=True, type="primary"):
        # 내용을 안 쓰면 "기록 없음"으로 자동 처리
        final_content = c.strip() if c.strip() else "기록 없음"
        
        new_row = pd.DataFrame({
            'id': [f"{uid}_{int(time.time())}"],
            '날짜': [date_str],
            '구분': [t],
            '내용': [final_content],
            '금액': [int(a)]
        })
        
        if save_data(pd.concat([all_df, new_row], ignore_index=True)):
            st.success("저장 성공!")
            time.sleep(1)
            st.rerun()

    # 삭제 리스트
    day_df = all_df[all_df['날짜'] == date_str]
    if not day_df.empty:
        st.write("---")
        for _, row in day_df.iterrows():
            col1, col2 = st.columns([4, 1])
            col1.write(f"{'🔴' if row['구분']=='지출' else '🔵'} {int(row['금액']):,}원 | {row['내용']}")
            if col2.button("🗑️", key=f"del_{row['id']}"):
                if save_data(all_df[all_df['id'] != row['id']]): st.rerun()

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

state = calendar(events=events, options={"initialView": "dayGridMonth", "locale": "ko", "height": "auto"}, key="calendar_v3")

if state.get("dateClick"): manage_entry(state["dateClick"]["date"].split("T")[0])
elif state.get("eventClick"): manage_entry(state["eventClick"]["event"]["start"].split("T")[0])
