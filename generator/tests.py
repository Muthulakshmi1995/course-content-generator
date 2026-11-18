import json
from unittest.mock import patch
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from .models import CourseTopic, GeneratedContent, Quiz, Question, Answer, Summary

User = get_user_model()

class CourseModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="StrongPass123!")
        self.topic = CourseTopic.objects.create(title="Python Basics", teacher=self.user)

    def test_topic_create_update_delete(self):
        self.assertEqual(self.topic.title, "Python Basics")
        self.topic.title = "Advanced Python"
        self.topic.save()
        self.assertEqual(CourseTopic.objects.get(pk=self.topic.pk).title, "Advanced Python")
        pk = self.topic.pk
        self.topic.delete()
        self.assertFalse(CourseTopic.objects.filter(pk=pk).exists())

    def test_related_models_create_update_delete(self):
        quiz = Quiz.objects.create(topic=self.topic, title="Quiz", description="Test")
        question = Question.objects.create(quiz=quiz, question_text="What is Python?")
        answer = Answer.objects.create(question=question, answer_text="A language", is_correct=True)
        content = GeneratedContent.objects.create(topic=self.topic, quiz=quiz, notes="Notes", key_points="Point")
        summary = Summary.objects.create(topic=self.topic, summary_text="Summary")
        answer.answer_text = "Programming language"
        answer.save()
        self.assertEqual(answer.answer_text, "Programming language")
        self.assertEqual(content.topic, self.topic)
        self.assertEqual(summary.topic, self.topic)
        quiz.delete()
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())
        self.assertFalse(Answer.objects.filter(pk=answer.pk).exists())
        self.assertIsNone(GeneratedContent.objects.get(pk=content.pk).quiz)

class ViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="teacher", password="StrongPass123!")
        self.client.login(username="teacher", password="StrongPass123!")
        self.topic = CourseTopic.objects.create(title="Django", teacher=self.user)

    def sample_payload(self):
        return {
            "notes": "Django notes", "keyPoints": ["MTV architecture", "ORM"],
            "summary": "Django is a Python web framework.",
            "quiz": {"title": "Django Quiz", "description": "Test",
                     "questions": [{"questionText": "Django uses which language?",
                                    "options": [{"text": "Python", "isCorrect": True},
                                                {"text": "Java", "isCorrect": False}]}]}
        }

    @patch("generator.views.generate_course_payload")
    def test_generate_content_saves_everything(self, mocked):
        mocked.return_value = self.sample_payload()
        response = self.client.post(reverse("generate_content"), {"title": "Django"})
        self.assertEqual(response.status_code, 302)
        topic = CourseTopic.objects.get(title="Django", teacher=self.user)
        self.assertTrue(topic.generated_contents.exists())
        self.assertTrue(topic.quizzes.first().questions.first().answers.exists())
        self.assertTrue(topic.summaries.exists())

    def test_student_dashboard_and_content(self):
        GeneratedContent.objects.create(topic=self.topic, notes="Notes", key_points="Point")
        self.assertEqual(self.client.get(reverse("student_dashboard")).status_code, 200)
        self.assertEqual(self.client.get(reverse("view_content", args=[self.topic.pk])).status_code, 200)

    def test_quiz_submission_score(self):
        quiz = Quiz.objects.create(topic=self.topic, title="Quiz")
        q = Question.objects.create(quiz=quiz, question_text="2+2?")
        correct = Answer.objects.create(question=q, answer_text="4", is_correct=True)
        Answer.objects.create(question=q, answer_text="5", is_correct=False)
        response = self.client.post(reverse("submit_quiz", args=[self.topic.pk]),
                                    {f"question_{q.pk}": str(correct.pk)})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "100%")

    def test_export_pdf(self):
        GeneratedContent.objects.create(topic=self.topic, notes="Notes", key_points="One\\nTwo")
        response = self.client.get(reverse("export_pdf", args=[self.topic.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment", response["Content-Disposition"])

    def test_quiz_and_answer_delete_cascade(self):
        quiz = Quiz.objects.create(topic=self.topic, title="Quiz")
        question = Question.objects.create(quiz=quiz, question_text="Q")
        answer = Answer.objects.create(question=question, answer_text="A")
        quiz.delete()
        self.assertFalse(Question.objects.filter(pk=question.pk).exists())
        self.assertFalse(Answer.objects.filter(pk=answer.pk).exists())
