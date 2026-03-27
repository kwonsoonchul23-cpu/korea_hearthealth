import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import numpy as np
import geopandas as gpd
from shapely.geometry import box
import json
import requests
import streamlit.components.v1 as components # 네이버 지도 렌더링을 위한 컴포넌트

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 페이지 기본 설정 및 환경 변수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Youth Canvas: 청소년 안전망 찾기", layout="wide", initial_sidebar_state="expanded")

MAPBOX_TOKEN = st.secrets.get("MAPBOX_TOKEN", "")
PUBLIC_DATA_API_KEY = st.secrets.get("PUBLIC_DATA_API_KEY", "")
# 🚨 [추가] 네이버 클라우드 플랫폼에서 발급받은 Maps Client ID를 secrets에 넣어주세요.
NAVER_CLIENT_ID = st.secrets.get("NAVER_CLIENT_ID", "") 

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 데이터 로더 및 검색 엔진 함수
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@st.cache_data(ttl=86400) 
def load_facilities_data():
    sido_sigungu_map = {
        "서울특별시": {"강남구": (37.517, 127.047), "마포구": (37.566, 126.901), "서초구": (37.483, 127.032)},
        "경기도": {"수원시": (37.263, 127.028), "고양시 일산동구": (37.658, 126.766), "성남시": (37.420, 127.126)},
        "부산광역시": {"해운대구": (35.163, 129.163)}
    }
    types = ["청소년 수련시설", "청소년상담복지센터", "청소년쉼터"]
    records = []
    np.random.seed(42)
    for sido, sigungu_dict in sido_sigungu_map.items():
        for sigungu, (lat, lon) in sigungu_dict.items():
            for i in range(np.random.randint(5, 12)):
                fac_type = np.random.choice(types, p=[0.5, 0.3, 0.2])
                records.append({
                    "title": f"{sido} {sigungu} {fac_type} {i+1}호",
                    "category": fac_type,
                    "sido": sido, "sigungu": sigungu,
                    "lat": lat + np.random.uniform(-0.04, 0.04), 
                    "lon": lon + np.random.uniform(-0.04, 0.04),
                    "interp": "✅ [긍정] 청소년이 안전하게 머물며 보호받을 수 있는 지역 인프라입니다.",
                    "detail": f"전화: 02-{np.random.randint(1000,9999)}-{np.random.randint(1000,9999)}"
                })
    data = pd.DataFrame(records)
    color_map = {"청소년 수련시설": [50, 150, 255, 200], "청소년상담복지센터": [50, 255, 150, 200], "청소년쉼터": [255, 150, 50, 200]}
    data['color'] = data['category'].map(color_map)
    return data

@st.cache_data(ttl=86400)
def generate_threat_data(center_lat, center_lon, num_points, threat_type):
    np.random.seed(hash(threat_type) % 10000)
    df = pd.DataFrame({
        "title": f"{threat_type} 지점",
        "category": threat_type,
        "lat": np.random.normal(center_lat, 0.05, num_points).astype(float),
        "lon": np.random.normal(center_lon, 0.05, num_points).astype(float),
        "interp": "🚨 [부정] 청소년의 안전과 건강을 위협할 수 있는 취약 구역으로 주의가 필요합니다.",
        "detail": "해당 반경 내 보행 주의 및 경찰/지자체의 관리 요망"
    })
    return df

@st.cache_data
def load_survey_metrics_data():
    return pd.DataFrame({
        "region_name": ["서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시", "대전광역시", "경기도"],
        "지표명": ["스트레스 인지율(%)"] * 7,
        "value": [38.5, 34.2, 35.8, 36.1, 33.4, 32.5, 39.2],
        "interp": ["🚨 [부정] 수치가 높을수록 해당 지역 청소년의 정신적 압박감이 심각함을 의미합니다."] * 7
    })

@st.cache_data
def load_hotline_contacts():
    return pd.DataFrame({
        "contact_name": ["청소년전화 1388", "자살예방상담전화", "여성긴급전화 1366", "안전드림(학교폭력)"],
        "phone": ["1388", "109", "1366", "117"],
        "description": ["365일 24시간 청소년 고민 상담", "우울감 등 말하기 어려운 고민이 있을 때", "가정폭력, 성폭력 등 긴급 상담", "학교폭력, 소년범죄 신고 및 상담"],
        "hours": ["24시간", "24시간", "24시간", "24시간"]
    })

