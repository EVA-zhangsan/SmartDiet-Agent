import os
from typing import Any

import django
import openai
from django.apps import apps as django_apps
from openai import OpenAI

# ==========================================
# 1) 挂载 Django 环境（让脚本能读 Django 数据库）
# ==========================================
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutrition_project.settings")
if not django_apps.ready:
    django.setup()

from recipes.models import Recipe  # noqa: E402


# ==========================================
# 2) 配置 DeepSeek（OpenAI 兼容接口）
# ==========================================
def _require_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未检测到 DEEPSEEK_API_KEY。\n"
            "请在 PowerShell 设置：$env:DEEPSEEK_API_KEY='你的真实Key'"
        )
    return api_key


def _get_client_and_model() -> tuple[OpenAI, str]:
    api_key = _require_api_key()
    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
    )
    model_name = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"
    return client, model_name


def _normalize_messages(messages_history: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for msg in messages_history or []:
        if not isinstance(msg, dict):
            continue
        role = str(msg.get("role", "")).strip()
        content = str(msg.get("content", "")).strip()
        if not role or not content:
            continue
        if role not in {"user", "assistant"}:
            continue
        normalized.append({"role": role, "content": content})
    return normalized


def ask_smartdiet_agent(messages_history: list[dict[str, Any]], user_profile: str = "") -> str:
    """SmartDiet-Agent 的核心处理逻辑（支持多轮对话 + 用户画像注入）。"""
    recipes = Recipe.objects.all()

    if not recipes:
        return "数据库里还没有食谱哦，请先去 Django 后台录入几个测试数据！"

    recipe_context = "【当前系统可用的食谱库】：\n"
    for r in recipes:
        recipe_context += (
            f"- {r.name}: 热量 {r.calories}kcal, 蛋白 {r.protein}g, "
            f"碳水 {r.carbs}g, 脂肪 {r.fats}g\n"
            f"食材清单: {r.ingredients}\n"
        )

    system_message = {
        "role": "system",
        "content": (
            "你是 SmartDiet-Agent，一个专业营养师助手（教练口吻，温柔但坚定）。\n"
            "你必须严格基于【系统可用的食谱库】进行推荐与回答，不要编造食谱库里没有的菜。\n"
            "你必须严格参考用户的【每日目标热量】来推荐食谱，并用教练口吻解释这道菜的热量为何符合他当天的热量缺口/盈余需求。\n"
            "如果用户追问做法/食材替换/热量等，请只针对你推荐的那道食谱或食谱库内相关食谱回答。\n\n"
            f"【当前用户的身体档案与目标热量】：\n{user_profile or '未提供'}\n\n"
            f"【系统可用的食谱库】：\n{recipe_context}"
        ),
    }

    normalized_history = _normalize_messages(messages_history)
    if not normalized_history:
        normalized_history = [
            {
                "role": "user",
                "content": "请根据系统食谱库推荐一款适合减脂的餐，并简要说明理由。",
            }
        ]

    print("Agent 正在思考中...")
    try:
        client, model_name = _get_client_and_model()
        response = client.chat.completions.create(
            model=model_name,
            messages=[system_message] + normalized_history,
        )
        return (response.choices[0].message.content or "").strip()
    except RuntimeError as e:
        return str(e)
    except openai.APIStatusError as e:
        if getattr(e, "status_code", None) == 402:
            return (
                "DeepSeek 返回 402 Insufficient Balance：当前 Key 余额不足/未开通计费，无法调用模型。\n"
                "你可以先用离线模式把食谱造进数据库跑通演示：\n"
                "- $env:SMARTDIET_OFFLINE='1'\n"
                "- python auto_populate_db.py\n"
                "然后再重试对话。"
            )
        return f"DeepSeek 请求失败：{e}"
    except Exception as e:
        return f"DeepSeek 请求失败：{e}"


if __name__ == "__main__":
    test_messages = [
        {"role": "user", "content": "我想吃减脂餐"},
        {"role": "assistant", "content": "好的，你更偏好米饭还是面食？"},
        {"role": "user", "content": "都行，但想高蛋白"},
    ]
    print(
        ask_smartdiet_agent(
            test_messages,
            user_profile="用户男，20岁，身高170cm，体重70kg，目标减脂，每日目标热量≈1800kcal。",
        )
    )