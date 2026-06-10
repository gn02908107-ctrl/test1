import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from folium.plugins import AntPath
import numpy as np

# 設置網頁標題與寬度版面
st.set_page_config(page_title="三大機場客運市場儀表板", layout="wide")

# 1. 讀取資料
@st.cache_data
def load_data():
    try:
        return pd.read_csv('airport_final_focus.csv')
    except FileNotFoundError:
        st.error("❌ 找不到 'airport_final_focus.csv'，請確保檔案在同一個資料夾下。")
        return None

df = load_data()

if df is not None:
    # 定義對照表
    airport_display_map = {
        "台北-桃園 (TPE)": "TPE",
        "香港 (HKG)": "HKG",
        "東京-羽田 (HND)": "HND"
    }
    reverse_display_map = {v: k for k, v in airport_display_map.items()}

    # ==========================================
    # 🗺️ 側邊欄 (Sidebar)
    # ==========================================
    st.sidebar.header("🗺️ 數據篩選中心")
    
    st.sidebar.subheader("1. 機場對比選擇")
    ap1_label = st.sidebar.selectbox("請選擇第一家機場：", options=list(airport_display_map.keys()), index=0)
    ap2_label = st.sidebar.selectbox("請選擇第二家機場 (選填)：", options=["無"] + list(airport_display_map.keys()), index=2)
    ap3_label = st.sidebar.selectbox("請選擇第三家機場 (選填)：", options=["無"] + list(airport_display_map.keys()), index=3)
    
    selected_airports = []
    if ap1_label and ap1_label != "無": selected_airports.append(airport_display_map[ap1_label])
    if ap2_label and ap2_label != "無": selected_airports.append(airport_display_map[ap2_label])
    if ap3_label and ap3_label != "無": selected_airports.append(airport_display_map[ap3_label])
    selected_airports = list(set(selected_airports))

    df_filtered = df[df['出發機場'].isin(selected_airports)].copy()
    df_filtered['出發機場顯示'] = df_filtered['出發機場'].map(reverse_display_map)

    st.sidebar.markdown("---")
    st.sidebar.subheader("2. 航空公司基地特寫")
    
    # 萃取單一航司萃取出來當選單
    raw_airlines = df_filtered['航空公司'].dropna().unique()
    split_airlines = set()
    for al in raw_airlines:
        for part in str(al).split('/'):
            split_airlines.add(part.strip())
            
    available_airlines = list(split_airlines)
    available_airlines.sort()
    
    selected_airline = st.sidebar.selectbox(
        "選擇欲深入分析的航空公司 (從已選機場起飛)：",
        options=["無"] + available_airlines,
        index=0  
    )

    # ==========================================
    # 網頁主面板 (Main Panel)
    # ==========================================
    title_airports = " vs ".join([reverse_display_map[ap] for ap in selected_airports])
    st.title(f"✈️ 樞紐機場客運市場對比研究")
    
    # 標題動態提示目前地圖的連動狀態
    if selected_airline != "無":
        st.markdown(f"目前正在對比：**{title_airports}** ｜ 🔍 地圖已鎖定【**{selected_airline}**】專屬航網")
    else:
        st.markdown(f"目前正在對比：**{title_airports}** ｜ 🌐 目前顯示機場**完整大航網**")
    st.markdown("---")

    # KPI 卡片模糊比對
    if selected_airline != "無":
        df_kpi = df_filtered[df_filtered['航空公司'].str.contains(selected_airline, na=False)]
    else:
        df_kpi = df_filtered
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("當前聯營航線總數" if selected_airline == "無" else f"{selected_airline} 相關航線數", f"{len(df_kpi)} 條")
    with col2:
        st.metric("涵蓋航空公司總計" if selected_airline == "無" else "營運基地機場數", f"{df_kpi['航空公司'].nunique()} 家" if selected_airline == "無" else f"{df_kpi['出發機場'].nunique()} 個")
    with col3:
        st.metric("直飛目的地總計" if selected_airline == "無" else f"{selected_airline} 直飛航點", f"{df_kpi['航點'].nunique()} 個")

    # 地圖標題
    if selected_airline != "無":
        st.markdown(f"### 🗺️ 【{selected_airline}】專屬動態航線流動網絡")
    else:
        st.markdown("### 🗺️ 選定樞紐之航線流動網絡對比 (完整航網模式)")
    
    # 地圖地理座標字典
    geo_dict = {
        'TPE': [25.0797, 121.2342], 'HKG': [22.3080, 113.9185], 'HND': [35.5494, 139.7798],
        '香港': [22.3080, 113.9185], '台北-桃園': [25.0797, 121.2342],
        '台中': [24.2643, 120.6206], '高雄': [22.5768, 120.3500],
        '北京-大興': [39.5094, 116.4105], '北京-首都': [40.0799, 116.6031], 
        '上海-浦東': [31.1443, 121.8083], '上海-虹橋': [31.1979, 121.3363], 
        '廣州': [23.3924, 113.2988], '深圳': [22.6393, 113.8107],
        '東京-成田': [35.7720, 140.3929], '東京-羽田': [35.5494, 139.7798],
        '大阪-關西': [34.4320, 135.2304], '大阪-伊丹': [34.7855, 135.4382],
        '名古屋-中部': [34.8584, 136.8054], '福岡': [33.5859, 130.4507],
        '沖繩': [26.2064, 127.6465], '札幌-新千歲': [42.7752, 141.6923],
        '首爾-仁川': [37.4602, 126.4407], '首爾-金浦': [37.5581, 126.7906],
        '釜山': [35.1796, 128.9382], '曼谷-蘇凡納布': [13.6926, 100.7512], 
        '新加坡': [1.3644, 103.9915], '吉隆坡': [2.7456, 101.7072], 
        '河內': [21.2212, 105.8072], '胡志明市': [10.8185, 106.6518], 
        '峴港': [16.0439, 108.1994], '馬尼拉': [14.5086, 121.0194]
    }
    
    # 禁用滾輪和雙指縮放，避免手勢衝突
    m = folium.Map(location=geo_dict[selected_airports[0]], zoom_start=4, tiles='CartoDB dark_matter', zoom_control=False, scrollWheelZoom=False, dragging=True)
    airport_colors = {'TPE': '#00FFCC', 'HKG': '#FF3366', 'HND': '#FFFF33'}

    for ap in selected_airports:
        folium.CircleMarker(location=geo_dict[ap], radius=9, color=airport_colors[ap], fill=True, fill_color=airport_colors[ap], fill_opacity=0.9, tooltip=reverse_display_map[ap]).add_to(m)

    # 地圖資料包含判定
    if selected_airline != "無":
        df_map_source = df_filtered[df_filtered['航空公司'].str.contains(selected_airline, na=False)]
    else:
        df_map_source = df_filtered

    unique_routes = df_map_source.groupby(['出發機場', '航點']).size().reset_index(name='數量')
    
    for idx, row in unique_routes.iterrows():
        origin = row['出發機場']
        dest = row['航點']
        if origin in geo_dict and dest in geo_dict:
            p1, p2 = geo_dict[origin], geo_dict[dest]
            dist = np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            mid_lat = (p1[0]+p2[0])/2 + dist*0.14
            mid_lon = (p1[1]+p2[1])/2
            arc_path = [[p1[0], p1[1]], [mid_lat, mid_lon], [p2[0], p2[1]]]
            
            AntPath(locations=arc_path, color=airport_colors[origin], pulse_color='#FFFFFF', weight=2.5, opacity=0.8, delay=1200).add_to(m)
            folium.CircleMarker(location=geo_dict[dest], radius=3.5, color='#FFFFFF', fill=True, fill_color=airport_colors[origin], fill_opacity=0.8, popup=dest).add_to(m)

    # 💡 終極修正：在這裡加入一個動態變化的 key！
    # 只要選取的機場組合或航空公司一換，key 就會徹底改變，逼迫 Streamlit 銷毀快取並畫出正確新地圖。
    map_key = f"map_render_{'_'.join(selected_airports)}_{selected_airline}"
    st_folium(m, width=1400, height=450, returned_objects=[], key=map_key)

    # 各機場主力航空公司運力份額占比
    st.markdown("---")
    st.markdown("### 🏢 各機場主力航空公司運力份額占比")
    
    airline_share = df_filtered.groupby(['出發機場顯示', '航空公司']).size().reset_index(name='配置班次')
    
    fig_airline_pie = px.pie(
        airline_share, values='配置班次', names='航空公司', facet_col='出發機場顯示', hole=0.3,
        facet_col_spacing=0.07, color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig_airline_pie.update_traces(textposition='outside', textinfo='percent+label', direction='clockwise')
    fig_airline_pie.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font=dict(size=13, weight='bold'), y=1.15))
    
    fig_airline_pie.update_layout(
        margin=dict(t=100, b=50, l=20, r=20),
        legend=dict(orientation="h", yanchor="bottom", y=-0.18, xanchor="center", x=0.5)
    )
    st.plotly_chart(fig_airline_pie, use_container_width=True)

    # ==========================================
    # 第一組左右並排區塊
    # ==========================================
    st.markdown("---")
    model_col1, model_col2 = st.columns(2)

    with model_col1:
        st.markdown("### 🧱 各機場客機體型結構 (寬體 vs 窄體)")
        df_filtered['客機體型'] = df_filtered['簡化機型'].apply(lambda x: '寬體客機 (Wide-body)' if x in ['A350', 'B777', 'B787', 'A330', 'B767'] else '窄體客機 (Narrow-body)')
        body_counts = df_filtered.groupby(['出發機場顯示', '客機體型']).size().reset_index(name='數量')
        
        fig_bar = px.bar(body_counts, x='客機體型', y='數量', color='客機體型',
                         animation_frame='出發機場顯示', 
                         labels={'數量': '配置航線數'},
                         color_discrete_map={'寬體客機 (Wide-body)': '#1F77B4', '窄體客機 (Narrow-body)': '#FFBB78'})
        
        fig_bar.update_layout(
            margin=dict(t=30, b=100, l=20, r=20),
            xaxis_title="",
            yaxis=dict(range=[0, body_counts['數量'].max() * 1.15]),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with model_col2:
        if selected_airline != "無":
            st.markdown(f"### 🔍 旗艦特寫：【{selected_airline}】機型結構")
            df_airline_specific = df_filtered[df_filtered['航空公司'].str.contains(selected_airline, na=False)]
            
            if not df_airline_specific.empty:
                airline_model_counts = df_airline_specific['簡化機型'].value_counts().reset_index()
                airline_model_counts.columns = ['機型系列', '配置次數']
                
                fig_air_models = px.pie(
                    airline_model_counts, values='配置次數', names='機型系列', 
                    hole=0.4, color_discrete_sequence=px.colors.qualitative.Dark2
                )
                fig_air_models.update_traces(textposition='outside', textinfo='percent+label', direction='clockwise')
                fig_air_models.update_layout(
                    margin=dict(t=50, b=80, l=20, r=20),
                    legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5)
                )
                st.plotly_chart(fig_air_models, use_container_width=True)
            else:
                st.warning(f"暫無 {selected_airline} 的詳細機型數據。")
        else:
            st.markdown("### 🔍 旗艦特寫：航空公司機型結構")
            st.info("💡 請在左側側邊欄選擇特定的「航空公司」，即可在此解鎖該航空的機型比例細節特寫。")

    # ==========================================
    # 第二組左右並排區塊
    # ==========================================
    st.markdown("---")
    route_col1, route_col2 = st.columns(2)
    
    with route_col1:
        st.markdown("### 📊 各機場區域航線配置占比")
        def categorize_region_simple(row):
            greater_china = ['香港', '台北-桃園', '台中', '高雄', '北京-大興', '北京-首都', '上海-浦東', '上海-虹橋', '廣州', '深圳']
            japan_domestic = ['小松', '大分', '三澤', '山口宇部', '旭川', '函館', '青森', '鹿兒島', '東京-羽田', '東京-成田', '大阪-伊丹', '大阪-關西', '名古屋-中部', '福岡', '沖繩', '札幌-新千歲']
            if row['出發機場'] == 'HND' and row['航點'] in japan_domestic: return '日本國內幹線'
            elif row['航點'] in greater_china: return '大中華/兩岸三地線'
            else: return '亞太跨國區域線'
        
        df_filtered['航網區域'] = df_filtered.apply(categorize_region_simple, axis=1)
        region_counts = df_filtered.groupby(['出發機場顯示', '航網區域']).size().reset_index(name='航線數')
        
        fig_pie = px.pie(region_counts, values='航線數', names='航網區域', facet_col='出發機場顯示', hole=0.4,
                         facet_col_spacing=0.07, color_discrete_sequence=px.colors.qualitative.Safe)
        fig_pie.update_traces(textposition='outside', textinfo='percent+label', insidetextorientation='radial', direction='clockwise')
        fig_pie.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1], font=dict(size=13, weight='bold'), y=1.15))
        
        fig_pie.update_layout(margin=dict(t=100, b=80, l=20, r=20), showlegend=True,
                              legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5))
        st.plotly_chart(fig_pie, use_container_width=True)

    with route_col2:
        if selected_airline != "無":
            st.markdown(f"### 📈 【{selected_airline}】熱門航點分佈")
            df_airline_specific = df_filtered[df_filtered['航空公司'].str.contains(selected_airline, na=False)]
            if not df_airline_specific.empty:
                df_air_dest = df_airline_specific['航點'].value_counts().reset_index().head(8)
                df_air_dest.columns = ['目的地航點', '航班次數']
                fig_air_dest = px.bar(
                    df_air_dest, x='航班次數', y='目的地航點', orientation='h',
                    color_discrete_sequence=['#7F7F7F']
                )
                fig_air_dest.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=30, b=50, l=20, r=20))
                st.plotly_chart(fig_air_dest, use_container_width=True)
        else:
            st.markdown("### 📈 航空公司熱門航點分佈")
            st.info("💡 請在左側選單選擇航空公司以檢視其專屬航點排行。")

    st.markdown("---")
    
    # 全幅熱門航線排行
    st.markdown("### 🏆 各機場核心航空公司之黃金熱門航線排行 (各機場 Top 5 動態巡航)")
    route_counts = df_filtered.groupby(['出發機場', '出發機場顯示', '航空公司', '航點']).size().reset_index(name='次數')
    
    top_routes_list = []
    for ap in selected_airports:
        ap_top = route_counts[route_counts['出發機場'] == ap].sort_values(by='次數', ascending=False).head(5)
        top_routes_list.append(ap_top)
        
    if top_routes_list:
        top_routes = pd.concat(top_routes_list)
        top_routes = top_routes.sort_values(by='次數', ascending=True)
        
        airport_bar_colors = {
            '台北-桃園 (TPE)': '#2CA02C', 
            '香港 (HKG)': '#D62728', 
            '東京-羽田 (HND)': '#1F77B4'
        }
        
        fig_routes = px.bar(
            top_routes, x='次數', y='航點', color='出發機場顯示', orientation='h',
            animation_frame='出發機場顯示', 
            text='航空公司',
            color_discrete_map=airport_bar_colors
        )
        
        fig_routes.update_traces(textposition='inside')
        fig_routes.update_layout(
            margin=dict(t=20, b=40, l=20, r=20),
            xaxis=dict(range=[0, top_routes['次數'].max() * 1.15]), 
            showlegend=False
        )
        st.plotly_chart(fig_routes, use_container_width=True)
