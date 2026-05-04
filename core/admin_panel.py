from dataclasses import dataclass

from django import forms
from django.contrib import messages
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.core.paginator import Paginator
from django.db import models, transaction
from django.db.models import Q
from django.forms import modelform_factory
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import urlencode
from django.views import View

from core.models import AdminLog, Department, Group, Subject
from grading.models import Attendance, Course, Grade, LectureTopic, Lesson, StudentCourse
from users.models import ChatDialog, ChatMessage, Parent, Student, Teacher


@dataclass(frozen=True)
class AdminModelConfig:
    model: type[models.Model]
    list_display: tuple[str, ...] = ('id',)
    search_fields: tuple[str, ...] = ()
    list_filter: tuple[str, ...] = ()
    form_fields: tuple[str, ...] | None = None
    readonly: bool = False
    ordering: tuple[str, ...] = ()
    inlines: tuple[str, ...] = ()

    @property
    def key(self):
        return f'{self.model._meta.app_label}.{self.model._meta.model_name}'

    @property
    def title(self):
        return self.model._meta.verbose_name_plural.title()


REGISTRY = {
    'auth.user': AdminModelConfig(
        User,
        list_display=('id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff'),
        search_fields=('username', 'first_name', 'last_name', 'email'),
        list_filter=('is_active', 'is_staff', 'is_superuser', 'groups'),
        form_fields=('username', 'first_name', 'last_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        ordering=('username',),
    ),
    'auth.group': AdminModelConfig(
        AuthGroup,
        list_display=('id', 'name'),
        search_fields=('name',),
        form_fields=('name', 'permissions'),
        ordering=('name',),
    ),
    'core.department': AdminModelConfig(
        Department,
        list_display=('id', 'name'),
        search_fields=('name',),
        ordering=('name',),
        inlines=('groups', 'subjects', 'teachers'),
    ),
    'core.group': AdminModelConfig(
        Group,
        list_display=('id', 'name', 'department', 'curator', 'is_active', 'source'),
        search_fields=('name', 'curator__username', 'curator__first_name', 'curator__last_name'),
        list_filter=('department', 'curator', 'is_active', 'source'),
        ordering=('name',),
        inlines=('students', 'courses'),
    ),
    'core.subject': AdminModelConfig(
        Subject,
        list_display=('id', 'name', 'department', 'is_active', 'source'),
        search_fields=('name',),
        list_filter=('department', 'is_active', 'source'),
        ordering=('name',),
        inlines=('courses',),
    ),
    'users.teacher': AdminModelConfig(
        Teacher,
        list_display=('id', 'user', 'department', 'is_active', 'source'),
        search_fields=('user__username', 'user__first_name', 'user__last_name'),
        list_filter=('department', 'is_active', 'source'),
        inlines=('courses',),
    ),
    'users.student': AdminModelConfig(
        Student,
        list_display=('id', 'user', 'group', 'date_of_birth'),
        search_fields=('user__username', 'user__first_name', 'user__last_name', 'group__name'),
        list_filter=('group',),
        inlines=('studentcourse_set', 'grades', 'attendances'),
    ),
    'users.parent': AdminModelConfig(
        Parent,
        list_display=('id', 'user'),
        search_fields=('user__username', 'user__first_name', 'user__last_name', 'children__user__username'),
        list_filter=('children',),
        form_fields=('user', 'children'),
    ),
    'users.chatdialog': AdminModelConfig(
        ChatDialog,
        list_display=('id', 'title', 'student', 'teacher', 'related_grade', 'updated_at'),
        search_fields=('title', 'student__user__username', 'teacher__user__username'),
        list_filter=('student', 'teacher', 'related_grade'),
        inlines=('messages',),
    ),
    'users.chatmessage': AdminModelConfig(
        ChatMessage,
        list_display=('id', 'chat', 'sender', 'sender_role', 'created_at', 'is_read'),
        search_fields=('message', 'sender__username', 'chat__title'),
        list_filter=('sender_role', 'is_read', 'chat'),
    ),
    'grading.course': AdminModelConfig(
        Course,
        list_display=('id', 'subject', 'teacher', 'group', 'semester', 'year', 'is_active'),
        search_fields=('subject__name', 'teacher__user__username', 'teacher__user__first_name', 'teacher__user__last_name', 'group__name', 'semester'),
        list_filter=('subject', 'teacher', 'group', 'semester', 'is_active'),
        ordering=('-year', 'semester'),
        inlines=('studentcourse_set', 'lessons', 'grades'),
    ),
    'grading.studentcourse': AdminModelConfig(
        StudentCourse,
        list_display=('id', 'student', 'course'),
        search_fields=('student__user__username', 'student__user__first_name', 'student__user__last_name', 'course__subject__name'),
        list_filter=('course', 'student'),
    ),
    'grading.lesson': AdminModelConfig(
        Lesson,
        list_display=('id', 'course', 'date', 'topic'),
        search_fields=('topic', 'course__subject__name', 'course__group__name'),
        list_filter=('course', 'date'),
        ordering=('-date',),
        inlines=('attendances',),
    ),
    'grading.lecturetopic': AdminModelConfig(
        LectureTopic,
        list_display=('id', 'course', 'order', 'title'),
        search_fields=('title', 'course__subject__name', 'course__group__name'),
        list_filter=('course',),
        ordering=('course', 'order', 'title'),
    ),
    'grading.attendance': AdminModelConfig(
        Attendance,
        list_display=('id', 'lesson', 'student', 'status', 'comment'),
        search_fields=('student__user__username', 'student__user__first_name', 'student__user__last_name', 'comment'),
        list_filter=('status', 'lesson', 'student'),
    ),
    'grading.grade': AdminModelConfig(
        Grade,
        list_display=('id', 'student', 'course', 'grade_type', 'value', 'date', 'comment'),
        search_fields=('student__user__username', 'student__user__first_name', 'student__user__last_name', 'course__subject__name', 'comment'),
        list_filter=('course', 'student', 'grade_type', 'value', 'date'),
        ordering=('-date',),
    ),
    'core.adminlog': AdminModelConfig(
        AdminLog,
        list_display=('id', 'created_at', 'user', 'content_type', 'object_repr', 'action'),
        search_fields=('object_repr', 'user__username'),
        list_filter=('content_type', 'action', 'user'),
        readonly=True,
        ordering=('-created_at',),
    ),
}


def is_admin_user(user):
    return user.is_authenticated and (user.is_superuser or user.groups.filter(name='Admin').exists())


def model_permission(user, config, action):
    if not user.is_authenticated:
        return False
    if is_admin_user(user):
        return not (config.readonly and action in {'add', 'change', 'delete'})
    perm_map = {'view': 'view', 'add': 'add', 'change': 'change', 'delete': 'delete'}
    return user.has_perm(f'{config.model._meta.app_label}.{perm_map[action]}_{config.model._meta.model_name}')


def available_configs(user):
    return [config for config in REGISTRY.values() if model_permission(user, config, 'view')]


def get_config(key, user, action='view'):
    config = REGISTRY.get(key)
    if not config:
        raise Http404('Сущность не найдена')
    if not model_permission(user, config, action):
        raise PermissionDenied('Недостаточно прав')
    return config


def model_field(model, name):
    try:
        return model._meta.get_field(name)
    except FieldDoesNotExist:
        return None


def label_for(config, name):
    field_obj = model_field(config.model, name)
    if field_obj:
        return field_obj.verbose_name.title()
    return name.replace('_', ' ').title()


def editable_field_names(config):
    if config.form_fields is not None:
        return list(config.form_fields)
    names = []
    for field_obj in config.model._meta.get_fields():
        if not getattr(field_obj, 'editable', False):
            continue
        if field_obj.auto_created and not field_obj.concrete:
            continue
        if getattr(field_obj, 'many_to_many', False) and not field_obj.remote_field.through._meta.auto_created:
            continue
        names.append(field_obj.name)
    return names


class AdminGeneratedFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            elif isinstance(widget, forms.SelectMultiple):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')


class UserAdminForm(AdminGeneratedFormMixin, forms.ModelForm):
    password1 = forms.CharField(
        label='Новый пароль',
        required=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        help_text='Оставьте пустым, если пароль менять не нужно.',
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        required=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
    )

    class Meta:
        model = User
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'is_active',
            'is_staff',
            'is_superuser',
            'groups',
            'user_permissions',
        )

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 or password2:
            if password1 != password2:
                raise forms.ValidationError('Пароли не совпадают.')
            if len(password1) < 8:
                raise forms.ValidationError('Пароль должен быть не короче 8 символов.')
        elif not self.instance.pk:
            raise forms.ValidationError('Для нового пользователя нужно указать пароль.')
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('password1')
        if password:
            user.set_password(password)
        if commit:
            user.save()
            self.save_m2m()
        return user


