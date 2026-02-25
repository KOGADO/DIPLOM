from rest_framework import generics, permissions

from grading.models import Course, Grade
from grading.serializers import CourseSerializer, GradeSerializer


class MyGradesApiView(generics.ListAPIView):
    serializer_class = GradeSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Grade.objects.filter(student__user=self.request.user).select_related('course__subject')


class TeacherCoursesApiView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Course.objects.filter(teacher__user=self.request.user).select_related('subject', 'group')
