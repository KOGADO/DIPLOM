from django.urls import include, path
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework import routers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.reverse import reverse
from rest_framework.response import Response

from grading.api_views import MyGradesApiView, TeacherCoursesApiView
from .api_viewsets import (
    AttendanceViewSet,
    ChatDialogViewSet,
    ChatMessageViewSet,
    CourseViewSet,
    DepartmentViewSet,
    GradeViewSet,
    GroupViewSet,
    LessonViewSet,
    ParentViewSet,
    StudentCourseViewSet,
    StudentViewSet,
    SubjectViewSet,
    TeacherViewSet,
)


router = routers.DefaultRouter()
router.register("departments", DepartmentViewSet, basename="api_departments")
router.register("groups", GroupViewSet, basename="api_groups")
router.register("subjects", SubjectViewSet, basename="api_subjects")
router.register("teachers", TeacherViewSet, basename="api_teachers")
router.register("students", StudentViewSet, basename="api_students")
router.register("parents", ParentViewSet, basename="api_parents")
router.register("courses", CourseViewSet, basename="api_courses")
router.register("enrollments", StudentCourseViewSet, basename="api_enrollments")
router.register("lessons", LessonViewSet, basename="api_lessons")
router.register("attendance", AttendanceViewSet, basename="api_attendance")
router.register("grades", GradeViewSet, basename="api_grades")
router.register("chats", ChatDialogViewSet, basename="api_chats")
router.register("messages", ChatMessageViewSet, basename="api_messages")


@extend_schema(
    summary="API root",
    description="Список основных API-разделов и ссылок на них.",
    responses={200: OpenApiTypes.OBJECT},
)
@api_view(["GET"])
@permission_classes([AllowAny])
def api_root(request, format=None):
    data = {
        "my_grades": reverse("api_my_grades_v2", request=request, format=format),
        "my_courses": reverse("api_teacher_courses_v2", request=request, format=format),
        "auth": reverse("rest_framework:login", request=request, format=format),
    }
    # Expose CRUD collections from router at API root.
    for prefix, _, basename in router.registry:
        data[prefix] = reverse(f"{basename}-list", request=request, format=format)
    return Response(data)


urlpatterns = [
    path("", api_root, name="api_root"),
    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
    path("", include(router.urls)),
    path("my-grades/", MyGradesApiView.as_view(), name="api_my_grades_v2"),
    path("my-courses/", TeacherCoursesApiView.as_view(), name="api_teacher_courses_v2"),
    path("auth/", include("rest_framework.urls")),
]
