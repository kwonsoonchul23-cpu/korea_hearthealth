import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np

# 1. 페이지 설정
st.set_page_config(page_title="Youth Canvas", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.main {background-color: #f8f9fa;}
h1, h2, h3 {color: #2c3e50;}
</style>
""", unsafe_allow_html=True)

st.title("🚨 Youth Canvas: 청소년 위험 구역 및 마음건강 3D 대시보드")
st.markdown("**제7차 청소년정책기본계획** 기반 지역사회 청소년 인프라 및 마음건강 분석 프로젝트")
st.markdown("---")

# 2. 데이터 불러오기
@st.cache_data
def load_data():
    fac_df = pd.read_csv("clean_facility.csv")
    mind_df = pd.read_csv("clean_mind_health.csv")
    
    mind_df['지역명'] = mind_df['지역명'].astype(str)
    mind_df['지표명'] = mind_df['지표명'].astype(str)
    mind_df['연도'] = mind_df['연도'].astype(int).astype(str) 
    mind_df['비율(%)'] = pd.to_numeric(mind_df['비율(%)'], errors='coerce')
    
    fac_df['시도명'] = fac_df['시도명'].astype(str)
    fac_df['위도'] = pd.to_numeric(fac_df['위도'], errors='coerce')
    fac_df['경도'] = pd.to_numeric(fac_df['경도'], errors='coerce')
    
    return fac_df.dropna(subset=['위도', '경도']), mind_df.dropna(subset=['비율(%)'])

fac_df, mind_df = load_data()

# 3. 사이드바 - 지역 검색 기능
region_coords = {
    "전국": [36.5, 127.5], "서울특별시": [37.5665, 126.9780], "부산광역시": [35.1796, 129.0756],
    "대구광역시": [35.8714, 128.6014], "인천광역시": [37.4563, 126.7052], "광주광역시": [35.1595, 126.8526],
    "대전광역시": [36.3504, 127.3845], "울산광역시": [35.5384, 129.3114], "세종특별자치시": [36.4800, 127.2890],
    "경기도": [37.2752, 127.0095], "강원도": [37.8854, 127.7298], "충청북도": [36.6358, 127.4913],
    "충청남도": [36.6588, 126.6728], "전라북도": [35.8203, 127.1088], "전라남도": [34.8163, 126.4629],
    "경상북도": [36.5760, 128.5056], "경상남도": [35.2383, 128.6925], "제주특별자치도": [33.4890, 126.4983]
}

st.sidebar.header("🔍 데이터 탐색 필터")
selected_region = st.sidebar.selectbox("📍 분석할 지역 선택", list(region_coords.keys()))
year_list = sorted(mind_df['연도'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("📅 연도 선택", year_list)
indicator_list = mind_df['지표명'].unique()
selected_indicator = st.sidebar.selectbox("🧠 마음건강 지표 선택", indicator_list)

# 4. 상단 레이아웃 (3D 지도 vs 막대 그래프)
col1, col2 = st.columns([6, 4])

with col1:
    st.subheader(f"🗺️ {selected_region} 3D 위험도 및 방어망 시각화")
    st.caption("💡 마우스 **우클릭 후 드래그**하면 지도를 3D로 기울이거나 회전할 수 있습니다.")
    
    map_center = region_coords[selected_region]
    zoom_level = 6.5 if selected_region == "전국" else 10.5
    
    # 지역 필터링
    if selected_region != "전국":
        fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)]
    else:
        fac_filtered = fac_df

    # 가상의 위험 지역 데이터 생성 (실제 데이터 수집 전 데모용)
    np.random.seed(42)
    num_danger = 1000 if selected_region == "전국" else 200
    lat_var, lon_var = (1.5, 1.5) if selected_region == "전국" else (0.05, 0.05)
    danger_df = pd.DataFrame({
        "위도": np.random.normal(map_center[0], lat_var, num_danger),
        "경도": np.random.normal(map_center[1], lon_var, num_danger)
    })

    # [PyDeck 레이어 1] 위험 구역: 붉은색 3D 육각 기둥 (HexagonLayer)
    layer_danger_hex = pdk.Layer(
        "HexagonLayer",
        danger_df,
        get_position=["경도", "위도"],
        radius=1500 if selected_region == "전국" else 300, # 육각형 크기
        elevation_scale=50 if selected_region == "전국" else 15, # 기둥 높이 배율
        elevation_range=[0, 1000],
        extruded=True, # 3D 입체 효과 켜기
        get_fill_color="[220, 50, 50, 180]", # 붉은색
        coverage=1,
    )

    # [PyDeck 레이어 2] 청소년 안전망: 파란색 점 (ScatterplotLayer)
    layer_safe_scatter = pdk.Layer(
        "ScatterplotLayer",
        fac_filtered,
        get_position=["경도", "위도"],
        get_radius=1200 if selected_region == "전국" else 250,
        get_fill_color="[50, 150, 255, 200]", # 파란색
        pickable=True,
    )

    # 3D 뷰포트 설정
    view_state = pdk.ViewState(
        longitude=map_center[1],
        latitude=map_center[0],
        zoom=zoom_level,
        pitch=50, # 지도를 50도 기울여서 3D 효과 극대화
        bearing=0
    )

    # Streamlit에 PyDeck 지도 렌더링
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",
        layers=[layer_danger_hex, layer_safe_scatter],
        initial_view_state=view_state,
        tooltip={"text": "{시설명}"}
    ))

with col2:
    st.subheader(f"📊 {selected_year}년 지역별 {selected_indicator} 비교")
    filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]
    mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
    mind_sorted['color'] = mind_sorted['지역명'].apply(
        lambda x: '#e74c3c' if selected_region != "전국" and x[:2] in selected_region else '#3498db'
    )
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='color', color_discrete_map="identity")
    fig_bar.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=500)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
st.subheader("📈 다각적 데이터 분석 (인포그래픽 스타일)")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("**1. 5년간 변화 추이 (라인 그래프)**")
    target_region = mind_df['지역명'].iloc[0] if selected_region == "전국" else selected_region[:2]
    matched_regions = mind_df[mind_df['지역명'].str.contains(target_region)]['지역명']
    final_target = matched_regions.iloc[0] if not matched_regions.empty else mind_df['지역명'].iloc[0]
    
    trend_df = mind_df[(mind_df['지역명'] == final_target) & (mind_df['지표명'] == selected_indicator)].sort_values('연도')
    fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True, title=f"{final_target} {selected_indicator} 추이")
    st.plotly_chart(fig_line, use_container_width=True)

with col4:
    st.markdown("**2. 세부 지역별 시설 비율 (도넛 차트)**")
    if not fac_filtered.empty:
        pie_df = fac_filtered['시군구명'].value_counts().reset_index()
        pie_df.columns = ['시군구명', '시설 수']
        if len(pie_df) > 5:
            top_5 = pie_df.iloc[:5]
            others = pd.DataFrame([['기타', pie_df['시설 수'].iloc[5:].sum()]], columns=['시군구명', '시설 수'])
            pie_df = pd.concat([top_5, others])
        fig_pie = px.pie(pie_df, values='시설 수', names='시군구명', hole=0.4, title=f"{selected_region} 내 시설 분포")
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)

with col5:
    st.markdown("**3. 인프라와 마음건강 관계 (산점도)**")
    fac_count = fac_df['시도명'].value_counts().reset_index()
    fac_count.columns = ['지역명_원본', '시설 수']
    fac_count['지역명_축약'] = fac_count['지역명_원본'].str[:2]
    
    mind_scatter = filtered_mind_year.copy()
    mind_scatter['지역명_축약'] = mind_scatter['지역명'].str[:2]
    scatter_df = pd.merge(mind_scatter, fac_count, on='지역명_축약', how='inner')
    if not scatter_df.empty:
        fig_scatter = px.scatter(scatter_df, x="시설 수", y="비율(%)", hover_name="지역명", 
                                 title=f"청소년 시설 수 vs {selected_indicator}",
                                 color_discrete_sequence=['#9b59b6'])
        st.plotly_chart(fig_scatter, use_container_width=True)
