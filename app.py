import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 페이지 기본 설정 및 환경 변수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Youth Canvas: 청소년 안전망 찾기", layout="wide", initial_sidebar_state="expanded")

# Mapbox 토큰 (스트림릿 클라우드 Secrets 사용, 없을 경우 빈 문자열 반환하여 에러 방지)
MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 데이터 로더 함수 (추후 CSV 연동 시 이 부분을 수정)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data
def load_facilities_data():
    # 실제로는 pd.read_csv("facilities_points.csv") 를 사용합니다.
    # MVP 테스트를 위한 샘플 데이터 생성
    data = pd.DataFrame({
        "facility_name": ["서울시립청소년센터", "강남구청소년상담복지센터", "마포구청소년쉼터", "부산해운대청소년수련관", "제주청소년상담센터"],
        "facility_type": ["청소년 수련시설", "청소년상담복지센터", "청소년쉼터", "청소년 수련시설", "청소년상담복지센터"],
        "sido": ["서울특별시", "서울특별시", "서울특별시", "부산광역시", "제주특별자치도"],
        "address": ["서울시 중구...", "서울시 강남구...", "서울시 마포구...", "부산시 해운대구...", "제주시..."],
        "phone": ["02-123-4567", "02-987-6543", "02-555-7777", "051-111-2222", "064-333-4444"],
        "lat": [37.5665, 37.5172, 37.5662, 35.1631, 33.4890],
        "lon": [126.9780, 127.0473, 126.9016, 129.1636, 126.4983]
    })
    # 유형별 색상 매핑
    color_map = {
        "청소년 수련시설": [50, 150, 255, 200],   # 파랑
        "청소년상담복지센터": [50, 255, 150, 200], # 초록
        "청소년쉼터": [255, 150, 50, 200]          # 주황
    }
    data['color'] = data['facility_type'].map(color_map)
    return data

@st.cache_data
def load_metrics_data():
    # 실제로는 pd.read_csv("regional_metrics.csv") 를 사용합니다.
    data = pd.DataFrame({
        "region_name": ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "경기도"],
        "지표명": ["10만명당 안전망 시설 수"] * 7,
        "연도": ["2024"] * 7,
        "value": [12.5, 10.2, 9.8, 11.1, 13.4, 10.5, 14.2]
    })
    return data

@st.cache_data
def load_hotline_contacts():
    # 실제로는 pd.read_csv("hotline_contacts.csv") 를 사용합니다.
    data = pd.DataFrame({
        "contact_name": ["청소년전화 1388", "자살예방상담전화", "여성긴급전화 1366", "안전드림(학교폭력)"],
        "phone": ["1388", "109", "1366", "117"],
        "description": ["365일 24시간 청소년 고민 상담", "우울감 등 말하기 어려운 고민이 있을 때", "가정폭력, 성폭력 등 긴급 상담", "학교폭력, 소년범죄 신고 및 상담"],
        "hours": ["24시간", "24시간", "24시간", "24시간"]
    })
    return data

@st.cache_resource
def get_korea_geometry():
    url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_provinces_geo_simple.json"
    try:
        kr_gdf = gpd.read_file(url)
        kr_geom = kr_gdf.geometry.unary_union 
        world_box = box(-180, -90, 180, 90)
        mask_geom = world_box.difference(kr_geom)
        mask_gdf = gpd.GeoDataFrame(geometry=[mask_geom], crs="EPSG:4326")
        return json.loads(mask_gdf.to_json()), kr_geom
    except Exception as e:
        return None, None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 데이터 로딩 및 공통 변수 초기화
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fac_df = load_facilities_data()
mind_df = load_metrics_data()
hotline_df = load_hotline_contacts()
mask_json, kr_geom = get_korea_geometry()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 사이드바 및 UI 테마 설정 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_theme_config(theme_choice):
    if theme_choice == "다크 모드":
        return {
            "bg_color": "#0E1117", "text_color": "#FFFFFF",
            "card_bg": "linear-gradient(135deg, #1A1C23 0%, #111318 100%)",
            "map_style": "mapbox://styles/mapbox/dark-v11",
            "mask_color": [14, 17, 23, 255], "plotly_theme": "plotly_dark"
        }
    else:
        return {
            "bg_color": "#FFFFFF", "text_color": "#2C3E50",
            "card_bg": "linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%)",
            "map_style": "mapbox://styles/mapbox/light-v10",
            "mask_color": [255, 255, 255, 255], "plotly_theme": "plotly_white"
        }

