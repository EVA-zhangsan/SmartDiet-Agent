from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
	age = models.PositiveIntegerField(null=True, blank=True)
	weight = models.FloatField(help_text="体重（kg）", null=True, blank=True)
	height = models.FloatField(help_text="身高（cm）", null=True, blank=True)
	goal = models.CharField(
		max_length=20,
		choices=[
			("lose", "减脂"),
			("maintain", "维持"),
			("gain", "增肌"),
		],
		default="lose",
	)

	class Meta:
		db_table = "custom_user"
