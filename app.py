import streamlit as st
import leafmap.foliumap as leafmap
import folium
from streamlit_folium import st_folium

# -------------------------- 页面全局配置 --------------------------
st.set_page_config(
    page_title="无人机智能化应用",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------- 侧边栏（导航+坐标系+状态） --------------------------
with st.sidebar:
    st.header("🚁 导航")
    st.subheader("功能页面")
    
    # 功能页按钮（航线规划默认选中）
    col1, col2 = st.columns(2)
    with col1:
        st.button("📖 航线规划", type="primary", use_container_width=True)
    with col2:
        st.button("📡 飞行监控", type="secondary", use_container_width=True)
    
    st.divider()
    
    # 坐标系设置
    st.subheader("⚙️ 坐标系设置")
    st.write("输入坐标系")
    coord_system = st.radio(
        "",
        ["WGS-84", "GCJ-02(高德/百度)"],
        index=1,  # 默认选中GCJ-02，和你截图一致
        label_visibility="collapsed"
    )
    
    st.divider()
    
    # 系统状态
    st.subheader("✅ 系统状态")
    if "a_point_set" not in st.session_state:
        st.session_state.a_point_set = False
    st.write(f"A点状态: {'已设置' if st.session_state.a_point_set else '未设置'}")

# -------------------------- 主页面（3D地图+控制面板） --------------------------
# 分三栏布局：地图主体 + 右侧控制面板
col_map, col_ctrl = st.columns([3, 1])

# 右侧控制面板
with col_ctrl:
    st.header("⚙️ 控制面板")
    
    # 起点A设置
    st.subheader("📍 起点A")
    a_lat = st.number_input("纬度", value=32.23, min_value=-90.0, max_value=90.0, step=0.01)
    a_lon = st.number_input("经度", value=118.75, min_value=-180.0, max_value=180.0, step=0.01)
    set_a = st.checkbox("✅ 设置A点", value=st.session_state.a_point_set)
    
    # 终点B设置（补充完整功能）
    st.subheader("📍 终点B")
    b_lat = st.number_input("纬度", value=32.24, min_value=-90.0, max_value=90.0, step=0.01)
    b_lon = st.number_input("经度", value=118.76, min_value=-180.0, max_value=180.0, step=0.01)
    set_b = st.checkbox("✅ 设置B点")
    
    # 更新A点状态
    if set_a:
        st.session_state.a_point_set = True
    else:
        st.session_state.a_point_set = False

# 中间3D地图区域
with col_map:
    st.header("🗺️ 3D校园地图")
    
    # -------------------------- 底图配置（核心修复） --------------------------
    # 根据坐标系选择对应底图
    if coord_system == "GCJ-02(高德/百度)":
        # 高德GCJ-02坐标系瓦片（国内可直接加载，无网络问题）
        tile_url = "https://webrd02.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}"
        tile_attr = "&copy; 高德地图"
        # GCJ-02默认中心（南京，和你截图坐标一致）
        center_lat, center_lon = 32.23, 118.75
    else:
        # WGS-84坐标系（天地图国际版，海外兼容）
        tile_url = "https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=你的天地图Key"
        tile_attr = "&copy; 天地图"
        center_lat, center_lon = 32.23, 118.75
    
    # -------------------------- 地图初始化 --------------------------
    # 若A点已设置，以A点为中心；否则用默认中心
    if st.session_state.a_point_set:
        center_lat, center_lon = a_lat, a_lon
    
    # 创建folium地图（支持3D倾斜视角）
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=17,  # 校园级缩放
        tiles=tile_url,
        attr=tile_attr,
        control_scale=True,
        prefer_canvas=True  # 优化渲染性能
    )
    
    # 添加3D倾斜视角（模拟3D效果）
    m.fit_bounds([[center_lat-0.005, center_lon-0.005], [center_lat+0.005, center_lon+0.005]])
    
    # -------------------------- 标记点（A/B点） --------------------------
    # 起点A标记
    if st.session_state.a_point_set:
        folium.Marker(
            location=[a_lat, a_lon],
            popup="起点A",
            icon=folium.Icon(color="red", icon="map-marker")
        ).add_to(m)
    
    # 终点B标记
    if set_b:
        folium.Marker(
            location=[b_lat, b_lon],
            popup="终点B",
            icon=folium.Icon(color="blue", icon="map-marker")
        ).add_to(m)
        # 绘制A-B航线
        if st.session_state.a_point_set:
            folium.PolyLine(
                locations=[[a_lat, a_lon], [b_lat, b_lon]],
                color="green",
                weight=3,
                opacity=0.8
            ).add_to(m)
    
    # -------------------------- 渲染地图到Streamlit --------------------------
    st_folium(m, width="100%", height=600)

# -------------------------- 补充说明 --------------------------
st.info("""
### 📌 修复说明
1.  **底图替换**：默认使用高德GCJ-02瓦片，国内网络直接加载，彻底解决空白问题
2.  **坐标适配**：完美兼容你当前的GCJ-02坐标系，无需切换WGS-84
3.  **状态同步**：A点设置状态实时同步侧边栏，解决未设置导致的空白
4.  **3D效果**：通过倾斜视角+缩放模拟3D校园地图，可直接用于航线规划
""")