def form_class_for(config):
    if config.model is User:
        return UserAdminForm

    widgets = {}
    for field_name in editable_field_names(config):
        field_obj = model_field(config.model, field_name)
        if isinstance(field_obj, models.DateField) and not isinstance(field_obj, models.DateTimeField):
            widgets[field_name] = forms.DateInput(attrs={'type': 'date'})
        if isinstance(field_obj, models.DateTimeField):
            widgets[field_name] = forms.DateTimeInput(attrs={'type': 'datetime-local'})
    base_form = modelform_factory(config.model, fields=editable_field_names(config), widgets=widgets)
    return type(f'{config.model.__name__}AdminForm', (AdminGeneratedFormMixin, base_form), {})


def object_url(obj, action='change'):
    key = f'{obj._meta.app_label}.{obj._meta.model_name}'
    if key not in REGISTRY:
        return ''
    return reverse(f'admin_panel:{action}', kwargs={'model_key': key, 'pk': obj.pk})


def display_value(obj, name):
    field_obj = model_field(obj.__class__, name)
    value = getattr(obj, name, None)
    if field_obj and field_obj.choices:
        value = getattr(obj, f'get_{name}_display')()
    if isinstance(field_obj, models.BooleanField):
        return {'text': 'Да' if value else 'Нет', 'url': ''}
    if isinstance(field_obj, (models.ForeignKey, models.OneToOneField)) and value is not None:
        return {'text': str(value), 'url': object_url(value)}
    return {'text': value if value not in (None, '') else '-', 'url': ''}


