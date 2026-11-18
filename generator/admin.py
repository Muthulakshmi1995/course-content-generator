from django.contrib import admin
from .models import CourseTopic, GeneratedContent, Quiz, Question, Answer, Summary

class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 0

class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0

@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ("title", "topic", "created_at")
    inlines = [QuestionInline]

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("question_text", "quiz")
    inlines = [AnswerInline]

admin.site.register(CourseTopic)
admin.site.register(GeneratedContent)
admin.site.register(Summary)
