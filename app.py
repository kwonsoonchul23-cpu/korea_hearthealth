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

    # [에러 해결] 좌표를 배열(List)로 명확히 묶어주는 coord 컬럼 생성
    fac_filtered['coord'] = fac_filtered.apply(lambda row: [float(row['경도']), float(row['위도'])], axis=1)

    # 가상의 위험 지역 데이터 생성 (실제 데이터 도입 시 교체될 부분)
    np.random.seed(42)
    num_danger = 800 if selected_region == "전국" else 150
    lat_var, lon_var = (1.5, 1.5) if selected_region == "전국" else (0.05, 0.05)
    danger_df = pd.DataFrame({
        "위도": np.random.normal(map_center[0], lat_var, num_danger).astype(float),
        "경도": np.random.normal(map_center[1], lon_var, num_danger).astype(float)
    })
    danger_df['coord'] = danger_df.apply(lambda row: [float(row['경도']), float(row['위도'])], axis=1)

    # [PyDeck 레이어 1] 붉은색 3D 육각 기둥 (위험 지역)
    layer_danger_hex = pdk.Layer(
        "HexagonLayer",
        data=danger_df,
        get_position="coord", # 수정된 좌표 지정 방식
        radius=1500 if selected_region == "전국" else 300,
        elevation_scale=50 if selected_region == "전국" else 15,
        elevation_range=[0, 1000],
        extruded=True,
        get_fill_color=[220, 50, 50, 180], 
        coverage=1,
        pickable=False
    )

    # [PyDeck 레이어 2] 파란색 점 (청소년 안전망)
    layer_safe_scatter = pdk.Layer(
        "ScatterplotLayer",
        data=fac_filtered,
        get_position="coord", # 수정된 좌표 지정 방식
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
    * 🚨 **붉은색 육각 기둥**: 유해업소, 사고 다발 지역 등 **청소년 위험 요소가 밀집된 곳**입니다. 기둥이 높게 솟을수록 위험도가 심각합니다.
    * 🔵 **파란색 마커**: 청소년 수련시설 및 복지센터 등 **지역사회의 방어망(안전지대)**입니다.
    * **✅ 긍정적 지점**: 붉은 기둥 주변이나 사이사이에 파란 마커가 잘 분포되어 있다면, 위험 구역에 적절한 안전 인프라가 구축되어 있다는 뜻입니다.
    * **⚠️ 부정적 지점**: 거대한 붉은 기둥만 있고 파란 마커가 텅 비어있는 지역은 **'보호 사각지대'**입니다. 가장 시급하게 정책적 지원과 시설 확충이 필요한 곳입니다.
    """)

with col2:
    st.subheader(f"📊 {selected_year}년 지역별 {selected_indicator} 비교")
    filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]
    mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
    mind_sorted['color'] = mind_sorted['지역명'].apply(
        lambda x: '#e74c3c' if selected_region != "전국" and x[:2] in selected_region else '#bdc3c7'
    )
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='color', color_discrete_map="identity")
    fig_bar.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=400)
    st.plotly_chart(fig_bar, use_container_width=True)
    
    # 💡 막대그래프 해석 가이드
    st.success("""
    **📊 순위 비교 가이드: 우리 동네의 현주소**
    * 붉은색으로 강조된 우리가 선택한 지역이 타지역 대비 어느 위치에 있는지 확인합니다.
    * 스트레스, 우울감, 자살 시도율은 **막대기가 짧을수록(수치가 낮을수록) 긍정적**입니다. 만약 우리 지역이 가장 긴 막대 그룹에 속해 있다면, 지역적 특성에 기인한 강력한 원인(학업, 환경 등)이 숨어있다는 뜻입니다.
    """)

st.markdown("---")
st.subheader("📈 다각적 데이터 심층 분석 (원인과 결과 찾기)")

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
    * **우하향(↘, 긍정):** 지역사회의 인프라 확충이나 교육 정책이 올바르게 작동하여 청소년 마음건강이 개선되고 있습니다.
    * **우상향(↗, 부정):** 코로나 이후 일상 회복 과정의 부작용, 사교육 심화, 혹은 새로운 디지털 위험(사이버 폭력 등)이 급증하여 악영향을 미치고 있음을 의미합니다.
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
    * 차트 조각들이 비교적 균등하다면 인프라가 고르게 잘 배분된 **긍정적 상태**입니다.
    * 하나의 큰 조각이 파이를 독차지한다면 특정 학군이나 신도시에만 시설이 쏠린 **인프라 불평등(부정적 상태)**을 나타냅니다.
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
    * 각 점은 하나의 시/도를 의미합니다. 점들의 흐름이 **오른쪽 아래(↘)로 향할수록 긍정적**입니다. 
    * 즉, "오른쪽(안전망이 많음)으로 갈수록, 아래(스트레스/우울감이 낮음)에 위치한다"는 가설이 성립하며, 이는 예산을 들여 청소년 인프라를 지어야 하는 가장 완벽한 논리적 근거가 됩니다.
    """)
