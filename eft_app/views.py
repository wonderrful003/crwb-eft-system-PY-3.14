# eft_app/views.py - COMPLETE FIXED VERSION WITH AUTO-COST CENTER
# Updated for Django 5.0.6 and Python 3.14
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.db import transaction as db_transaction, connection
from django.db.models import Sum, Count, Q, Avg, Max, Min
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

# ================ COMMON VIEWS ================

@login_required
def dashboard(request):
    """Role-based dashboard"""
    user = request.user
    
    if user.is_superuser or user.groups.filter(name='System Admin').exists():
        return redirect('admin_dashboard')
    elif user.groups.filter(name='Accounts Personnel').exists():
        return redirect('accounts_dashboard')
    elif user.groups.filter(name='Authorizer').exists():
        return redirect('authorizer_dashboard')
    else:
        messages.warning(request, 'No role assigned. Contact administrator.')
        return redirect('logout')

# ================ SYSTEM ADMIN VIEWS ================

def is_system_admin(user):
    """Check if user is system admin"""
    return user.is_superuser or user.groups.filter(name='System Admin').exists()

def check_database_connection():
    """Check if database is connected properly"""
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
    """Calculate system uptime based on first user registration"""
    try:
        first_user = User.objects.order_by('date_joined').first()
        if first_user:
            uptime_delta = timezone.now() - first_user.date_joined
            days = uptime_delta.days
            hours = uptime_delta.seconds // 3600
            minutes = (uptime_delta.seconds % 3600) // 60
            
            if days > 0:
                if hours > 0:
                    return f"{days}d {hours}h"
                return f"{days} day{'s' if days > 1 else ''}"
            elif hours > 0:
                if minutes > 0:
                    return f"{hours}h {minutes}m"
                return f"{hours} hour{'s' if hours > 1 else ''}"
            else:
                return f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return "System initializing"
    except:
        return "1 day"

@login_required
@user_passes_test(is_system_admin)
def admin_dashboard(request):
    """System Admin Dashboard"""
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
            stats = {
                'users_count': 0,
                'active_users_count': 0,
                'banks_count': 0,
                'suppliers_count': 0,
                'zones_count': 0,
                'schemes_count': 0,
                'debit_accounts_count': 0,
            }
        
        uptime = calculate_uptime()
        today = timezone.now().date()
        
        today_batches_count = 0
        last_batch = None
        try:
            today_batches_count = EFTBatch.objects.filter(
                created_at__date=today
            ).count()
            last_batch = EFTBatch.objects.order_by('-created_at').first()
        except (OperationalError, DatabaseError):
            pass
        
        current_date = timezone.now()
        python_version = platform.python_version()
        
        context = {
            'stats': stats,
            'db_connected': db_connected,
            'db_error': db_error if not db_connected else None,
            'uptime': uptime,
            'today_batches_count': today_batches_count,
            'last_batch': last_batch,
            'current_date': current_date,
            'python_version': python_version,
            'django_version': '5.0.6',
            'debug': settings.DEBUG,
        }
        
        return render(request, 'admin/dashboard.html', context)
        
    except Exception as e:
        context = {
            'stats': {
                'users_count': 0,
                'active_users_count': 0,
                'banks_count': 0,
                'suppliers_count': 0,
                'zones_count': 0,
                'schemes_count': 0,
                'debit_accounts_count': 0,
            },
            'db_connected': False,
            'db_error': str(e),
            'uptime': "1 day",
            'today_batches_count': 0,
            'last_batch': None,
            'current_date': timezone.now(),
            'python_version': 'Unknown',
            'django_version': 'Unknown',
            'debug': settings.DEBUG,
        }
        return render(request, 'admin/dashboard.html', context)

@login_required
@user_passes_test(is_system_admin)
def api_system_activity(request):
    """API endpoint for system activity feed"""
    try:
        activities = []
        
        db_connected, _ = check_database_connection()
        if not db_connected:
            return JsonResponse({
                'success': False,
                'error': 'Database not connected',
                'activities': []
            })
        
        try:
            recent_users = User.objects.order_by('-date_joined')[:3]
            for user in recent_users:
                activities.append({
                    'icon': 'fas fa-user-plus',
                    'icon_color': 'bg-success',
                    'title': 'New User Registration',
                    'description': f'User "{user.get_full_name() or user.username}" registered',
                    'time': format_time_ago(user.date_joined)
                })
        except:
            pass
        
        try:
            recent_banks = Bank.objects.order_by('-created_at')[:2]
            for bank in recent_banks:
                activities.append({
                    'icon': 'fas fa-university',
                    'icon_color': 'bg-primary',
                    'title': 'Bank Added',
                    'description': f'Bank "{bank.bank_name}" ({bank.code}) configured',
                    'time': format_time_ago(bank.created_at) if bank.created_at else 'Recently'
                })
        except:
            pass
        
        try:
            recent_batches = EFTBatch.objects.filter(status='APPROVED').order_by('-approved_at')[:3]
            for batch in recent_batches:
                activities.append({
                    'icon': 'fas fa-file-invoice-dollar',
                    'icon_color': 'bg-warning',
                    'title': 'EFT Batch Approved',
                    'description': f'Batch "{batch.batch_name}" approved',
                    'time': format_time_ago(batch.approved_at) if batch.approved_at else 'Recently'
                })
        except:
            pass
        
        if not activities:
            activities.append({
                'icon': 'fas fa-info-circle',
                'icon_color': 'bg-info',
                'title': 'System Ready',
                'description': 'CRWB EFT System is operational',
                'time': 'Just now'
            })
        
        activities.sort(key=lambda x: x.get('time', ''), reverse=True)
        
        return JsonResponse({
            'success': True,
            'activities': activities[:10],
            'timestamp': timezone.now().isoformat(),
            'db_connected': db_connected
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'activities': []
        }, status=500)

