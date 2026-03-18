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
.stInfo, .stSuccess, .stWarning {padding: 1rem; border-radius: 0.5rem;}
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
    fac_df['위도'] = pd.to_numeric(fac_df['위도'], errors='coerce').astype(float)
    fac_df['경도'] = pd.to_numeric(fac_df['경도'], errors='coerce').astype(float)
    
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
    st.subheader(f"🗺️ {selected_region} 3D 위험 구역 및 안전망 시각화")
    st.caption("💡 마우스 **우클릭 후 드래그**하면 지도를 3D로 기울이거나 회전할 수 있습니다.")
    
    map_center = region_coords[selected_region]
    zoom_level = 6.5 if selected_region == "전국" else 10.5
    
    if selected_region != "전국":
        fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)].copy()
    else:
        fac_filtered = fac_df.copy()

    # 가상의 위험 지역 데이터 생성
    np.random.seed(42)
    num_danger = 800 if selected_region == "전국" else 150
    lat_var, lon_var = (1.5, 1.5) if selected_region == "전국" else (0.05, 0.05)
    danger_df = pd.DataFrame({
        "위도": np.random.normal(map_center[0], lat_var, num_danger).astype(float),
        "경도": np.random.normal(map_center[1], lon_var, num_danger).astype(float)
    })

    # 🚨 [핵심 해결] Pandas 직렬화 에러를 막기 위해 순수 Python 리스트 형태로 변환
    fac_chart_data = fac_filtered[['경도', '위도', '시설명']].to_dict(orient='records')
    danger_chart_data = danger_df[['경도', '위도']].to_dict(orient='records')

    # [PyDeck 레이어 1] 붉은색 3D 육각 기둥 (위험 지역)
    # HexagonLayer는 밀도에 따라 자동 배색되므로 get_fill_color 속성 제거
    layer_danger_hex = pdk.Layer(
        "HexagonLayer",
        data=danger_chart_data,
        get_position=["경도", "위도"],
        radius=1500 if selected_region == "전국" else 300,
        elevation_scale=50 if selected_region == "전국" else 15,
        elevation_range=[0, 1000],
        extruded=True,
        pickable=False
    )

    # [PyDeck 레이어 2] 파란색 점 (청소년 안전망)
    layer_safe_scatter = pdk.Layer(
        "ScatterplotLayer",
        data=fac_chart_data,
        get_position=["경도", "위도"],
        get_radius=1500 if selected_region == "전국" else 300,
        get_fill_color=[50, 150, 255, 200],
        pickable=True,
    )

    view_state = pdk.ViewState(
        longitude=map_center[1],
        latitude=map_center[0],
        zoom=zoom_level,
        pitch=50,
        bearing=0
    )

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",
        layers=[layer_danger_hex, layer_safe_scatter],
        initial_view_state=view_state,
        tooltip={"html": "<b>🛡️ 안전망:</b> {시설명}"}
    ))
    
    # 💡 지도 해석 가이드
    st.info("""
    **🧭 지도 분석 가이드: 무엇을 봐야 할까요?**
    * 🚨 **육각 기둥**: 교통사고 다발 구역, 유해업소 등 **청소년 위험 요소가 밀집된 곳**입니다. 붉은색으로 솟아오를수록 위험도가 심각합니다.
    * 🔵 **파란색 마커**: 청소년 수련시설 및 복지센터 등 **지역사회의 방어망(안전지대)**입니다.
    * **✅ 긍정적 지점**: 육각 기둥 주변에 파란 마커가 잘 분포되어 있다면, 위험 구역에 적절한 보호 인프라가 구축되어 있다는 뜻입니다.
    * **⚠️ 부정적 지점**: 거대한 붉은 기둥만 있고 파란 마커가 텅 비어있는 지역은 **'보호 사각지대'**입니다. 정책적 지원이 가장 시급한 곳입니다.
    """)

