import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import streamlit_folium
import folium
from folium import plugins
import math

# --------------------------
# 🔴 页面配置（必须第一行）
# --------------------------
st.set_page_config(
    page_title="无人机智能化应用2451",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------
# 1. 坐标系转换工具（WGS-84 ↔ GCJ-02）
# --------------------------
# 火星坐标系 (GCJ-02) 与 WGS84 互转
class CoordTransform:
    #  Krasovsky 1940
    a = 6378245.0
    ee = 0.00669342162296594323

    @staticmethod
    def _transform_lat(lng, lat):
        ret = -100.0 + 2.0 * lng + 3.0 * lat + 0.2 * lat * lat + \
              0.1 * lng * lat + 0.2 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 *
                math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lat * math.pi) + 40.0 *
                math.sin(lat / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (160.0 * math.sin(lat / 12.0 * math.pi) + 320 *
                math.sin(lat * math.pi / 30.0)) * 2.0 / 3.0
        return ret

    @staticmethod
    def _transform_lng(lng, lat):
        ret = 300.0 + lng + 2.0 * lat + 0.1 * lng * lng + \
              0.1 * lng * lat + 0.1 * math.sqrt(abs(lng))
        ret += (20.0 * math.sin(6.0 * lng * math.pi) + 20.0 *
                math.sin(2.0 * lng * math.pi)) * 2.0 / 3.0
        ret += (20.0 * math.sin(lng * math.pi) + 40.0 *
                math.sin(lng / 3.0 * math.pi)) * 2.0 / 3.0
        ret += (150.0 * math.sin(lng / 12.0 * math.pi) + 300.0 *
                math.sin(lng / 30.0 * math.pi)) * 2.0 / 3.0
        return ret

    @staticmethod
    def wgs84_to_gcj02(lng, lat):
        """WGS84转GCJ02(火星坐标系)"""
        dlat = CoordTransform._transform_lat(lng - 105.0, lat - 35.0)
        dlng = CoordTransform._transform_lng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - CoordTransform.ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((CoordTransform.a * (1 - CoordTransform.ee)) / (magic * sqrtmagic) * math.pi)
        dlng = (dlng * 180.0) / (CoordTransform.a / sqrtmagic * math.cos(radlat) * math.pi)
        mglat = lat + dlat
        mglng = lng + dlng
        return [mglng, mglat]

    @staticmethod
    def gcj02_to_wgs84(lng, lat):
        """GCJ02(火星坐标系)转WGS84"""
        dlat = CoordTransform._transform_lat(lng - 105.0, lat - 35.0)
        dlng = CoordTransform._transform_lng(lng - 105.0, lat - 35.0)
        radlat = lat / 180.0 * math.pi
        magic = math.sin(radlat)
        magic = 1 - CoordTransform.ee * magic * magic
        sqrtmagic = math.sqrt(magic)
        dlat = (dlat * 180.0) / ((CoordTransform.a * (1 - CoordTransform.ee)) / (magic * sqrtmagic) * math.pi)
        dlng = (dlng * 180.0) / (CoordTransform.a / sqrtmagic * math.cos(radlat) * math.pi)
        mglat = lat + dlat
        mglng = lng + dlng
        return [lng * 2 - mglng, lat * 2 - mglat]

# --------------------------
# 2. 会话状态初始化
# --------------------------
if "page" not in st.session_state:
    st.session_state.page = "route_plan"  # 默认航线规划页
if "point_a" not in st.session_state:
    st.session_state.point_a = None  # (lat, lng) GCJ-02
if "point_b" not in st.session_state:
    st.session_state.point_b = None  # (lat, lng) GCJ-02
if "coord_system" not in st.session_state:
    st.session_state.coord_system = "GCJ-02"
if "flight_height" not in st.session_state:
    st.session_state.flight_height = 50
# 心跳数据初始化
if "heartbeat_history" not in st.session_state:
    st.session_state.heartbeat_history = pd.DataFrame({
        "时间": [datetime.now() - timedelta(seconds=i*10) for i in range(10, 0, -1)],
        "心跳频率(Hz)": [120 + np.random.normal(0, 1.5) for _ in range(10)]
    })
if "alert_count" not in st.session_state:
    st.session_state.alert_count = 0

# --------------------------
# 3. 侧边栏导航与设置
# --------------------------
with st.sidebar:
    st.header("🚁 导航")
    # 页面切换
    st.subheader("功能页面")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🗺️ 航线规划", use_container_width=True, 
                     type="primary" if st.session_state.page == "route_plan" else "secondary"):
            st.session_state.page = "route_plan"
            st.experimental_rerun()
    with col2:
        if st.button("📡 飞行监控", use_container_width=True,
                     type="primary" if st.session_state.page == "flight_monitor" else "secondary"):
            st.session_state.page = "flight_monitor"
            st.experimental_rerun()
    
    st.markdown("---")
    # 坐标系设置
    st.subheader("⚙️ 坐标系设置")
    coord_system = st.radio(
        "输入坐标系",
        ["WGS-84", "GCJ-02(高德/百度)"],
        index=1,
        key="coord_radio"
    )
    st.session_state.coord_system = "GCJ-02" if "GCJ" in coord_system else "WGS-84"
    
    st.markdown("---")
    # 系统状态
    st.subheader("✅ 系统状态")
    st.write(f"A点状态: {'已设置' if st.session_state.point_a else '未设置'}")
    st.write(f"B点状态: {'已设置' if st.session_state.point_b else '未设置'}")