@login_required
@user_passes_test(is_system_admin)
def api_system_status(request):
    """API endpoint for system status"""
    try:
        db_connected, db_error = check_database_connection()
        
        active_users = 0
        if db_connected:
            try:
                active_users = User.objects.filter(is_active=True).count()
            except:
                pass
        
        system_info = {
            'python_version': platform.python_version(),
            'django_version': '5.0.6',
            'os': platform.system(),
            'server_time': timezone.now().isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'system_info': system_info,
            'database_connected': db_connected,
            'database_error': db_error if not db_connected else None,
            'active_users': active_users,
            'server_time': timezone.now().isoformat(),
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

def format_time_ago(timestamp):
    """Format timestamp as time ago"""
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

# ================ USER MANAGEMENT VIEWS ================

@login_required
@user_passes_test(is_system_admin)
def user_list(request):
    """List all system users with search and filter"""
    users = User.objects.all().order_by('-date_joined')
    
    query = request.GET.get('q')
    if query:
        users = users.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        )
    
    role_filter = request.GET.get('role')
    if role_filter:
        match role_filter:
            case 'Superuser':
                users = users.filter(is_superuser=True)
            case 'System Admin' | 'Accounts Personnel' | 'Authorizer':
                users = users.filter(groups__name=role_filter)
    
    status_filter = request.GET.get('status')
    match status_filter:
        case 'active':
            users = users.filter(is_active=True)
        case 'inactive':
            users = users.filter(is_active=False)
    
    sort_field = request.GET.get('sort', 'date_joined')
    order = request.GET.get('order', 'desc')
    
    if sort_field in ['username', 'email', 'date_joined', 'last_login']:
        if order == 'desc':
            sort_field = f'-{sort_field}'
        users = users.order_by(sort_field)
    
    total_users = users.count()
    active_users_count = users.filter(is_active=True).count()
    superusers_count = users.filter(is_superuser=True).count()
    recent_logins = users.filter(last_login__date=timezone.now().date()).count()
    
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'users': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'sort_field': sort_field.lstrip('-'),
        'order': order,
        'total_users': total_users,
        'active_users_count': active_users_count,
        'superusers_count': superusers_count,
        'recent_logins': recent_logins,
    }
    
    return render(request, 'admin/user_list.html', context)

@login_required
@user_passes_test(is_system_admin)
def user_create(request):
    """Create new user"""
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
                
                messages.success(request, f'User "{user.username}" created successfully with role "{role}"')
                return redirect('user_list')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'admin/user_form.html', {'form': form})

@login_required
@user_passes_test(is_system_admin)
def user_detail(request, user_id):
    """User detail view"""
    user_obj = get_object_or_404(User, id=user_id)
    
    batches_created = EFTBatch.objects.filter(created_by=user_obj).count()
    approved_batches = EFTBatch.objects.filter(approved_by=user_obj).count()
    
    context = {
        'user_obj': user_obj,
        'batches_created': batches_created,
        'approved_batches': approved_batches,
    }
    
    return render(request, 'admin/user_detail.html', context)

@login_required
@user_passes_test(is_system_admin)
def user_edit(request, user_id):
    """Edit existing user"""
    user_obj = get_object_or_404(User, id=user_id)
    
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
                
                messages.success(request, f'User "{user.username}" updated successfully')
                return redirect('user_list')
    else:
        initial_data = {'role': user_obj.groups.first().name if user_obj.groups.exists() else ''}
        form = UserEditForm(instance=user_obj, initial=initial_data)
    
    return render(request, 'admin/user_edit.html', {'form': form, 'user_obj': user_obj})

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_delete(request, user_id):
    """Delete user"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if user_obj == request.user:
        messages.error(request, 'You cannot delete your own account')
        return redirect('user_list')
    
    username = user_obj.username
    user_obj.delete()
    messages.success(request, f'User "{username}" deleted successfully')
    return redirect('user_list')

@login_required
@user_passes_test(is_system_admin)
def user_reset_password(request, user_id):
    """Reset user password"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')
        
        if new_password == confirm_password:
            user_obj.set_password(new_password)
            user_obj.save()
            messages.success(request, f'Password reset successfully for user "{user_obj.username}"')
            return redirect('user_list')
        else:
            messages.error(request, 'Passwords do not match')
    
    return render(request, 'admin/user_reset_password.html', {'user_obj': user_obj})