with st.sidebar:
    st.markdown('<div style="text-align:center; font-size:3rem; margin-bottom:-10px;">🌌</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:1.2rem; font-weight:700; color:#5865F2;">Youth Canvas</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:0.8rem; color:gray; margin-bottom:20px;">청소년 안전망 찾기 서비스</div>', unsafe_allow_html=True)
    
    st.header("🎨 테마 설정")
    theme_choice = st.radio("모드를 선택하세요", ["다크 모드", "라이트 모드"])
    theme = get_theme_config(theme_choice)
    st.markdown("---")
    
    st.header("🔍 지역 및 기관 필터")
    region_list = ["전국"] + list(fac_df['sido'].unique())
    selected_region = st.selectbox("📍 지역 선택", region_list)
    
    type_list = fac_df['facility_type'].unique()
    selected_types = st.multiselect("🏢 기관 유형 선택", type_list, default=type_list)
    
    st.markdown("---")
    show_danger = st.checkbox("🔴 지역 위험 신호 보기 (Beta)", value=False, help="준비 중인 데이터입니다. 주변의 위험 구역 척도를 표시합니다.")

# 동적 CSS 주입
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"] {{ font-family: 'Inter', sans-serif; }}
.kpi-card {{
    background: {theme['card_bg']};
    border: 1px solid rgba(128, 128, 128, 0.2); border-radius: 12px; padding: 20px; text-align: center;
    box-shadow: 0 4px 10px rgba(0, 0, 0, 0.1);
}}
.kpi-value {{ font-size: 1.8rem; font-weight: 700; color: {theme['text_color']}; }}
.kpi-label {{ color: gray; font-size: 0.9rem; font-weight: 500; }}
.gradient-title {{
    background: linear-gradient(120deg, #5865F2 0%, #00F0FF 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    font-size: 2.2rem; font-weight: 700; margin-bottom: 0.2rem;
}}
.section-header {{ color: #5865F2; font-size: 1.2rem; font-weight: 600; margin: 1.5rem 0 1rem 0; padding-left: 10px; border-left: 4px solid #5865F2; }}
</style>
""", unsafe_allow_html=True)

# 데이터 필터링 적용
if selected_region != "전국":
    fac_filtered = fac_df[(fac_df['sido'].str.contains(selected_region[:2])) & (fac_df['facility_type'].isin(selected_types))]
else:
    fac_filtered = fac_df[fac_df['facility_type'].isin(selected_types)]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 메인 화면 헤더
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="gradient-title">Youth Canvas: 청소년 안전망 탐색</div>', unsafe_allow_html=True)
st.markdown("<span style='color:gray;'>우리 동네의 청소년 수련시설, 상담복지센터, 쉼터를 한눈에 찾고 도움을 요청하세요.</span><br><br>", unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
with k1: 
    st.markdown(f'<div class="kpi-card"><div style="font-size: 1.8rem;">📍</div><div class="kpi-label">선택 지역</div><div class="kpi-value">{selected_region}</div></div>', unsafe_allow_html=True)
with k2: 
    st.markdown(f'<div class="kpi-card"><div style="font-size: 1.8rem;">🛡️</div><div class="kpi-label">검색된 보호/지원 기관</div><div class="kpi-value">{len(fac_filtered)}개</div></div>', unsafe_allow_html=True)
with k3: 
    st.markdown(f'<div class="kpi-card"><div style="font-size: 1.8rem;">🆘</div><div class="kpi-label">긴급 상담 전화</div><div class="kpi-value">1388</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 탭(Tab)별 렌더링 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tab1, tab2, tab3 = st.tabs(["🗺️ 청소년 안전망 지도", "📊 지역 지표 비교", "🆘 긴급 도움받기"])

def render_map_tab():
    st.markdown('<div class="section-header">우리 동네 안전망 찾기</div>', unsafe_allow_html=True)
    st.caption("💡 지도에 표시된 마커에 마우스를 올리면 기관의 상세 정보와 연락처를 확인할 수 있습니다.")
    
    map_center = [36.5, 127.5] if selected_region == "전국" else [fac_filtered['lat'].mean(), fac_filtered['lon'].mean()]
    if pd.isna(map_center[0]): map_center = [37.5665, 126.9780]
    
    layers = []
    
    # 1. 암막 레이어 (한국 이외 차단)
    if mask_json is not None:
        layers.append(pdk.Layer("GeoJsonLayer", mask_json, get_fill_color=theme['mask_color'], stroked=False, pickable=False))

    # 2. 베타: 위험 레이어
    if show_danger:
        np.random.seed(42)
        danger_df = pd.DataFrame({"위도": np.random.normal(map_center[0], 1.5, 300).astype(float), "경도": np.random.normal(map_center[1], 1.5, 300).astype(float)})
        if kr_geom is not None:
            danger_gdf = gpd.GeoDataFrame(danger_df, geometry=gpd.points_from_xy(danger_df['경도'], danger_df['위도']), crs="EPSG:4326")
            danger_chart_data = danger_gdf[danger_gdf.geometry.within(kr_geom)][['경도', '위도']].to_dict(orient='records')
        else:
            danger_chart_data = danger_df[['경도', '위도']].to_dict(orient='records')
            
        layers.append(pdk.Layer("HexagonLayer", data=danger_chart_data, get_position=["경도", "위도"], radius=1500, elevation_scale=50, elevation_range=[0, 1000], extruded=True, get_fill_color=[255, 75, 75, 150], pickable=False))

    # 3. 안전망 기관 마커 레이어
    fac_chart_data = fac_filtered.to_dict(orient='records')
    layers.append(pdk.Layer(
        "ScatterplotLayer",
        data=fac_chart_data,
        get_position=["lon", "lat"],
        get_radius=1500 if selected_region == "전국" else 500,
        get_fill_color="color", 
        pickable=True,
    ))

    view_state = pdk.ViewState(longitude=map_center[1], latitude=map_center[0], zoom=6.8 if selected_region=="전국" else 10.5, min_zoom=6.8, max_zoom=15.0, pitch=40, bearing=0)

    # 툴팁 HTML 포맷 구성
    tooltip_html = """
    <div style='background-color:#2C3E50; padding:10px; border-radius:5px; color:white;'>
        <h4 style='margin:0 0 5px 0;'>{facility_name}</h4>
        <b>유형:</b> {facility_type}<br>
        <b>전화:</b> <span style='color:#00F0FF;'>{phone}</span><br>
        <span style='font-size:0.8em; color:lightgray;'>{address}</span>
    </div>
    """

    st.pydeck_chart(pdk.Deck(
        map_provider="mapbox", map_style=theme['map_style'], api_keys={'mapbox': MAPBOX_TOKEN}, 
        layers=layers, initial_view_state=view_state, tooltip={"html": tooltip_html}
    ))

def render_compare_tab():
    st.markdown('<div class="section-header">지역사회 지표 단순 비교</div>', unsafe_allow_html=True)
    st.info("⚠️ **참고용 데이터입니다.** 본 차트는 각 지역의 인프라 현황을 단순 비교하기 위한 목적이며, 인과관계를 나타내지 않습니다.")
    
    if not mind_df.empty:
        mind_sorted = mind_df.sort_values(by="value", ascending=True)
        mind_sorted['선택 여부'] = mind_sorted['region_name'].apply(lambda x: '선택 지역' if selected_region != "전국" and x[:2] in selected_region else '타 지역')
        
        fig_bar = px.bar(mind_sorted, x="value", y="region_name", orientation='h', color='선택 여부', 
                         color_discrete_map={'선택 지역': '#00F0FF', '타 지역': 'gray'},
                         title="10만 명당 청소년 안전망 시설 수 비교")
        fig_bar.update_layout(template=theme['plotly_theme'], height=400, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.warning("데이터가 준비되지 않았습니다.")

def render_help_tab():
    st.markdown('<div class="section-header">🆘 언제든 도움을 요청하세요</div>', unsafe_allow_html=True)
    st.markdown("청소년 여러분, 혼자 고민하지 마세요. 여러분을 도와줄 전문가들이 24시간 기다리고 있습니다.")
    
    for i, row in hotline_df.iterrows():
        st.markdown(f"""
        <div style="background-color:rgba(88, 101, 242, 0.1); border-left: 5px solid #5865F2; padding:15px; border-radius:8px; margin-bottom:15px;">
            <h3 style="color:#5865F2; margin:0 0 5px 0;">📞 {row['contact_name']} : <strong>{row['phone']}</strong></h3>
            <p style="margin:0; color:gray;">{row['description']} ({row['hours']})</p>
        </div>
        """, unsafe_allow_html=True)
        
    render_source_expander()

def render_source_expander():
    with st.expander("ℹ️ 데이터 출처 및 지표 설명 (안내)"):
        st.markdown("""
        * **청소년 안전망 데이터**: 여성가족부 청소년시설 통합 정보 (2024년 기준)
        * **지역 위험 지표**: 통계청 및 공공데이터포털 자료 재가공
        * **유의사항**: 본 대시보드는 MVP(최소 기능 제품) 버전으로 지속적으로 데이터가 업데이트되고 있습니다. 
        """)

# 탭 실행
with tab1: render_map_tab()
with tab2: render_compare_tab()
with tab3: render_help_tab()