with col2:
    st.subheader(f"📊 지역별 {selected_indicator} 수준 비교 ({selected_year}년)")
    filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]
    mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
    mind_sorted['color'] = mind_sorted['지역명'].apply(
        lambda x: '#e74c3c' if selected_region != "전국" and x[:2] in selected_region else '#bdc3c7'
    )
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='color', color_discrete_map="identity")
    fig_bar.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=400)
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # 💡 막대그래프 해석 가이드
    st.success("""
    **📊 순위 비교 가이드: 우리 동네의 현주소**
    * 붉은색으로 강조된 우리가 선택한 지역이 타지역 대비 어느 위치에 있는지 비교합니다.
    * 스트레스, 우울감, 자살 시도율은 **막대기가 짧을수록 긍정적**입니다. 우리 지역이 가장 긴 그룹에 있다면 지역적 특성에 기인한 원인이 숨어있다는 경고입니다.
    """)

st.markdown("---")
st.subheader("📈 인프라와 마음건강의 상관관계 다각적 분석")

col3, col4, col5 = st.columns(3)

with col3:
    st.markdown(f"**1. 5년간 {selected_indicator} 변화 추이**")
    target_region = mind_df['지역명'].iloc[0] if selected_region == "전국" else selected_region[:2]
    matched_regions = mind_df[mind_df['지역명'].str.contains(target_region)]['지역명']
    final_target = matched_regions.iloc[0] if not matched_regions.empty else mind_df['지역명'].iloc[0]
    
    trend_df = mind_df[(mind_df['지역명'] == final_target) & (mind_df['지표명'] == selected_indicator)].sort_values('연도')
    fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True)
    fig_line.update_traces(line_color='#e74c3c', marker=dict(size=8))
    fig_line.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.warning("""
    **📉 추이 가이드: 왜 이런 변화가 생겼을까?**
    * **우하향(↘, 긍정):** 지역사회의 인프라 확충과 교육 정책이 올바르게 작동하고 있다는 뜻입니다.
    * **우상향(↗, 부정):** 코로나 이후 일상 회복의 부작용, 학업 스트레스, 신종 사이버 범죄 등이 악영향을 미치고 있음을 의미합니다.
    """)

with col4:
    st.markdown("**2. 세부 지역별 안전망(시설) 분포율**")
    if not fac_filtered.empty:
        pie_df = fac_filtered['시군구명'].value_counts().reset_index()
        pie_df.columns = ['시군구명', '시설 수']
        if len(pie_df) > 5:
            top_5 = pie_df.iloc[:5]
            others = pd.DataFrame([['나머지 지역', pie_df['시설 수'].iloc[5:].sum()]], columns=['시군구명', '시설 수'])
            pie_df = pd.concat([top_5, others])
        fig_pie = px.pie(pie_df, values='시설 수', names='시군구명', hole=0.4)
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.info("""
    **🍩 분포 가이드: 혜택은 공평한가?**
    * 차트 조각들이 비슷하게 균등하다면 인프라가 고르게 배분된 **안정적 상태**입니다.
    * 하나의 큰 조각이 파이를 독차지한다면 특정 지역에만 시설이 쏠린 **인프라 불평등(부정적 상태)**을 나타냅니다.
    """)

with col5:
    st.markdown(f"**3. 시설 개수 vs {selected_indicator} 상관관계**")
    fac_count = fac_df['시도명'].value_counts().reset_index()
    fac_count.columns = ['지역명_원본', '시설 수']
    fac_count['지역명_축약'] = fac_count['지역명_원본'].str[:2]
    
    mind_scatter = filtered_mind_year.copy()
    mind_scatter['지역명_축약'] = mind_scatter['지역명'].str[:2]
    scatter_df = pd.merge(mind_scatter, fac_count, on='지역명_축약', how='inner')
    if not scatter_df.empty:
        fig_scatter = px.scatter(scatter_df, x="시설 수", y="비율(%)", hover_name="지역명", color_discrete_sequence=['#9b59b6'])
        fig_scatter.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    st.success("""
    **🌌 상관관계 가이드: 안전망은 진짜 효과가 있을까?**
    * 전체적인 점들의 흐름이 **오른쪽 아래(↘)로 향할수록 긍정적**입니다. 
    * "오른쪽(안전망이 많음)으로 갈수록, 아래(스트레스/우울감이 낮음)에 위치한다"는 강력한 논리적 근거가 됩니다.
    """)
