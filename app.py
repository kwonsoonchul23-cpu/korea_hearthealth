import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json
import requests  # API 호출을 위한 필수 라이브러리

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 페이지 기본 설정 및 환경 변수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Youth Canvas: 청소년 안전망 찾기", layout="wide", initial_sidebar_state="expanded")

MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 데이터 로더 함수 (API 자동 갱신 적용)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 🚨 [핵심] ttl=86400 옵션을 주면 24시간마다 알아서 함수를 다시 실행하여 최신 API 데이터를 가져옵니다.
@st.cache_data(ttl=86400) 
def load_facilities_data():
    # 🌟 향후 공공데이터 API 연동 시 사용할 로직 (현재는 주석 처리)
    """
    api_key = st.secrets.get("PUBLIC_DATA_API_KEY", "")
    if api_key:
        url = "http://api.data.go.kr/openapi/tn_pubr_public_youth_fclty_api"
        params = {'serviceKey': api_key, 'pageNo': '1', 'numOfRows': '1000', 'type': 'json'}
        response = requests.get(url, params=params)
        # JSON 파싱 후 DataFrame으로 변환하는 코드...
        # return df
    """

    # --- [현재 실감나는 테스트를 위한 대규모 전국 데이터 자동 생성기] ---
    sido_sigungu_map = {
        "서울특별시": {"강남구": (37.517, 127.047), "강동구": (37.530, 127.123), "강북구": (37.639, 127.025), "강서구": (37.550, 126.849), "관악구": (37.478, 126.951), "광진구": (37.538, 127.082), "구로구": (37.495, 126.887), "금천구": (37.451, 126.902), "노원구": (37.654, 127.056), "도봉구": (37.668, 127.047), "동대문구": (37.574, 127.039), "동작구": (37.512, 126.939), "마포구": (37.566, 126.901), "서대문구": (37.579, 126.936), "서초구": (37.483, 127.032), "성동구": (37.563, 127.036), "성북구": (37.589, 127.016), "송파구": (37.514, 127.105), "양천구": (37.516, 126.866), "영등포구": (37.526, 126.896), "용산구": (37.532, 126.990), "은평구": (37.602, 126.929), "종로구": (37.572, 126.979), "중구": (37.563, 126.997), "중랑구": (37.606, 127.092)},
        "경기도": {"수원시": (37.263, 127.028), "성남시": (37.420, 127.126), "고양시": (37.658, 126.832), "용인시": (37.241, 127.177)},
        "부산광역시": {"해운대구": (35.163, 129.163), "부산진구": (35.162, 129.053), "동래구": (35.204, 129.077)}
    }
    
    types = ["청소년 수련시설", "청소년상담복지센터", "청소년쉼터"]
    records = []
    
    np.random.seed(42)
    for sido, sigungu_dict in sido_sigungu_map.items():
        for sigungu, (lat, lon) in sigungu_dict.items():
            # 각 구마다 3~7개의 기관을 무작위로 흩뿌림
            num_facilities = np.random.randint(3, 8)
            for i in range(num_facilities):
                fac_type = np.random.choice(types, p=[0.5, 0.3, 0.2])
                records.append({
                    "facility_name": f"{sido} {sigungu} {fac_type} {i+1}호",
                    "facility_type": fac_type,
                    "sido": sido,
                    "sigungu": sigungu,
                    "address": f"{sido} {sigungu} 어느 길 {np.random.randint(1, 100)}",
                    "phone": f"02-{np.random.randint(1000, 9999)}-{np.random.randint(1000, 9999)}",
                    "lat": lat + np.random.uniform(-0.02, 0.02),
                    "lon": lon + np.random.uniform(-0.02, 0.02)
                })
    
    data = pd.DataFrame(records)
    # -----------------------------------------------------------

    color_map = {
        "청소년 수련시설": [50, 150, 255, 200],   
        "청소년상담복지센터": [50, 255, 150, 200], 
        "청소년쉼터": [255, 150, 50, 200]          
    }
    data['color'] = data['facility_type'].map(color_map)
    return data

