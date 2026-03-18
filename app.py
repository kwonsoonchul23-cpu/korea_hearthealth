import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 페이지 기본 설정 (가장 먼저 와야 함)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Youth Canvas", layout="wide", initial_sidebar_state="expanded")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 사이드바 - 테마 선택 및 필터 (첨부파일의 고도화된 UI 적용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown('<div style="text-align:center; font-size:3rem; margin-bottom:-10px;">🌌</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:1.2rem; font-weight:700; color:#5865F2;">Youth Canvas</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:0.8rem; color:gray; margin-bottom:20px;">청소년 인프라·마음건강 분석</div>', unsafe_allow_html=True)
    
    # 🎨 [핵심 업데이트] 전체 사이트 색상 모드 선택
    st.header("🎨 테마 설정")
    theme_choice = st.radio("모드를 선택하세요", ["다크 모드", "라이트 모드"])
    st.markdown("---")
    
    region_coords = {
        "전국": [36.5, 127.5], "서울특별시": [37.5665, 126.9780], "부산광역시": [35.1796, 129.0756],
        "대구광역시": [35.8714, 128.6014], "인천광역시": [37.4563, 126.7052], "광주광역시": [35.1595, 126.8526],
        "대전광역시": [36.3504, 127.3845], "울산광역시": [35.5384, 129.3114], "세종특별자치시": [36.4800, 127.2890],
        "경기도": [37.2752, 127.0095], "강원도": [37.8854, 127.7298], "충청북도": [36.6358, 127.4913],
        "충청남도": [36.6588, 126.6728], "전라북도": [35.8203, 127.1088], "전라남도": [34.8163, 126.4629],
        "경상북도": [36.5760, 128.5056], "경상남도": [35.2383, 128.6925], "제주특별자치도": [33.4890, 126.4983]
    }
    
    st.header("🔍 데이터 필터")
    selected_region = st.selectbox("📍 분석할 지역 선택", list(region_coords.keys()))
    
    # 임시 연도/지표 (데이터 로드 전 미리 선언)
    year_list = ['2024', '2023', '2022', '2021']
    indicator_list = ['우울감', '스트레스', '자살시도율']
    selected_year = st.selectbox("📅 연도 선택", year_list)
    selected_indicator = st.selectbox("🧠 마음건강 지표 선택", indicator_list)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 테마에 따른 동적 변수 할당 (CSS, 배경색, 지도 스타일)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if theme_choice == "다크 모드":
    bg_color = "#0E1117"
    text_color = "#FFFFFF"
    card_bg = "linear-gradient(135deg, #1A1C23 0%, #111318 100%)"
    map_style = "dark"
    mask_color = [14, 17, 23, 255] # 스트림릿 다크 배경과 완벽히 일치하는 색상
    plotly_theme = "plotly_dark"
    safe_color = [0, 240, 255, 200]
else:
    bg_color = "#FFFFFF"
    text_color = "#2C3E50"
    card_bg = "linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%)"
    map_style = "light"
    mask_color = [255, 255, 255, 255] # 스트림릿 라이트 배경과 완벽히 일치하는 색상
    plotly_theme = "plotly_white"
    safe_color = [0, 120, 255, 200]

# 동적 CSS 주입
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.kpi-card {{
    background: {card_bg};
    border: 1px solid rgba(128, 128, 128, 0.2);
    border-radius: 12px; padding: 20px; text-align: center;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}}
