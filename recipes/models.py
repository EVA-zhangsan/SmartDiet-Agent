from django.db import models

class Recipe(models.Model):
	name = models.CharField("食谱名称", max_length=255)
	calories = models.PositiveIntegerField("卡路里")
	protein = models.FloatField("蛋白质")
	carbs = models.FloatField("碳水")
	fats = models.FloatField("脂肪")
	ingredients = models.TextField("食材清单")
	instructions = models.TextField("制作步骤")

	def __str__(self) -> str:
		return self.name