def relation_blocks(config, obj):
    blocks = []
    for relation_name in config.inlines:
        manager = getattr(obj, relation_name, None)
        if manager is None:
            continue
        rel_model = getattr(manager, 'model', None)
        rel_key = f'{rel_model._meta.app_label}.{rel_model._meta.model_name}' if rel_model else ''
        if not rel_key or rel_key not in REGISTRY:
            continue
        rows = list(manager.all()[:5])
        blocks.append(
            {
                'title': rel_model._meta.verbose_name_plural.title(),
                'count': manager.count(),
                'list_url': reverse('admin_panel:list', kwargs={'model_key': rel_key}),
                'rows': [{'text': str(row), 'url': object_url(row)} for row in rows],
            }
        )
    return blocks


def log_change(user, obj, action, changed_fields=None, object_repr=None):
    AdminLog.objects.create(
        user=user if user.is_authenticated else None,
        content_type=ContentType.objects.get_for_model(obj.__class__),
        object_id=str(obj.pk),
        object_repr=(object_repr or str(obj))[:255],
        action=action,
        changed_fields=changed_fields or {},
    )


def changed_data_map(form):
    result = {}
    for name in form.changed_data:
        if name.startswith('password'):
            result['password'] = {'before': '********', 'after': '********'}
            continue
        result[name] = {
            'before': str(form.initial.get(name, '')),
            'after': str(form.cleaned_data.get(name, '')),
        }
    return result


class AdminPanelBase(View):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        return super().dispatch(request, *args, **kwargs)

    def common_context(self, config=None):
        return {
            'admin_models': available_configs(self.request.user),
            'current_config': config,
        }


class AdminIndexView(AdminPanelBase):
    def get(self, request):
        models_list = []
        for config in available_configs(request.user):
            models_list.append(
                {
                    'config': config,
                    'count': config.model.objects.count(),
                    'list_url': reverse('admin_panel:list', kwargs={'model_key': config.key}),
                    'can_add': model_permission(request.user, config, 'add'),
                }
            )
        context = self.common_context()
        context['models_list'] = models_list
        return render(request, 'core/admin_panel/index.html', context)


