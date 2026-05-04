# eft_app/views.py - COMPLETE FIXED FILE

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction as db_transaction, connection
from django.db.models import Sum, Count, Q
from django.db.utils import OperationalError, DatabaseError
from django.views.decorators.http import require_POST
from django.contrib.auth.models import Group, User
from django.utils.safestring import mark_safe
from django.conf import settings
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
import json
import platform
import csv
import xlwt
from datetime import datetime, timedelta
from decimal import Decimal

from .models import (
    Bank, Zone, Scheme, Supplier, DebitAccount,
    EFTBatch, EFTTransaction, ApprovalAuditLog
)
from .forms import (
    BankForm, ZoneForm, SchemeForm, SupplierForm, DebitAccountForm,
    EFTBatchForm, EFTTransactionForm, BatchApprovalForm, BatchRejectionForm,
    UserRegistrationForm, UserEditForm
)
from .eft_generator import EFTGenerator

# ================ HELPER FUNCTIONS ================

def get_user_role(user):
    if user.is_superuser:
        return 'admin'
    groups = user.groups.values_list('name', flat=True)
    if 'System Admin' in groups:
        return 'admin'
    if 'Director of Finance' in groups:
        return 'director'
    if 'Finance Manager' in groups:
        return 'finance_manager'
    if 'Accounts Personnel' in groups:
        return 'accounts'
    return 'unknown'

def format_time_ago(timestamp):
    if not timestamp:
        return 'Recently'
    now = timezone.now()
    diff = now - timestamp
    if diff.days > 0:
        return f'{diff.days} day{"s" if diff.days > 1 else ""} ago'
    elif diff.seconds >= 3600:
        hours = diff.seconds // 3600
        return f'{hours} hour{"s" if hours > 1 else ""} ago'
    elif diff.seconds >= 60:
        minutes = diff.seconds // 60
        return f'{minutes} minute{"s" if minutes > 1 else ""} ago'
    else:
        return 'Just now'

def check_database_connection():
    try:
        User.objects.count()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True, None
    except (OperationalError, DatabaseError) as e:
        return False, str(e)
    except Exception as e:
        return True, str(e)

def calculate_uptime():
    try:
        first_user = User.objects.order_by('date_joined').first()
        if first_user:
            uptime_delta = timezone.now() - first_user.date_joined
            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60
            if days > 0:
                return f"{days}d {hours}h" if hours > 0 else f"{days} day{'s' if days > 1 else ''}"
            elif hours > 0:
                return f"{hours}h {minutes}m" if minutes > 0 else f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"{minutes} minute{'s' if minutes > 1 else ''}"
        return "System initializing"
    except:
        return "1 day"

# ================ ROLE CHECK FUNCTIONS ================

def is_system_admin(user):
    return user.is_superuser or user.groups.filter(name='System Admin').exists()

def is_accounts_personnel(user):
    return user.groups.filter(name='Accounts Personnel').exists()

def is_finance_manager(user):
    return user.groups.filter(name='Finance Manager').exists()

def is_director_of_finance(user):
    return user.groups.filter(name='Director of Finance').exists()

# ================ COMMON VIEWS ================

@login_required
def dashboard(request):
    user = request.user
    if user.is_superuser or user.groups.filter(name='System Admin').exists():
        return redirect('admin_dashboard')
    elif user.groups.filter(name='Director of Finance').exists():
        return redirect('director_dashboard')
    elif user.groups.filter(name='Finance Manager').exists():
        return redirect('fm_dashboard')
    elif user.groups.filter(name='Accounts Personnel').exists():
        return redirect('accounts_dashboard')
    else:
        messages.warning(request, 'No role assigned. Contact your system administrator.')
        return redirect('logout')

# ================ SHARED VIEW BATCH — ALL ROLES ================

@login_required
def view_batch(request, batch_id):
    """
    Role-aware batch view — renders shared/view_batch.html for all roles.
    Each role gets appropriate action buttons and back URLs.
    """
    batch = get_object_or_404(EFTBatch, id=batch_id)
    user = request.user
    user_role = get_user_role(user)

    # Permission check — accounts can only see their own batches
    if user_role == 'accounts' and batch.created_by != user:
        messages.error(request, 'You can only view your own batches.')
        return redirect('accounts_dashboard')

    if user_role == 'unknown':
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')

    # Role-appropriate URLs
    if user_role == 'admin':
        dashboard_url = reverse('admin_dashboard')
        list_url = reverse('admin_dashboard')
        back_url = reverse('admin_dashboard')
    elif user_role == 'director':
        dashboard_url = reverse('director_dashboard')
        list_url = reverse('director_batch_list')
        back_url = reverse('director_review_batch', args=[batch.id]) if batch.status == 'PENDING_DIRECTOR' else reverse('director_batch_list')
    elif user_role == 'finance_manager':
        dashboard_url = reverse('fm_dashboard')
        list_url = reverse('fm_batch_list')
        back_url = reverse('fm_review_batch', args=[batch.id]) if batch.status == 'PENDING_FM' else reverse('fm_batch_list')
    else:
        dashboard_url = reverse('accounts_dashboard')
        list_url = reverse('batch_list')
        back_url = reverse('edit_batch', args=[batch.id]) if batch.status == 'DRAFT' else reverse('batch_list')

    audit_logs = batch.audit_logs.all().order_by('-timestamp')
    total_amount = sum(t.amount for t in batch.transactions.all())
    can_export = (
        user.has_perm('eft_app.can_export_eft') or
        user_role in ['accounts', 'director', 'admin']
    )
    can_preview = batch.status not in ['DRAFT', 'REJECTED']

    context = {
        'batch': batch,
        'transactions': batch.transactions.all().order_by('sequence_number'),
        'audit_logs': audit_logs,
        'total_amount': total_amount,
        'back_url': back_url,
        'dashboard_url': dashboard_url,
        'list_url': list_url,
        'user_role': user_role,
        'can_export': can_export,
        'can_preview': can_preview,
    }
    return render(request, 'shared/view_batch.html', context)


@login_required
def preview_eft_file(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id)
    user = request.user
    user_role = get_user_role(user)

    can_preview = (
        batch.created_by == user or
        user.has_perm('eft_app.can_approve_eft') or
        user.has_perm('eft_app.can_fm_review_eft') or
        user.has_perm('eft_app.can_export_eft') or
        user.is_superuser or
        user_role in ['admin', 'accounts', 'finance_manager', 'director']
    )
    if not can_preview:
        messages.error(request, 'You do not have permission to preview this file.')
        return redirect('dashboard')

    if batch.status not in ('PENDING_FM', 'PENDING_DIRECTOR', 'APPROVED', 'EXPORTED'):
        messages.error(request, 'File preview is only available once a batch has been submitted.')
        return redirect('dashboard')

    try:
        content = EFTGenerator.generate_eft_file(batch)
        lines = content.strip().split('\n')
        header = lines[0] if lines else ''
        body_rows = lines[1:] if len(lines) > 1 else []
    except Exception as e:
        messages.error(request, f'Could not generate preview: {str(e)}')
        return redirect('view_batch', batch_id=batch.id)

    if user_role == 'director':
        back_url = reverse('director_review_batch', args=[batch.id]) if batch.status == 'PENDING_DIRECTOR' else reverse('director_batch_list')
        dashboard_url = reverse('director_dashboard')
    elif user_role == 'finance_manager':
        back_url = reverse('fm_review_batch', args=[batch.id]) if batch.status == 'PENDING_FM' else reverse('fm_batch_list')
        dashboard_url = reverse('fm_dashboard')
    elif user_role == 'accounts':
        back_url = reverse('view_batch', args=[batch.id])
        dashboard_url = reverse('accounts_dashboard')
    else:
        back_url = reverse('view_batch', args=[batch.id])
        dashboard_url = reverse('admin_dashboard')

    can_export = (
        user.has_perm('eft_app.can_export_eft') or
        user_role in ['accounts', 'director', 'admin']
    )

    context = {
        'batch': batch,
        'header': header,
        'body_rows': body_rows,
        'total_lines': len(lines),
        'filename': batch.get_obdx_filename('txt'),
        'back_url': back_url,
        'dashboard_url': dashboard_url,
        'user_role': user_role,
        'can_export': can_export,
    }
    return render(request, 'shared/preview_eft_file.html', context)


