from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from core.models import Department, Group, Subject
from grading.models import Attendance, Course, Grade, Lesson, StudentCourse
from users.models import ChatDialog, ChatMessage, Parent, Student, Teacher

from .api_serializers import (
    AttendanceSerializer,
    ChatDialogSerializer,
    ChatMessageSerializer,
    CourseSerializer,
    DepartmentSerializer,
    GradeSerializer,
    GroupSerializer,
    LessonSerializer,
    ParentSerializer,
    StudentCourseSerializer,
    StudentSerializer,
    SubjectSerializer,
    TeacherSerializer,
)


def is_admin(user):
    return user.is_superuser or user.groups.filter(name="Admin").exists()


def is_teacher(user):
    return user.groups.filter(name="Teacher").exists()


def is_student(user):
    return user.groups.filter(name="Student").exists()


def is_parent(user):
    return user.groups.filter(name="Parent").exists()


class RoleWritePermission(permissions.IsAuthenticated):
    teacher_can_write = False

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        return is_teacher(request.user) and getattr(view, "teacher_can_write", False)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if is_admin(request.user):
            return True
        checker = getattr(view, "can_teacher_write_obj", None)
        return bool(checker and checker(obj))


class RoleFilteredViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleWritePermission]
    teacher_can_write = False

    def _teacher(self):
        return Teacher.objects.filter(user=self.request.user).first()


def chat_role(user):
    if Teacher.objects.filter(user=user).exists():
        return ChatMessage.SenderRole.TEACHER
    if Student.objects.filter(user=user).exists():
        return ChatMessage.SenderRole.STUDENT
    return ""


def can_access_chat(user, chat):
    return is_admin(user) or chat.student.user_id == user.id or chat.teacher.user_id == user.id


class ChatDialogViewSet(viewsets.ModelViewSet):
    serializer_class = ChatDialogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ChatDialog.objects.select_related(
            "student__user",
            "teacher__user",
            "related_grade__course__subject",
        ).prefetch_related("messages")
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(teacher__user=user)
        if is_student(user):
            return qs.filter(student__user=user)
        return qs.none()

    def perform_create(self, serializer):
        student = Student.objects.filter(user=self.request.user).first()
        if not student:
            raise PermissionDenied("Создавать чаты может только студент")
        teacher = serializer.validated_data["teacher"]
        related_grade = serializer.validated_data.get("related_grade")
        if related_grade:
            if related_grade.student_id != student.id:
                raise PermissionDenied("Нет доступа к этой оценке")
            if related_grade.course.teacher_id != teacher.id:
                raise PermissionDenied("Оценка относится к другому преподавателю")
        if not Course.objects.filter(group=student.group, teacher=teacher).exists():
            raise PermissionDenied("Можно писать только преподавателям своих курсов")
        serializer.save(student=student)

    @action(detail=True, methods=["get", "post"])
    def messages(self, request, pk=None):
        chat = self.get_object()
        if not can_access_chat(request.user, chat):
            raise PermissionDenied("Нет доступа к диалогу")
        if request.method == "GET":
            chat.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
            serializer = ChatMessageSerializer(chat.messages.select_related("sender"), many=True, context={"request": request})
            return Response(serializer.data)

        role = chat_role(request.user)
        if not role:
            raise PermissionDenied("Нет роли для отправки сообщений")
        serializer = ChatMessageSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(chat=chat, sender=request.user, sender_role=role, is_read=False)
        chat.save(update_fields=["updated_at"])
        return Response(ChatMessageSerializer(message, context={"request": request}).data, status=status.HTTP_201_CREATED)


class ChatMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ChatMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = ChatMessage.objects.select_related("chat__student__user", "chat__teacher__user", "sender")
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(chat__teacher__user=user)
        if is_student(user):
            return qs.filter(chat__student__user=user)
        return qs.none()

    @action(detail=True, methods=["patch"])
    def read(self, request, pk=None):
        message = self.get_object()
        if message.sender_id != request.user.id:
            message.is_read = True
            message.save(update_fields=["is_read"])
        return Response(ChatMessageSerializer(message, context={"request": request}).data)


class DepartmentViewSet(RoleFilteredViewSet):
    queryset = Department.objects.all().order_by("name")
    serializer_class = DepartmentSerializer


class GroupViewSet(RoleFilteredViewSet):
    queryset = Group.objects.select_related("department", "curator").order_by("name")
    serializer_class = GroupSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(courses__teacher__user=user).distinct()
        if is_student(user):
            return qs.filter(students__user=user).distinct()
        if is_parent(user):
            return qs.filter(students__parents__user=user).distinct()
        return qs.none()