# --------------------------
# 4. 页面1：航线规划（地图+坐标设置）
# --------------------------
if st.session_state.page == "route_plan":
    st.title("🗺️ 无人机航线规划")
    st.markdown("---")
    
    # 分栏：地图 + 控制面板
    col_map, col_ctrl = st.columns([3, 1])
    
    with col_ctrl:
        st.subheader("⚙️ 控制面板")
        
        # 起点A设置
        st.markdown("#### 📍 起点A")
        a_lat = st.number_input("纬度", value=32.2322, step=0.0001, key="a_lat")
        a_lng = st.number_input("经度", value=118.749, step=0.0001, key="a_lng")
        if st.button("✅ 设置A点", key="set_a"):
            # 转换为GCJ-02存储
            if st.session_state.coord_system == "WGS-84":
                lng_gcj, lat_gcj = CoordTransform.wgs84_to_gcj02(a_lng, a_lat)
                st.session_state.point_a = (lat_gcj, lng_gcj)
            else:
                st.session_state.point_a = (a_lat, a_lng)
            st.success("A点设置成功！")
            st.experimental_rerun()
        
        st.markdown("---")
        # 终点B设置
        st.markdown("#### 📍 终点B")
        b_lat = st.number_input("纬度", value=32.2343, step=0.0001, key="b_lat")
        b_lng = st.number_input("经度", value=118.749, step=0.0001, key="b_lng")
        if st.button("✅ 设置B点", key="set_b"):
            if st.session_state.coord_system == "WGS-84":
                lng_gcj, lat_gcj = CoordTransform.wgs84_to_gcj02(b_lng, a_lat)
                st.session_state.point_b = (lat_gcj, lng_gcj)
            else:
                st.session_state.point_b = (b_lat, b_lng)
            st.success("B点设置成功！")
            st.experimental_rerun()
        
        st.markdown("---")
        # 飞行参数
        st.markdown("#### ✈️ 飞行参数")
        st.session_state.flight_height = st.slider(
            "设定飞行高度(m)",
            min_value=10,
            max_value=200,
            value=50,
            step=5
        )
    
    with col_map:
        st.subheader("🗺️ 3D校园地图")
        # 初始化地图（默认校园中心）
        center_lat, center_lng = 32.2332, 118.7490
        if st.session_state.point_a:
            center_lat, center_lng = st.session_state.point_a
        elif st.session_state.point_b:
            center_lat, center_lng = st.session_state.point_b
        
        # 创建3D地图（Leaflet 3D）
        m = folium.Map(
            location=[center_lat, center_lng],
            zoom_start=17,
            tiles="https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}",
            attr="Google Satellite",
            crs="EPSG3857"
        )
        # 添加3D图层
        plugins.MousePosition().add_to(m)
        plugins.Fullscreen().add_to(m)
        
        # 标记A点和B点
        if st.session_state.point_a:
            folium.Marker(
                location=st.session_state.point_a,
                popup="起点A",
                icon=folium.Icon(color="red", icon="location-dot")
            ).add_to(m)
        if st.session_state.point_b:
            folium.Marker(
                location=st.session_state.point_b,
                popup="终点B",
                icon=folium.Icon(color="green", icon="location-dot")
            ).add_to(m)
        
        # 绘制AB航线
        if st.session_state.point_a and st.session_state.point_b:
            folium.PolyLine(
                locations=[st.session_state.point_a, st.session_state.point_b],
                color="blue",
                weight=3,
                opacity=0.7,
                popup=f"飞行高度: {st.session_state.flight_height}m"
            ).add_to(m)
        
        # 渲染地图
        streamlit_folium.folium_static(m, width=1000, height=600)

# --------------------------
# 5. 页面2：飞行监控（心跳包显示）
# --------------------------
elif st.session_state.page == "flight_monitor":
    st.title("📡 无人机飞行监控")
    st.markdown("---")
    
    # 实时状态卡片
    st.header("📊 实时心跳监测")
    col1, col2, col3 = st.columns(3)
    
    # 获取最新数据
    latest_data = st.session_state.heartbeat_history.iloc[-1]
    current_freq = latest_data["心跳频率(Hz)"]
    min_freq, max_freq = 115.0, 125.0
    
    # 判断状态
    if current_freq < min_freq or current_freq > max_freq:
        status = "异常⚠️"
        st.session_state.alert_count += 1
        status_color = "red"
    else:
        status = "正常✅"
        status_color = "green"
    
    with col1:
        st.metric(
            label="当前心跳频率",
            value=f"{current_freq:.1f} Hz",
            delta=f"{current_freq - 120:.1f} Hz"
        )
    with col2:
        st.metric(
            label="系统状态",
            value=status
        )
    with col3:
        st.metric(
            label="异常告警次数",
            value=st.session_state.alert_count
        )
    
    # 告警提示
    if status == "异常⚠️":
        st.error("🚨 无人机心跳异常！请立即检查飞控状态！")
    else:
        st.success("✅ 无人机状态正常，运行稳定")
    
    st.markdown("---")
    
    # 心跳趋势图
    st.header("📈 心跳频率趋势图")
    st.line_chart(
        st.session_state.heartbeat_history.set_index("时间"),
        use_container_width=True,
        color="#FF4B4B"
    )
    
    # 历史数据表格
    st.header("📋 历史心跳数据")
    st.dataframe(
        st.session_state.heartbeat_history,
        use_container_width=True,
        hide_index=True
    )
    
    # 自动刷新
    time.sleep(3)
    # 追加新数据
    new_time = datetime.now()
    new_freq = 120 + np.random.normal(0, 1.5)
    new_row = pd.DataFrame({"时间": [new_time], "心跳频率(Hz)": [round(new_freq, 1)]})
    st.session_state.heartbeat_history = pd.concat(
        [st.session_state.heartbeat_history, new_row],
        ignore_index=True
    ).tail(20)
    st.experimental_rerun()