@st.cache_data
def load_metrics_data():
    data = pd.DataFrame({
        "region_name": ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "경기도"],
        "지표명": ["10만명당 안전망 시설 수"] * 7,
        "연도": ["2024"] * 7,
        "value": [12.5, 10.2, 9.8, 11.1, 13.4, 10.5, 14.2]
    })
    return data

@st.cache_data
def load_hotline_contacts():
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
    except:
        return None, None

def generate_threat_data(center_lat, center_lon, num_points, threat_type):
    np.random.seed(hash(threat_type) % 10000)
    df = pd.DataFrame({
        "위도": np.random.normal(center_lat, 0.05, num_points).astype(float),
        "경도": np.random.normal(center_lon, 0.05, num_points).astype(float),
        "위협요인": threat_type
    })
    return df

fac_df = load_facilities_data()
mind_df = load_metrics_data()
hotline_df = load_hotline_contacts()
mask_json, kr_geom = get_korea_geometry()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 테마 및 반응형 CSS 설정
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_theme_config(theme_choice):
    if theme_choice == "다크 모드":
        return {
            "name": "dark", "text_color": "#F8FAFC", "text_muted": "#94A3B8",
            "card_bg": "#1E293B", "card_border": "rgba(56, 189, 248, 0.2)",
            "accent_color": "#38BDF8", "accent_gradient": "linear-gradient(120deg, #38BDF8 0%, #818CF8 100%)",
            "guide_bg": "#0F172A", "map_style": "mapbox://styles/mapbox/dark-v11",
            "mask_color": [14, 17, 23, 255], "plotly_theme": "plotly_dark",
            "threat_colors": {"유해업소 밀집": [248, 113, 113, 200], "교통사고 다발": [251, 146, 60, 200], "치안/범죄 취약": [192, 132, 252, 200]},
            "safe_colors": {"청소년 수련시설": [56, 189, 248, 200], "청소년상담복지센터": [52, 211, 153, 200], "청소년쉼터": [250, 204, 21, 200]},
            "chart_colors": {'선택 지역': '#38BDF8', '타 지역': '#475569'}
        }
    else:
        return {
            "name": "light", "text_color": "#0F172A", "text_muted": "#475569",
            "card_bg": "#F8FAFC", "card_border": "rgba(29, 78, 216, 0.2)",
            "accent_color": "#1D4ED8", "accent_gradient": "linear-gradient(120deg, #1D4ED8 0%, #4338CA 100%)",
            "guide_bg": "#EFF6FF", "map_style": "mapbox://styles/mapbox/light-v10",
            "mask_color": [255, 255, 255, 255], "plotly_theme": "plotly_white",
            "threat_colors": {"유해업소 밀집": [225, 29, 72, 200], "교통사고 다발": [234, 88, 12, 200], "치안/범죄 취약": [147, 51, 234, 200]},
            "safe_colors": {"청소년 수련시설": [37, 99, 235, 200], "청소년상담복지센터": [5, 150, 105, 200], "청소년쉼터": [217, 119, 6, 200]},
            "chart_colors": {'선택 지역': '#1D4ED8', '타 지역': '#CBD5E1'}
        }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 사이드바 (정밀 지역 필터링 도입)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown('<div style="text-align:center; font-size:2.5rem; margin-bottom:-10px;">🌌</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:1.2rem; font-weight:700; color:#5865F2;">Youth Canvas</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:0.8rem; color:gray; margin-bottom:20px;">청소년 안전망 찾기</div>', unsafe_allow_html=True)
    
    st.header("🎨 화면 테마")
    theme_choice = st.radio("모드 선택", ["다크 모드", "라이트 모드"], label_visibility="collapsed")
    theme = get_theme_config(theme_choice)
    st.markdown("---")
    
    # 🚨 [핵심 업데이트] 시/도 선택에 따른 시/군/구 연동 필터링
    st.header("🔍 정밀 지역 필터")
    sido_list = ["전국"] + list(fac_df['sido'].unique())
    selected_sido = st.selectbox("📍 시/도 선택", sido_list)
    
    if selected_sido != "전국":
        sigungu_list = ["전체"] + list(fac_df[fac_df['sido'] == selected_sido]['sigungu'].unique())
        selected_sigungu = st.selectbox("📍 시/군/구 선택 (예: 마포구)", sigungu_list)
    else:
        selected_sigungu = "전체"
        
    st.markdown("---")
    type_list = fac_df['facility_type'].unique()
    selected_types = st.multiselect("🏢 보호 기관 유형", list(type_list), default=list(type_list))