.kpi-value {{ font-size: 1.8rem; font-weight: 700; color: {text_color}; }}
.kpi-label {{ color: gray; font-size: 0.9rem; font-weight: 500; }}
.gradient-title {{
    background: linear-gradient(120deg, #5865F2 0%, #00F0FF 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;
}}
.section-header {{
    color: #5865F2; font-size: 1.2rem; font-weight: 600; margin: 1.5rem 0 1rem 0;
    padding-left: 10px; border-left: 4px solid #5865F2;
}}
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 데이터 및 공간 마스크(가림막) 로드
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data
def load_data():
    try:
        fac_df = pd.read_csv("clean_facility.csv")
        mind_df = pd.read_csv("clean_mind_health.csv")
        mind_df['비율(%)'] = pd.to_numeric(mind_df['비율(%)'], errors='coerce')
        fac_df['위도'] = pd.to_numeric(fac_df['위도'], errors='coerce').astype(float)
        fac_df['경도'] = pd.to_numeric(fac_df['경도'], errors='coerce').astype(float)
        return fac_df.dropna(subset=['위도', '경도']), mind_df.dropna(subset=['비율(%)'])
    except:
        return pd.DataFrame(), pd.DataFrame()

@st.cache_resource
def get_korea_geometry():
    url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_provinces_geo_simple.json"
    try:
        kr_gdf = gpd.read_file(url)
        kr_geom = kr_gdf.geometry.unary_union 
        world_box = box(-180, -90, 180, 90)
        # 🚨 전 세계를 덮는 이불(world_box)에서 대한민국(kr_geom)만 빵꾸를 뚫음!
        mask_geom = world_box.difference(kr_geom)
        mask_gdf = gpd.GeoDataFrame(geometry=[mask_geom], crs="EPSG:4326")
        return json.loads(mask_gdf.to_json()), kr_geom
    except Exception as e:
        return None, None

fac_df, mind_df = load_data()
mask_json, kr_geom = get_korea_geometry()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 본문 대시보드 렌더링
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="gradient-title">Youth Canvas: 통합 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown("<span style='color:gray;'>지역사회 청소년 인프라 및 심리적/물리적 안전망 분석 (다크/라이트 모드 지원)</span><br><br>", unsafe_allow_html=True)

# KPI 카드 생성
def kpi_card(icon, label, value):
    st.markdown(f'<div class="kpi-card"><div style="font-size: 1.8rem;">{icon}</div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div>', unsafe_allow_html=True)

if not fac_df.empty and not mind_df.empty:
    if selected_region == "전국":
        fac_filtered = fac_df.copy()
        avg_mind = mind_df[mind_df['지표명'] == selected_indicator]['비율(%)'].mean()
    else:
        fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)].copy()
        avg_mind = mind_df[(mind_df['지역명'].str.contains(selected_region[:2], na=False)) & (mind_df['지표명'] == selected_indicator)]['비율(%)'].mean()
else:
    fac_filtered = pd.DataFrame([{"위도": 37.5, "경도": 127.0, "시설명": "데모 데이터"}])
    avg_mind = 0

k1, k2, k3 = st.columns(3)
with k1: kpi_card("📍", "선택된 지역", selected_region)
with k2: kpi_card("🛡️", "청소년 수련시설 (안전망)", f"{len(fac_filtered):,}개")
with k3: kpi_card("🧠", f"{selected_indicator} 평균 ({selected_year})", f"{avg_mind:.1f}%" if not pd.isna(avg_mind) else "데이터 없음")

st.markdown("<br>", unsafe_allow_html=True)

# 탭 구성
tab1, tab2, tab3 = st.tabs(["🗺️ 3D 입체 안전망 지도 (대한민국 전용)", "📊 마음건강 심층 분석", "🚦 교통사고 다발 구역 (준비중)"])

