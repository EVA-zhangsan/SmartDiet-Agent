import os

import django
import joblib
import plotly.graph_objects as go
import pandas as pd
import streamlit as st
from django.apps import apps as django_apps

# ==========================================
# 1) 挂载 Django 环境（必须最先做）
# ==========================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutrition_project.settings")
if not django_apps.ready:
    django.setup()

# ==========================================
# 2) 导入 Agent 大脑
# ==========================================
from agent_core import ask_smartdiet_agent  # noqa: E402


# ==========================================
# 3) 配置页面
# ==========================================
st.set_page_config(page_title="🥗 SmartDiet-Agent 智能营养师")

st.title("🥗 SmartDiet-Agent 智能营养师")
st.caption("欢迎！我会基于你数据库里的食谱，为你做饮食推荐。")

# 轻量 UI 微调：缩小侧边栏 metric 字号、压缩标题与图表间距
st.markdown(
        """
<style>
section[data-testid="stSidebar"] [data-testid="stMetricValue"] {
    font-size: 1.6rem;
    line-height: 1.9rem;
}
section[data-testid="stSidebar"] [data-testid="stMetricLabel"] {
    font-size: 0.95rem;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    margin-top: 0.6rem;
    margin-bottom: 0.1rem;
}
section[data-testid="stSidebar"] .stPlotlyChart {
    margin-top: -24px;
}
section[data-testid="stSidebar"] [data-testid="stPlotlyChart"] > div {
    margin-top: 0 !important;
    padding-top: 0 !important;
}
</style>
""",
        unsafe_allow_html=True,
)


# ==========================================
# 3.5) 侧边栏：用户画像 + 动态热量计算
# ==========================================
with st.sidebar:
    st.title("👤 个性化身体档案")

    gender = st.selectbox("性别", ["男", "女"], index=0)
    age = st.number_input("年龄", min_value=1, max_value=120, value=20, step=1)
    height_cm = st.number_input("身高 (cm)", min_value=80.0, max_value=250.0, value=170.0, step=1.0)
    weight_kg = st.number_input("体重 (kg)", min_value=20.0, max_value=300.0, value=70.0, step=0.5)

    activity_label = st.selectbox(
        "日常活动量",
        [
            "久坐（几乎不运动）",
            "轻度（每周1-3次轻运动）",
            "中度（每周3-5次运动）",
            "高度（每周6-7次高强度）",
            "极高（体力劳动/高强度训练）",
        ],
        index=1,
    )
    goal = st.selectbox("健康目标", ["减脂", "维持", "增肌"], index=0)

    activity_factor_map = {
        "久坐（几乎不运动）": 1.2,
        "轻度（每周1-3次轻运动）": 1.375,
        "中度（每周3-5次运动）": 1.55,
        "高度（每周6-7次高强度）": 1.725,
        "极高（体力劳动/高强度训练）": 1.9,
    }
    activity_factor = activity_factor_map[activity_label]

    # ==========================================
    # 3.55) AI 策略预测（传统机器学习模型）
    # ==========================================
    try:
        model_path = os.path.join(
            os.path.dirname(__file__),
            "diet_planner",
            "ml_models",
            "diet_model_v1.pkl",
        )
        model = joblib.load(model_path)

        features = pd.DataFrame(
            [
                {
                    "age": int(age),
                    "weight": float(weight_kg),
                    "height": float(height_cm),
                    "activity_level": float(activity_factor),
                }
            ]
        )

        prediction = model.predict(features)
        prediction_value = prediction[0] if hasattr(prediction, "__len__") else prediction

        pred_text = str(prediction_value)
        pred_norm = pred_text.strip().lower()
        pred_map = {
            "0": "减脂",
            "1": "维持",
            "2": "增肌",
            "cut": "减脂",
            "loss": "减脂",
            "lose": "减脂",
            "maintain": "维持",
            "bulk": "增肌",
            "gain": "增肌",
            "减脂": "减脂",
            "维持": "维持",
            "增肌": "增肌",
        }
        prediction_label = pred_map.get(pred_norm, pred_text)

        st.success(f"🤖 机器学习模型预测您最适合的策略是：{prediction_label}")
    except FileNotFoundError:
        st.warning("⚠️ 机器学习预测模型未挂载")
    except Exception:
        st.warning("⚠️ 机器学习预测暂不可用")

    # Mifflin-St Jeor
    if gender == "男":
        bmr = 10 * float(weight_kg) + 6.25 * float(height_cm) - 5 * int(age) + 5
    else:
        bmr = 10 * float(weight_kg) + 6.25 * float(height_cm) - 5 * int(age) - 161

    tdee = bmr * activity_factor

    if goal == "减脂":
        target_calories = tdee - 500
    elif goal == "增肌":
        target_calories = tdee + 300
    else:
        target_calories = tdee

    bmr_i = int(round(bmr))
    tdee_i = int(round(tdee))
    target_i = int(round(target_calories))

    st.divider()
    st.metric("BMR（基础代谢）", f"{bmr_i} kcal")
    st.metric("TDEE（维持消耗）", f"{tdee_i} kcal")
    st.metric("每日目标热量", f"{target_i} kcal")

    # ==========================================
    # 3.6) 三大宏量营养素建议（克数 + 可视化）
    # ==========================================
    if goal == "减脂":
        carbs_ratio, protein_ratio, fat_ratio = 0.40, 0.40, 0.20
    elif goal == "增肌":
        carbs_ratio, protein_ratio, fat_ratio = 0.50, 0.30, 0.20
    else:  # 维持
        carbs_ratio, protein_ratio, fat_ratio = 0.50, 0.20, 0.30

    carbs_g = int(round((float(target_i) * carbs_ratio) / 4))
    protein_g = int(round((float(target_i) * protein_ratio) / 4))
    fat_g = int(round((float(target_i) * fat_ratio) / 9))

    st.markdown("### 📊 今日营养配比建议")

    fig = go.Figure(
        data=[
            go.Pie(
                labels=["碳水化合物", "蛋白质", "脂肪"],
                values=[carbs_g, protein_g, fat_g],
                hole=0.4,
                marker=dict(colors=["#636EFA", "#EF553B", "#00CC96"]),
                textinfo="label+percent",
                hovertemplate="%{label}: %{value}g (%{percent})<extra></extra>",
            )
        ]
    )
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

    user_profile = (
        f"用户{gender}，{int(age)}岁，身高{int(round(height_cm))}cm，体重{float(weight_kg):.1f}kg，"
        f"日常活动量：{activity_label}，健康目标：{goal}。"
        f"系统计算：BMR≈{bmr_i}kcal，TDEE≈{tdee_i}kcal，每日目标热量≈{target_i}kcal。"
        f"三大宏量建议：碳水≈{carbs_g}g，蛋白≈{protein_g}g，脂肪≈{fat_g}g。"
    )


# ==========================================
# 4) 记忆管理：st.session_state.messages
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "你好！我可以根据系统现有食谱库给你推荐。你今天想减脂、增肌还是日常均衡？",
        }
    ]


# ==========================================
# 5) 核心交互：渲染历史 + 输入 + 调用大脑
# ==========================================
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("请输入你的需求，例如：我想吃高蛋白低脂的晚餐")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            # 不把第一条欢迎语传入模型，避免污染上下文
            messages_history = st.session_state.messages[1:]
            answer = ask_smartdiet_agent(messages_history, user_profile=user_profile)
        st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})