class SubjectViewSet(RoleFilteredViewSet):
    queryset = Subject.objects.select_related("department").order_by("name")
    serializer_class = SubjectSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(courses__teacher__user=user).distinct()
        if is_student(user):
            return qs.filter(courses__students__user=user).distinct()
        if is_parent(user):
            return qs.filter(courses__students__parents__user=user).distinct()
        return qs.none()


class TeacherViewSet(RoleFilteredViewSet):
    queryset = Teacher.objects.select_related("user", "department").order_by("user__last_name", "user__first_name")
    serializer_class = TeacherSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(user=user)
        if is_student(user):
            return qs.filter(courses__students__user=user).distinct()
        if is_parent(user):
            return qs.filter(courses__students__parents__user=user).distinct()
        return qs.none()


class StudentViewSet(RoleFilteredViewSet):
    queryset = Student.objects.select_related("user", "group").order_by("user__last_name", "user__first_name")
    serializer_class = StudentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(courses__teacher__user=user).distinct()
        if is_student(user):
            return qs.filter(user=user)
        if is_parent(user):
            return qs.filter(parents__user=user)
        return qs.none()


class ParentViewSet(RoleFilteredViewSet):
    queryset = Parent.objects.select_related("user").prefetch_related("children__user", "children__group")
    serializer_class = ParentSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_parent(user):
            return qs.filter(user=user)
        return qs.none()


class CourseViewSet(RoleFilteredViewSet):
    queryset = Course.objects.select_related("subject", "teacher__user", "group").order_by("-year", "semester")
    serializer_class = CourseSerializer
    teacher_can_write = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(teacher__user=user)
        if is_student(user):
            return qs.filter(students__user=user).distinct()
        if is_parent(user):
            return qs.filter(students__parents__user=user).distinct()
        return qs.none()

    def can_teacher_write_obj(self, obj):
        return obj.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
            return
        teacher = self._teacher()
        if not teacher:
            raise PermissionDenied("Профиль преподавателя не найден")
        serializer.save(teacher=teacher)


class StudentCourseViewSet(RoleFilteredViewSet):
    queryset = StudentCourse.objects.select_related("student__user", "course__teacher__user", "course__group")
    serializer_class = StudentCourseSerializer
    teacher_can_write = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(course__teacher__user=user)
        if is_student(user):
            return qs.filter(student__user=user)
        if is_parent(user):
            return qs.filter(student__parents__user=user)
        return qs.none()

    def can_teacher_write_obj(self, obj):
        return obj.course.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
            return
        course = serializer.validated_data.get("course")
        if not course or course.teacher.user_id != self.request.user.id:
            raise PermissionDenied("Можно зачислять только на свои курсы")
        serializer.save()


class LessonViewSet(RoleFilteredViewSet):
    queryset = Lesson.objects.select_related("course__teacher__user", "course__subject", "course__group")
    serializer_class = LessonSerializer
    teacher_can_write = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(course__teacher__user=user)
        if is_student(user):
            return qs.filter(course__students__user=user).distinct()
        if is_parent(user):
            return qs.filter(course__students__parents__user=user).distinct()
        return qs.none()

    def can_teacher_write_obj(self, obj):
        return obj.course.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
            return
        course = serializer.validated_data.get("course")
        if not course or course.teacher.user_id != self.request.user.id:
            raise PermissionDenied("Можно создавать занятия только для своих курсов")
        serializer.save()


class AttendanceViewSet(RoleFilteredViewSet):
    queryset = Attendance.objects.select_related("lesson__course__teacher__user", "student__user")
    serializer_class = AttendanceSerializer
    teacher_can_write = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(lesson__course__teacher__user=user)
        if is_student(user):
            return qs.filter(student__user=user)
        if is_parent(user):
            return qs.filter(student__parents__user=user)
        return qs.none()

    def can_teacher_write_obj(self, obj):
        return obj.lesson.course.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
            return
        lesson = serializer.validated_data.get("lesson")
        if not lesson or lesson.course.teacher.user_id != self.request.user.id:
            raise PermissionDenied("Можно отмечать посещаемость только на своих занятиях")
        serializer.save()


class GradeViewSet(RoleFilteredViewSet):
    queryset = Grade.objects.select_related("course__teacher__user", "student__user")
    serializer_class = GradeSerializer
    teacher_can_write = True

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if is_admin(user):
            return qs
        if is_teacher(user):
            return qs.filter(course__teacher__user=user)
        if is_student(user):
            return qs.filter(student__user=user)
        if is_parent(user):
            return qs.filter(student__parents__user=user)
        return qs.none()

    def can_teacher_write_obj(self, obj):
        return obj.course.teacher.user_id == self.request.user.id

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
            return
        course = serializer.validated_data.get("course")
        if not course or course.teacher.user_id != self.request.user.id:
            raise PermissionDenied("Можно выставлять оценки только по своим курсам")
        serializer.save()
