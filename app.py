import streamlit as st
import pandas as pd
import folium
from folium.plugins import MarkerCluster
import streamlit.components.v1 as components
import plotly.express as px

# 1. 페이지 및 미니멀 스타일 설정
st.set_page_config(page_title="Youth Canvas", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.main {background-color: #f8f9fa;}
h1, h2, h3 {color: #2c3e50;}
</style>
""", unsafe_allow_html=True)

st.title("💡 Youth Canvas: 청소년 안전·마음건강 대시보드")
st.markdown("**제7차 청소년정책기본계획** 기반 지역사회 청소년 인프라 및 마음건강 분석 프로젝트")
st.markdown("---")

# 2. 데이터 불러오기 및 에러 방지 (Arrow 버그 해결)
@st.cache_data
def load_data():
    fac_df = pd.read_csv("clean_facility.csv")
    mind_df = pd.read_csv("clean_mind_health.csv")
    
    # 텍스트 데이터를 명확히 문자열로 변환하여 LargeUtf8 에러 원천 차단
    mind_df['지역명'] = mind_df['지역명'].astype(str)
    mind_df['지표명'] = mind_df['지표명'].astype(str)
    mind_df['연도'] = mind_df['연도'].astype(int).astype(str) 
    mind_df['비율(%)'] = pd.to_numeric(mind_df['비율(%)'], errors='coerce')
    
    fac_df['시도명'] = fac_df['시도명'].astype(str)
    fac_df['위도'] = pd.to_numeric(fac_df['위도'], errors='coerce')
    fac_df['경도'] = pd.to_numeric(fac_df['경도'], errors='coerce')
    
    return fac_df.dropna(subset=['위도', '경도']), mind_df.dropna(subset=['비율(%)'])

fac_df, mind_df = load_data()

# 3. 왼쪽 사이드바 (지역 검색 기능 추가)
st.sidebar.header("🔍 데이터 탐색 필터")

region_list = ["전국"] + sorted([str(x) for x in fac_df['시도명'].unique() if x != 'nan'])
selected_region = st.sidebar.selectbox("📍 지역(시/도)을 선택하세요", region_list)

year_list = sorted(mind_df['연도'].unique(), reverse=True)
selected_year = st.sidebar.selectbox("📅 연도를 선택하세요", year_list)

indicator_list = mind_df['지표명'].unique()
selected_indicator = st.sidebar.selectbox("🧠 마음건강 지표를 선택하세요", indicator_list)

# 데이터 필터링 로직
if selected_region == "전국":
    filtered_fac = fac_df
    map_center = [36.5, 127.5]
    map_zoom = 7
else:
    filtered_fac = fac_df[fac_df['시도명'].str.contains(selected_region)]
    if not filtered_fac.empty:
        map_center = [filtered_fac['위도'].mean(), filtered_fac['경도'].mean()]
    else:
        map_center = [36.5, 127.5]
    map_zoom = 10

filtered_mind_year = mind_df[(mind_df['연도'] == selected_year) & (mind_df['지표명'] == selected_indicator)]

# 4. 상단 레이아웃 (지도 vs 막대 그래프)
col1, col2 = st.columns([5, 5])

with col1:
    st.subheader(f"🗺️ {selected_region} 청소년 수련시설 분포")
    st.caption("마커를 클릭해 시설 이름을 확인하세요.")
    
    # 깔끔한 미니멀 스타일의 지도(cartodbpositron) 적용
    m = folium.Map(location=map_center, zoom_start=map_zoom, tiles='cartodbpositron')
    marker_cluster = MarkerCluster().add_to(m)
    
    for idx, row in filtered_fac.iterrows():
        folium.Marker(
            location=[row['위도'], row['경도']],
            tooltip=f"<b>{row['시설명']}</b><br>{row.get('시군구명', '')}",
            icon=folium.Icon(color='blue', icon='info-sign')
        ).add_to(marker_cluster)
        
    components.html(m._repr_html_(), height=450)

with col2:
    st.subheader(f"📊 {selected_year}년 지역별 {selected_indicator} 비교")
    st.caption("막대그래프: 지역별 수치를 직관적으로 비교합니다.")
    
    mind_sorted = filtered_mind_year.sort_values(by="비율(%)", ascending=True)
    # 선택한 지역을 빨간색으로 강조 표시
    mind_sorted['color'] = mind_sorted['지역명'].apply(
        lambda x: '#e74c3c' if selected_region != "전국" and x[:2] in selected_region else '#3498db'
    )
    
    fig_bar = px.bar(mind_sorted, x="비율(%)", y="지역명", orientation='h', 
                     color='color', color_discrete_map="identity")
    fig_bar.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=450)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")
st.subheader("📈 다각적 데이터 분석 (인포그래픽 스타일)")

# 5. 하단 레이아웃 (라인, 도넛, 산점도)
col3, col4, col5 = st.columns(3)

with col3:
    st.markdown("**1. 5년간 변화 추이 (라인 그래프)**")
    target_region = mind_df['지역명'].iloc[0] if selected_region == "전국" else selected_region[:2]
    # 지역명 매칭 보정
    matched_regions = mind_df[mind_df['지역명'].str.contains(target_region)]['지역명']
    final_target = matched_regions.iloc[0] if not matched_regions.empty else mind_df['지역명'].iloc[0]
    
    trend_df = mind_df[(mind_df['지역명'] == final_target) & (mind_df['지표명'] == selected_indicator)].sort_values('연도')
    fig_line = px.line(trend_df, x="연도", y="비율(%)", markers=True, title=f"{final_target} {selected_indicator} 추이")
    st.plotly_chart(fig_line, use_container_width=True)

with col4:
    st.markdown("**2. 세부 지역별 시설 비율 (도넛 차트)**")
    if not filtered_fac.empty:
        pie_df = filtered_fac['시군구명'].value_counts().reset_index()
        pie_df.columns = ['시군구명', '시설 수']
        # 상위 5개만 보여주고 나머지는 '기타'로 처리하여 깔끔하게
        if len(pie_df) > 5:
            top_5 = pie_df.iloc[:5]
            others = pd.DataFrame([['기타', pie_df['시설 수'].iloc[5:].sum()]], columns=['시군구명', '시설 수'])
            pie_df = pd.concat([top_5, others])
            
        fig_pie = px.pie(pie_df, values='시설 수', names='시군구명', hole=0.4, title=f"{selected_region} 내 시설 분포")
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("해당 지역의 시설 데이터가 없습니다.")

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
    else:
        st.info("데이터 매칭에 실패했습니다.")
