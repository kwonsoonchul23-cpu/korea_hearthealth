import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap, MarkerCluster
import streamlit.components.v1 as components
import plotly.express as px
import numpy as np

# 1. 페이지 설정 (지도를 넓게 쓰기 위해 layout="wide" 적용)
st.set_page_config(page_title="Youth Canvas", layout="wide")

st.title("🚨 Youth Canvas: 청소년 위험 구역 및 마음건강 분석 대시보드")
st.markdown("우리 동네의 **위험 구역(유해업소 밀집)**과 **안전망(청소년 수련시설)**을 비교하고, 지역별 마음건강 변화 추이를 분석합니다.")
st.markdown("---")

# 2. 데이터 불러오기 (에러 방지를 위해 숫자형 강제 변환)
@st.cache_data
def load_data():
    fac_df = pd.read_csv("clean_facility.csv")
    mind_df = pd.read_csv("clean_mind_health.csv")
    
    mind_df['비율(%)'] = pd.to_numeric(mind_df['비율(%)'], errors='coerce')
    fac_df['위도'] = pd.to_numeric(fac_df['위도'], errors='coerce')
    fac_df['경도'] = pd.to_numeric(fac_df['경도'], errors='coerce')
    
    fac_df = fac_df.dropna(subset=['위도', '경도'])
    mind_df = mind_df.dropna(subset=['비율(%)'])
    return fac_df, mind_df

fac_df, mind_df = load_data()

# 3. 사이드바 - 지역 검색 기능 (자동 줌인을 위한 좌표 딕셔너리)
region_coords = {
    "전국": [36.5, 127.5], "서울특별시": [37.5665, 126.9780], "부산광역시": [35.1796, 129.0756],
    "대구광역시": [35.8714, 128.6014], "인천광역시": [37.4563, 126.7052], "광주광역시": [35.1595, 126.8526],
    "대전광역시": [36.3504, 127.3845], "울산광역시": [35.5384, 129.3114], "세종특별자치시": [36.4800, 127.2890],
    "경기도": [37.2752, 127.0095], "강원도": [37.8854, 127.7298], "충청북도": [36.6358, 127.4913],
    "충청남도": [36.6588, 126.6728], "전라북도": [35.8203, 127.1088], "전라남도": [34.8163, 126.4629],
    "경상북도": [36.5760, 128.5056], "경상남도": [35.2383, 128.6925], "제주특별자치도": [33.4890, 126.4983]
}

st.sidebar.header("🔍 지역 및 데이터 검색")
selected_region = st.sidebar.selectbox("📍 분석할 지역 선택", list(region_coords.keys()))
year_list = sorted(mind_df['연도'].astype(str).unique(), reverse=True)
selected_year = st.sidebar.selectbox("📅 연도 선택", year_list)
indicator_list = mind_df['지표명'].unique()
selected_indicator = st.sidebar.selectbox("🧠 마음건강 지표 선택", indicator_list)

# 4. 지도 영역 (크게 만들기 위해 전체 너비 사용)
st.subheader(f"🗺️ {selected_region} 청소년 위험구역 및 안전망 지도")
st.markdown("🔴 **붉은색 히트맵**: 유해환경 밀집 위험 구역 (현재 데모용 가상데이터) | 🔵 **파란색 마커**: 청소년 안전 보호망 (수련시설)")

map_center = region_coords[selected_region]
zoom = 7 if selected_region == "전국" else 11

# 대한민국 영토 밖으로 드래그 방지 설정 (min/max lat, lon)
m = folium.Map(
    location=map_center, 
    zoom_start=zoom, 
    tiles='cartodbpositron',
    min_zoom=6,
    max_bounds=True,
    min_lat=33.0, max_lat=39.0,
    min_lon=124.0, max_lon=132.0
)

# 지역 필터링 적용
if selected_region != "전국":
    fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)]
else:
    fac_filtered = fac_df

# [기능 1] 위험 구역 히트맵 추가 (시각화 테스트용 무작위 데이터 생성)
np.random.seed(42)
num_danger = 300 if selected_region == "전국" else 50
lat_var, lon_var = (2.0, 2.0) if selected_region == "전국" else (0.05, 0.05)

danger_lats = np.random.normal(map_center[0], lat_var, num_danger)
danger_lons = np.random.normal(map_center[1], lon_var, num_danger)
danger_data = [[lat, lon, 1] for lat, lon in zip(danger_lats, danger_lons)]

HeatMap(danger_data, radius=15, blur=10, gradient={0.4: 'yellow', 0.6: 'orange', 1: 'red'}).add_to(m)

# [기능 2] 안전망(수련시설) 마커 추가
marker_cluster = MarkerCluster().add_to(m)
for idx, row in fac_filtered.iterrows():
    folium.Marker(
        location=[row['위도'], row['경도']],
        tooltip=f"🛡️ 안전망: {row['시설명']}",
        icon=folium.Icon(color='blue', icon='shield')
    ).add_to(marker_cluster)

# 지도를 크고 웅장하게 렌더링 (높이 650px)
components.html(m._repr_html_(), height=650)

st.markdown("---")

# 5. 마음건강 분석 그래프 영역 (Plotly 적용)
st.subheader(f"📊 {selected_region} 마음건강 연도별·지역별 변화 분석")

col1, col2 = st.columns(2)
mind_filtered = mind_df[(mind_df['지표명'] == selected_indicator) & (mind_df['연도'].astype(str) == selected_year)]

with col1:
    st.markdown(f"**1. 지역별 {selected_indicator} 비교**")
    mind_sorted = mind_filtered.sort_values(by="비율(%)", ascending=True)
    # 선택한 지역만 눈에 띄게 빨간색으로 강조
    mind_sorted['color'] = mind_sorted['지역명'].apply(
        lambda x: '#e74c3c' if selected_region != "전국" and x[:2] in str(x) else '#bdc3c7'
    )
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='color', color_discrete_map="identity")
    fig_bar.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.markdown(f"**2. {selected_region} 연도별 변화 추이**")
    target_region = mind_df['지역명'].iloc[0] if selected_region == "전국" else selected_region[:2]
    matched_regions = mind_df[mind_df['지역명'].str.contains(target_region, na=False)]['지역명']
    final_target = matched_regions.iloc[0] if not matched_regions.empty else mind_df['지역명'].iloc[0]
    
    trend_df = mind_df[(mind_df['지역명'] == final_target) & (mind_df['지표명'] == selected_indicator)].sort_values('연도')
    fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True)
    fig_line.update_traces(line_color='#e74c3c', marker=dict(size=10))
    fig_line.update_layout(margin=dict(l=0, r=0, t=30, b=0), height=400)
    st.plotly_chart(fig_line, use_container_width=True)
