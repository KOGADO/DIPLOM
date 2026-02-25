from rest_framework import permissions, viewsets
from rest_framework.exceptions import PermissionDenied

from core.models import Department, Group, Subject
from grading.models import Attendance, Course, Grade, Lesson, StudentCourse
from users.models import Student, Teacher

from .api_serializers import (
    AttendanceSerializer,
    CourseSerializer,
    DepartmentSerializer,
    GradeSerializer,
    GroupSerializer,
    LessonSerializer,
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