@login_required
def export_batch(request, batch_id, format='txt'):
    batch = get_object_or_404(EFTBatch, id=batch_id)
    user_role = get_user_role(request.user)

    can_export = (
        request.user.has_perm('eft_app.can_export_eft') or
        user_role in ['accounts', 'director', 'admin']
    )
    if not can_export:
        messages.error(request, 'You do not have permission to export this file.')
        return redirect('view_batch', batch_id=batch.id)

    if batch.status not in ('APPROVED', 'EXPORTED'):
        messages.error(request, f'Only approved batches can be exported. Current status: {batch.get_status_display()}')
        return redirect('view_batch', batch_id=batch.id)

    if batch.get_party_id() == '000000000':
        messages.error(request, 'Cannot export: No valid debit account found.')
        return redirect('view_batch', batch_id=batch.id)

    try:
        content = EFTGenerator.generate_eft_file(batch)
    except Exception as e:
        messages.error(request, f'Export failed: {str(e)}')
        return redirect('view_batch', batch_id=batch.id)

    filename = batch.get_obdx_filename(format)
    response = HttpResponse(content, content_type='application/octet-stream')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Content-Length'] = str(len(content.encode('utf-8')))
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'

    if batch.status == 'APPROVED':
        batch.status = 'EXPORTED'
        batch.save(update_fields=['status', 'updated_at'])
        ApprovalAuditLog.objects.create(
            batch=batch,
            action='EXPORTED',
            user=request.user,
            remarks=f'Exported as {filename}',
            ip_address=request.META.get('REMOTE_ADDR'),
        )

    return response

# ================ SYSTEM ADMIN VIEWS ================

@login_required
@user_passes_test(is_system_admin)
def admin_dashboard(request):
    try:
        db_connected, db_error = check_database_connection()
        stats = {}
        try:
            stats = {
                'users_count': User.objects.count(),
                'active_users_count': User.objects.filter(is_active=True).count(),
                'banks_count': Bank.objects.count(),
                'suppliers_count': Supplier.objects.count(),
                'zones_count': Zone.objects.count(),
                'schemes_count': Scheme.objects.count(),
                'debit_accounts_count': DebitAccount.objects.count(),
            }
        except (OperationalError, DatabaseError):
            stats = {k: 0 for k in ['users_count', 'active_users_count', 'banks_count',
                                      'suppliers_count', 'zones_count', 'schemes_count', 'debit_accounts_count']}
        uptime = calculate_uptime()
        today = timezone.now().date()
        today_batches_count = 0
        last_batch = None
        try:
            today_batches_count = EFTBatch.objects.filter(created_at__date=today).count()
            last_batch = EFTBatch.objects.order_by('-created_at').first()
        except (OperationalError, DatabaseError):
            pass
        context = {
            'stats': stats, 'db_connected': db_connected,
            'db_error': db_error if not db_connected else None,
            'uptime': uptime, 'today_batches_count': today_batches_count,
            'last_batch': last_batch, 'current_date': timezone.now(),
            'python_version': platform.python_version(), 'django_version': '5.0.6',
            'debug': settings.DEBUG,
        }
        return render(request, 'admin/dashboard.html', context)
    except Exception as e:
        context = {
            'stats': {k: 0 for k in ['users_count', 'active_users_count', 'banks_count',
                                       'suppliers_count', 'zones_count', 'schemes_count', 'debit_accounts_count']},
            'db_connected': False, 'db_error': str(e), 'uptime': '1 day',
            'today_batches_count': 0, 'last_batch': None, 'current_date': timezone.now(),
            'python_version': 'Unknown', 'django_version': 'Unknown', 'debug': settings.DEBUG,
        }
        return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_system_admin)
def api_system_activity(request):
    try:
        activities = []
        db_connected, _ = check_database_connection()
        if not db_connected:
            return JsonResponse({'success': False, 'error': 'Database not connected', 'activities': []})
        try:
            for user in User.objects.order_by('-date_joined')[:3]:
                activities.append({
                    'icon': 'fas fa-user-plus', 'icon_color': 'bg-success',
                    'title': 'New User Registration',
                    'description': f'User "{user.get_full_name() or user.username}" registered',
                    'time': format_time_ago(user.date_joined)
                })
        except: pass
        try:
            for bank in Bank.objects.order_by('-created_at')[:2]:
                activities.append({
                    'icon': 'fas fa-university', 'icon_color': 'bg-primary',
                    'title': 'Bank Added',
                    'description': f'Bank "{bank.bank_name}" configured',
                    'time': format_time_ago(bank.created_at) if bank.created_at else 'Recently'
                })
        except: pass
        try:
            for batch in EFTBatch.objects.filter(status__in=['APPROVED', 'EXPORTED']).order_by('-approved_at')[:3]:
                activities.append({
                    'icon': 'fas fa-file-invoice-dollar', 'icon_color': 'bg-warning',
                    'title': 'EFT Batch Approved',
                    'description': f'Batch "{batch.batch_name}" approved',
                    'time': format_time_ago(batch.approved_at) if batch.approved_at else 'Recently'
                })
        except: pass
        if not activities:
            activities.append({
                'icon': 'fas fa-info-circle', 'icon_color': 'bg-info',
                'title': 'System Ready', 'description': 'CRWB EFT System is operational',
                'time': 'Just now'
            })
        return JsonResponse({
            'success': True, 'activities': activities[:10],
            'timestamp': timezone.now().isoformat(), 'db_connected': db_connected
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e), 'activities': []}, status=500)

