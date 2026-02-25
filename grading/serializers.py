from rest_framework import serializers

from grading.models import Course, Grade


class GradeSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='course.subject.name', read_only=True)

    class Meta:
        model = Grade
        fields = ['id', 'subject', 'value', 'date', 'comment']


class CourseSerializer(serializers.ModelSerializer):
    subject = serializers.CharField(source='subject.name', read_only=True)
    group = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Course
        fields = ['id', 'subject', 'group', 'semester', 'year']
