def role_flags(request):
    user = request.user
    if not user.is_authenticated:
        return {
            'is_admin': False,
            'is_teacher': False,
            'is_student': False,
            'is_parent': False,
            'is_student_only': False,
            'is_parent_only': False,
            'student_profile_id': None,
            'display_name': '',
        }

    is_admin = user.is_superuser or user.groups.filter(name='Admin').exists()
    is_teacher = user.groups.filter(name='Teacher').exists()
    is_student = user.groups.filter(name='Student').exists()
    is_parent = user.groups.filter(name='Parent').exists()

    student_profile_id = None
    if is_student:
        try:
            student_profile_id = user.student_profile.id
        except Exception:
            student_profile_id = None

    display_name = user.get_full_name().strip() or user.username

    return {
        'is_admin': is_admin,
        'is_teacher': is_teacher,
        'is_student': is_student,
        'is_parent': is_parent,
        'is_student_only': is_student and not is_teacher and not is_admin,
        'is_parent_only': is_parent and not is_student and not is_teacher and not is_admin,
        'student_profile_id': student_profile_id,
        'display_name': display_name,
    }
