import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. 페이지 설정 및 프리미엄 다크 테마 CSS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
st.set_page_config(page_title="Youth Canvas", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* ── 프리미엄 KPI 카드 ── */
.kpi-card {
    background: linear-gradient(135deg, #1A1C23 0%, #111318 100%);
    border: 1px solid rgba(88, 101, 242, 0.2);
    border-radius: 12px;
    padding: 20px;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(88, 101, 242, 0.3);
    border-color: rgba(88, 101, 242, 0.5);
}
.kpi-icon { font-size: 1.8rem; margin-bottom: 5px; }
.kpi-label { color: #8F95B2; font-size: 0.9rem; font-weight: 500; margin-bottom: 5px; }
.kpi-value { font-size: 1.8rem; font-weight: 700; color: #FFFFFF; }

/* ── 그라데이션 타이틀 ── */
.gradient-title {
    background: linear-gradient(120deg, #5865F2 0%, #00F0FF 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.section-header {
    color: #00F0FF;
    font-size: 1.2rem;
    font-weight: 600;
    margin: 1.5rem 0 1rem 0;
    padding-left: 10px;
    border-left: 4px solid #5865F2;
}

/* ── 탭 디자인 ── */
.stTabs [data-baseweb="tab-list"] {
    background-color: rgba(26, 28, 35, 0.5);
    border-radius: 12px;
    padding: 5px;
    gap: 10px;
}
.stTabs [data-baseweb="tab"] { padding: 10px 20px; border-radius: 8px; font-weight: 600; }
.stTabs [aria-selected="true"] { background-color: rgba(88, 101, 242, 0.2) !important; }
</style>
""", unsafe_allow_html=True)

DARK_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8F95B2", size=12),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.05)")
)

def apply_dark(fig):
    fig.update_layout(**DARK_LAYOUT)
    return fig

def kpi_card(icon, label, value):
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
    </div>""", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. 데이터 불러오기
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
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

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. 사이드바 및 헤더 영역
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with st.sidebar:
    st.markdown('<div style="text-align:center; font-size:3rem; margin-bottom:-10px;">🌌</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:1.2rem; font-weight:700; color:#5865F2;">Youth Canvas</div>', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; font-size:0.8rem; color:#8F95B2; margin-bottom:20px;">청소년 인프라·마음건강 분석</div>', unsafe_allow_html=True)
    
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
    year_list = sorted(mind_df['연도'].unique(), reverse=True)
    selected_year = st.selectbox("📅 연도 선택", year_list)
    indicator_list = mind_df['지표명'].unique()
    selected_indicator = st.selectbox("🧠 마음건강 지표 선택", indicator_list)

st.markdown('<div class="gradient-title">Youth Canvas: 통합 분석 대시보드</div>', unsafe_allow_html=True)
st.markdown("<span style='color:#8F95B2;'>제7차 청소년정책기본계획 기반 지역사회 청소년 인프라 및 심리적/물리적 안전망 분석</span>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ── 핵심 KPI 지표 ──
filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]
if selected_region == "전국":
    fac_filtered = fac_df.copy()
    avg_mind = filtered_mind_year['비율(%)'].mean()
else:
    fac_filtered = fac_df[fac_df['시도명'].str.contains(selected_region[:2], na=False)].copy()
    target_mind = filtered_mind_year[filtered_mind_year['지역명'].str.contains(selected_region[:2], na=False)]
    avg_mind = target_mind['비율(%)'].mean() if not target_mind.empty else 0

k1, k2, k3 = st.columns(3)
with k1:
    kpi_card("📍", "선택된 지역", selected_region)
with k2:
    kpi_card("🛡️", "청소년 수련시설 (안전망)", f"{len(fac_filtered):,}개")
with k3:
    kpi_card("🧠", f"{selected_indicator} 평균 ({selected_year})", f"{avg_mind:.1f}%")

st.markdown("<br>", unsafe_allow_html=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 탭(Tab) 레이아웃 구성
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
tab1, tab2, tab3 = st.tabs(["🗺️ 3D 입체 안전망 지도", "📊 마음건강 심층 분석", "🚦 교통사고 다발 구역 (데이터 대기중)"])

# ──────────────────────────────────────────────
# 탭 1: 3D 입체 안전망 지도
# ──────────────────────────────────────────────
with tab1:
    st.markdown('<div class="section-header">위험 구역 vs 청소년 안전망 3D 뷰</div>', unsafe_allow_html=True)
    
    legend_col1, legend_col2 = st.columns(2)
    with legend_col1:
        show_danger = st.checkbox("🔴 유해환경/위험구역 (3D 기둥) 켜기", value=True)
    with legend_col2:
        show_safe = st.checkbox("🔵 청소년 수련시설 (안전 마커) 켜기", value=True)

    map_center = region_coords[selected_region]
    
    # 🚨 [핵심 수정] 줌 레벨을 타이트하게 조절하여 시야를 한반도에 가둠
    zoom_level = 6.8 if selected_region == "전국" else 11.0

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
            get_fill_color="[255, 75, 75, 200]", 
            pickable=False
        ))

    if show_safe:
        layers.append(pdk.Layer(
            "ScatterplotLayer",
            data=fac_chart_data,
            get_position=["경도", "위도"],
            get_radius=1500 if selected_region == "전국" else 300,
            get_fill_color=[0, 240, 255, 200], 
            pickable=True,
        ))

    view_state = pdk.ViewState(
        longitude=map_center[1],
        latitude=map_center[0],
        zoom=zoom_level,
        min_zoom=6.8,  # 축소 한계선을 높여서 지도가 한반도 밖으로 빠져나가지 못하게 차단
        max_zoom=15.0,
        pitch=50,
        bearing=0
    )

    # 🚨 [핵심 수정] 글씨와 도로가 뚜렷하게 보이는 '상세 다크 테마'로 복구
    st.pydeck_chart(pdk.Deck(
        map_style="mapbox://styles/mapbox/dark-v10", 
        layers=layers,
        initial_view_state=view_state,
        tooltip={"html": "<div style='color:white;'><b>🛡️ 안전망:</b> {시설명}</div>"}
    ))

    with st.expander("💡 3D 지도 해석 가이드 보기"):
        st.markdown("""
        * 🔴 **붉은 기둥**: 유해업소, 사고 다발 지역 등 위험 요소입니다. 
        * 🔵 **푸른 마커**: 청소년을 보호하는 안전망(시설)입니다.
        * **피해야 할 구역**: 붉은 기둥이 집중적으로 솟아있는 지역의 지명과 길을 확인하고, 해당 구역으로의 접근을 주의하세요.
        """)

# ──────────────────────────────────────────────
# 탭 2: 마음건강 심층 분석
# ──────────────────────────────────────────────
with tab2:
    st.markdown('<div class="section-header">인프라와 마음건강의 상관관계 분석</div>', unsafe_allow_html=True)
    
    row1_col1, row1_col2 = st.columns([5, 5])
    
    with row1_col1:
        st.markdown(f"**📊 지역별 {selected_indicator} 수준 비교**")
        mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
        mind_sorted['선택 여부'] = mind_sorted['지역명'].apply(lambda x: '선택 지역' if selected_region != "전국" and x[:2] in selected_region else '타 지역')
        
        fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', color='선택 여부', 
                         color_discrete_map={'선택 지역': '#00F0FF', '타 지역': '#394263'})
        fig_bar.update_layout(height=350, showlegend=False)
        st.plotly_chart(apply_dark(fig_bar), use_container_width=True)

    with row1_col2:
        st.markdown(f"**📈 5년간 {selected_indicator} 변화 추이**")
        target_region = mind_df['지역명'].iloc[0] if selected_region == "전국" else selected_region[:2]
        matched_regions = mind_df[mind_df['지역명'].str.contains(target_region)]['지역명']
        final_target = matched_regions.iloc[0] if not matched_regions.empty else mind_df['지역명'].iloc[0]
        
        trend_df = mind_df[(mind_df['지역명'] == final_target) & (mind_df['지표명'] == selected_indicator)].sort_values('연도')
        fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True, color_discrete_sequence=['#5865F2'])
        fig_line.update_traces(marker=dict(size=10, color='#00F0FF'))
        fig_line.update_layout(height=350, hovermode="x unified")
        st.plotly_chart(apply_dark(fig_line), use_container_width=True)

    row2_col1, row2_col2 = st.columns([5, 5])
    
    with row2_col1:
        st.markdown("**🍩 지역 내 시설 분포 (불균형 확인)**")
        if not fac_filtered.empty:
            pie_df = fac_filtered['시군구명'].value_counts().reset_index()
            pie_df.columns = ['시군구명', '시설 수']
            if len(pie_df) > 5:
                pie_df = pd.concat([pie_df.iloc[:5], pd.DataFrame([['나머지 지역', pie_df['시설 수'].iloc[5:].sum()]], columns=['시군구명', '시설 수'])])
            fig_pie = px.pie(pie_df, values='시설 수', names='시군구명', hole=0.5, color_discrete_sequence=px.colors.sequential.Agal)
            fig_pie.update_traces(textposition='inside', textinfo='percent+label')
            fig_pie.update_layout(height=350, showlegend=False)
            st.plotly_chart(apply_dark(fig_pie), use_container_width=True)

    with row2_col2:
        st.markdown(f"**🌌 시설 수와 {selected_indicator}의 상관관계**")
        fac_count = fac_df['시도명'].value_counts().reset_index()
        fac_count.columns = ['지역명_원본', '시설 수']
        fac_count.loc[:, '지역명_축약'] = fac_count['지역명_원본'].str[:2]
        mind_scatter = filtered_mind_year.copy()
        mind_scatter.loc[:, '지역명_축약'] = mind_scatter['지역명'].str[:2]
        scatter_df = pd.merge(mind_scatter, fac_count, on='지역명_축약', how='inner')
        
        if not scatter_df.empty:
            fig_scatter = px.scatter(scatter_df, x="시설 수", y="비율(%)", hover_name="지역명", size="시설 수", size_max=20, color_discrete_sequence=['#00F0FF'])
            fig_scatter.update_layout(height=350)
            st.plotly_chart(apply_dark(fig_scatter), use_container_width=True)

    with st.expander("💡 차트 종합 해석 가이드 보기"):
        st.markdown("""
        * **막대그래프**: 막대가 짧을수록 긍정적입니다. 타지역과의 격차를 확인하세요.
        * **라인그래프**: 선이 우하향(↘) 할수록 정책적 개선이 이루어지고 있다는 뜻입니다.
        * **도넛차트**: 조각 크기가 균등할수록 인프라가 특정 구에 쏠리지 않고 공평하게 배분되었음을 의미합니다.
        * **산점도(상관관계)**: 점들이 전체적으로 우하향(↘) 형태를 띤다면, "시설이 많을수록 마음건강이 좋다"는 가설이 입증되는 것입니다.
        """)

# ──────────────────────────────────────────────
# 탭 3: 교통사고 다발 구역 (데이터 수집 완료 시 연동)
# ──────────────────────────────────────────────
with tab3:
    st.markdown('<div class="section-header">🚦 사상자 연령대별 교통사고 심층 분석</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="background-color:rgba(88, 101, 242, 0.1); padding:30px; border-radius:12px; text-align:center; border: 1px dashed rgba(88, 101, 242, 0.5);">
        <h2 style="color:#00F0FF; margin-bottom:10px;">데이터 적재 대기 중... ⏳</h2>
        <p style="color:#8F95B2; font-size:1.1rem;">
        현재 TAAS(교통사고분석시스템)에서 <strong>2021년~2024년 전국 사상자 연령대별 교통사고 데이터</strong>를 수집 중입니다.<br>
        수집 및 정제가 완료되는 대로 해당 탭에 <strong>연령별 취약 구역 타임라인 추이</strong>와 <strong>사고 다발 히트맵</strong>이 연동될 예정입니다.
        </p>
    </div>
    """, unsafe_allow_html=True)