@st.cache_resource
def get_precise_geometry(sido_name, sigungu_name):
    try:
        if sigungu_name != "전체" and sido_name != "전국":
            url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_municipalities_geo_simple.json"
            gdf = gpd.read_file(url)
            target_geom = gdf[gdf['name'] == sigungu_name].geometry.unary_union
        else:
            url = "https://raw.githubusercontent.com/southkorea/southkorea-maps/master/kostat/2018/json/skorea_provinces_geo_simple.json"
            gdf = gpd.read_file(url)
            target_geom = gdf.geometry.unary_union if sido_name == "전국" else gdf[gdf['name'] == sido_name].geometry.unary_union

        if target_geom.is_empty: return None, None
        world_box = box(-180, -90, 180, 90)
        mask_geom = world_box.difference(target_geom)
        mask_gdf = gpd.GeoDataFrame(geometry=[mask_geom], crs="EPSG:4326")
        return json.loads(mask_gdf.to_json()), target_geom
    except:
        return None, None

# 🚨 [핵심 업데이트] 진짜 주소를 위도/경도로 바꿔주는 지오코딩 엔진 (일산 검색 해결)
@st.cache_data
def get_lat_lon_from_query(query):
    # 1차: 자주 찾는 주요 지역 직접 매핑 (MVP 속도 향상)
    known_places = {"일산": (37.658, 126.766), "분당": (37.382, 127.118), "홍대": (37.556, 126.923), "강남역": (37.498, 127.027)}
    for place, coords in known_places.items():
        if place in query: return coords
        
    # 2차: 오픈스트리트맵(OSM) API를 통한 실제 주소 검색
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={query}&format=json"
        headers = {'User-Agent': 'YouthCanvasApp/1.0'}
        res = requests.get(url, headers=headers).json()
        if res: return float(res[0]['lat']), float(res[0]['lon'])
    except: pass
    return None, None

fac_df = load_facilities_data()
survey_df = load_survey_metrics_data()
hotline_df = load_hotline_contacts()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 테마 및 반응형 CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def get_theme_config(theme_choice):
    if theme_choice == "다크 모드":
        return {
            "name": "dark", "text_color": "#F8FAFC", "text_muted": "#94A3B8",
            "card_bg": "#1E293B", "card_border": "rgba(56, 189, 248, 0.2)",
            "accent_color": "#38BDF8", "accent_gradient": "linear-gradient(120deg, #38BDF8 0%, #818CF8 100%)",
            "guide_bg": "#0F172A", "map_style": "mapbox://styles/mapbox/dark-v11",
            "mask_color": [14, 17, 23, 255], "plotly_theme": "plotly_dark",
            "threat_colors": {"단란/유흥업소 등 유해환경": [248, 113, 113, 200], "보행/교통사고 다발 구역": [251, 146, 60, 200], "어두운 골목 등 치안 취약지": [192, 132, 252, 200]},
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
            "threat_colors": {"단란/유흥업소 등 유해환경": [225, 29, 72, 200], "보행/교통사고 다발 구역": [234, 88, 12, 200], "어두운 골목 등 치안 취약지": [147, 51, 234, 200]},
            "safe_colors": {"청소년 수련시설": [37, 99, 235, 200], "청소년상담복지센터": [5, 150, 105, 200], "청소년쉼터": [217, 119, 6, 200]},
            "chart_colors": {'선택 지역': '#1D4ED8', '타 지역': '#CBD5E1'}
        }

