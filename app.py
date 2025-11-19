import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from datetime import datetime
import numpy as np

# ========== 設定 ==========
st.set_page_config(page_title="Lime Retrieval Tool", layout="wide")
TARGET_VALUE = "needs_retrieval"
BASE_URL_TEMPLATE = "https://admintool.lime.bike/vehicle/{id}?region=MDH3CPXCIE5F3"

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    a = np.sin(delta_phi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    return R * c

# タイトル
st.title("🛴 Lime 回収マップ")

# 1. ポート情報の読み込み (リポジトリ内のTokyo.csv)
try:
    df_ports = pd.read_csv("Tokyo.csv")
    df_ports.columns = df_ports.columns.str.strip().str.lower()
except:
    st.error("⚠️ Tokyo.csv が見つかりません。同じフォルダに置いてください。")
    st.stop()

# 2. ファイルアップロード
uploaded_file = st.file_uploader("LimeのCSVをアップロード", type="csv")

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)
        df.columns = df.columns.str.strip().str.lower()
        
        # フィルタリング
        if "operational state" in df.columns:
            targets = df[df["operational state"].str.lower() == TARGET_VALUE.lower()].copy()
            
            if targets.empty:
                st.success("✅ 回収対象はありません！")
            else:
                # 時間計算
                if 'last ride' in targets.columns:
                    targets['last ride'] = pd.to_datetime(targets['last ride'], errors='coerce')
                    now = datetime.now()
                    targets['hours'] = (now - targets['last ride']).dt.total_seconds() / 3600
                    targets = targets.sort_values('hours', ascending=False)
                else:
                    targets['hours'] = 0
                
                st.warning(f"🚨 **{len(targets)}台** の回収対象が見つかりました")

                # 地図作成
                m = folium.Map(location=[targets.iloc[0]['latitude'], targets.iloc[0]['longitude']], zoom_start=14)
                
                # マーカー
                for _, row in targets.iterrows():
                    v_lat, v_lon = row['latitude'], row['longitude']
                    
                    # 最寄りポート
                    df_ports['dist'] = haversine_distance(v_lat, v_lon, df_ports['latitude'], df_ports['longitude'])
                    nearest = df_ports.nsmallest(1, 'dist').iloc[0]
                    
                    # 赤ピン
                    time_str = f"{int(row['hours'])}h前"
                    folium.Marker(
                        [v_lat, v_lon], 
                        popup=f"{row['plate number']}\n{time_str}", 
                        icon=folium.Icon(color='red', icon='bicycle', prefix='fa')
                    ).add_to(m)
                    
                    # 青ピン
                    folium.Marker(
                        [nearest['latitude'], nearest['longitude']], 
                        popup=nearest['place_name'], 
                        icon=folium.Icon(color='blue', icon='info-sign')
                    ).add_to(m)
                    
                    # 線
                    folium.PolyLine([[v_lat, v_lon], [nearest['latitude'], nearest['longitude']]], color="gray", dash_array='5,5').add_to(m)

                # 地図表示
                st_folium(m, width=700, height=500)

                # リスト表示
                st.subheader("📋 詳細リスト")
                for _, row in targets.iterrows():
                    # 最寄り再計算
                    df_ports['dist'] = haversine_distance(row['latitude'], row['longitude'], df_ports['latitude'], df_ports['longitude'])
                    nearest = df_ports.nsmallest(1, 'dist').iloc[0]
                    
                    lime_link = BASE_URL_TEMPLATE.format(id=row['id'])
                    map_link = f"https://www.google.com/maps/dir/?api=1&destination={nearest['latitude']},{nearest['longitude']}&travelmode=walking"

                    with st.expander(f"🚗 {row['plate number']} ({int(row['hours'])}時間前)"):
                        st.write(f"📍 最寄り: **{nearest['place_name']}** (距離: {nearest['dist']:.0f}m)")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.link_button("Lime管理画面", lime_link)
                        with col2:
                            st.link_button("Google Mapルート", map_link)

        else:
            st.error("CSVの形式が違います (operational state列なし)")
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")
