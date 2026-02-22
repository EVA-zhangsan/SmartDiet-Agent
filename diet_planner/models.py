from django.conf import settings
from django.db import models


class DietPlanItem(models.Model):
	class MealType(models.TextChoices):
		BREAKFAST = "breakfast", "早餐"
		LUNCH = "lunch", "午餐"
		DINNER = "dinner", "晚餐"
		SNACK = "snack", "加餐"

	diet_plan = models.ForeignKey(
		"diet_planner.DietPlan",
		on_delete=models.CASCADE,
		related_name="items",
		verbose_name="饮食计划",
	)
	recipe = models.ForeignKey(
		"recipes.Recipe",
		on_delete=models.CASCADE,
		related_name="diet_plan_items",
		verbose_name="食谱",
	)
	meal_type = models.CharField("餐次", max_length=20, choices=MealType.choices)
	portion = models.FloatField("份数", default=1.0)

	class Meta:
		db_table = "diet_plan_item"
		verbose_name = "饮食计划条目"
		verbose_name_plural = "饮食计划条目"

	def __str__(self) -> str:
		return f"{self.diet_plan} - {self.get_meal_type_display()} - {self.recipe} x{self.portion}"


class DietPlan(models.Model):
	user = models.ForeignKey(
		settings.AUTH_USER_MODEL,
		on_delete=models.CASCADE,
		related_name="diet_plans",
		verbose_name="用户",
	)
	date = models.DateField("日期")
	target_calories = models.PositiveIntegerField("当天目标总热量(kcal)")

	recipes = models.ManyToManyField(
		"recipes.Recipe",
		through="diet_planner.DietPlanItem",
		blank=True,
		related_name="diet_plans",
		verbose_name="食谱",
	)

	class Meta:
		db_table = "diet_plan"
		unique_together = ("user", "date")
		verbose_name = "饮食计划"
		verbose_name_plural = "饮食计划"

	def __str__(self) -> str:
		return f"{self.user} - {self.date}"