# ──────────────────────────────────────────────
# 탭 1: 3D 입체 지도 (대한민국 외 지역 완벽 차단)
# ──────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">위험 구역 vs 청소년 안전망 3D 뷰</div>', unsafe_allow_html=True)
    st.caption("💡 마우스를 우클릭 후 드래그하여 지도를 입체적으로 확인하세요.")
    
    legend_col1, legend_col2 = st.columns(2)
    with legend_col1: show_danger = st.checkbox("🔴 유해환경/위험구역 (3D 기둥) 켜기", value=True)
    with legend_col2: show_safe = st.checkbox("🔵 청소년 수련시설 (안전 마커) 켜기", value=True)

    map_center = region_coords[selected_region]
    zoom_level = 6.5 if selected_region == "전국" else 10.5

    # 가상 위험 데이터 생성
    np.random.seed(42)
    danger_df = pd.DataFrame({
        "위도": np.random.normal(map_center[0], 1.5 if selected_region == "전국" else 0.05, 800 if selected_region == "전국" else 150).astype(float),
        "경도": np.random.normal(map_center[1], 1.5 if selected_region == "전국" else 0.05, 800 if selected_region == "전국" else 150).astype(float)
    })

    # 바다에 빠진 데이터 삭제
    if kr_geom is not None:
        danger_gdf = gpd.GeoDataFrame(danger_df, geometry=gpd.points_from_xy(danger_df['경도'], danger_df['위도']), crs="EPSG:4326")
        danger_gdf = danger_gdf[danger_gdf.geometry.within(kr_geom)]
        danger_chart_data = danger_gdf[['경도', '위도']].to_dict(orient='records')
    else:
        danger_chart_data = danger_df[['경도', '위도']].to_dict(orient='records')

    fac_chart_data = fac_filtered[['경도', '위도', '시설명']].to_dict(orient='records')

    layers = []
    
    # 🚨 [핵심 해결] 스트림릿 테마 배경색과 똑같은 거대한 이불로 전 세계를 덮음! (한국만 뚫려있음)
    if mask_json is not None:
        layers.append(pdk.Layer(
            "GeoJsonLayer",
            mask_json,
            get_fill_color=mask_color, # 다크모드면 검정, 라이트모드면 하양
            stroked=False,
            pickable=False
        ))

    if show_danger:
        layers.append(pdk.Layer(
            "HexagonLayer",
            data=danger_chart_data,
            get_position=["경도", "위도"],
            radius=1500 if selected_region == "전국" else 300,
            elevation_scale=50 if selected_region == "전국" else 15,
            elevation_range=[0, 1000],
            extruded=True,
            get_fill_color=[255, 75, 75, 200],
            pickable=False
        ))

    if show_safe:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=fac_chart_data,
            get_position=["경도", "위도"],
            get_radius=1500 if selected_region == "전국" else 300,
            get_fill_color=safe_color, 
            pickable=True,
        ))

    view_state = pdk.ViewState(
        longitude=map_center[1],
        latitude=map_center[0],
        zoom=zoom_level,
        min_zoom=6.5, # 축소 한계
        max_zoom=15.0,
        pitch=50,
        bearing=0
    )

    st.pydeck_chart(pdk.Deck(
        map_style=map_style, # 테마에 맞춰 'dark' 또는 'light'로 자동 변경
        layers=layers,
        initial_view_state=view_state,
        tooltip={"html": "<div style='color:white; font-size:12px;'><b>🛡️ 안전망:</b> {시설명}</div>"}
    ))

# ──────────────────────────────────────────────
# 탭 2: 마음건강 심층 분석 (Plotly 테마 동적 변경)
# ──────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">인프라와 마음건강의 상관관계 분석</div>', unsafe_allow_html=True)
    
    if not mind_df.empty:
        row1_col1, row1_col2 = st.columns([5, 5])
        
        with row1_col1:
            st.markdown(f"**📊 지역별 {selected_indicator} 수준 비교**")
            mind_sorted = mind_df[mind_df['지표명'] == selected_indicator].copy()
            mind_sorted['선택 여부'] = mind_sorted['지역명'].apply(lambda x: '선택 지역' if selected_region != "전국" and x[:2] in selected_region else '타 지역')
            fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='선택 여부', color_discrete_map={'선택 지역': '#00F0FF', '타 지역': 'gray'})
            fig_bar.update_layout(template=plotly_theme, height=350, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)

        with row1_col2:
            st.markdown(f"**📈 5년간 {selected_indicator} 변화 추이**")
            fig_line = px.line(mind_df[mind_df['지표명'] == selected_indicator], x="연도", y="비율(%)", color="지역명", markers=True)
            fig_line.update_layout(template=plotly_theme, height=350)
            st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.info("데이터를 불러오는 중입니다.")

# ──────────────────────────────────────────────
# 탭 3: 교통사고 다발 구역 
# ──────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🚦 사상자 연령대별 교통사고 심층 분석</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="background-color:rgba(88, 101, 242, 0.1); padding:30px; border-radius:12px; text-align:center; border: 1px dashed #5865F2;">
        <h2 style="color:#5865F2; margin-bottom:10px;">데이터 적재 대기 중... ⏳</h2>
        <p style="color:gray; font-size:1.1rem;">
        현재 TAAS에서 <strong>2021년~2024년 교통사고 데이터</strong>를 수집 중입니다.<br>
        완료되는 대로 연령별 취약 구역 추이와 3D 히트맵이 연동됩니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