@login_required
@user_passes_test(is_system_admin)
def api_system_status(request):
    try:
        db_connected, db_error = check_database_connection()
        active_users = 0
        if db_connected:
            try:
                active_users = User.objects.filter(is_active=True).count()
            except: pass
        return JsonResponse({
            'success': True,
            'system_info': {
                'python_version': platform.python_version(), 'django_version': '5.0.6',
                'os': platform.system(), 'server_time': timezone.now().isoformat(),
            },
            'database_connected': db_connected,
            'database_error': db_error if not db_connected else None,
            'active_users': active_users, 'server_time': timezone.now().isoformat(),
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

# ================ USER MANAGEMENT VIEWS ================

@login_required
@user_passes_test(is_system_admin)
def user_list(request):
    users = User.objects.all().order_by('-date_joined')
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) | Q(email__icontains=query) |
            Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    role_filter = request.GET.get('role')
    if role_filter:
        if role_filter == 'Superuser':
            users = users.filter(is_superuser=True)
        elif role_filter in ['System Admin', 'Accounts Personnel', 'Finance Manager', 'Director of Finance']:
            users = users.filter(groups__name=role_filter)
    status_filter = request.GET.get('status')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    sort_field = request.GET.get('sort', 'date_joined')
    order = request.GET.get('order', 'desc')
    if sort_field in ['username', 'email', 'date_joined', 'last_login']:
        if order == 'desc':
            sort_field = f'-{sort_field}'
        users = users.order_by(sort_field)
    total_users = users.count()
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except:
        page_obj = paginator.page(1)
    context = {
        'users': page_obj, 'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'sort_field': sort_field.lstrip('-'), 'order': order,
        'total_users': total_users,
        'active_users_count': User.objects.filter(is_active=True).count(),
        'superusers_count': User.objects.filter(is_superuser=True).count(),
        'recent_logins': User.objects.filter(last_login__date=timezone.now().date()).count(),
    }
    return render(request, 'admin/user_list.html', context)

@login_required
@user_passes_test(is_system_admin)
def user_create(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.save()
                role = form.cleaned_data['role']
                group = Group.objects.get(name=role)
                user.groups.add(group)
                messages.success(request, f'User "{user.username}" created with role "{role}"')
                return redirect('user_list')
    else:
        form = UserRegistrationForm()
    return render(request, 'admin/user_form.html', {'form': form})

@login_required
@user_passes_test(is_system_admin)
def user_detail(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    context = {
        'user_obj': user_obj,
        'batches_created': EFTBatch.objects.filter(created_by=user_obj).count(),
        'approved_batches': EFTBatch.objects.filter(approved_by=user_obj).count(),
    }
    return render(request, 'admin/user_detail.html', context)

@login_required
@user_passes_test(is_system_admin)
def user_edit(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    current_role = user_obj.groups.first().name if user_obj.groups.exists() else ''
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user_obj)
        if form.is_valid():
            with db_transaction.atomic():
                user = form.save()
                role = form.cleaned_data.get('role')
                if role:
                    user.groups.clear()
                    group = Group.objects.get(name=role)
                    user.groups.add(group)
                    user.is_staff = (role == 'System Admin')
                    user.save()
                messages.success(request, f'User "{user.username}" updated successfully')
                return redirect('user_list')
    else:
        form = UserEditForm(instance=user_obj, initial={'role': current_role})
    return render(request, 'admin/user_edit.html', {
        'form': form, 'user_obj': user_obj, 'current_role': current_role
    })

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_delete(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if user_obj == request.user:
        messages.error(request, 'You cannot delete your own account')
        return redirect('user_list')
    if user_obj.is_superuser:
        messages.error(request, 'Cannot delete superuser accounts')
        return redirect('user_list')
    username = user_obj.username
    user_obj.delete()
    messages.success(request, f'User "{username}" deleted successfully')
    return redirect('user_list')

@login_required
@user_passes_test(is_system_admin)
def user_delete_confirm(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    try:
        batches_created = EFTBatch.objects.filter(created_by=user_obj).count()
        batches_approved = EFTBatch.objects.filter(approved_by=user_obj).count()
        banks_created = Bank.objects.filter(created_by=user_obj).count()
        suppliers_created = Supplier.objects.filter(created_by=user_obj).count()
    except Exception:
        batches_created = batches_approved = banks_created = suppliers_created = 0
    context = {
        'user_obj': user_obj, 'batches_created': batches_created,
        'batches_approved': batches_approved, 'banks_created': banks_created,
        'suppliers_created': suppliers_created,
        'has_activity': any([batches_created > 0, batches_approved > 0, banks_created > 0, suppliers_created > 0]),
    }
    if request.method == 'POST':
        return user_delete(request, user_id)
    return render(request, 'admin/user_confirm_delete.html', context)

@login_required
@user_passes_test(is_system_admin)
def user_reset_password(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        if new_password == confirm_password:
            user_obj.set_password(new_password)
            user_obj.save()
            messages.success(request, f'Password reset for "{user_obj.username}"')
            return redirect('user_list')
        else:
            messages.error(request, 'Passwords do not match')
    return render(request, 'admin/user_reset_password.html', {'user_obj': user_obj})

@login_required
@user_passes_test(is_system_admin)
def user_toggle_status(request, user_id):
    user_obj = get_object_or_404(User, id=user_id)
    if user_obj == request.user:
        messages.error(request, 'You cannot change your own status')
        return redirect('user_list')
    if user_obj.is_superuser:
        messages.error(request, 'Cannot change status of superuser')
        return redirect('user_list')
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    messages.success(request, f'User "{user_obj.username}" {"activated" if user_obj.is_active else "deactivated"}')
    next_url = request.POST.get('next', request.GET.get('next', 'user_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_users(request):
    format = request.GET.get('format', 'csv')
    users = User.objects.all().order_by('-date_joined')
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="users.csv"'
        writer = csv.writer(response)
        writer.writerow(['Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login', 'Date Joined'])
        for user in users:
            role = 'Superuser' if user.is_superuser else (user.groups.first().name if user.groups.exists() else 'No Role')
            writer.writerow([
                user.username, user.get_full_name(), user.email, role,
                'Active' if user.is_active else 'Inactive',
                user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never',
                user.date_joined.strftime('%Y-%m-%d')
            ])
        return response
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="users.xls"'
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Users')
        for col_num, col in enumerate(['Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login', 'Date Joined']):
            ws.write(0, col_num, col)
        for row_num, user in enumerate(users, 1):
            role = 'Superuser' if user.is_superuser else (user.groups.first().name if user.groups.exists() else 'No Role')
            ws.write(row_num, 0, user.username)
            ws.write(row_num, 1, user.get_full_name() or '')
            ws.write(row_num, 2, user.email or '')
            ws.write(row_num, 3, role)
            ws.write(row_num, 4, 'Active' if user.is_active else 'Inactive')
            ws.write(row_num, 5, user.last_login.strftime('%Y-%m-%d %H:%M') if user.last_login else 'Never')
            ws.write(row_num, 6, user.date_joined.strftime('%Y-%m-%d'))
        wb.save(response)
        return response
    return redirect('user_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_bulk_activate(request):
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    users.update(is_active=True)
    messages.success(request, f'{users.count()} user(s) activated')
    return redirect(request.POST.get('next', 'user_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_bulk_deactivate(request):
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    users.update(is_active=False)
    messages.success(request, f'{users.count()} user(s) deactivated')
    return redirect(request.POST.get('next', 'user_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_bulk_delete(request):
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    count = users.count()
    users.delete()
    messages.success(request, f'{count} user(s) deleted')
    return redirect(request.POST.get('next', 'user_list'))

# ================ BANK CRUD VIEWS ================

class BankListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Bank
    template_name = 'admin/bank_list.html'
    context_object_name = 'banks'
    permission_required = 'eft_app.view_bank'
    paginate_by = 20
    def get_queryset(self):
        queryset = Bank.objects.all().select_related('created_by')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(bank_name__icontains=query) | Q(swift_code__icontains=query))
        status = self.request.GET.get('status')
        if status == 'active': queryset = queryset.filter(is_active=True)
        elif status == 'inactive': queryset = queryset.filter(is_active=False)
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        if sort_field in ['bank_name', 'swift_code', 'is_active', 'created_at']:
            if order == 'desc': sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'active_banks_count': Bank.objects.filter(is_active=True).count(),
            'total_users_count': User.objects.filter(is_active=True).count(),
        })
        return context

class BankCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Bank
    form_class = BankForm
    template_name = 'admin/bank_form.html'
    permission_required = 'eft_app.add_bank'
    success_url = reverse_lazy('bank_list')
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Bank created successfully')
        return super().form_valid(form)

class BankDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Bank
    template_name = 'admin/bank_detail.html'
    permission_required = 'eft_app.view_bank'
    context_object_name = 'bank'

class BankUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Bank
    form_class = BankForm
    template_name = 'admin/bank_form.html'
    permission_required = 'eft_app.change_bank'
    success_url = reverse_lazy('bank_list')
    def form_valid(self, form):
        messages.success(self.request, 'Bank updated successfully')
        return super().form_valid(form)

class BankDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Bank
    template_name = 'admin/bank_confirm_delete.html'
    permission_required = 'eft_app.delete_bank'
    success_url = reverse_lazy('bank_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Bank deleted successfully')
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(is_system_admin)
def bank_toggle_status(request, pk):
    bank = get_object_or_404(Bank, pk=pk)
    bank.is_active = not bank.is_active
    bank.save()
    messages.success(request, f'Bank "{bank.bank_name}" {"activated" if bank.is_active else "deactivated"}')
    return redirect(request.POST.get('next', request.GET.get('next', 'bank_list')))

@login_required
@user_passes_test(is_system_admin)
def export_banks(request):
    format = request.GET.get('format', 'csv')
    banks = Bank.objects.all().order_by('bank_name')
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="banks.csv"'
        writer = csv.writer(response)
        writer.writerow(['Bank Name', 'SWIFT Code', 'Status', 'Created By', 'Created At'])
        for bank in banks:
            writer.writerow([
                bank.bank_name, bank.swift_code,
                'Active' if bank.is_active else 'Inactive',
                bank.created_by.get_full_name() or bank.created_by.username if bank.created_by else 'N/A',
                bank.created_at.strftime('%Y-%m-%d') if bank.created_at else 'N/A'
            ])
        return response
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="banks.xls"'
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Banks')
        for col_num, col in enumerate(['Bank Name', 'SWIFT Code', 'Status', 'Created By', 'Created At']):
            ws.write(0, col_num, col)
        for row_num, bank in enumerate(banks, 1):
            ws.write(row_num, 0, bank.bank_name)
            ws.write(row_num, 1, bank.swift_code)
            ws.write(row_num, 2, 'Active' if bank.is_active else 'Inactive')
            ws.write(row_num, 3, bank.created_by.get_full_name() or bank.created_by.username if bank.created_by else 'N/A')
            ws.write(row_num, 4, bank.created_at.strftime('%Y-%m-%d') if bank.created_at else 'N/A')
        wb.save(response)
        return response
    return redirect('bank_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_activate(request):
    bank_ids = request.POST.getlist('bank_ids')
    Bank.objects.filter(id__in=bank_ids).update(is_active=True)
    messages.success(request, f'{len(bank_ids)} bank(s) activated')
    return redirect(request.POST.get('next', 'bank_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_deactivate(request):
    bank_ids = request.POST.getlist('bank_ids')
    Bank.objects.filter(id__in=bank_ids).update(is_active=False)
    messages.success(request, f'{len(bank_ids)} bank(s) deactivated')
    return redirect(request.POST.get('next', 'bank_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_delete(request):
    bank_ids = request.POST.getlist('bank_ids')
    count = Bank.objects.filter(id__in=bank_ids).delete()[0]
    messages.success(request, f'{count} bank(s) deleted')
    return redirect(request.POST.get('next', 'bank_list'))

# ================ ZONE CRUD VIEWS ================

class ZoneListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Zone
    template_name = 'admin/zone_list.html'
    context_object_name = 'zones'
    permission_required = 'eft_app.view_zone'
    paginate_by = 20
    def get_queryset(self):
        queryset = Zone.objects.all()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(zone_code__icontains=query) | Q(zone_name__icontains=query))
        status = self.request.GET.get('status')
        if status == 'active': queryset = queryset.filter(is_active=True)
        elif status == 'inactive': queryset = queryset.filter(is_active=False)
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        if sort_field in ['zone_code', 'zone_name', 'is_active', 'created_at']:
            if order == 'desc': sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'active_zones_count': Zone.objects.filter(is_active=True).count(),
        })
        return context

class ZoneCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Zone
    form_class = ZoneForm
    template_name = 'admin/zone_form.html'
    permission_required = 'eft_app.add_zone'
    success_url = reverse_lazy('zone_list')
    def form_valid(self, form):
        messages.success(self.request, 'Zone created successfully')
        return super().form_valid(form)

class ZoneDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Zone
    template_name = 'admin/zone_detail.html'
    permission_required = 'eft_app.view_zone'
    context_object_name = 'zone'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['schemes'] = self.get_object().schemes.all()
        return context

class ZoneUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Zone
    form_class = ZoneForm
    template_name = 'admin/zone_form.html'
    permission_required = 'eft_app.change_zone'
    success_url = reverse_lazy('zone_list')
    def form_valid(self, form):
        messages.success(self.request, 'Zone updated successfully')
        return super().form_valid(form)

class ZoneDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Zone
    template_name = 'admin/zone_confirm_delete.html'
    permission_required = 'eft_app.delete_zone'
    success_url = reverse_lazy('zone_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Zone deleted successfully')
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(is_system_admin)
def zone_toggle_status(request, pk):
    zone = get_object_or_404(Zone, pk=pk)
    zone.is_active = not zone.is_active
    zone.save()
    messages.success(request, f'Zone "{zone.zone_name}" {"activated" if zone.is_active else "deactivated"}')
    return redirect(request.POST.get('next', 'zone_list'))

@login_required
@user_passes_test(is_system_admin)
def export_zones(request):
    zones = Zone.objects.all().order_by('zone_code')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="zones.csv"'
    writer = csv.writer(response)
    writer.writerow(['Zone Code', 'Zone Name', 'Description', 'Status', 'Created At'])
    for zone in zones:
        writer.writerow([
            zone.zone_code, zone.zone_name, zone.description or '',
            'Active' if zone.is_active else 'Inactive',
            zone.created_at.strftime('%Y-%m-%d') if zone.created_at else 'N/A'
        ])
    return response

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_activate(request):
    Zone.objects.filter(id__in=request.POST.getlist('zone_ids')).update(is_active=True)
    messages.success(request, 'Zones activated')
    return redirect(request.POST.get('next', 'zone_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_deactivate(request):
    Zone.objects.filter(id__in=request.POST.getlist('zone_ids')).update(is_active=False)
    messages.success(request, 'Zones deactivated')
    return redirect(request.POST.get('next', 'zone_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_delete(request):
    count = Zone.objects.filter(id__in=request.POST.getlist('zone_ids')).delete()[0]
    messages.success(request, f'{count} zone(s) deleted')
    return redirect(request.POST.get('next', 'zone_list'))

# ================ SUPPLIER CRUD VIEWS ================

class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Supplier
    template_name = 'admin/supplier_list.html'
    context_object_name = 'suppliers'
    permission_required = 'eft_app.view_supplier'
    paginate_by = 20
    def get_queryset(self):
        queryset = Supplier.objects.all().select_related('bank', 'created_by')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(supplier_code__icontains=query) | Q(supplier_name__icontains=query) |
                Q(account_number__icontains=query) | Q(account_name__icontains=query)
            )
        bank_id = self.request.GET.get('bank')
        if bank_id: queryset = queryset.filter(bank_id=bank_id)
        status = self.request.GET.get('status')
        if status == 'active': queryset = queryset.filter(is_active=True)
        elif status == 'inactive': queryset = queryset.filter(is_active=False)
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        if sort_field in ['supplier_code', 'supplier_name', 'is_active', 'created_at']:
            if order == 'desc': sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_suppliers = Supplier.objects.all()
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'all_banks': Bank.objects.all(),
            'total_suppliers': all_suppliers.count(),
            'active_suppliers': all_suppliers.filter(is_active=True).count(),
            'bank_count': all_suppliers.values('bank').distinct().count(),
            'payment_count': EFTTransaction.objects.count(),
        })
        return context

class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'admin/supplier_form.html'
    permission_required = 'eft_app.add_supplier'
    success_url = reverse_lazy('supplier_list')
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        messages.success(self.request, 'Supplier created successfully')
        return super().form_valid(form)

class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Supplier
    template_name = 'admin/supplier_detail.html'
    permission_required = 'eft_app.view_supplier'
    context_object_name = 'supplier'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_object()
        transactions = EFTTransaction.objects.filter(supplier=supplier).select_related('batch', 'scheme')
        context.update({
            'transactions': transactions[:10],
            'total_payments': transactions.count(),
            'total_amount': transactions.aggregate(Sum('amount'))['amount__sum'] or 0,
        })
        return context

class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Supplier
    form_class = SupplierForm
    template_name = 'admin/supplier_form.html'
    permission_required = 'eft_app.change_supplier'
    success_url = reverse_lazy('supplier_list')
    def form_valid(self, form):
        messages.success(self.request, 'Supplier updated successfully')
        return super().form_valid(form)

class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Supplier
    template_name = 'admin/supplier_confirm_delete.html'
    permission_required = 'eft_app.delete_supplier'
    success_url = reverse_lazy('supplier_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Supplier deleted successfully')
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(is_system_admin)
def supplier_toggle_status(request, pk):
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save()
    messages.success(request, f'Supplier "{supplier.supplier_name}" {"activated" if supplier.is_active else "deactivated"}')
    return redirect(request.POST.get('next', 'supplier_list'))

@login_required
@user_passes_test(is_system_admin)
def export_suppliers(request):
    suppliers = Supplier.objects.all().select_related('bank', 'created_by').order_by('supplier_name')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Supplier Code', 'Supplier Name', 'Bank', 'Account Number', 'Account Name', 'Status'])
    for s in suppliers:
        writer.writerow([
            s.supplier_code, s.supplier_name, s.bank.bank_name if s.bank else 'N/A',
            s.account_number, s.account_name, 'Active' if s.is_active else 'Inactive'
        ])
    return response

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_activate(request):
    Supplier.objects.filter(id__in=request.POST.getlist('supplier_ids')).update(is_active=True)
    messages.success(request, 'Suppliers activated')
    return redirect(request.POST.get('next', 'supplier_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_deactivate(request):
    Supplier.objects.filter(id__in=request.POST.getlist('supplier_ids')).update(is_active=False)
    messages.success(request, 'Suppliers deactivated')
    return redirect(request.POST.get('next', 'supplier_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_delete(request):
    count = Supplier.objects.filter(id__in=request.POST.getlist('supplier_ids')).delete()[0]
    messages.success(request, f'{count} supplier(s) deleted')
    return redirect(request.POST.get('next', 'supplier_list'))

# ================ SCHEME CRUD VIEWS ================

class SchemeListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Scheme
    template_name = 'admin/scheme_list.html'
    context_object_name = 'schemes'
    permission_required = 'eft_app.view_scheme'
    paginate_by = 20
    def get_queryset(self):
        queryset = Scheme.objects.all().select_related('zone')
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(Q(scheme_code__icontains=query) | Q(scheme_name__icontains=query))
        zone_id = self.request.GET.get('zone')
        if zone_id: queryset = queryset.filter(zone_id=zone_id)
        status = self.request.GET.get('status')
        if status == 'active': queryset = queryset.filter(is_active=True)
        elif status == 'inactive': queryset = queryset.filter(is_active=False)
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        if sort_field in ['scheme_code', 'scheme_name', 'is_active', 'created_at']:
            if order == 'desc': sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        return queryset
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_schemes = Scheme.objects.all()
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'all_zones': Zone.objects.all(),
            'total_schemes': all_schemes.count(),
            'active_schemes_count': all_schemes.filter(is_active=True).count(),
            'zones_count': all_schemes.values('zone').distinct().count(),
            'transactions_count': EFTTransaction.objects.count(),
        })
        return context

class SchemeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'admin/scheme_form.html'
    permission_required = 'eft_app.add_scheme'
    success_url = reverse_lazy('scheme_list')
    def form_valid(self, form):
        messages.success(self.request, f'Scheme "{form.cleaned_data["scheme_name"]}" created.')
        return super().form_valid(form)

class SchemeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Scheme
    template_name = 'admin/scheme_detail.html'
    permission_required = 'eft_app.view_scheme'
    context_object_name = 'scheme'

class SchemeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'admin/scheme_form.html'
    permission_required = 'eft_app.change_scheme'
    success_url = reverse_lazy('scheme_list')
    def form_valid(self, form):
        messages.success(self.request, 'Scheme updated successfully')
        return super().form_valid(form)

class SchemeDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Scheme
    template_name = 'admin/scheme_confirm_delete.html'
    permission_required = 'eft_app.delete_scheme'
    success_url = reverse_lazy('scheme_list')
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Scheme deleted successfully')
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(is_system_admin)
def scheme_toggle_status(request, pk):
    scheme = get_object_or_404(Scheme, pk=pk)
    scheme.is_active = not scheme.is_active
    scheme.save()
    messages.success(request, f'Scheme "{scheme.scheme_name}" {"activated" if scheme.is_active else "deactivated"}')
    return redirect(request.POST.get('next', 'scheme_list'))

@login_required
@user_passes_test(is_system_admin)
def export_schemes(request):
    schemes = Scheme.objects.all().select_related('zone').order_by('scheme_code')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="schemes.csv"'
    writer = csv.writer(response)
    writer.writerow(['Scheme Code', 'Scheme Name', 'Zone', 'Default Cost Center', 'Status'])
    for scheme in schemes:
        writer.writerow([
            scheme.scheme_code, scheme.scheme_name,
            f"{scheme.zone.zone_code} - {scheme.zone.zone_name}" if scheme.zone else 'N/A',
            scheme.default_cost_center or '', 'Active' if scheme.is_active else 'Inactive'
        ])
    return response

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_activate(request):
    Scheme.objects.filter(id__in=request.POST.getlist('scheme_ids')).update(is_active=True)
    messages.success(request, 'Schemes activated')
    return redirect(request.POST.get('next', 'scheme_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_deactivate(request):
    Scheme.objects.filter(id__in=request.POST.getlist('scheme_ids')).update(is_active=False)
    messages.success(request, 'Schemes deactivated')
    return redirect(request.POST.get('next', 'scheme_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_delete(request):
    count = Scheme.objects.filter(id__in=request.POST.getlist('scheme_ids')).delete()[0]
    messages.success(request, f'{count} scheme(s) deleted')
    return redirect(request.POST.get('next', 'scheme_list'))

# ================ DEBIT ACCOUNT CRUD VIEWS ================

class DebitAccountListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = DebitAccount
    template_name = 'admin/debit_account_list.html'
    context_object_name = 'debit_accounts'
    permission_required = 'eft_app.view_debitaccount'
    paginate_by = 20

class DebitAccountCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DebitAccount
    form_class = DebitAccountForm
    template_name = 'admin/debit_account_form.html'
    permission_required = 'eft_app.add_debitaccount'
    success_url = reverse_lazy('debit_account_list')
    def form_valid(self, form):
        messages.success(self.request, 'Debit Account created successfully')
        return super().form_valid(form)

class DebitAccountUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DebitAccount
    form_class = DebitAccountForm
    template_name = 'admin/debit_account_form.html'
    permission_required = 'eft_app.change_debitaccount'
    success_url = reverse_lazy('debit_account_list')

class DebitAccountDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DebitAccount
    template_name = 'admin/debit_account_confirm_delete.html'
    permission_required = 'eft_app.delete_debitaccount'
    success_url = reverse_lazy('debit_account_list')

@login_required
@user_passes_test(is_system_admin)
def debit_account_toggle_status(request, pk):
    account = get_object_or_404(DebitAccount, pk=pk)
    account.is_active = not account.is_active
    account.save()
    messages.success(request, f'Debit Account {"activated" if account.is_active else "deactivated"}')
    return redirect(request.POST.get('next', 'debit_account_list'))

@login_required
@user_passes_test(is_system_admin)
def export_debit_accounts(request):
    accounts = DebitAccount.objects.all().order_by('account_number')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="debit_accounts.csv"'
    writer = csv.writer(response)
    writer.writerow(['Account Number', 'Account Name', 'Description', 'Status'])
    for account in accounts:
        writer.writerow([
            account.account_number, account.account_name, account.description or '',
            'Active' if account.is_active else 'Inactive'
        ])
    return response

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_activate(request):
    DebitAccount.objects.filter(id__in=request.POST.getlist('account_ids')).update(is_active=True)
    messages.success(request, 'Accounts activated')
    return redirect(request.POST.get('next', 'debit_account_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_deactivate(request):
    DebitAccount.objects.filter(id__in=request.POST.getlist('account_ids')).update(is_active=False)
    messages.success(request, 'Accounts deactivated')
    return redirect(request.POST.get('next', 'debit_account_list'))

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_delete(request):
    count = DebitAccount.objects.filter(id__in=request.POST.getlist('account_ids')).delete()[0]
    messages.success(request, f'{count} account(s) deleted')
    return redirect(request.POST.get('next', 'debit_account_list'))

# ================ ACCOUNTS PERSONNEL VIEWS ================

@login_required
@user_passes_test(is_accounts_personnel)
def accounts_dashboard(request):
    user = request.user
    batches = EFTBatch.objects.filter(created_by=user)
    pending_fm = batches.filter(status='PENDING_FM').count()
    pending_dir = batches.filter(status='PENDING_DIRECTOR').count()
    stats = {
        'total_batches': batches.count(),
        'draft_batches': batches.filter(status='DRAFT').count(),
        'pending_fm_batches': pending_fm,
        'pending_director_batches': pending_dir,
        'approved_batches': batches.filter(status__in=['APPROVED', 'EXPORTED']).count(),
        'rejected_batches': batches.filter(status='REJECTED').count(),
        'exported_batches': batches.filter(status='EXPORTED').count(),
        'total_amount': batches.filter(status__in=['APPROVED', 'EXPORTED']).aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    recent_batches = batches.order_by('-created_at')[:10]
    return render(request, 'accounts/dashboard.html', {'stats': stats, 'recent_batches': recent_batches})

@login_required
@user_passes_test(is_accounts_personnel)
def batch_list(request):
    batches = EFTBatch.objects.filter(created_by=request.user).order_by('-created_at')
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        # If filtering by APPROVED, also include EXPORTED batches
        if status_filter == 'APPROVED':
            batches = batches.filter(status__in=['APPROVED', 'EXPORTED'])
        else:
            batches = batches.filter(status=status_filter)
    
    search = request.GET.get('search')
    if search:
        batches = batches.filter(Q(batch_reference__icontains=search) | Q(batch_name__icontains=search))
    
    total_amount = batches.filter(status__in=['APPROVED', 'EXPORTED']).aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    all_my_batches = EFTBatch.objects.filter(created_by=request.user)
    
    paginator = Paginator(batches, 20)
    page = request.GET.get('page')
    try:
        page_obj = paginator.page(page)
    except:
        page_obj = paginator.page(1)
    
    context = {
        'batches': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_filter': status_filter,
        'total_batches': batches.count(),
        'total_amount': total_amount,
        'draft_count': all_my_batches.filter(status='DRAFT').count(),
        'pending_fm_count': all_my_batches.filter(status='PENDING_FM').count(),
        'pending_director_count': all_my_batches.filter(status='PENDING_DIRECTOR').count(),
        'approved_count': all_my_batches.filter(status__in=['APPROVED', 'EXPORTED']).count(),
        'rejected_count': all_my_batches.filter(status='REJECTED').count(),
        'can_delete_any': batches.filter(status='DRAFT').exists(),
    }
    return render(request, 'accounts/batch_list.html', context)

@login_required
@user_passes_test(is_accounts_personnel)
def create_batch(request):
    if request.method == 'POST':
        form = EFTBatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.created_by = request.user
            batch.save()
            messages.success(request, mark_safe(
                f'EFT batch created. Reference: <code>{batch.batch_reference}</code>'
            ))
            return redirect('edit_batch', batch_id=batch.id)
    else:
        form = EFTBatchForm()
    return render(request, 'accounts/create_batch.html', {'form': form})

@login_required
@user_passes_test(is_accounts_personnel)
def edit_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    if batch.status != 'DRAFT':
        messages.error(request, 'Cannot edit a batch that is not in DRAFT status.')
        return redirect('accounts_dashboard')
    transactions = batch.transactions.all().order_by('sequence_number')
    if request.method == 'POST':
        form = EFTBatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch updated')
            return redirect('edit_batch', batch_id=batch.id)
    else:
        form = EFTBatchForm(instance=batch)
    return render(request, 'accounts/edit_batch.html', {
        'batch': batch, 'transactions': transactions, 'form': form,
        'transaction_form': EFTTransactionForm(),
        'total_amount': sum(t.amount for t in transactions)
    })

@login_required
@user_passes_test(is_accounts_personnel)
def add_transaction(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    if batch.status != 'DRAFT':
        return JsonResponse({'success': False, 'message': 'Batch not in DRAFT status'})
    if request.method == 'POST':
        form = EFTTransactionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                transaction = form.save(commit=False)
                transaction.batch = batch
                last_seq = batch.transactions.order_by('sequence_number').last()
                transaction.sequence_number = str(int(last_seq.sequence_number) + 1 if last_seq else 1).zfill(4)
                transaction.zone = transaction.scheme.zone
                transaction.save()
                batch.update_totals()
                return JsonResponse({
                    'success': True, 'message': 'Transaction added',
                    'batch_total': str(batch.total_amount), 'record_count': batch.record_count
                })
        return JsonResponse({'success': False, 'errors': form.errors.get_json_data()})
    return JsonResponse({'success': False})

@login_required
@user_passes_test(is_accounts_personnel)
def delete_transaction(request, batch_id, transaction_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    if batch.status != 'DRAFT':
        return JsonResponse({'success': False, 'message': 'Batch not in DRAFT status'})
    transaction = get_object_or_404(EFTTransaction, id=transaction_id, batch=batch)
    transaction.delete()
    batch.update_totals()
    for idx, t in enumerate(batch.transactions.all().order_by('id'), 1):
        t.sequence_number = str(idx).zfill(4)
        t.save()
    return JsonResponse({'success': True, 'batch_total': str(batch.total_amount), 'record_count': batch.record_count})

@login_required
@user_passes_test(is_accounts_personnel)
def submit_for_approval(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    if batch.status != 'DRAFT':
        messages.error(request, 'Only DRAFT batches can be submitted.')
        return redirect('view_batch', batch_id=batch.id)
    if batch.transactions.count() == 0:
        messages.error(request, 'Cannot submit an empty batch.')
        return redirect('edit_batch', batch_id=batch.id)
    batch.status = 'PENDING_FM'
    batch.save()
    ApprovalAuditLog.objects.create(batch=batch, action='SUBMITTED', user=request.user, ip_address=request.META.get('REMOTE_ADDR'))
    messages.success(request, 'Batch submitted to Finance Manager for review.')
    return redirect('accounts_dashboard')

@login_required
@require_POST
def delete_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    if batch.status != 'DRAFT':
        messages.error(request, 'Only DRAFT batches can be deleted.')
        return redirect('batch_list')
    batch.delete()
    messages.success(request, 'Batch deleted.')
    return redirect('batch_list')

@login_required
@user_passes_test(is_accounts_personnel)
def export_batch_details(request, batch_id):
    return redirect('export_batch', batch_id=batch_id, format='csv')

@login_required
@user_passes_test(is_accounts_personnel)
def batch_export_all(request):
    format = request.GET.get('format', 'csv')
    batches = EFTBatch.objects.filter(created_by=request.user).order_by('-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="my_batches.csv"'
    writer = csv.writer(response)
    writer.writerow(['Batch Reference', 'Batch Name', 'File Type', 'Status', 'Records', 'Total Amount (MWK)', 'Created'])
    for batch in batches:
        writer.writerow([
            batch.batch_reference, batch.batch_name, batch.get_file_type_display(),
            batch.get_status_display(), batch.record_count, str(batch.total_amount),
            batch.created_at.strftime('%Y-%m-%d')
        ])
    return response

@login_required
@user_passes_test(is_accounts_personnel)
def batch_export_selected(request):
    batch_ids = request.GET.getlist('batch_ids')
    if not batch_ids:
        messages.error(request, 'No batches selected')
        return redirect('batch_list')
    batches = EFTBatch.objects.filter(id__in=batch_ids, created_by=request.user).order_by('-created_at')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="selected_batches.csv"'
    writer = csv.writer(response)
    writer.writerow(['Batch Reference', 'Batch Name', 'Status', 'Records', 'Total Amount (MWK)', 'Created'])
    for batch in batches:
        writer.writerow([
            batch.batch_reference, batch.batch_name, batch.get_status_display(),
            batch.record_count, str(batch.total_amount), batch.created_at.strftime('%Y-%m-%d')
        ])
    return response

@login_required
@user_passes_test(is_accounts_personnel)
@require_POST
def batch_bulk_delete(request):
    batch_ids = request.POST.getlist('batch_ids')
    count = EFTBatch.objects.filter(id__in=batch_ids, created_by=request.user, status='DRAFT').delete()[0]
    messages.success(request, f'{count} draft batch(es) deleted')
    return redirect(request.POST.get('next', 'batch_list'))

# ================ FINANCE MANAGER VIEWS ================

@login_required
@user_passes_test(is_finance_manager)
def fm_dashboard(request):
    pending = EFTBatch.objects.filter(status='PENDING_FM').order_by('-created_at')
    recent = EFTBatch.objects.filter(
        status__in=['PENDING_DIRECTOR', 'APPROVED', 'REJECTED', 'EXPORTED'],
        fm_reviewed_by=request.user
    ).order_by('-fm_reviewed_at')[:10]
    
    stats = {
        'pending_count': pending.count(),
        'forwarded_today': EFTBatch.objects.filter(
            status='PENDING_DIRECTOR', fm_reviewed_at__date=timezone.now().date(), fm_reviewed_by=request.user
        ).count(),
        'total_forwarded': EFTBatch.objects.filter(
            fm_reviewed_by=request.user, status__in=['PENDING_DIRECTOR', 'APPROVED', 'EXPORTED']
        ).count(),
        'total_rejected': EFTBatch.objects.filter(fm_reviewed_by=request.user, status='REJECTED').count(),
    }
    return render(request, 'finance_manager/fm_dashboard.html', {
        'pending_batches': pending, 'recent_batches': recent, 'stats': stats
    })

@login_required
@user_passes_test(is_finance_manager)
def fm_batch_list(request):
    batches = EFTBatch.objects.exclude(status='DRAFT').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        # If filtering by APPROVED, also include EXPORTED batches
        if status_filter == 'APPROVED':
            batches = batches.filter(status__in=['APPROVED', 'EXPORTED'])
        else:
            batches = batches.filter(status=status_filter)
    
    # Calculate counts for the filter tabs
    approved_count = EFTBatch.objects.filter(status__in=['APPROVED', 'EXPORTED']).count()
    exported_count = EFTBatch.objects.filter(status='EXPORTED').count()
    pending_fm_count = EFTBatch.objects.filter(status='PENDING_FM').count()
    
    return render(request, 'finance_manager/batch_list.html', {
        'batches': batches,
        'status_filter': status_filter,
        'pending_fm_count': pending_fm_count,
        'approved_count': approved_count,
        'exported_count': exported_count,
    })

@login_required
@user_passes_test(is_finance_manager)
def fm_review_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING_FM')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot review your own batch.')
        return redirect('fm_dashboard')
    return render(request, 'finance_manager/review_batch.html', {
        'batch': batch,
        'transactions': batch.transactions.all().order_by('sequence_number'),
        'audit_logs': batch.audit_logs.all().order_by('timestamp'),
        'approval_form': BatchApprovalForm(),
        'rejection_form': BatchRejectionForm(),
        'total_amount': sum(t.amount for t in batch.transactions.all()),
    })

@login_required
@user_passes_test(is_finance_manager)
def fm_forward_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING_FM')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot forward your own batch.')
        return redirect('fm_dashboard')
    if request.method == 'POST':
        form = BatchApprovalForm(request.POST)
        if form.is_valid():
            batch.status = 'PENDING_DIRECTOR'
            batch.fm_reviewed_by = request.user
            batch.fm_reviewed_at = timezone.now()
            batch.fm_remarks = form.cleaned_data.get('remarks', '')
            batch.save()
            ApprovalAuditLog.objects.create(
                batch=batch, action='FM_REVIEWED', user=request.user,
                remarks=batch.fm_remarks, ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Batch {batch.batch_reference} forwarded to Director of Finance.')
            return redirect('fm_dashboard')
    return redirect('fm_review_batch', batch_id=batch_id)

@login_required
@user_passes_test(is_finance_manager)
def fm_reject_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING_FM')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot reject your own batch.')
        return redirect('fm_dashboard')
    if request.method == 'POST':
        form = BatchRejectionForm(request.POST)
        if form.is_valid():
            batch.status = 'REJECTED'
            batch.rejection_reason = form.cleaned_data['rejection_reason']
            batch.fm_reviewed_by = request.user
            batch.fm_reviewed_at = timezone.now()
            batch.save()
            ApprovalAuditLog.objects.create(
                batch=batch, action='FM_REJECTED', user=request.user,
                remarks=batch.rejection_reason, ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Batch {batch.batch_reference} has been rejected.')
            return redirect('fm_dashboard')
    return redirect('fm_review_batch', batch_id=batch_id)

# ================ DIRECTOR OF FINANCE VIEWS ================

@login_required
@user_passes_test(is_director_of_finance)
def director_dashboard(request):
    pending = EFTBatch.objects.filter(status='PENDING_DIRECTOR').order_by('-created_at')
    recent = EFTBatch.objects.filter(
        status__in=['APPROVED', 'REJECTED', 'EXPORTED'], approved_by=request.user
    ).order_by('-approved_at')[:10]
    
    stats = {
        'pending_count': pending.count(),
        'approved_today': EFTBatch.objects.filter(
            status__in=['APPROVED', 'EXPORTED'], approved_at__date=timezone.now().date(), approved_by=request.user
        ).count(),
        'total_approved': EFTBatch.objects.filter(approved_by=request.user, status__in=['APPROVED', 'EXPORTED']).count(),
        'total_rejected': EFTBatch.objects.filter(approved_by=request.user, status='REJECTED').count(),
    }
    return render(request, 'director/director_dashboard.html', {
        'pending_batches': pending, 'recent_approvals': recent, 'stats': stats
    })

@login_required
@user_passes_test(is_director_of_finance)
def director_batch_list(request):
    batches = EFTBatch.objects.exclude(status='DRAFT').order_by('-created_at')
    status_filter = request.GET.get('status', '')
    
    if status_filter:
        # If filtering by APPROVED, also include EXPORTED batches
        if status_filter == 'APPROVED':
            batches = batches.filter(status__in=['APPROVED', 'EXPORTED'])
        else:
            batches = batches.filter(status=status_filter)
    
    # Calculate counts for the filter tabs
    approved_count = EFTBatch.objects.filter(status__in=['APPROVED', 'EXPORTED']).count()
    exported_count = EFTBatch.objects.filter(status='EXPORTED').count()
    pending_count = EFTBatch.objects.filter(status='PENDING_DIRECTOR').count()
    
    return render(request, 'director/batch_list.html', {
        'batches': batches,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'exported_count': exported_count,
    })

@login_required
@user_passes_test(is_director_of_finance)
def director_review_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING_DIRECTOR')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot approve your own batch.')
        return redirect('director_dashboard')
    return render(request, 'director/review_batch.html', {
        'batch': batch,
        'transactions': batch.transactions.all().order_by('sequence_number'),
        'audit_logs': batch.audit_logs.all().order_by('timestamp'),
        'approval_form': BatchApprovalForm(),
        'rejection_form': BatchRejectionForm(),
        'total_amount': sum(t.amount for t in batch.transactions.all()),
    })

@login_required
@user_passes_test(is_director_of_finance)
def director_approve_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id)
    if batch.status != 'PENDING_DIRECTOR':
        messages.error(request, f'Batch is not pending director approval. Current status: {batch.get_status_display()}')
        return redirect('director_dashboard')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot approve your own batch.')
        return redirect('director_dashboard')
    if request.method == 'POST':
        form = BatchApprovalForm(request.POST)
        if form.is_valid():
            batch.status = 'APPROVED'
            batch.approved_by = request.user
            batch.approved_at = timezone.now()
            batch.remarks = form.cleaned_data.get('remarks', '')
            batch.save()
            ApprovalAuditLog.objects.create(
                batch=batch, action='APPROVED', user=request.user,
                remarks=form.cleaned_data.get('remarks', ''),
                ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, mark_safe(
                f'Batch <strong>{batch.batch_reference}</strong> approved. Ready to export as <code>{batch.get_obdx_filename()}</code>.'
            ))
            return redirect('director_dashboard')
    return redirect('director_review_batch', batch_id=batch_id)

@login_required
@user_passes_test(is_director_of_finance)
def director_reject_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING_DIRECTOR')
    if batch.created_by == request.user:
        messages.error(request, 'You cannot reject your own batch.')
        return redirect('director_dashboard')
    if request.method == 'POST':
        form = BatchRejectionForm(request.POST)
        if form.is_valid():
            batch.status = 'REJECTED'
            batch.rejection_reason = form.cleaned_data['rejection_reason']
            batch.approved_by = request.user
            batch.approved_at = timezone.now()
            batch.save()
            ApprovalAuditLog.objects.create(
                batch=batch, action='REJECTED', user=request.user,
                remarks=batch.rejection_reason, ip_address=request.META.get('REMOTE_ADDR')
            )
            messages.success(request, f'Batch {batch.batch_reference} has been rejected.')
            return redirect('director_dashboard')
    return redirect('director_review_batch', batch_id=batch_id)

# ================ LEGACY AUTHORIZER VIEWS ================

@login_required
def authorizer_dashboard(request):
    if request.user.groups.filter(name='Finance Manager').exists():
        return redirect('fm_dashboard')
    if request.user.groups.filter(name='Director of Finance').exists():
        return redirect('director_dashboard')
    return redirect('dashboard')

@login_required
def authorizer_batch_list(request):
    batches = EFTBatch.objects.exclude(status='DRAFT').order_by('-created_at')
    return render(request, 'authorizer/batch_list.html', {'batches': batches})

@login_required
def review_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status__in=['PENDING_FM', 'PENDING_DIRECTOR'])
    if batch.created_by == request.user:
        messages.error(request, 'You cannot review your own batch.')
        return redirect('authorizer_dashboard')
    return render(request, 'authorizer/review_batch.html', {
        'batch': batch,
        'transactions': batch.transactions.all().order_by('sequence_number'),
        'total_amount': sum(t.amount for t in batch.transactions.all()),
        'approval_form': BatchApprovalForm(),
        'rejection_form': BatchRejectionForm(),
    })

@login_required
def approve_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status__in=['PENDING_FM', 'PENDING_DIRECTOR'])
    if batch.created_by == request.user:
        messages.error(request, 'You cannot approve your own batch.')
        return redirect('authorizer_dashboard')
    if request.method == 'POST':
        if batch.status == 'PENDING_FM':
            batch.status = 'PENDING_DIRECTOR'
            batch.fm_reviewed_by = request.user
            batch.fm_reviewed_at = timezone.now()
            messages.success(request, 'Batch forwarded to Director.')
        else:
            batch.status = 'APPROVED'
            batch.approved_by = request.user
            batch.approved_at = timezone.now()
            messages.success(request, 'Batch approved.')
        batch.save()
        return redirect('authorizer_dashboard')
    return redirect('review_batch', batch_id=batch_id)

@login_required
def reject_batch(request, batch_id):
    batch = get_object_or_404(EFTBatch, id=batch_id, status__in=['PENDING_FM', 'PENDING_DIRECTOR'])
    if batch.created_by == request.user:
        messages.error(request, 'You cannot reject your own batch.')
        return redirect('authorizer_dashboard')
    if request.method == 'POST':
        batch.status = 'REJECTED'
        batch.rejection_reason = request.POST.get('rejection_reason', '')
        batch.save()
        messages.success(request, 'Batch rejected.')
        return redirect('authorizer_dashboard')
    return redirect('review_batch', batch_id=batch_id)

# ================ API VIEWS ================

@login_required
def get_supplier_details(request, supplier_id):
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        return JsonResponse({
            'bank_name': supplier.bank.bank_name if supplier.bank else '',
            'swift_code': supplier.bank.swift_code if supplier.bank else '',
            'account_number': supplier.account_number,
            'account_name': supplier.account_name,
        })
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)

@login_required
def get_scheme_zone(request, scheme_id):
    try:
        try:
            scheme = Scheme.objects.get(id=int(scheme_id))
        except (ValueError, Scheme.DoesNotExist):
            scheme = Scheme.objects.get(scheme_code=scheme_id)
        return JsonResponse({
            'zone_code': scheme.zone.zone_code if scheme.zone else '',
            'zone_name': scheme.zone.zone_name if scheme.zone else '',
        })
    except Scheme.DoesNotExist:
        return JsonResponse({'error': 'Scheme not found'}, status=404)

@login_required
def get_scheme_details(request, scheme_id):
    try:
        try:
            scheme = Scheme.objects.get(id=int(scheme_id))
        except (ValueError, Scheme.DoesNotExist):
            scheme = Scheme.objects.get(scheme_code=scheme_id)
        return JsonResponse({
            'success': True,
            'zone_code': scheme.zone.zone_code if scheme.zone else '',
            'zone_name': scheme.zone.zone_name if scheme.zone else '',
            'default_cost_center': scheme.default_cost_center or '',
        })
    except Scheme.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Scheme not found'}, status=404)