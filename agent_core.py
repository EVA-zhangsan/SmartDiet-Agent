import os
from typing import Any

import django
import openai
from django.apps import apps as django_apps
from django.core.management import call_command
from django.db.utils import OperationalError
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
    # 1) 自动建表：云端首次启动常见 db.sqlite3 不存在（被 .gitignore 拦截）导致表未创建
    try:
        recipes = Recipe.objects.all()
        recipe_count = recipes.count()
    except OperationalError:
        call_command("migrate", interactive=False, run_syncdb=True, verbosity=0)
        recipes = Recipe.objects.all()
        recipe_count = recipes.count()

    # 2) 自动塞入初始数据（Seeding）：确保云端首次打开就可用
    if recipe_count == 0:
        seed_items = [
            {
                "name": "泰式青柠煎鸡胸",
                "calories": 350,
                "protein": 40.0,
                "carbs": 15.0,
                "fats": 10.0,
                "ingredients": "鸡胸肉 200g、青柠 1 个、蒜 2 瓣、黑胡椒、少量橄榄油、盐、辣椒粉（可选）",
                "instructions": "1) 鸡胸肉拍松，加入青柠汁、蒜末、盐和黑胡椒腌 10-15 分钟；2) 平底锅少油中火煎至两面金黄、熟透；3) 出锅再挤少量青柠汁提味。",
            },
            {
                "name": "意式番茄牛肉全麦面",
                "calories": 550,
                "protein": 35.0,
                "carbs": 60.0,
                "fats": 15.0,
                "ingredients": "全麦意面 80g（干重）、瘦牛肉末 150g、番茄/番茄罐头、洋葱、蒜、橄榄油、盐、黑胡椒、意式香草",
                "instructions": "1) 意面煮至 8 分熟；2) 少油炒香洋葱蒜末，下牛肉末炒散；3) 加番茄与香草小火收汁；4) 与意面拌匀即可。",
            },
            {
                "name": "藜麦大虾牛油果沙拉",
                "calories": 420,
                "protein": 25.0,
                "carbs": 30.0,
                "fats": 20.0,
                "ingredients": "藜麦 60g（熟）、虾仁 150g、牛油果 1/2 个、生菜/黄瓜/小番茄、柠檬汁、盐、黑胡椒",
                "instructions": "1) 虾仁焯水或快炒至变色；2) 藜麦提前煮熟放凉；3) 与蔬菜、牛油果混合；4) 用柠檬汁+盐+黑胡椒简单调味。",
            },
            {
                "name": "迷迭香烤三文鱼配时蔬",
                "calories": 600,
                "protein": 45.0,
                "carbs": 45.0,
                "fats": 25.0,
                "ingredients": "三文鱼 200g、迷迭香、柠檬、盐、黑胡椒、橄榄油、时蔬（西兰花/胡萝卜/彩椒）、小土豆（可选）",
                "instructions": "1) 三文鱼抹盐胡椒与迷迭香，铺柠檬片；2) 烤箱 200°C 烤 12-15 分钟；3) 时蔬同盘烤或蒸熟，少量橄榄油调味。",
            },
            {
                "name": "经典燕麦牛奶蓝莓碗",
                "calories": 300,
                "protein": 15.0,
                "carbs": 45.0,
                "fats": 6.0,
                "ingredients": "燕麦 40g、牛奶/无糖豆奶 200ml、蓝莓一小把、奇亚籽/坚果（可选）、肉桂粉（可选）",
                "instructions": "1) 燕麦与牛奶小火煮至浓稠；2) 盛出后加入蓝莓；3) 可按需撒奇亚籽/少量坚果提升口感与饱腹感。",
            },
        ]

        for item in seed_items:
            Recipe.objects.get_or_create(
                name=item["name"],
                defaults={
                    "calories": item["calories"],
                    "protein": item["protein"],
                    "carbs": item["carbs"],
                    "fats": item["fats"],
                    "ingredients": item["ingredients"],
                    "instructions": item["instructions"],
                },
            )

        recipes = Recipe.objects.all()

    # 3) 继续向下执行
    if not recipes.exists():
        return "数据库里还没有食谱哦，请先生成/录入一些食谱数据再试。"

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