@login_required
@user_passes_test(is_system_admin)
def user_toggle_status(request, user_id):
    """Toggle user active status"""
    user_obj = get_object_or_404(User, id=user_id)
    
    if user_obj == request.user:
        messages.error(request, 'You cannot change your own status')
        return redirect('user_list')
    
    if user_obj.is_superuser:
        messages.error(request, 'Cannot change status of superuser')
        return redirect('user_list')
    
    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    
    status = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f'User "{user_obj.username}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'user_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_users(request):
    """Export users to CSV or Excel"""
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
                user.username,
                user.get_full_name(),
                user.email,
                role,
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
        
        row_num = 0
        columns = ['Username', 'Full Name', 'Email', 'Role', 'Status', 'Last Login', 'Date Joined']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for user in users:
            row_num += 1
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
    """Bulk activate users"""
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    
    users.update(is_active=True)
    messages.success(request, f'{users.count()} user(s) activated successfully')
    
    next_url = request.POST.get('next', 'user_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_bulk_deactivate(request):
    """Bulk deactivate users"""
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    
    users.update(is_active=False)
    messages.success(request, f'{users.count()} user(s) deactivated successfully')
    
    next_url = request.POST.get('next', 'user_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def user_bulk_delete(request):
    """Bulk delete users"""
    user_ids = request.POST.getlist('user_ids')
    users = User.objects.filter(id__in=user_ids, is_superuser=False).exclude(id=request.user.id)
    
    count = users.count()
    users.delete()
    messages.success(request, f'{count} user(s) deleted successfully')
    
    next_url = request.POST.get('next', 'user_list')
    return redirect(next_url)

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
            queryset = queryset.filter(
                Q(bank_name__icontains=query) |
                Q(code__icontains=query) |
                Q(swift_code__icontains=query)
            )
        
        status = self.request.GET.get('status')
        match status:
            case 'active':
                queryset = queryset.filter(is_active=True)
            case 'inactive':
                queryset = queryset.filter(is_active=False)
        
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        
        if sort_field in ['bank_name', 'code', 'is_active', 'created_at']:
            if order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        banks = self.get_queryset()
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'active_banks_count': banks.filter(is_active=True).count(),
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
    """Toggle bank active status"""
    bank = get_object_or_404(Bank, pk=pk)
    bank.is_active = not bank.is_active
    bank.save()
    
    status = "activated" if bank.is_active else "deactivated"
    messages.success(request, f'Bank "{bank.bank_name}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'bank_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_banks(request):
    """Export banks to CSV or Excel"""
    format = request.GET.get('format', 'csv')
    banks = Bank.objects.all().order_by('bank_name')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="banks.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Bank Name', 'Code', 'SWIFT Code', 'Status', 'Created By', 'Created At'])
        
        for bank in banks:
            writer.writerow([
                bank.bank_name,
                bank.code,
                bank.swift_code,
                'Active' if bank.is_active else 'Inactive',
                bank.created_by.get_full_name() or bank.created_by.username,
                bank.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="banks.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Banks')
        
        row_num = 0
        columns = ['Bank Name', 'Code', 'SWIFT Code', 'Status', 'Created By', 'Created At']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for bank in banks:
            row_num += 1
            ws.write(row_num, 0, bank.bank_name)
            ws.write(row_num, 1, bank.code or '')
            ws.write(row_num, 2, bank.swift_code)
            ws.write(row_num, 3, 'Active' if bank.is_active else 'Inactive')
            ws.write(row_num, 4, bank.created_by.get_full_name() or bank.created_by.username)
            ws.write(row_num, 5, bank.created_at.strftime('%Y-%m-%d'))
        
        wb.save(response)
        return response
    
    return redirect('bank_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_activate(request):
    """Bulk activate banks"""
    bank_ids = request.POST.getlist('bank_ids')
    Bank.objects.filter(id__in=bank_ids).update(is_active=True)
    
    messages.success(request, f'{len(bank_ids)} bank(s) activated successfully')
    next_url = request.POST.get('next', 'bank_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_deactivate(request):
    """Bulk deactivate banks"""
    bank_ids = request.POST.getlist('bank_ids')
    Bank.objects.filter(id__in=bank_ids).update(is_active=False)
    
    messages.success(request, f'{len(bank_ids)} bank(s) deactivated successfully')
    next_url = request.POST.get('next', 'bank_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def bank_bulk_delete(request):
    """Bulk delete banks"""
    bank_ids = request.POST.getlist('bank_ids')
    banks = Bank.objects.filter(id__in=bank_ids)
    
    count = banks.count()
    banks.delete()
    messages.success(request, f'{count} bank(s) deleted successfully')
    
    next_url = request.POST.get('next', 'bank_list')
    return redirect(next_url)

# ================ ZONE CRUD VIEWS ================

class ZoneListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Zone
    template_name = 'admin/zone_list.html'
    context_object_name = 'zones'
    permission_required = 'eft_app.view_zone'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Zone.objects.all().annotate(
            scheme_count=Count('schemes', distinct=True)
        )
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(zone_code__icontains=query) |
                Q(zone_name__icontains=query) |
                Q(description__icontains=query)
            )
        
        status = self.request.GET.get('status')
        match status:
            case 'active':
                queryset = queryset.filter(is_active=True)
            case 'inactive':
                queryset = queryset.filter(is_active=False)
        
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        
        if sort_field in ['zone_code', 'zone_name', 'is_active', 'created_at']:
            if order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        zones = self.get_queryset()
        total_schemes_count = zones.aggregate(total=Sum('scheme_count'))['total'] or 0
        avg_schemes_per_zone = zones.aggregate(avg=Avg('scheme_count'))['avg'] or 0
        active_zones_count = zones.filter(is_active=True).count()
        
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'total_schemes_count': total_schemes_count,
            'avg_schemes_per_zone': avg_schemes_per_zone,
            'active_zones_count': active_zones_count,
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
        zone = self.get_object()
        context['schemes'] = zone.schemes.all()
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
    """Toggle zone active status"""
    zone = get_object_or_404(Zone, pk=pk)
    zone.is_active = not zone.is_active
    zone.save()
    
    status = "activated" if zone.is_active else "deactivated"
    messages.success(request, f'Zone "{zone.zone_name}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'zone_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_zones(request):
    """Export zones to CSV or Excel"""
    format = request.GET.get('format', 'csv')
    zones = Zone.objects.all().order_by('zone_code')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="zones.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Zone Code', 'Zone Name', 'Description', 'Status', 'Created At'])
        
        for zone in zones:
            writer.writerow([
                zone.zone_code,
                zone.zone_name,
                zone.description or '',
                'Active' if zone.is_active else 'Inactive',
                zone.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="zones.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Zones')
        
        row_num = 0
        columns = ['Zone Code', 'Zone Name', 'Description', 'Status', 'Created At']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for zone in zones:
            row_num += 1
            ws.write(row_num, 0, zone.zone_code)
            ws.write(row_num, 1, zone.zone_name)
            ws.write(row_num, 2, zone.description or '')
            ws.write(row_num, 3, 'Active' if zone.is_active else 'Inactive')
            ws.write(row_num, 4, zone.created_at.strftime('%Y-%m-%d'))
        
        wb.save(response)
        return response
    
    return redirect('zone_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_activate(request):
    """Bulk activate zones"""
    zone_ids = request.POST.getlist('zone_ids')
    Zone.objects.filter(id__in=zone_ids).update(is_active=True)
    
    messages.success(request, f'{len(zone_ids)} zone(s) activated successfully')
    next_url = request.POST.get('next', 'zone_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_deactivate(request):
    """Bulk deactivate zones"""
    zone_ids = request.POST.getlist('zone_ids')
    Zone.objects.filter(id__in=zone_ids).update(is_active=False)
    
    messages.success(request, f'{len(zone_ids)} zone(s) deactivated successfully')
    next_url = request.POST.get('next', 'zone_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def zone_bulk_delete(request):
    """Bulk delete zones"""
    zone_ids = request.POST.getlist('zone_ids')
    zones = Zone.objects.filter(id__in=zone_ids)
    
    count = zones.count()
    zones.delete()
    messages.success(request, f'{count} zone(s) deleted successfully')
    
    next_url = request.POST.get('next', 'zone_list')
    return redirect(next_url)

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
                Q(supplier_code__icontains=query) |
                Q(supplier_name__icontains=query) |
                Q(account_number__icontains=query) |
                Q(account_name__icontains=query)
            )
        
        bank_id = self.request.GET.get('bank')
        if bank_id:
            queryset = queryset.filter(bank_id=bank_id)
        
        status = self.request.GET.get('status')
        match status:
            case 'active':
                queryset = queryset.filter(is_active=True)
            case 'inactive':
                queryset = queryset.filter(is_active=False)
        
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        
        if sort_field in ['supplier_code', 'supplier_name', 'is_active', 'created_at']:
            if order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        suppliers = self.get_queryset()
        total_suppliers = suppliers.count()
        active_suppliers = suppliers.filter(is_active=True).count()
        bank_count = suppliers.values('bank').distinct().count()
        
        payment_count = EFTTransaction.objects.filter(
            supplier__in=suppliers
        ).count()
        
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'all_banks': Bank.objects.all(),
            'total_suppliers': total_suppliers,
            'active_suppliers': active_suppliers,
            'bank_count': bank_count,
            'payment_count': payment_count,
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
        total_payments = transactions.count()
        total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        
        context.update({
            'transactions': transactions[:10],
            'total_payments': total_payments,
            'total_amount': total_amount,
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
    """Toggle supplier active status"""
    supplier = get_object_or_404(Supplier, pk=pk)
    supplier.is_active = not supplier.is_active
    supplier.save()
    
    status = "activated" if supplier.is_active else "deactivated"
    messages.success(request, f'Supplier "{supplier.supplier_name}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'supplier_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_suppliers(request):
    """Export suppliers to CSV or Excel"""
    format = request.GET.get('format', 'csv')
    suppliers = Supplier.objects.all().select_related('bank', 'created_by').order_by('supplier_name')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="suppliers.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Supplier Code', 'Supplier Name', 'Bank', 'Account Number', 'Account Name', 'Status', 'Created By', 'Created At'])
        
        for supplier in suppliers:
            writer.writerow([
                supplier.supplier_code,
                supplier.supplier_name,
                supplier.bank.bank_name,
                supplier.account_number,
                supplier.account_name,
                'Active' if supplier.is_active else 'Inactive',
                supplier.created_by.get_full_name() or supplier.created_by.username,
                supplier.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="suppliers.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Suppliers')
        
        row_num = 0
        columns = ['Supplier Code', 'Supplier Name', 'Bank', 'Account Number', 'Account Name', 'Status', 'Created By', 'Created At']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for supplier in suppliers:
            row_num += 1
            ws.write(row_num, 0, supplier.supplier_code)
            ws.write(row_num, 1, supplier.supplier_name)
            ws.write(row_num, 2, supplier.bank.bank_name)
            ws.write(row_num, 3, supplier.account_number)
            ws.write(row_num, 4, supplier.account_name)
            ws.write(row_num, 5, 'Active' if supplier.is_active else 'Inactive')
            ws.write(row_num, 6, supplier.created_by.get_full_name() or supplier.created_by.username)
            ws.write(row_num, 7, supplier.created_at.strftime('%Y-%m-%d'))
        
        wb.save(response)
        return response
    
    return redirect('supplier_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_activate(request):
    """Bulk activate suppliers"""
    supplier_ids = request.POST.getlist('supplier_ids')
    Supplier.objects.filter(id__in=supplier_ids).update(is_active=True)
    
    messages.success(request, f'{len(supplier_ids)} supplier(s) activated successfully')
    next_url = request.POST.get('next', 'supplier_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_deactivate(request):
    """Bulk deactivate suppliers"""
    supplier_ids = request.POST.getlist('supplier_ids')
    Supplier.objects.filter(id__in=supplier_ids).update(is_active=False)
    
    messages.success(request, f'{len(supplier_ids)} supplier(s) deactivated successfully')
    next_url = request.POST.get('next', 'supplier_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def supplier_bulk_delete(request):
    """Bulk delete suppliers"""
    supplier_ids = request.POST.getlist('supplier_ids')
    suppliers = Supplier.objects.filter(id__in=supplier_ids)
    
    count = suppliers.count()
    suppliers.delete()
    messages.success(request, f'{count} supplier(s) deleted successfully')
    
    next_url = request.POST.get('next', 'supplier_list')
    return redirect(next_url)

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
            queryset = queryset.filter(
                Q(scheme_code__icontains=query) |
                Q(scheme_name__icontains=query) |
                Q(description__icontains=query)
            )
        
        zone_id = self.request.GET.get('zone')
        if zone_id:
            queryset = queryset.filter(zone_id=zone_id)
            try:
                self.current_zone = Zone.objects.get(id=zone_id)
            except Zone.DoesNotExist:
                self.current_zone = None
        
        status = self.request.GET.get('status')
        match status:
            case 'active':
                queryset = queryset.filter(is_active=True)
            case 'inactive':
                queryset = queryset.filter(is_active=False)
        
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        
        if sort_field in ['scheme_code', 'scheme_name', 'zone', 'is_active', 'created_at']:
            if order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        schemes = self.get_queryset()
        total_schemes = schemes.count()
        active_schemes_count = schemes.filter(is_active=True).count()
        zones_count = schemes.values('zone').distinct().count()
        
        transactions_count = EFTTransaction.objects.filter(
            scheme__in=schemes
        ).count()
        
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'all_zones': Zone.objects.all(),
            'total_schemes': total_schemes,
            'active_schemes_count': active_schemes_count,
            'zones_count': zones_count,
            'transactions_count': transactions_count,
        })
        
        if hasattr(self, 'current_zone') and self.current_zone:
            context['current_zone'] = self.current_zone
        
        return context

class SchemeCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'admin/scheme_form.html'
    permission_required = 'eft_app.add_scheme'
    success_url = reverse_lazy('scheme_list')
    
    def get_initial(self):
        initial = super().get_initial()
        zone_id = self.request.GET.get('zone')
        if zone_id:
            try:
                zone = Zone.objects.get(id=zone_id)
                initial['zone'] = zone
            except Zone.DoesNotExist:
                pass
        return initial
    
    def form_valid(self, form):
        scheme_name = form.cleaned_data['scheme_name']
        messages.success(self.request, 
            mark_safe(f'Scheme "<strong>{scheme_name}</strong>" created successfully. '
                      f'<a href="{reverse("scheme_list")}" class="alert-link">View all schemes</a>')
        )
        return super().form_valid(form)

class SchemeDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = Scheme
    template_name = 'admin/scheme_detail.html'
    permission_required = 'eft_app.view_scheme'
    context_object_name = 'scheme'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        scheme = self.get_object()
        
        transactions = EFTTransaction.objects.filter(scheme=scheme).select_related('batch', 'supplier')
        total_transactions = transactions.count()
        total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0
        
        context.update({
            'transactions': transactions[:10],
            'total_transactions': total_transactions,
            'total_amount': total_amount,
        })
        
        return context

class SchemeUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Scheme
    form_class = SchemeForm
    template_name = 'admin/scheme_form.html'
    permission_required = 'eft_app.change_scheme'
    success_url = reverse_lazy('scheme_list')
    
    def form_valid(self, form):
        scheme_name = form.cleaned_data['scheme_name']
        messages.success(self.request, 
            mark_safe(f'Scheme "<strong>{scheme_name}</strong>" updated successfully. '
                      f'<a href="{reverse("scheme_list")}" class="alert-link">View all schemes</a>')
        )
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
    """Toggle scheme active status"""
    scheme = get_object_or_404(Scheme, pk=pk)
    scheme.is_active = not scheme.is_active
    scheme.save()
    
    status = "activated" if scheme.is_active else "deactivated"
    messages.success(request, f'Scheme "{scheme.scheme_name}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'scheme_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_schemes(request):
    """Export schemes to CSV or Excel"""
    format = request.GET.get('format', 'csv')
    schemes = Scheme.objects.all().select_related('zone').order_by('scheme_code')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="schemes.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Scheme Code', 'Scheme Name', 'Zone', 'Default Cost Center', 'Status', 'Created At'])
        
        for scheme in schemes:
            writer.writerow([
                scheme.scheme_code,
                scheme.scheme_name,
                f"{scheme.zone.zone_code} - {scheme.zone.zone_name}",
                scheme.default_cost_center or '',
                'Active' if scheme.is_active else 'Inactive',
                scheme.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="schemes.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Schemes')
        
        row_num = 0
        columns = ['Scheme Code', 'Scheme Name', 'Zone', 'Default Cost Center', 'Status', 'Created At']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for scheme in schemes:
            row_num += 1
            ws.write(row_num, 0, scheme.scheme_code)
            ws.write(row_num, 1, scheme.scheme_name)
            ws.write(row_num, 2, f"{scheme.zone.zone_code} - {scheme.zone.zone_name}")
            ws.write(row_num, 3, scheme.default_cost_center or '')
            ws.write(row_num, 4, 'Active' if scheme.is_active else 'Inactive')
            ws.write(row_num, 5, scheme.created_at.strftime('%Y-%m-%d'))
        
        wb.save(response)
        return response
    
    return redirect('scheme_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_activate(request):
    """Bulk activate schemes"""
    scheme_ids = request.POST.getlist('scheme_ids')
    Scheme.objects.filter(id__in=scheme_ids).update(is_active=True)
    
    messages.success(request, f'{len(scheme_ids)} scheme(s) activated successfully')
    next_url = request.POST.get('next', 'scheme_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_deactivate(request):
    """Bulk deactivate schemes"""
    scheme_ids = request.POST.getlist('scheme_ids')
    Scheme.objects.filter(id__in=scheme_ids).update(is_active=False)
    
    messages.success(request, f'{len(scheme_ids)} scheme(s) deactivated successfully')
    next_url = request.POST.get('next', 'scheme_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def scheme_bulk_delete(request):
    """Bulk delete schemes"""
    scheme_ids = request.POST.getlist('scheme_ids')
    schemes = Scheme.objects.filter(id__in=scheme_ids)
    
    count = schemes.count()
    schemes.delete()
    messages.success(request, f'{count} scheme(s) deleted successfully')
    
    next_url = request.POST.get('next', 'scheme_list')
    return redirect(next_url)

# ================ DEBIT ACCOUNT CRUD VIEWS ================

class DebitAccountListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = DebitAccount
    template_name = 'admin/debit_account_list.html'
    context_object_name = 'debit_accounts'
    permission_required = 'eft_app.view_debitaccount'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = DebitAccount.objects.all()
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(account_number__icontains=query) |
                Q(account_name__icontains=query) |
                Q(description__icontains=query)
            )
        
        status = self.request.GET.get('status')
        match status:
            case 'active':
                queryset = queryset.filter(is_active=True)
            case 'inactive':
                queryset = queryset.filter(is_active=False)
        
        sort_field = self.request.GET.get('sort', 'created_at')
        order = self.request.GET.get('order', 'desc')
        
        if sort_field in ['account_number', 'account_name', 'is_active', 'created_at']:
            if order == 'desc':
                sort_field = f'-{sort_field}'
            queryset = queryset.order_by(sort_field)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        accounts = self.get_queryset()
        total_accounts = accounts.count()
        active_accounts = accounts.filter(is_active=True).count()
        
        transactions_count = EFTBatch.objects.filter(
            debit_account__in=accounts
        ).count()
        
        context.update({
            'sort_field': self.request.GET.get('sort', 'created_at'),
            'order': self.request.GET.get('order', 'desc'),
            'total_accounts': total_accounts,
            'active_accounts': active_accounts,
            'transactions_count': transactions_count,
        })
        
        return context

class DebitAccountCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = DebitAccount
    form_class = DebitAccountForm
    template_name = 'admin/debit_account_form.html'
    permission_required = 'eft_app.add_debitaccount'
    success_url = reverse_lazy('debit_account_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Debit Account created successfully')
        return super().form_valid(form)

class DebitAccountDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    model = DebitAccount
    template_name = 'admin/debit_account_detail.html'
    permission_required = 'eft_app.view_debitaccount'
    context_object_name = 'account'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        account = self.get_object()
        
        batches = EFTBatch.objects.filter(debit_account=account).order_by('-created_at')
        total_batches = batches.count()
        total_amount = batches.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        context.update({
            'batches': batches[:10],
            'total_batches': total_batches,
            'total_amount': total_amount,
        })
        
        return context

class DebitAccountUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = DebitAccount
    form_class = DebitAccountForm
    template_name = 'admin/debit_account_form.html'
    permission_required = 'eft_app.change_debitaccount'
    success_url = reverse_lazy('debit_account_list')
    
    def form_valid(self, form):
        messages.success(self.request, 'Debit Account updated successfully')
        return super().form_valid(form)

class DebitAccountDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = DebitAccount
    template_name = 'admin/debit_account_confirm_delete.html'
    permission_required = 'eft_app.delete_debitaccount'
    success_url = reverse_lazy('debit_account_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Debit Account deleted successfully')
        return super().delete(request, *args, **kwargs)

@login_required
@user_passes_test(is_system_admin)
def debit_account_toggle_status(request, pk):
    """Toggle debit account active status"""
    account = get_object_or_404(DebitAccount, pk=pk)
    account.is_active = not account.is_active
    account.save()
    
    status = "activated" if account.is_active else "deactivated"
    messages.success(request, f'Debit Account "{account.account_name}" {status} successfully')
    
    next_url = request.POST.get('next', request.GET.get('next', 'debit_account_list'))
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
def export_debit_accounts(request):
    """Export debit accounts to CSV or Excel"""
    format = request.GET.get('format', 'csv')
    accounts = DebitAccount.objects.all().order_by('account_number')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="debit_accounts.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Account Number', 'Account Name', 'Description', 'Status', 'Created At'])
        
        for account in accounts:
            writer.writerow([
                account.account_number,
                account.account_name,
                account.description or '',
                'Active' if account.is_active else 'Inactive',
                account.created_at.strftime('%Y-%m-%d')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="debit_accounts.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Debit Accounts')
        
        row_num = 0
        columns = ['Account Number', 'Account Name', 'Description', 'Status', 'Created At']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for account in accounts:
            row_num += 1
            ws.write(row_num, 0, account.account_number)
            ws.write(row_num, 1, account.account_name)
            ws.write(row_num, 2, account.description or '')
            ws.write(row_num, 3, 'Active' if account.is_active else 'Inactive')
            ws.write(row_num, 4, account.created_at.strftime('%Y-%m-%d'))
        
        wb.save(response)
        return response
    
    return redirect('debit_account_list')

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_activate(request):
    """Bulk activate debit accounts"""
    account_ids = request.POST.getlist('account_ids')
    DebitAccount.objects.filter(id__in=account_ids).update(is_active=True)
    
    messages.success(request, f'{len(account_ids)} debit account(s) activated successfully')
    next_url = request.POST.get('next', 'debit_account_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_deactivate(request):
    """Bulk deactivate debit accounts"""
    account_ids = request.POST.getlist('account_ids')
    DebitAccount.objects.filter(id__in=account_ids).update(is_active=False)
    
    messages.success(request, f'{len(account_ids)} debit account(s) deactivated successfully')
    next_url = request.POST.get('next', 'debit_account_list')
    return redirect(next_url)

@login_required
@user_passes_test(is_system_admin)
@require_POST
def debit_account_bulk_delete(request):
    """Bulk delete debit accounts"""
    account_ids = request.POST.getlist('account_ids')
    accounts = DebitAccount.objects.filter(id__in=account_ids)
    
    count = accounts.count()
    accounts.delete()
    messages.success(request, f'{count} debit account(s) deleted successfully')
    
    next_url = request.POST.get('next', 'debit_account_list')
    return redirect(next_url)

# ================ ACCOUNTS PERSONNEL VIEWS ================

def is_accounts_personnel(user):
    """Check if user is accounts personnel"""
    return user.groups.filter(name='Accounts Personnel').exists()

@login_required
@user_passes_test(is_accounts_personnel)
def accounts_dashboard(request):
    """Accounts Personnel Dashboard"""
    user = request.user
    
    batches = EFTBatch.objects.filter(created_by=user)
    
    stats = {
        'total_batches': batches.count(),
        'draft_batches': batches.filter(status='DRAFT').count(),
        'pending_batches': batches.filter(status='PENDING').count(),
        'approved_batches': batches.filter(status='APPROVED').count(),
        'rejected_batches': batches.filter(status='REJECTED').count(),
        'total_amount': batches.filter(status='APPROVED').aggregate(Sum('total_amount'))['total_amount__sum'] or 0,
    }
    
    recent_batches = batches.order_by('-created_at')[:5]
    
    return render(request, 'accounts/dashboard.html', {
        'stats': stats,
        'recent_batches': recent_batches
    })

@login_required
@user_passes_test(is_accounts_personnel)
def batch_list(request):
    """List all batches for accounts personnel with search and filter"""
    batches = EFTBatch.objects.filter(created_by=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        batches = batches.filter(status=status_filter)
    
    search_query = request.GET.get('search')
    if search_query:
        batches = batches.filter(
            Q(batch_reference__icontains=search_query) |
            Q(batch_name__icontains=search_query)
        )
    
    total_batches = batches.count()
    total_amount = batches.aggregate(Sum('total_amount'))['total_amount__sum'] or Decimal('0')
    total_records = batches.aggregate(Sum('record_count'))['record_count__sum'] or 0
    avg_batch_size = batches.aggregate(Avg('record_count'))['record_count__avg'] or 0
    
    draft_count = EFTBatch.objects.filter(created_by=request.user, status='DRAFT').count()
    pending_count = EFTBatch.objects.filter(created_by=request.user, status='PENDING').count()
    approved_count = EFTBatch.objects.filter(created_by=request.user, status='APPROVED').count()
    rejected_count = EFTBatch.objects.filter(created_by=request.user, status='REJECTED').count()
    
    can_delete_any = batches.filter(status='DRAFT').exists()
    
    paginator = Paginator(batches, 20)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    context = {
        'batches': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'status_filter': status_filter,
        'total_count': total_batches,
        'total_batches': total_batches,
        'total_amount': total_amount,
        'total_records': total_records,
        'avg_batch_size': avg_batch_size,
        'draft_count': draft_count,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'can_delete_any': can_delete_any,
    }
    
    return render(request, 'accounts/batch_list.html', context)

@login_required
@user_passes_test(is_accounts_personnel)
def create_batch(request):
    """Create new EFT batch"""
    if request.method == 'POST':
        form = EFTBatchForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                batch = form.save(commit=False)
                batch.created_by = request.user
                batch.batch_reference = f"CRWB-{timezone.now().strftime('%Y%m%d-%H%M%S')}"
                batch.save()
                
                messages.success(request, 'EFT batch created successfully')
                return redirect('edit_batch', batch_id=batch.id)
    else:
        form = EFTBatchForm()
    
    return render(request, 'accounts/create_batch.html', {'form': form})

@login_required
@user_passes_test(is_accounts_personnel)
def edit_batch(request, batch_id):
    """Edit EFT batch (only in DRAFT status)"""
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    
    if batch.status != 'DRAFT':
        messages.error(request, 'Cannot edit batch that is not in DRAFT status')
        return redirect('accounts_dashboard')
    
    transactions = batch.transactions.all().order_by('sequence_number')
    
    if request.method == 'POST':
        form = EFTBatchForm(request.POST, instance=batch)
        if form.is_valid():
            form.save()
            messages.success(request, 'Batch updated successfully')
            return redirect('edit_batch', batch_id=batch.id)
    else:
        form = EFTBatchForm(instance=batch)
    
    transaction_form = EFTTransactionForm()
    
    return render(request, 'accounts/edit_batch.html', {
        'batch': batch,
        'transactions': transactions,
        'form': form,
        'transaction_form': transaction_form,
        'total_amount': sum(t.amount for t in transactions)
    })

@login_required
@user_passes_test(is_accounts_personnel)
def add_transaction(request, batch_id):
    """Add transaction to batch"""
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    
    if batch.status != 'DRAFT':
        return JsonResponse({
            'success': False,
            'message': 'Cannot add transactions to batch that is not in DRAFT status'
        })
    
    if request.method == 'POST':
        form = EFTTransactionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                transaction = form.save(commit=False)
                transaction.batch = batch
                
                last_seq = batch.transactions.order_by('sequence_number').last()
                if last_seq:
                    next_seq = int(last_seq.sequence_number) + 1
                else:
                    next_seq = 1
                transaction.sequence_number = str(next_seq).zfill(4)
                
                transaction.zone = transaction.scheme.zone
                
                transaction.save()
                
                batch.update_totals()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Transaction added successfully',
                    'transaction_id': transaction.id,
                    'sequence_number': transaction.sequence_number,
                    'amount': str(transaction.amount),
                    'supplier_name': transaction.supplier.supplier_name,
                    'batch_total': str(batch.total_amount),
                    'record_count': batch.record_count
                })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
@user_passes_test(is_accounts_personnel)
def delete_transaction(request, batch_id, transaction_id):
    """Delete transaction from batch"""
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    
    if batch.status != 'DRAFT':
        return JsonResponse({
            'success': False,
            'message': 'Cannot delete transactions from batch that is not in DRAFT status'
        })
    
    transaction = get_object_or_404(EFTTransaction, id=transaction_id, batch=batch)
    
    with db_transaction.atomic():
        transaction.delete()
        batch.update_totals()
        
        transactions = batch.transactions.all().order_by('id')
        for idx, trans in enumerate(transactions, 1):
            trans.sequence_number = str(idx).zfill(4)
            trans.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Transaction deleted successfully',
        'batch_total': str(batch.total_amount),
        'record_count': batch.record_count
    })

@login_required
@user_passes_test(is_accounts_personnel)
def submit_for_approval(request, batch_id):
    """Submit batch for approval"""
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    
    if batch.status != 'DRAFT':
        messages.error(request, 'Only DRAFT batches can be submitted for approval')
        return redirect('view_batch', batch_id=batch.id)
    
    if batch.transactions.count() == 0:
        messages.error(request, 'Cannot submit empty batch')
        return redirect('edit_batch', batch_id=batch.id)
    
    with db_transaction.atomic():
        batch.status = 'PENDING'
        batch.save()
        
        ApprovalAuditLog.objects.create(
            batch=batch,
            action='SUBMITTED',
            user=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, 'Batch submitted for approval successfully')
    
    return redirect('accounts_dashboard')

@login_required
@user_passes_test(is_accounts_personnel)
@require_POST
def delete_batch(request, batch_id):
    """Delete a draft batch"""
    batch = get_object_or_404(EFTBatch, id=batch_id, created_by=request.user)
    
    if batch.status != 'DRAFT':
        messages.error(request, 'Only DRAFT batches can be deleted')
        return redirect('batch_list')
    
    with db_transaction.atomic():
        batch_name = batch.batch_name
        batch.delete()
        messages.success(request, f'Batch "{batch_name}" deleted successfully')
    
    return redirect('batch_list')

@login_required
def view_batch(request, batch_id):
    """View batch details"""
    batch = get_object_or_404(EFTBatch, id=batch_id)
    
    if not (batch.created_by == request.user or 
            request.user.has_perm('eft_app.can_approve_eft') or
            request.user.is_superuser):
        messages.error(request, 'You do not have permission to view this batch')
        return redirect('dashboard')
    
    transactions = batch.transactions.all().order_by('sequence_number')
    audit_logs = batch.audit_logs.all().order_by('-timestamp')
    
    return render(request, 'accounts/view_batch.html', {
        'batch': batch,
        'transactions': transactions,
        'audit_logs': audit_logs
    })

@login_required
def export_batch(request, batch_id, format='txt'):
    """Export EFT file (only for approved batches)"""
    batch = get_object_or_404(EFTBatch, id=batch_id)
    
    if not (request.user.has_perm('eft_app.can_export_eft') and batch.status == 'APPROVED'):
        messages.error(request, 'You do not have permission to export this file or batch is not approved')
        return redirect('view_batch', batch_id=batch.id)
    
    try:
        generator = EFTGenerator()
        content = generator.generate_eft_file(batch)
        filename = f"CRWB_EFT_{batch.batch_reference}_{timezone.now().strftime('%Y%m%d_%H%M%S')}"
        
        if format == 'csv':
            response = generator.export_to_csv(content, filename)
        else:
            response = generator.export_to_txt(content, filename)
        
        ApprovalAuditLog.objects.create(
            batch=batch,
            action='EXPORTED',
            user=request.user,
            remarks=f'Exported as {format.upper()}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        return response
        
    except Exception as e:
        messages.error(request, f'Error generating file: {str(e)}')
        return redirect('view_batch', batch_id=batch.id)

@login_required
@user_passes_test(is_accounts_personnel)
def export_batch_details(request, batch_id):
    """Export batch details as PDF"""
    return redirect('export_batch', batch_id=batch_id, format='csv')

@login_required
@user_passes_test(is_accounts_personnel)
def batch_export_all(request):
    """Export all batches for the current user"""
    format = request.GET.get('format', 'csv')
    batches = EFTBatch.objects.filter(created_by=request.user).order_by('-created_at')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="my_batches.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Batch Reference', 'Batch Name', 'Status', 'Records', 'Total Amount (MWK)', 'Created', 'Last Updated'])
        
        for batch in batches:
            writer.writerow([
                batch.batch_reference,
                batch.batch_name,
                batch.get_status_display(),
                batch.record_count,
                str(batch.total_amount),
                batch.created_at.strftime('%Y-%m-%d'),
                batch.updated_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="my_batches.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('My Batches')
        
        row_num = 0
        columns = ['Batch Reference', 'Batch Name', 'Status', 'Records', 'Total Amount (MWK)', 'Created', 'Last Updated']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for batch in batches:
            row_num += 1
            ws.write(row_num, 0, batch.batch_reference)
            ws.write(row_num, 1, batch.batch_name)
            ws.write(row_num, 2, batch.get_status_display())
            ws.write(row_num, 3, batch.record_count)
            ws.write(row_num, 4, str(batch.total_amount))
            ws.write(row_num, 5, batch.created_at.strftime('%Y-%m-%d'))
            ws.write(row_num, 6, batch.updated_at.strftime('%Y-%m-%d %H:%M'))
        
        wb.save(response)
        return response
    
    return redirect('batch_list')

@login_required
@user_passes_test(is_accounts_personnel)
def batch_export_selected(request):
    """Export selected batches"""
    format = request.GET.get('format', 'csv')
    batch_ids = request.GET.getlist('batch_ids')
    
    if not batch_ids:
        messages.error(request, 'No batches selected for export')
        return redirect('batch_list')
    
    batches = EFTBatch.objects.filter(id__in=batch_ids, created_by=request.user).order_by('-created_at')
    
    if format == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="selected_batches.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Batch Reference', 'Batch Name', 'Status', 'Records', 'Total Amount (MWK)', 'Created', 'Last Updated'])
        
        for batch in batches:
            writer.writerow([
                batch.batch_reference,
                batch.batch_name,
                batch.get_status_display(),
                batch.record_count,
                str(batch.total_amount),
                batch.created_at.strftime('%Y-%m-%d'),
                batch.updated_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    elif format == 'excel':
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename="selected_batches.xls"'
        
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Selected Batches')
        
        row_num = 0
        columns = ['Batch Reference', 'Batch Name', 'Status', 'Records', 'Total Amount (MWK)', 'Created', 'Last Updated']
        
        for col_num, column_title in enumerate(columns):
            ws.write(row_num, col_num, column_title)
        
        for batch in batches:
            row_num += 1
            ws.write(row_num, 0, batch.batch_reference)
            ws.write(row_num, 1, batch.batch_name)
            ws.write(row_num, 2, batch.get_status_display())
            ws.write(row_num, 3, batch.record_count)
            ws.write(row_num, 4, str(batch.total_amount))
            ws.write(row_num, 5, batch.created_at.strftime('%Y-%m-%d'))
            ws.write(row_num, 6, batch.updated_at.strftime('%Y-%m-%d %H:%M'))
        
        wb.save(response)
        return response
    
    return redirect('batch_list')

@login_required
@user_passes_test(is_accounts_personnel)
@require_POST
def batch_bulk_delete(request):
    """Bulk delete draft batches"""
    batch_ids = request.POST.getlist('batch_ids')
    batches = EFTBatch.objects.filter(id__in=batch_ids, created_by=request.user, status='DRAFT')
    
    count = batches.count()
    batches.delete()
    
    messages.success(request, f'{count} draft batch(es) deleted successfully')
    next_url = request.POST.get('next', 'batch_list')
    return redirect(next_url)

# ================ AUTHORIZER VIEWS ================

def is_authorizer(user):
    """Check if user is authorizer"""
    return user.groups.filter(name='Authorizer').exists()

@login_required
@user_passes_test(is_authorizer)
def authorizer_dashboard(request):
    """Authorizer Dashboard"""
    pending_batches = EFTBatch.objects.filter(status='PENDING').order_by('-created_at')
    
    recent_approvals = EFTBatch.objects.filter(
        status__in=['APPROVED', 'REJECTED']
    ).order_by('-approved_at')[:10]
    
    stats = {
        'pending_count': pending_batches.count(),
        'approved_today': EFTBatch.objects.filter(
            status='APPROVED',
            approved_at__date=timezone.now().date()
        ).count(),
        'total_approved': EFTBatch.objects.filter(status='APPROVED').count(),
        'total_rejected': EFTBatch.objects.filter(status='REJECTED').count(),
    }
    
    return render(request, 'authorizer/dashboard.html', {
        'pending_batches': pending_batches,
        'recent_approvals': recent_approvals,
        'stats': stats
    })

@login_required
@user_passes_test(is_authorizer)
def authorizer_batch_list(request):
    """List all batches for authorizer"""
    batches = EFTBatch.objects.exclude(
        Q(status='DRAFT', created_by=request.user)
    ).order_by('-created_at')
    
    status_filter = request.GET.get('status', '')
    if status_filter:
        batches = batches.filter(status=status_filter)
    
    return render(request, 'authorizer/batch_list.html', {
        'batches': batches,
        'status_filter': status_filter
    })

@login_required
@user_passes_test(is_authorizer)
def review_batch(request, batch_id):
    """Review batch for approval/rejection"""
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING')
    
    if batch.created_by == request.user:
        messages.error(request, 'You cannot approve or reject your own batch')
        return redirect('authorizer_dashboard')
    
    transactions = batch.transactions.all().order_by('sequence_number')
    approval_form = BatchApprovalForm()
    rejection_form = BatchRejectionForm()
    
    return render(request, 'authorizer/review_batch.html', {
        'batch': batch,
        'transactions': transactions,
        'approval_form': approval_form,
        'rejection_form': rejection_form,
        'total_amount': sum(t.amount for t in transactions)
    })

@login_required
@user_passes_test(is_authorizer)
def approve_batch(request, batch_id):
    """Approve EFT batch"""
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING')
    
    if batch.created_by == request.user:
        messages.error(request, 'You cannot approve your own batch')
        return redirect('authorizer_dashboard')
    
    if request.method == 'POST':
        form = BatchApprovalForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                batch.status = 'APPROVED'
                batch.approved_by = request.user
                batch.approved_at = timezone.now()
                batch.save()
                
                ApprovalAuditLog.objects.create(
                    batch=batch,
                    action='APPROVED',
                    user=request.user,
                    remarks=form.cleaned_data['remarks'],
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 'Batch approved successfully')
                return redirect('authorizer_dashboard')
    
    messages.error(request, 'Invalid request')
    return redirect('review_batch', batch_id=batch_id)

@login_required
@user_passes_test(is_authorizer)
def reject_batch(request, batch_id):
    """Reject EFT batch"""
    batch = get_object_or_404(EFTBatch, id=batch_id, status='PENDING')
    
    if batch.created_by == request.user:
        messages.error(request, 'You cannot reject your own batch')
        return redirect('authorizer_dashboard')
    
    if request.method == 'POST':
        form = BatchRejectionForm(request.POST)
        if form.is_valid():
            with db_transaction.atomic():
                batch.status = 'REJECTED'
                batch.rejection_reason = form.cleaned_data['rejection_reason']
                batch.save()
                
                ApprovalAuditLog.objects.create(
                    batch=batch,
                    action='REJECTED',
                    user=request.user,
                    remarks=form.cleaned_data['rejection_reason'],
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                messages.success(request, 'Batch rejected successfully')
                return redirect('authorizer_dashboard')
    
    messages.error(request, 'Invalid request')
    return redirect('review_batch', batch_id=batch_id)

# ================ API VIEWS ================

@login_required
def get_supplier_details(request, supplier_id):
    """Get supplier details for AJAX"""
    try:
        supplier = Supplier.objects.get(id=supplier_id)
        
        data = {
            'bank_name': supplier.bank.bank_name,
            'swift_code': supplier.bank.swift_code,
            'account_number': supplier.account_number,
            'account_name': supplier.account_name,
            'credit_reference': supplier.credit_reference or '',
            'cost_center': supplier.cost_center or '',
        }
        
        return JsonResponse(data)
    except Supplier.DoesNotExist:
        return JsonResponse({'error': 'Supplier not found'}, status=404)

@login_required
def get_scheme_zone(request, scheme_id):
    """Get zone for a scheme - BACKWARD COMPATIBILITY"""
    try:
        # First try to convert to integer (if it's an ID)
        try:
            scheme_id_int = int(scheme_id)
            scheme = Scheme.objects.get(id=scheme_id_int)
        except (ValueError, Scheme.DoesNotExist):
            # If not found by ID, try to find by scheme_code
            scheme = Scheme.objects.get(scheme_code=scheme_id)
        
        data = {
            'zone_code': scheme.zone.zone_code,
            'zone_name': scheme.zone.zone_name,
        }
        return JsonResponse(data)
    except Scheme.DoesNotExist:
        return JsonResponse({'error': 'Scheme not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# NEW API ENDPOINT FOR AUTO-COST CENTER
@login_required
def get_scheme_details(request, scheme_id):
    """Get scheme details including default cost center"""
    try:
        # First try to convert to integer (if it's an ID)
        try:
            scheme_id_int = int(scheme_id)
            scheme = Scheme.objects.get(id=scheme_id_int)
        except (ValueError, Scheme.DoesNotExist):
            # If not found by ID, try to find by scheme_code
            scheme = Scheme.objects.get(scheme_code=scheme_id)
        
        data = {
            'success': True,
            'zone_code': scheme.zone.zone_code,
            'zone_name': scheme.zone.zone_name,
            'default_cost_center': scheme.default_cost_center or '',
            'scheme_code': scheme.scheme_code,
            'scheme_name': scheme.scheme_name,
        }
        return JsonResponse(data)
        
    except Scheme.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': f'Scheme not found with ID/code: {scheme_id}'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Server error: {str(e)}'
        }, status=500)