class AdminModelListView(AdminPanelBase):
    paginate_by = 25

    def get(self, request, model_key):
        config = get_config(model_key, request.user, 'view')
        qs = config.model.objects.all()
        if config.ordering:
            qs = qs.order_by(*config.ordering)

        q = (request.GET.get('q') or '').strip()
        if q and config.search_fields:
            query = Q()
            for field_name in config.search_fields:
                query |= Q(**{f'{field_name}__icontains': q})
            qs = qs.filter(query)

        filter_values = {}
        for field_name in config.list_filter:
            value = request.GET.get(field_name)
            if value not in (None, ''):
                filter_values[field_name] = value
                qs = qs.filter(**{field_name: value})

        sort = request.GET.get('sort') or ''
        sort_name = sort[1:] if sort.startswith('-') else sort
        if sort_name in config.list_display and model_field(config.model, sort_name):
            qs = qs.order_by(sort)

        selected_columns = request.GET.getlist('columns') or list(config.list_display)
        selected_columns = [name for name in selected_columns if name in config.list_display]
        if not selected_columns:
            selected_columns = list(config.list_display)

        paginator = Paginator(qs, self.paginate_by)
        page_obj = paginator.get_page(request.GET.get('page') or 1)

        rows = []
        for obj in page_obj.object_list:
            rows.append(
                {
                    'obj': obj,
                    'change_url': reverse('admin_panel:change', kwargs={'model_key': model_key, 'pk': obj.pk}),
                    'delete_url': reverse('admin_panel:delete', kwargs={'model_key': model_key, 'pk': obj.pk}),
                    'history_url': reverse('admin_panel:history', kwargs={'model_key': model_key, 'pk': obj.pk}),
                    'cells': [display_value(obj, name) for name in selected_columns],
                }
            )

        filter_specs = []
        for field_name in config.list_filter:
            field_obj = model_field(config.model, field_name)
            choices = []
            if isinstance(field_obj, models.BooleanField):
                choices = [('True', 'Да'), ('False', 'Нет')]
            elif field_obj and field_obj.choices:
                choices = list(field_obj.choices)
            elif isinstance(field_obj, (models.ForeignKey, models.OneToOneField, models.ManyToManyField)):
                choices = [(str(item.pk), str(item)) for item in field_obj.related_model.objects.all()[:100]]
            filter_specs.append(
                {
                    'name': field_name,
                    'label': label_for(config, field_name),
                    'value': filter_values.get(field_name, ''),
                    'choices': choices,
                }
            )

        base_params = request.GET.copy()
        base_params.pop('page', None)
        context = self.common_context(config)
        context.update(
            {
                'config': config,
                'q': q,
                'selected_columns': selected_columns,
                'available_columns': [{'name': name, 'label': label_for(config, name)} for name in config.list_display],
                'headers': [
                    {
                        'name': name,
                        'label': label_for(config, name),
                        'sort_url': f'?{urlencode({**base_params.dict(), "sort": f"-{name}" if sort == name else name})}',
                    }
                    for name in selected_columns
                ],
                'rows': rows,
                'filter_specs': filter_specs,
                'page_obj': page_obj,
                'base_query': base_params.urlencode(),
                'add_url': reverse('admin_panel:add', kwargs={'model_key': model_key}),
                'can_add': model_permission(request.user, config, 'add'),
                'can_change': model_permission(request.user, config, 'change'),
                'can_delete': model_permission(request.user, config, 'delete'),
            }
        )
        return render(request, 'core/admin_panel/list.html', context)

    def post(self, request, model_key):
        config = get_config(model_key, request.user, 'delete')
        selected_ids = request.POST.getlist('selected')
        if request.POST.get('action') == 'bulk_delete' and selected_ids:
            with transaction.atomic():
                objects = list(config.model.objects.filter(pk__in=selected_ids))
                for obj in objects:
                    obj_repr = str(obj)
                    pk = obj.pk
                    obj.delete()
                    obj.pk = pk
                    log_change(request.user, obj, AdminLog.Action.DELETE, {'bulk': True}, object_repr=obj_repr)
            messages.success(request, f'Удалено записей: {len(objects)}')
        return HttpResponseRedirect(request.get_full_path())