with st.sidebar:
    st.markdown('<div style="text-align:center; font-size:2.5rem; margin-bottom:-10px;">🌌</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:1.2rem; font-weight:700; color:#5865F2;">Youth Canvas</div>', unsafe_allow_html=True)
    
    st.header("🎨 화면 테마")
    theme_choice = st.radio("모드 선택", ["다크 모드", "라이트 모드"], label_visibility="collapsed")
    theme = get_theme_config(theme_choice)
    st.markdown("---")
    
    st.header("🔍 정밀 지역 필터")
    sido_list = ["전국"] + list(fac_df['sido'].unique())
    selected_sido = st.selectbox("📍 시/도 선택", sido_list)
    if selected_sido != "전국":
        sigungu_list = ["전체"] + list(fac_df[fac_df['sido'] == selected_sido]['sigungu'].unique())
        selected_sigungu = st.selectbox("📍 시/군/구 선택", sigungu_list)
    else:
        selected_sigungu = "전체"
    
    st.markdown("---")
    st.header("🎯 내 위치/관심지역 검색")
    custom_address = st.text_input("상세 주소 (예: 일산, 강남역)", placeholder="검색 시 해당 위치로 줌인 됩니다.")
    search_radius = st.slider("검색 반경 (km)", min_value=1, max_value=10, value=3)
        
    st.markdown("---")
    type_list = fac_df['category'].unique()
    selected_types = st.multiselect("🏢 보호 기관 (안전망) 표시", list(type_list), default=list(type_list))

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
html, body, [class*="css"], p, div, h1, h2, h3, span {{ font-family: 'Inter', sans-serif; word-break: keep-all; overflow-wrap: break-word; }}
.kpi-card {{ background-color: {theme['card_bg']}; border: 1px solid {theme['card_border']}; border-radius: 12px; padding: 15px; text-align: center; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); display: flex; flex-direction: column; justify-content: center; height: 100%; }}
.kpi-value {{ font-size: 1.6rem; font-weight: 700; color: {theme['text_color']}; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.kpi-label {{ color: {theme['text_muted']}; font-size: 0.85rem; font-weight: 600; margin-bottom: 5px; }}
.gradient-title {{ background: {theme['accent_gradient']}; -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: clamp(1.5rem, 4vw, 2.2rem); font-weight: 700; margin-bottom: 0.2rem; }}
.section-header {{ color: {theme['accent_color']}; font-size: 1.2rem; font-weight: 700; margin: 1.5rem 0 1rem 0; padding-left: 10px; border-left: 4px solid {theme['accent_color']}; }}
</style>
""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 데이터 필터링 적용 및 지오코딩 검색
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
mask_json, target_geom = get_precise_geometry(selected_sido, selected_sigungu)
fac_filtered = fac_df.copy()

# 1차 필터링 (행정구역)
if selected_sido != "전국":
    fac_filtered = fac_filtered[fac_filtered['sido'] == selected_sido]
    if selected_sigungu != "전체":
        fac_filtered = fac_filtered[fac_filtered['sigungu'] == selected_sigungu]

# 2차 필터링 (주소 검색 시)
map_center = [37.5665, 126.9780] # 기본값 (서울시청)
zoom_level = 11.0

if custom_address:
    search_lat, search_lon = get_lat_lon_from_query(custom_address)
    if search_lat and search_lon:
        map_center = [search_lat, search_lon]
        zoom_level = 14.5 # 상세 위치 검색 시 깊게 줌인
        radius_deg = search_radius * 0.009
        fac_filtered = fac_df[ # 전체 데이터에서 검색 반경으로 다시 필터링
            (fac_df['lat'] >= search_lat - radius_deg) & (fac_df['lat'] <= search_lat + radius_deg) &
            (fac_df['lon'] >= search_lon - radius_deg) & (fac_df['lon'] <= search_lon + radius_deg)
        ]
    else:
        st.sidebar.warning("입력하신 위치를 찾을 수 없어 기본 지도로 표시합니다.")
elif not fac_filtered.empty:
    map_center = [fac_filtered['lat'].mean(), fac_filtered['lon'].mean()]
    if selected_sigungu != "전체": zoom_level = 13.0
    elif selected_sido != "전국": zoom_level = 10.5
    else: zoom_level = 6.8

fac_filtered = fac_filtered[fac_filtered['category'].isin(selected_types)].copy()
fac_filtered['color'] = fac_filtered['category'].map(theme['safe_colors'])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. 메인 화면 
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.markdown('<div class="gradient-title">Youth Canvas: 청소년 안전망 탐색</div>', unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
display_region = custom_address if custom_address else (f"{selected_sido} {selected_sigungu}".replace(" 전체", "") if selected_sido != "전국" else "전국")

with k1: st.markdown(f'<div class="kpi-card"><div class="kpi-label">📍 선택/검색 지역</div><div class="kpi-value" title="{display_region}">{display_region}</div></div>', unsafe_allow_html=True)
with k2: st.markdown(f'<div class="kpi-card"><div class="kpi-label">🛡️ 반경 내 보호 인프라</div><div class="kpi-value">{len(fac_filtered)}개</div></div>', unsafe_allow_html=True)
with k3: st.markdown(f'<div class="kpi-card"><div class="kpi-label">🆘 긴급 상담 전화</div><div class="kpi-value" style="color:{theme["accent_color"]};">☎ 1388</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 🚨 [핵심 업데이트] 탭 구성을 2D/3D 지도 중심으로 개편
tab1, tab2, tab3 = st.tabs(["🗺️ 집중 분석 지도 (3D & 2D)", "📊 지역 통계 및 실태 비교", "🆘 긴급 도움받기"])

# ──────────────────────────────────────────────
# 탭 1: 3D 거시 분석 맵 vs 2D 네이버 상세 맵 (Sub-tabs)
# ──────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">선택 구역 집중 분석 (Spotlight)</div>', unsafe_allow_html=True)
    
    threat_list = ["단란/유흥업소 등 유해환경", "보행/교통사고 다발 구역", "어두운 골목 등 치안 취약지"]
    selected_threats = st.multiselect("⚠️ 지도에 겹쳐볼 위험 요인 (다중 선택 가능)", threat_list, help="위협 요인을 선택하면 지도 위에 겹쳐서 표시됩니다.")

    # 지도 형태를 고를 수 있는 이중 탭 구성
    sub_tab1, sub_tab2 = st.tabs(["🌐 3D 거시적 입체 분석 (추천)", "📍 2D 네이버 상세 지도 (골목/지번 확인용)"])
    
    with sub_tab1:
        st.markdown(f"<div style='color:{theme['text_muted']}; font-size:0.85rem; margin-bottom:10px;'>💡 <b>사용법:</b> 마커에 마우스를 올리면 <b>긍정/부정 해석 정보</b>가 나타납니다. 다른 지역은 암막 처리되어 현재 지역에만 집중할 수 있습니다.</div>", unsafe_allow_html=True)
        layers = []
        if mask_json is not None:
            layers.append(pdk.Layer("GeoJsonLayer", mask_json, get_fill_color=theme['mask_color'], stroked=True, get_line_color=theme['accent_color'].replace('#', '').replace(theme['accent_color'], '[56, 189, 248, 255]'), line_width_min_pixels=2, pickable=False))

        for threat in selected_threats:
            t_df = generate_threat_data(map_center[0], map_center[1], 150 if selected_sigungu=="전체" else 30, threat)
            t_df['color'] = [theme['threat_colors'][threat]] * len(t_df)
            if target_geom is not None:
                t_gdf = gpd.GeoDataFrame(t_df, geometry=gpd.points_from_xy(t_df['경도'], t_df['위도']), crs="EPSG:4326")
                t_chart_data = t_gdf[t_gdf.geometry.within(target_geom)].to_dict(orient='records')
            else:
                t_chart_data = t_df.to_dict(orient='records')
            layers.append(pdk.Layer("ScatterplotLayer", data=t_chart_data, get_position=["lon", "lat"], get_radius=800 if selected_sigungu != "전체" else 2000, get_fill_color="color", pickable=True, opacity=0.7))

        fac_chart_data = fac_filtered.to_dict(orient='records')
        layers.append(pdk.Layer("ScatterplotLayer", data=fac_chart_data, get_position=["lon", "lat"], get_radius=300 if selected_sigungu != "전체" else 1000, get_fill_color="color", pickable=True))

        view_state = pdk.ViewState(longitude=map_center[1], latitude=map_center[0], zoom=zoom_level, min_zoom=6.8, max_zoom=18.0, pitch=40, bearing=0)
        
        tooltip_html = f"<div style='background-color:{theme['card_bg']}; padding:12px; border-radius:8px; border: 1px solid {theme['card_border']}; color:{theme['text_color']}; max-width: 250px; box-shadow: 0 4px 6px rgba(0,0,0,0.3);'><div style='font-size:1.1em; font-weight:700; margin-bottom:5px;'>{{title}}</div><div style='font-size:0.85em; color:{theme['accent_color']}; font-weight:600; margin-bottom:8px;'>분류: {{category}}</div><div style='font-size:0.85em; font-weight:500; line-height:1.4; margin-bottom:5px;'>{{interp}}</div><div style='font-size:0.8em; color:{theme['text_muted']}; border-top: 1px solid {theme['card_border']}; padding-top: 5px;'>{{detail}}</div></div>"
        st.pydeck_chart(pdk.Deck(map_provider="mapbox", map_style=theme['map_style'], api_keys={'mapbox': MAPBOX_TOKEN}, layers=layers, initial_view_state=view_state, tooltip={"html": tooltip_html}))

    with sub_tab2:
        # 🚨 [네이버 지도 2D 연동 구역] HTML 및 Javascript 인젝션
        st.markdown(f"<div style='color:{theme['text_muted']}; font-size:0.85rem; margin-bottom:10px;'>💡 <b>안내:</b> 네이버 지도는 정확한 골목길과 지번을 확인하기 위한 2D 전용 지도입니다. (네이버 API 키가 연동되어야 정상 작동합니다.)</div>", unsafe_allow_html=True)
        
        if NAVER_CLIENT_ID:
            # 안전망 데이터 마커 생성 자바스크립트 준비
            markers_js = ""
            for i, row in fac_filtered.iterrows():
                markers_js += f"""
                new naver.maps.Marker({{
                    position: new naver.maps.LatLng({row['lat']}, {row['lon']}),
                    map: map,
                    title: '{row['title']}'
                }});
                """
            
            naver_map_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0, user-scalable=no">
                <script type="text/javascript" src="https://oapi.map.naver.com/openapi/v3/maps.js?ncpClientId={NAVER_CLIENT_ID}"></script>
            </head>
            <body>
                <div id="map" style="width:100%;height:500px; border-radius:12px;"></div>
                <script>
                    var mapOptions = {{
                        center: new naver.maps.LatLng({map_center[0]}, {map_center[1]}),
                        zoom: {int(zoom_level) + 1}
                    }};
                    var map = new naver.maps.Map('map', mapOptions);
                    
                    // 마커 생성 루프
                    {markers_js}
                </script>
            </body>
            </html>
            """
            components.html(naver_map_html, height=520)
        else:
            st.warning("⚠️ 네이버 클라우드 플랫폼에서 발급받은 **NAVER_CLIENT_ID**를 Streamlit Secrets에 등록해야 지도가 나타납니다.")
            st.code("NAVER_CLIENT_ID = '발급받은_네이버_클라이언트_아이디'", language="toml")

# ──────────────────────────────────────────────
# 탭 2: 데이터 및 실태조사 차트
# ──────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">지역 청소년 실태조사 및 인프라 비교</div>', unsafe_allow_html=True)
    
    if not survey_df.empty:
        mind_sorted = survey_df.sort_values(by="value", ascending=True)
        mind_sorted['선택 여부'] = mind_sorted['region_name'].apply(lambda x: '선택 지역' if selected_sido != "전국" and x[:2] in selected_sido else '타 지역')
        
        fig_bar = px.bar(mind_sorted, x="value", y="region_name", orientation='h', color='선택 여부', 
                         color_discrete_map=theme['chart_colors'], title="지역별 스트레스 인지율(%) 비교", custom_data=['interp'])
        
        fig_bar.update_traces(hovertemplate="<b>%{y}</b><br>스트레스 인지율: %{x}%<br><br>💡 <b>데이터 해석:</b><br>%{customdata[0]}<extra></extra>")
        fig_bar.update_layout(template=theme['plotly_theme'], height=400, showlegend=False, font=dict(color=theme['text_color']), plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig_bar, use_container_width=True)

# ──────────────────────────────────────────────
# 탭 3: 긴급 도움받기
# ──────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🆘 언제든 도움을 요청하세요</div>', unsafe_allow_html=True)
    for i, row in hotline_df.iterrows():
        st.markdown(f"""
        <div style="background-color:rgba(88, 101, 242, 0.05); border-left: 5px solid {theme['accent_color']}; padding:15px; border-radius:8px; margin-bottom:12px;">
            <div style="font-size:1.15rem; font-weight:700; color:{theme['accent_color']}; margin-bottom:6px;">📞 {row['contact_name']} : {row['phone']}</div>
            <div style="font-size:0.95rem; font-weight:500; color:{theme['text_color']};">{row['description']} <span style='color:{theme['text_muted']}; font-size:0.85em;'>({row['hours']})</span></div>
        </div>
        """, unsafe_allow_html=True)
    
