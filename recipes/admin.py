from django.contrib import admin
from django.db import models
from django.forms import Textarea

from .models import Recipe


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
	list_display = ("name", "calories", "protein", "carbs", "fats")
	search_fields = ("name",)

	formfield_overrides = {
		models.TextField: {"widget": Textarea(attrs={"rows": 6, "cols": 100})},
	}