class AdminObjectFormView(AdminPanelBase):
    def get_object(self, config, pk):
        if pk is None:
            return None
        return get_object_or_404(config.model, pk=pk)

    def render_form(self, request, config, obj=None):
        form = form_class_for(config)(instance=obj)
        context = self.common_context(config)
        context.update(
            {
                'config': config,
                'object': obj,
                'form': form,
                'is_add': obj is None,
                'cancel_url': reverse('admin_panel:list', kwargs={'model_key': config.key}),
                'history_url': reverse('admin_panel:history', kwargs={'model_key': config.key, 'pk': obj.pk}) if obj else '',
                'relation_blocks': relation_blocks(config, obj) if obj else [],
            }
        )
        return render(request, 'core/admin_panel/form.html', context)

    def get(self, request, model_key, pk=None):
        action = 'add' if pk is None else 'change'
        config = get_config(model_key, request.user, action)
        return self.render_form(request, config, self.get_object(config, pk))

    def post(self, request, model_key, pk=None):
        action = 'add' if pk is None else 'change'
        config = get_config(model_key, request.user, action)
        obj = self.get_object(config, pk)
        form = form_class_for(config)(request.POST, request.FILES, instance=obj)
        if not form.is_valid():
            context = self.common_context(config)
            context.update(
                {
                    'config': config,
                    'object': obj,
                    'form': form,
                    'is_add': obj is None,
                    'cancel_url': reverse('admin_panel:list', kwargs={'model_key': config.key}),
                    'history_url': reverse('admin_panel:history', kwargs={'model_key': config.key, 'pk': obj.pk}) if obj else '',
                    'relation_blocks': relation_blocks(config, obj) if obj else [],
                }
            )
            return render(request, 'core/admin_panel/form.html', context)

        with transaction.atomic():
            saved = form.save()
            if obj is None:
                log_change(request.user, saved, AdminLog.Action.CREATE, {'created': True})
                messages.success(request, 'Запись создана.')
            else:
                changes = changed_data_map(form)
                if changes:
                    log_change(request.user, saved, AdminLog.Action.UPDATE, changes)
                messages.success(request, 'Изменения сохранены.')

        if '_continue' in request.POST:
            return redirect('admin_panel:change', model_key=model_key, pk=saved.pk)
        if '_addanother' in request.POST:
            return redirect('admin_panel:add', model_key=model_key)
        return redirect('admin_panel:list', model_key=model_key)


class AdminObjectDeleteView(AdminPanelBase):
    def get(self, request, model_key, pk):
        config = get_config(model_key, request.user, 'delete')
        obj = get_object_or_404(config.model, pk=pk)
        context = self.common_context(config)
        context.update(
            {
                'config': config,
                'object': obj,
                'cancel_url': reverse('admin_panel:list', kwargs={'model_key': model_key}),
            }
        )
        return render(request, 'core/admin_panel/confirm_delete.html', context)

    def post(self, request, model_key, pk):
        config = get_config(model_key, request.user, 'delete')
        obj = get_object_or_404(config.model, pk=pk)
        obj_repr = str(obj)
        with transaction.atomic():
            obj.delete()
            obj.pk = pk
            log_change(request.user, obj, AdminLog.Action.DELETE, object_repr=obj_repr)
        messages.success(request, 'Запись удалена.')
        return redirect('admin_panel:list', model_key=model_key)


class AdminObjectHistoryView(AdminPanelBase):
    def get(self, request, model_key, pk):
        config = get_config(model_key, request.user, 'view')
        obj = get_object_or_404(config.model, pk=pk)
        content_type = ContentType.objects.get_for_model(config.model)
        logs = AdminLog.objects.filter(content_type=content_type, object_id=str(pk)).select_related('user')
        context = self.common_context(config)
        context.update(
            {
                'config': config,
                'object': obj,
                'logs': logs,
                'change_url': reverse('admin_panel:change', kwargs={'model_key': model_key, 'pk': pk})
                if model_permission(request.user, config, 'change')
                else '',
            }
        )
        return render(request, 'core/admin_panel/history.html', context)
