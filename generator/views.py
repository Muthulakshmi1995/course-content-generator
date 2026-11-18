import io
import logging
from django.contrib.auth import login
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, ListFlowable, ListItem
from xml.sax.saxutils import escape

from .forms import CourseTopicForm,StudentRegistrationForm
from .models import CourseTopic, GeneratedContent, Quiz, Question, Answer, Summary
from .services import generate_course_payload

logger = logging.getLogger(__name__)

def register(request):
    if request.method == "POST":
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(
                request,
                "Registration successful! Welcome to CourseGen AI."
            )
            return redirect("student_dashboard")
    else:
        form = StudentRegistrationForm()

    return render(
        request,
        "generator/register.html",
        {"form": form}
    )

@login_required
def generate_content(request):
    if request.method == "POST":
        form = CourseTopicForm(request.POST)
        if form.is_valid():
            try:
                payload = generate_course_payload(form.cleaned_data["title"])
                with transaction.atomic():
                    topic = form.save(commit=False)
                    topic.teacher = request.user
                    topic.save()
                    quiz_data = payload["quiz"]
                    quiz = Quiz.objects.create(
                        topic=topic,
                        title=quiz_data.get("title") or f"{topic.title} Quiz",
                        description=quiz_data.get("description", ""),
                    )
                    for question_data in quiz_data["questions"]:
                        question = Question.objects.create(
                            quiz=quiz, question_text=question_data["questionText"]
                        )
                        Answer.objects.bulk_create([
                            Answer(question=question, answer_text=option["text"],
                                   is_correct=bool(option["isCorrect"]))
                            for option in question_data["options"]
                        ])
                    GeneratedContent.objects.create(
                        topic=topic, quiz=quiz,
                        notes=payload["notes"],
                        key_points="\n".join(str(p) for p in payload["keyPoints"]),
                    )
                    Summary.objects.create(topic=topic, summary_text=payload["summary"])
                messages.success(request, "Course notes, summary and quiz generated successfully.")
                return redirect("view_content", topic_id=topic.pk)
            except Exception as exc:
                logger.exception("Course generation failed")
                messages.error(request, f"Could not generate course content: {exc}")
    else:
        form = CourseTopicForm()
    return render(request, "generator/generate_content.html", {"form": form})

@login_required
def student_dashboard(request):
    topics = CourseTopic.objects.select_related("teacher").prefetch_related(
        "generated_contents", "summaries"
    )
    return render(request, "generator/student_dashboard.html", {"topics": topics})

@login_required
def view_content(request, topic_id):
    topic = get_object_or_404(CourseTopic.objects.select_related("teacher"), pk=topic_id)
    content = topic.generated_contents.order_by("-created_at").first()
    summary = topic.summaries.order_by("-created_at").first()
    quiz = content.quiz if content and content.quiz_id else topic.quizzes.order_by("-created_at").first()
    if quiz:
        quiz = Quiz.objects.prefetch_related("questions__answers").get(pk=quiz.pk)
    return render(request, "generator/view_content.html", {
        "topic": topic, "content": content, "summary": summary, "quiz": quiz,
    })

@login_required
@require_POST
def submit_quiz(request, topic_id):
    topic = get_object_or_404(CourseTopic, pk=topic_id)
    quiz = topic.quizzes.order_by("-created_at").first()
    if not quiz:
        messages.error(request, "No quiz is available for this topic.")
        return redirect("view_content", topic_id=topic.pk)
    questions = list(quiz.questions.prefetch_related("answers").all())
    results, score = [], 0
    for question in questions:
        selected_id = request.POST.get(f"question_{question.pk}")
        selected = question.answers.filter(pk=selected_id).first() if selected_id else None
        correct = question.answers.filter(is_correct=True).first()
        is_right = bool(selected and selected.is_correct)
        score += int(is_right)
        results.append({
            "question": question, "selected": selected, "correct": correct,
            "is_correct": is_right,
        })
    return render(request, "generator/quiz_results.html", {
        "topic": topic, "score": score, "total": len(questions),
        "percentage": round(score * 100 / len(questions)) if questions else 0,
        "results": results,
    })

@login_required
def export_pdf(request, topic_id):
    topic = get_object_or_404(CourseTopic.objects.select_related("teacher"), pk=topic_id)
    content = topic.generated_contents.order_by("-created_at").first()
    summary = topic.summaries.order_by("-created_at").first()
    quiz = content.quiz if content and content.quiz_id else topic.quizzes.order_by("-created_at").first()
    if not content:
        messages.error(request, "Study notes are not available for PDF export.")
        return redirect("view_content", topic_id=topic.pk)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("CoverTitle", parent=styles["Title"], alignment=TA_CENTER,
                                 textColor=colors.HexColor("#17365D"), spaceAfter=18)
    story = [
        Spacer(1, 55*mm),
        Paragraph(escape(topic.title), title_style),
        Paragraph(f"Prepared by: {escape(topic.teacher.get_full_name() or topic.teacher.username)}",
                  ParagraphStyle("Teacher", parent=styles["Normal"], alignment=TA_CENTER)),
        Spacer(1, 8*mm),
        Paragraph("Course Study Material", ParagraphStyle("Subtitle", parent=styles["Heading2"],
                                                           alignment=TA_CENTER)),
        PageBreak(),
    ]
    if summary:
        story += [Paragraph("Summary", styles["Heading1"]),
                  Paragraph(escape(summary.summary_text).replace("\\n", "<br/>"), styles["BodyText"]),
                  Spacer(1, 8)]
    story += [Paragraph("Study Notes", styles["Heading1"]),
              Paragraph(escape(content.notes).replace("\\n", "<br/>"), styles["BodyText"]),
              Spacer(1, 8), Paragraph("Key Points", styles["Heading1"])]
    key_points = [p.strip(" •-*\\t") for p in content.key_points.splitlines() if p.strip()]
    if key_points:
        story.append(ListFlowable([ListItem(Paragraph(escape(p), styles["BodyText"])) for p in key_points],
                                  bulletType="bullet", leftIndent=18))
    if quiz:
        story += [PageBreak(), Paragraph("Practice Quiz", styles["Heading1"]),
                  Paragraph(escape(quiz.title), styles["Heading2"]),
                  Paragraph(escape(quiz.description), styles["BodyText"]), Spacer(1, 6)]
        for index, question in enumerate(quiz.questions.prefetch_related("answers").all(), 1):
            story.append(Paragraph(f"{index}. {escape(question.question_text)}", styles["Heading3"]))
            for answer in question.answers.all():
                suffix = " (Correct answer)" if answer.is_correct else ""
                story.append(Paragraph("• " + escape(answer.answer_text) + suffix, styles["BodyText"]))
            story.append(Spacer(1, 5))
    doc.build(story)
    buffer.seek(0)
    filename = f"{topic.title[:45].replace(' ', '_')}_study_material.pdf"
    return FileResponse(buffer, as_attachment=True, filename=filename, content_type="application/pdf")
