import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from folium.plugins import MarkerCluster

# 1. 페이지 기본 설정
st.set_page_config(page_title="Youth Canvas", layout="wide")
st.title("Youth Canvas: 우리 동네 청소년 안전·마음건강 대시보드")
st.markdown("**제7차 청소년정책기본계획** 기반 지역사회 청소년 인프라 및 마음건강 분석 프로젝트")
st.divider()

# 2. 데이터 불러오기 (캐싱으로 로딩 속도 최적화)
@st.cache_data
def load_data():
    fac_df = pd.read_csv("clean_facility.csv")
    mind_df = pd.read_csv("clean_mind_health.csv")
    return fac_df, mind_df

fac_df, mind_df = load_data()

# 3. 왼쪽 사이드바 (필터링 기능)
st.sidebar.header("🔍 데이터 탐색하기")
year_list = sorted(mind_df['연도'].astype(str).unique(), reverse=True)
selected_year = st.sidebar.selectbox("연도를 선택하세요", year_list)

indicator_list = mind_df['지표명'].unique()
selected_indicator = st.sidebar.selectbox("마음건강 지표를 선택하세요", indicator_list)

# 선택한 데이터 필터링
filtered_mind = mind_df[(mind_df['연도'].astype(str) == selected_year) & (mind_df['지표명'] == selected_indicator)]

# 4. 화면 레이아웃 분할 (지도 6 : 그래프 4)
col1, col2 = st.columns([6, 4])

with col1:
    st.subheader("🗺️ 전국 청소년 수련시설 분포 지도")
    st.caption("지도를 확대/축소하거나 마커를 클릭해 시설 이름을 확인하세요.")
    
    # Folium 지도 생성 (대한민국 중심 좌표)
    m = folium.Map(location=[36.5, 127.5], zoom_start=7)
    marker_cluster = MarkerCluster().add_to(m) # 수많은 마커를 깔끔하게 그룹화
    
    # 좌표가 있는 시설만 지도에 마커 추가
    for idx, row in fac_df.dropna(subset=['위도', '경도']).iterrows():
        folium.Marker(
            location=[row['위도'], row['경도']],
            tooltip=row['시설명']
        ).add_to(marker_cluster)
        
    # Streamlit 화면에 지도 띄우기
    st_folium(m, width=700, height=500)

with col2:
    st.subheader(f"📊 {selected_year}년 {selected_indicator} 비율")
    st.caption(f"지역별 청소년 {selected_indicator} 현황을 비교합니다.")
    
    # 막대 그래프 그리기 (비율이 높은 순으로 정렬)
    filtered_mind_sorted = filtered_mind.sort_values(by="비율(%)", ascending=True)
    st.bar_chart(filtered_mind_sorted.set_index('지역명')['비율(%)'], height=500)

st.info("💡 데이터 출처: 통계청 KOSIS (청소년건강행태조사), 공공데이터포털 (전국청소년수련시설표준데이터)")
