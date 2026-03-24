import streamlit as st
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

# 🔴 页面配置（必须放在代码第一行，否则报错）
st.set_page_config(
    page_title="无人机心跳监测系统",
    page_icon="🚁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------
# 1. 模拟无人机真实心跳数据（可替换为真实串口/网络数据）
# --------------------------
@st.cache_data(ttl=60)  # 缓存1分钟，优化性能
def generate_heartbeat_data(duration_min=10, base_freq=120):
    """生成模拟心跳数据，真实场景可替换为飞控数据读取"""
    times = [datetime.now() - timedelta(minutes=i) for i in range(duration_min, 0, -1)]
    # 模拟心跳波动，贴近真实无人机状态
    freqs = base_freq + np.random.normal(0, 1.5, size=duration_min)
    return pd.DataFrame({"时间": times, "心跳频率(Hz)": freqs.round(1)})

# 初始化会话状态，保存实时数据
if "heartbeat_history" not in st.session_state:
    st.session_state.heartbeat_history = generate_heartbeat_data()
if "current_status" not in st.session_state:
    st.session_state.current_status = "正常"
if "alert_count" not in st.session_state:
    st.session_state.alert_count = 0

# --------------------------
# 2. 页面标题与侧边栏
# --------------------------
st.title("🚁 无人机心跳监测系统")
st.markdown("---")

# 侧边栏：系统设置
with st.sidebar:
    st.header("⚙️ 系统设置")
    # 心跳阈值设置（异常告警触发值）
    min_freq = st.number_input("最低正常心跳频率(Hz)", value=115.0, step=0.5)
    max_freq = st.number_input("最高正常心跳频率(Hz)", value=125.0, step=0.5)
    # 刷新间隔设置
    refresh_interval = st.slider("数据刷新间隔(秒)", min_value=1, max_value=10, value=3)
    # 手动刷新按钮
    if st.button("🔄 手动刷新数据"):
        st.session_state.heartbeat_history = generate_heartbeat_data()
        st.experimental_rerun()

# --------------------------
# 3. 实时状态卡片（核心监测区）
# --------------------------
st.header("📊 实时监测状态")
col1, col2, col3 = st.columns(3)

# 获取最新数据
latest_data = st.session_state.heartbeat_history.iloc[-1]
current_freq = latest_data["心跳频率(Hz)"]

# 判断系统状态
if current_freq < min_freq or current_freq > max_freq:
    st.session_state.current_status = "异常⚠️"
    st.session_state.alert_count += 1
    status_color = "red"
else:
    st.session_state.current_status = "正常✅"
    status_color = "green"

# 状态卡片展示
with col1:
    st.metric(
        label="当前心跳频率",
        value=f"{current_freq} Hz",
        delta=f"{current_freq - 120:.1f} Hz"
    )
with col2:
    st.metric(
        label="系统状态",
        value=st.session_state.current_status,
        delta="稳定" if status_color == "green" else "异常"
    )
with col3:
    st.metric(
        label="异常告警次数",
        value=st.session_state.alert_count
    )

# 异常告警提示
if st.session_state.current_status == "异常⚠️":
    st.error("🚨 无人机心跳异常！请立即检查飞控状态！")
else:
    st.success("✅ 无人机状态正常，运行稳定")

st.markdown("---")

# --------------------------
# 4. 心跳数据趋势图表
# --------------------------
st.header("📈 心跳频率趋势图")
st.line_chart(
    st.session_state.heartbeat_history.set_index("时间"),
    use_container_width=True,
    color="#FF4B4B"
)

# --------------------------
# 5. 历史数据表格
# --------------------------
st.header("📋 历史心跳数据")
st.dataframe(
    st.session_state.heartbeat_history,
    use_container_width=True,
    hide_index=True
)

# --------------------------
# 6. 自动刷新逻辑
# --------------------------
# 自动刷新页面，更新数据
time.sleep(refresh_interval)
# 追加新的实时数据
new_time = datetime.now()
new_freq = 120 + np.random.normal(0, 1.5)
new_row = pd.DataFrame({"时间": [new_time], "心跳频率(Hz)": [round(new_freq, 1)]})
st.session_state.heartbeat_history = pd.concat(
    [st.session_state.heartbeat_history, new_row],
    ignore_index=True
).tail(20)  # 保留最新20条数据，避免数据过多
st.experimental_rerun()
