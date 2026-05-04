from rest_framework import serializers

from core.models import Department, Group, Subject
from grading.models import Attendance, Course, Grade, Lesson, StudentCourse
from users.models import Parent, Student, Teacher
from users.models import ChatDialog, ChatMessage


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = "__all__"


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = "__all__"


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = "__all__"


class TeacherSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Teacher
        fields = "__all__"


class StudentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Student
        fields = "__all__"


class ParentSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.get_full_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Parent
        fields = "__all__"


class ChatMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)

    class Meta:
        model = ChatMessage
        fields = ["id", "chat", "sender", "sender_name", "sender_role", "message", "attachment", "created_at", "is_read"]
        read_only_fields = ["chat", "sender", "sender_role", "created_at", "is_read"]


class ChatDialogSerializer(serializers.ModelSerializer):
    related_grade_info = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    unread_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatDialog
        fields = [
            "id",
            "student",
            "teacher",
            "related_grade",
            "related_grade_info",
            "title",
            "created_at",
            "updated_at",
            "last_message",
            "unread_count",
        ]
        read_only_fields = ["student", "created_at", "updated_at", "related_grade_info", "last_message", "unread_count"]

    def get_related_grade_info(self, obj) -> dict | None:
        grade = obj.related_grade
        if not grade:
            return None
        return {
            "id": grade.id,
            "subject": str(grade.course.subject),
            "grade_type": grade.get_grade_type_display(),
            "value": grade.value,
            "date": grade.date,
        }

    def get_last_message(self, obj) -> dict | None:
        message = obj.messages.order_by("-created_at").first()
        if not message:
            return None
        return {
            "id": message.id,
            "message": message.message,
            "created_at": message.created_at,
            "sender_role": message.sender_role,
        }

    def get_unread_count(self, obj) -> int:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return 0
        return obj.messages.filter(is_read=False).exclude(sender=request.user).count()


class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = "__all__"


class StudentCourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCourse
        fields = "__all__"


class LessonSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lesson
        fields = "__all__"


class AttendanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Attendance
        fields = "__all__"


class GradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Grade
        fields = "__all__"