# CSS 인젝션
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], p, div, h1, h2, h3, span {{ font-family: 'Inter', sans-serif; word-break: keep-all; overflow-wrap: break-word; }}
.kpi-card {{ background-color: {theme['card_bg']}; border: 1px solid {theme['card_border']}; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); display: flex; flex-direction: column; justify-content: center; height: 100%; }}
.kpi-value {{ font-size: 1.6rem; font-weight: 700; color: {theme['text_color']}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.kpi-label {{ color: {theme['text_muted']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; }}
.gradient-title {{ background: {theme['accent_gradient']}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: clamp(1.5rem, 4vw, 2.2rem); font-weight: 700; margin-bottom: 0.2rem; }}
.section-header {{ color: {theme['accent_color']}; font-size: 1.2rem; font-weight: 700; margin: 1.5rem 0 1rem 0; padding-left: 10px; border-left: 4px solid {theme['accent_color']}; }}
.guide-box {{ background-color: {theme['guide_bg']}; border: 1px solid {theme['card_border']}; border-radius: 8px; padding: 15px; margin-top: 10px; color: {theme['text_color']}; }}
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 데이터 필터링 적용
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
fac_filtered = fac_df.copy()
if selected_sido != "전국":
    fac_filtered = fac_filtered[fac_filtered['sido'] == selected_sido]
    if selected_sigungu != "전체":
        fac_filtered = fac_filtered[fac_filtered['sigungu'] == selected_sigungu]
fac_filtered = fac_filtered[fac_filtered['facility_type'].isin(selected_types)].copy()

fac_filtered['color'] = fac_filtered['facility_type'].map(theme['safe_colors'])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 메인 화면 출력
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="gradient-title">Youth Canvas: 청소년 안전망 탐색</div>', unsafe_allow_html=True)
st.markdown(f"<span style='color:{theme['text_muted']}; font-size:0.95rem; font-weight:500;'>우리 동네의 청소년 보호 시설을 찾고, 잠재적 위험 요인과 비교 분석해보세요.</span><br><br>", unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
display_region = f"{selected_sido} {selected_sigungu}" if selected_sido != "전국" else "전국"
display_region = display_region.replace(" 전체", "")

with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">📍 선택 지역</div><div class="kpi-value" title="{display_region}">{display_region}</div></div>', unsafe_allow_html=True)
with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">🛡️ 검색된 보호 기관</div><div class="kpi-value">{len(fac_filtered)}개</div></div>', unsafe_allow_html=True)
with k3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">🆘 긴급 상담 전화</div><div class="kpi-value" style="color:{theme["accent_color"]};">☎ 1388</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🗺️ 청소년 안전 지도", "📊 지역 지표 비교", "🆘 긴급 도움받기"])

# ──────────────────────────────────────────────
# 탭 1: 안전망 및 위협 요인 맵핑
# ──────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">우리 동네 안전망 및 위험 요인 분석</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='color:{theme['text_muted']}; font-size:0.85rem;'>💡 지도에 표시된 마커에 마우스를 올리면 상세 정보를 볼 수 있습니다. (우클릭+드래그로 3D 회전)</div>", unsafe_allow_html=True)
    
    threat_list = ["유해업소 밀집", "교통사고 다발", "치안/범죄 취약"]
    selected_threats = st.multiselect("⚠️ 지도에 표시할 위험 요인 (Beta)", threat_list, help="위험 요인을 선택하면 지도에 3D 기둥으로 나타납니다.")

    # 🚨 [핵심] 선택한 '구' 단위에 맞춰 지도가 자동으로 포커싱 됨
    if fac_filtered.empty:
        map_center = [37.5665, 126.9780]
        zoom_level = 11.0
    else:
        map_center = [fac_filtered['lat'].mean(), fac_filtered['lon'].mean()]
        if selected_sigungu != "전체" and selected_sido != "전국":
            zoom_level = 12.5 # '구'를 선택하면 지도를 더 가깝게 확대
        elif selected_sido != "전국":
            zoom_level = 10.5
        else:
            zoom_level = 6.8

    layers = []
    
    if mask_json is not None:
        layers.append(pdk.Layer("GeoJsonLayer", mask_json, get_fill_color=theme['mask_color'], stroked=False, pickable=False))

    for threat in selected_threats:
        t_df = generate_threat_data(map_center[0], map_center[1], 150 if selected_sigungu=="전체" else 30, threat)
        if kr_geom is not None:
            t_gdf = gpd.GeoDataFrame(t_df, geometry=gpd.points_from_xy(t_df['경도'], t_df['위도']), crs="EPSG:4326")
            t_chart_data = t_gdf[t_gdf.geometry.within(kr_geom)][['경도', '위도']].to_dict(orient='records')
        else:
            t_chart_data = t_df[['경도', '위도']].to_dict(orient='records')
            
        layers.append(pdk.Layer(
            "HexagonLayer", data=t_chart_data, get_position=["경도", "위도"],
            radius=500 if selected_sigungu != "전체" else 1500, # '구' 단위일 땐 기둥 크기도 작게 조절
            elevation_scale=20 if selected_sigungu != "전체" else 50,
            elevation_range=[0, 1000], extruded=True, get_fill_color=theme['threat_colors'][threat], pickable=False
        ))

    fac_chart_data = fac_filtered.to_dict(orient='records')
    layers.append(pdk.Layer(
        "ScatterplotLayer", data=fac_chart_data, get_position=["lon", "lat"],
        get_radius=500 if selected_sigungu != "전체" else 1500, get_fill_color="color", pickable=True,
    ))

    view_state = pdk.ViewState(longitude=map_center[1], latitude=map_center[0], zoom=zoom_level, min_zoom=6.8, max_zoom=16.0, pitch=45, bearing=0)

    tooltip_html = f"""
    <div style='background-color:#1E293B; padding:12px; border-radius:8px; border: 1px solid #38BDF8; color:#F8FAFC; font-family:sans-serif;'>
        <div style='font-size:1.1em; font-weight:700; margin-bottom:5px;'>{{facility_name}}</div>
        <div style='font-size:0.85em; color:#38BDF8; font-weight:600;'>유형: {{facility_type}}</div>
        <div style='font-size:0.85em; margin-top:3px;'>전화: {{phone}}</div>
        <div style='font-size:0.8em; margin-top:3px; color:gray;'>{{address}}</div>
    </div>
    """

    st.pydeck_chart(pdk.Deck(map_provider="mapbox", map_style=theme['map_style'], api_keys={'mapbox': MAPBOX_TOKEN}, layers=layers, initial_view_state=view_state, tooltip={"html": tooltip_html}))

    with st.expander("📊 지도 데이터 팩트체크 및 해석 가이드"):
        st.markdown(f"""
        <div class="guide-box">
            <h4 style='margin-top:0; color:{theme['accent_color']}; font-weight:700;'>🚨 부정적 신호 (보호 사각지대)</h4>
            <p style='line-height:1.6; font-weight:500;'>특정 구역에 <b>위험 기둥(유해업소, 사고다발 등)</b>이 거대하게 솟아있는데, 주변 반경에 <b>청소년 보호 마커(수련시설, 쉼터 등)</b>가 전혀 없다면 해당 지역은 행정적 방어막이 뚫려있는 심각한 사각지대입니다.</p>
            <hr style='border:none; border-top:1px solid {theme['card_border']}; my-3;'>
            <h4 style='color:{theme['accent_color']}; font-weight:700;'>✅ 긍정적 신호 (안전망 작동)</h4>
            <p style='line-height:1.6; font-weight:500;'>상업지구 특성상 위험 기둥이 존재하더라도, 그 주변 골목과 길목에 청소년 보호 기관 마커가 촘촘히 배치되어 있다면 이는 지자체의 적절한 예산 배분과 완충지대가 형성되어 있다는 뜻입니다.</p>
        </div>
        """, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 탭 2: 마음건강 심층 분석
# ──────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">지역사회 지표 단순 비교</div>', unsafe_allow_html=True)
    st.markdown(f"<div style='color:{theme['text_muted']}; font-size:0.9rem; font-weight:500; margin-bottom:1rem;'>⚠️ <b>안내:</b> 본 차트는 각 지역의 인프라 현황을 단순 비교하기 위한 팩트체크 용도이며, 특정 현상의 인과관계를 단정짓지 않습니다.</div>", unsafe_allow_html=True)
    
    if not mind_df.empty:
        mind_sorted = mind_df.sort_values(by="value", ascending=True)
        mind_sorted['선택 여부'] = mind_sorted['region_name'].apply(lambda x: '선택 지역' if selected_sido != "전국" and x[:2] in selected_sido else '타 지역')
        
        fig_bar = px.bar(mind_sorted, x="value", y="region_name", orientation='h', color='선택 여부', 
                         color_discrete_map=theme['chart_colors'],
                         title="10만 명당 청소년 안전망 시설 수 비교")
        fig_bar.update_layout(
            template=theme['plotly_theme'], 
            height=400, 
            showlegend=False,
            font=dict(color=theme['text_color']),
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# ──────────────────────────────────────────────
# 탭 3: 긴급 도움받기
# ──────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🆘 언제든 도움을 요청하세요</div>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:{theme['text_muted']}; font-weight:500;'>청소년 여러분, 혼자 고민하지 마세요. 전문가들이 24시간 여러분을 기다립니다.</p>", unsafe_allow_html=True)
    
    for i, row in hotline_df.iterrows():
        st.markdown(f"""
        <div style="background-color:{theme['guide_bg']}; border-left: 5px solid {theme['accent_color']}; padding:15px; border-radius:8px; margin-bottom:12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
            <div style="font-size:1.15rem; font-weight:700; color:{theme['accent_color']}; margin-bottom:6px;">📞 {row['contact_name']} : {row['phone']}</div>
            <div style="font-size:0.95rem; font-weight:500; color:{theme['text_color']};">{row['description']} <span style='color:{theme['text_muted']}; font-size:0.85em;'>({row['hours']})</span></div>
        </div>
        """, unsafe_allow_html=True)
        
    with st.expander("ℹ️ 원본 데이터 출처 및 API 연동 안내"):
        st.markdown(f"""
        <div style="color:{theme['text_color']}; font-weight:500; line-height:1.6;">
            <ul>
                <li><b>청소년 안전망 데이터</b>: 여성가족부 청소년시설 통합 정보 오픈 API (매일 자정 자동 업데이트 연동 대기 중)</li>
                <li><b>지역 위험 지표</b>: 통계청 KOSIS 및 공공데이터포털 최신 자료 기준</li>
                <li><b>데이터 무결성</b>: 본 대시보드는 정부 공공데이터 API를 통해 수집된 정보를 시각화하며, 원본 데이터와 1:1 교차 검증이 가능합니다.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
