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
    
    # 🚨 체크박스로 안전하게 교체!
    st.markdown("👇 **[상호작용 범례]** 체크박스를 클릭해 원하는 데이터만 지도에 띄워보세요.")
    legend_col1, legend_col2 = st.columns(2)
    with legend_col1:
        show_danger = st.checkbox("🔴 위험 구역 (3D 육각 기둥) 켜기", value=True)
    with legend_col2:
        show_safe = st.checkbox("🔵 청소년 안전망 (파란 마커) 켜기", value=True)
    
    map_center = region_coords[selected_region]
    zoom_level = 6.5 if selected_region == "전국" else 10.5
    
    if selected_region != "전국":
        fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)].copy()
    else:
        fac_filtered = fac_df.copy()

    # 가상 위험 데이터 생성
    np.random.seed(42)
    num_danger = 800 if selected_region == "전국" else 150
    lat_var, lon_var = (1.5, 1.5) if selected_region == "전국" else (0.05, 0.05)
    danger_df = pd.DataFrame({
        "위도": np.random.normal(map_center[0], lat_var, num_danger).astype(float),
        "경도": np.random.normal(map_center[1], lon_var, num_danger).astype(float)
    })

    fac_chart_data = fac_filtered[['경도', '위도', '시설명']].to_dict(orient='records')
    danger_chart_data = danger_df[['경도', '위도']].to_dict(orient='records')

    layers = []
    
    if show_danger:
        layers.append(pdk.Layer(
            "HexagonLayer",
            data=danger_chart_data,
            get_position=["경도", "위도"],
            radius=1500 if selected_region == "전국" else 300,
            elevation_scale=50 if selected_region == "전국" else 15,
            elevation_range=[0, 1000],
            extruded=True,
            pickable=False
        ))

    if show_safe:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=fac_chart_data,
            get_position=["경도", "위도"],
            get_radius=1500 if selected_region == "전국" else 300,
            get_fill_color=[50, 150, 255, 200],
            pickable=True,
        ))

    view_state = pdk.ViewState(
        longitude=map_center[1],
        latitude=map_center[0],
        zoom=zoom_level,
        min_zoom=6.5,
        max_zoom=15.0,
        pitch=50,
        bearing=0
    )

    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/light-v10",
        layers=layers,
        initial_view_state=view_state,
        tooltip={"html": "<b>🛡️ 안전망:</b> {시설명}"}
    ))
    
    st.info("""
    **🧭 지도 분석 가이드: 무엇을 봐야 할까요?**
    * 🚨 **육각 기둥**: 유해업소 등 **청소년 위험 요소가 밀집된 곳**입니다. 
    * 🔵 **파란색 마커**: 청소년 수련시설 등 **지역사회의 방어망(안전지대)**입니다.
    * **⚠️ 부정적 지점**: 거대한 붉은 기둥만 있고 파란 마커가 텅 비어있는 지역은 **'보호 사각지대'**입니다. 
    """)

with col2:
    st.subheader(f"📊 지역별 {selected_indicator} 수준 비교 ({selected_year}년)")
    filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]
    mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
    mind_sorted['선택 지역'] = mind_sorted['지역명'].apply(
        lambda x: '선택됨' if selected_region != "전국" and x[:2] in selected_region else '기타 지역'
    )
    
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='선택 지역', 
                     color_discrete_map={'선택됨': '#e74c3c', '기타 지역': '#bdc3c7'})
    fig_bar.update_layout(margin=dict(l=0, r=0, t=20, b=0), height=400, legend=dict(title="지역 범례", yanchor="bottom", y=0.01, xanchor="right", x=0.99))
    st.plotly_chart(fig_bar, use_container_width=True)
    
    st.success("""
    **📊 순위 비교 가이드: 우리 동네의 현주소**
    * 💡 **마우스 오버**: 막대그래프에 마우스를 올리면 정확한 수치를 확인할 수 있습니다.
    * 🖱️ **범례 클릭**: 우측 하단 범례의 '기타 지역'을 클릭하면 우리 지역만 단독으로 떼어내서 볼 수 있습니다.
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
    fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True, color_discrete_sequence=['#e74c3c'])
    fig_line.update_traces(marker=dict(size=8))
    fig_line.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, hovermode="x unified")
    st.plotly_chart(fig_line, use_container_width=True)
    
    st.warning("""
    **📉 추이 가이드: 드래그해서 확대해보세요!**
    * 특정 연도 구간을 마우스로 드래그하면 화면이 줌인(Zoom-in) 됩니다. (되돌리려면 더블클릭)
    * **우하향(↘):** 환경 개선 노력이 효과를 거두고 있다는 긍정적 지표입니다.
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
        fig_pie.update_traces(textposition='inside', textinfo='percent+label', hovertemplate="%{label}: %{value}개 (%{percent})")
        fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, showlegend=True, legend=dict(orientation="h", yanchor="bottom", y=-0.2))
        st.plotly_chart(fig_pie, use_container_width=True)
    
    st.info("""
    **🍩 분포 가이드: 범례를 껐다 켜보세요!**
    * 그래프 밑의 범례(예: 특정 구)를 클릭하면 해당 구역이 차트에서 사라지며 나머지 지역의 비율이 자동으로 재계산됩니다.
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
        fig_scatter = px.scatter(scatter_df, x="시설 수", y="비율(%)", hover_name="지역명", color="지역명", size="시설 수", size_max=20)
        fig_scatter.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=300, showlegend=False)
        st.plotly_chart(fig_scatter, use_container_width=True)
        
    st.success("""
    **🌌 상관관계 가이드: 점에 마우스를 올려보세요!**
    * 점 위에 마우스를 올리면 해당 지역의 이름과 시설 개수가 나타납니다.
    * 전체적인 점들의 흐름이 **오른쪽 아래(↘)로 향할수록**, "안전망이 많을수록 청소년의 마음이 건강하다"는 증거가 됩니다.
    """)
