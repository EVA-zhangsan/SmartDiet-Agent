import json
import os
import re

import django
import openai
from openai import OpenAI

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "nutrition_project.settings")
django.setup()

from recipes.models import Recipe  # noqa: E402


def _require_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "未检测到 DEEPSEEK_API_KEY。\n"
            "请先在 PowerShell 设置：$env:DEEPSEEK_API_KEY='你的真实Key'"
        )
    return api_key


def _offline_recipes() -> list[dict]:
    return [
        {
            "name": "鸡胸肉彩椒藜麦碗（增肌）",
            "calories": 520,
            "protein": 45,
            "carbs": 55,
            "fats": 12,
            "ingredients": "鸡胸肉 200g, 藜麦(熟) 180g, 彩椒 100g, 西兰花 150g, 橄榄油 5g, 黑胡椒/盐 适量",
            "instructions": "鸡胸肉切片煎熟；藜麦煮熟；蔬菜焯水；混合装碗，淋少量橄榄油调味。",
        },
        {
            "name": "番茄鸡蛋全麦面（日常平衡）",
            "calories": 430,
            "protein": 22,
            "carbs": 55,
            "fats": 14,
            "ingredients": "全麦面 80g, 鸡蛋 2个, 番茄 2个, 葱花 适量, 盐 适量",
            "instructions": "番茄炒出汁；下鸡蛋滑炒；加水煮开后下面，调味出锅。",
        },
        {
            "name": "金枪鱼鹰嘴豆沙拉（减脂）",
            "calories": 360,
            "protein": 32,
            "carbs": 28,
            "fats": 12,
            "ingredients": "水浸金枪鱼罐头 1罐, 鹰嘴豆(熟) 120g, 生菜 100g, 黄瓜 100g, 柠檬汁 10ml, 黑胡椒 适量",
            "instructions": "蔬菜切好；金枪鱼沥水；与鹰嘴豆混合，挤柠檬汁和黑胡椒拌匀。",
        },
        {
            "name": "牛奶燕麦香蕉杯（早餐）",
            "calories": 390,
            "protein": 18,
            "carbs": 58,
            "fats": 10,
            "ingredients": "燕麦 60g, 牛奶 250ml, 香蕉 1根, 坚果碎 10g",
            "instructions": "燕麦加牛奶微波或小火煮熟；加入香蕉片与坚果碎即可。",
        },
        {
            "name": "清蒸鳕鱼配时蔬（低脂高蛋白）",
            "calories": 310,
            "protein": 35,
            "carbs": 18,
            "fats": 10,
            "ingredients": "鳕鱼 200g, 西兰花 200g, 胡萝卜 80g, 生抽 10ml, 姜丝 适量",
            "instructions": "鳕鱼铺姜丝清蒸 8-10 分钟；蔬菜焯水；出锅淋少量生抽。",
        },
    ]


def _extract_json_array(text: str) -> str:
    raw = (text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[-1]
        if raw.endswith("```"):
            raw = raw[:-3].strip()
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end < start:
        return raw
    return raw[start : end + 1]


def _to_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            try:
                return float(match.group(0))
            except ValueError:
                return default
    return default


def _to_int(value: object, default: int = 0) -> int:
    number = _to_float(value, default=float(default))
    try:
        return int(round(number))
    except Exception:
        return default


def generate_and_save_recipes() -> None:
    offline = os.getenv("SMARTDIET_OFFLINE") in {"1", "true", "TRUE", "yes", "YES"}
    if offline:
        print("离线模式：不调用 DeepSeek，直接写入示例食谱数据...")
        recipes_data = _offline_recipes()
    else:
        api_key = _require_api_key()
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL") or "https://api.deepseek.com",
        )
        model_name = os.getenv("DEEPSEEK_MODEL") or "deepseek-chat"

        print("正在呼叫 SmartDiet-Agent (DeepSeek) 生成专业食谱数据...")

        prompt = """
你是一个精通《中国居民膳食指南（2022）》的专业营养师。
请帮我生成 10 个适合不同人群的健康食谱（包括减脂、增肌、日常平衡）。

请严格按照以下 JSON 数组格式输出，不要包含任何其他说明文字（不要使用 Markdown 代码块，直接输出纯 JSON）：
[
  {
    "name": "食谱名称",
    "calories": 350,
    "protein": 25.5,
    "carbs": 30.0,
    "fats": 10.0,
    "ingredients": "食材1 100g, 食材2 50g",
    "instructions": "第一步...第二步..."
  }
]
""".strip()

        try:
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个严格输出 JSON 的机器，只输出有效的 JSON 数组，不包含任何多余文字和 Markdown 标记。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0,
            )
        except openai.APIStatusError as e:
            if getattr(e, "status_code", None) == 402:
                print(
                    "DeepSeek 返回 402 Insufficient Balance：当前 Key 余额不足/未开通计费，无法调用模型。\n"
                    "解决方案：\n"
                    "1) 登录 DeepSeek 控制台为该 Key 充值/开通计费后重试；或\n"
                    "2) 临时用离线模式跑通演示：$env:SMARTDIET_OFFLINE='1'\n"
                    "原始错误："
                )
                print(e)
                raise
            print(f"请求 DeepSeek 失败：{e}")
            raise
        except Exception as e:
            print(f"请求 DeepSeek 失败：{e}")
            raise

        raw_text = response.choices[0].message.content or ""
        raw_text = _extract_json_array(raw_text)

        if os.getenv("SMARTDIET_SHOW_MODEL_OUTPUT") in {"1", "true", "TRUE", "yes", "YES"}:
            print("--- DeepSeek 原始输出（截断）---")
            print(raw_text[:2000])
            print("--- 结束 ---")

        try:
            recipes_data = json.loads(raw_text)
        except json.JSONDecodeError:
            print("解析 JSON 失败，返回内容如下：")
            print(raw_text)
            return

        if not isinstance(recipes_data, list):
            print("模型输出不是 JSON 数组，返回内容如下：")
            print(raw_text)
            return

    count = 0
    for data in recipes_data:
        if not isinstance(data, dict) or "name" not in data:
            continue

        recipe, created = Recipe.objects.get_or_create(
            name=str(data["name"]).strip(),
            defaults={
                "calories": _to_int(data.get("calories", 0)),
                "protein": _to_float(data.get("protein", 0.0)),
                "carbs": _to_float(data.get("carbs", 0.0)),
                "fats": _to_float(data.get("fats", 0.0)),
                "ingredients": str(data.get("ingredients", "")),
                "instructions": str(data.get("instructions", "")),
            },
        )
        if created:
            count += 1
            print(f"成功入库: {recipe.name} ({recipe.calories} kcal)")

    print(f"完成：本次共生成并保存了 {count} 个新食谱到数据库中。")
    if count == 0:
        print(
            "提示：没有新食谱入库。常见原因是模型输出的 JSON 不符合预期（字段缺失/数组为空），"
            "或生成的 name 与库里已有重名导致 get_or_create 未新增。\n"
            "你可以设置环境变量 SMARTDIET_SHOW_MODEL_OUTPUT=1 来打印模型原始输出用于排查。"
        )


if __name__ == "__main__":
    generate_and_save_recipes()
