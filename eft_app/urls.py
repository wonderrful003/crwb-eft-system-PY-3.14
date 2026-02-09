from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Redirect root to login
    path('', RedirectView.as_view(pattern_name='login'), name='home'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # ================ SYSTEM ADMIN URLS ================
    path('system-admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('system-admin/api/system-activity/', views.api_system_activity, name='api_system_activity'),
    path('system-admin/api/system-status/', views.api_system_status, name='api_system_status'),
    
    # User Management
    path('system-admin/users/', views.user_list, name='user_list'),
    path('system-admin/users/create/', views.user_create, name='user_create'),
    path('system-admin/users/<int:user_id>/', views.user_detail, name='user_detail'),
    path('system-admin/users/<int:user_id>/edit/', views.user_edit, name='user_edit'),
    path('system-admin/users/<int:user_id>/delete/', views.user_delete, name='user_delete'),
    path('system-admin/users/<int:user_id>/reset-password/', views.user_reset_password, name='user_reset_password'),
    path('system-admin/users/<int:user_id>/toggle-status/', views.user_toggle_status, name='user_toggle_status'),
    path('system-admin/users/export/', views.export_users, name='user_export'),
    path('system-admin/users/bulk-activate/', views.user_bulk_activate, name='user_bulk_activate'),
    path('system-admin/users/bulk-deactivate/', views.user_bulk_deactivate, name='user_bulk_deactivate'),
    path('system-admin/users/bulk-delete/', views.user_bulk_delete, name='user_bulk_delete'),
    
    # Bank Management
    path('system-admin/banks/', views.BankListView.as_view(), name='bank_list'),
    path('system-admin/banks/add/', views.BankCreateView.as_view(), name='bank_add'),
    path('system-admin/banks/<int:pk>/', views.BankDetailView.as_view(), name='bank_detail'),
    path('system-admin/banks/<int:pk>/edit/', views.BankUpdateView.as_view(), name='bank_edit'),
    path('system-admin/banks/<int:pk>/delete/', views.BankDeleteView.as_view(), name='bank_delete'),
    path('system-admin/banks/<int:pk>/toggle-status/', views.bank_toggle_status, name='bank_toggle_status'),
    path('system-admin/banks/export/', views.export_banks, name='bank_export'),
    path('system-admin/banks/bulk-activate/', views.bank_bulk_activate, name='bank_bulk_activate'),
    path('system-admin/banks/bulk-deactivate/', views.bank_bulk_deactivate, name='bank_bulk_deactivate'),
    path('system-admin/banks/bulk-delete/', views.bank_bulk_delete, name='bank_bulk_delete'),
    
    # Zone Management
    path('system-admin/zones/', views.ZoneListView.as_view(), name='zone_list'),
    path('system-admin/zones/add/', views.ZoneCreateView.as_view(), name='zone_add'),
    path('system-admin/zones/<int:pk>/', views.ZoneDetailView.as_view(), name='zone_detail'),
    path('system-admin/zones/<int:pk>/edit/', views.ZoneUpdateView.as_view(), name='zone_edit'),
    path('system-admin/zones/<int:pk>/delete/', views.ZoneDeleteView.as_view(), name='zone_delete'),
    path('system-admin/zones/<int:pk>/toggle-status/', views.zone_toggle_status, name='zone_toggle_status'),
    path('system-admin/zones/export/', views.export_zones, name='zone_export'),
    path('system-admin/zones/bulk-activate/', views.zone_bulk_activate, name='zone_bulk_activate'),
    path('system-admin/zones/bulk-deactivate/', views.zone_bulk_deactivate, name='zone_bulk_deactivate'),
    path('system-admin/zones/bulk-delete/', views.zone_bulk_delete, name='zone_bulk_delete'),
    
    # Supplier Management
    path('system-admin/suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('system-admin/suppliers/add/', views.SupplierCreateView.as_view(), name='supplier_add'),
    path('system-admin/suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('system-admin/suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_edit'),
    path('system-admin/suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    path('system-admin/suppliers/<int:pk>/toggle-status/', views.supplier_toggle_status, name='supplier_toggle_status'),
    path('system-admin/suppliers/export/', views.export_suppliers, name='supplier_export'),
    path('system-admin/suppliers/bulk-activate/', views.supplier_bulk_activate, name='supplier_bulk_activate'),
    path('system-admin/suppliers/bulk-deactivate/', views.supplier_bulk_deactivate, name='supplier_bulk_deactivate'),
    path('system-admin/suppliers/bulk-delete/', views.supplier_bulk_delete, name='supplier_bulk_delete'),
    
    # Scheme Management
    path('system-admin/schemes/', views.SchemeListView.as_view(), name='scheme_list'),
    path('system-admin/schemes/add/', views.SchemeCreateView.as_view(), name='scheme_add'),
    path('system-admin/schemes/<int:pk>/', views.SchemeDetailView.as_view(), name='scheme_detail'),
    path('system-admin/schemes/<int:pk>/edit/', views.SchemeUpdateView.as_view(), name='scheme_edit'),
    path('system-admin/schemes/<int:pk>/delete/', views.SchemeDeleteView.as_view(), name='scheme_delete'),
    path('system-admin/schemes/<int:pk>/toggle-status/', views.scheme_toggle_status, name='scheme_toggle_status'),
    path('system-admin/schemes/export/', views.export_schemes, name='scheme_export'),
    path('system-admin/schemes/bulk-activate/', views.scheme_bulk_activate, name='scheme_bulk_activate'),
    path('system-admin/schemes/bulk-deactivate/', views.scheme_bulk_deactivate, name='scheme_bulk_deactivate'),
    path('system-admin/schemes/bulk-delete/', views.scheme_bulk_delete, name='scheme_bulk_delete'),
    
    # Debit Account Management
    path('system-admin/debit-accounts/', views.DebitAccountListView.as_view(), name='debit_account_list'),
    path('system-admin/debit-accounts/add/', views.DebitAccountCreateView.as_view(), name='debit_account_add'),
    path('system-admin/debit-accounts/<int:pk>/', views.DebitAccountDetailView.as_view(), name='debit_account_detail'),
    path('system-admin/debit-accounts/<int:pk>/edit/', views.DebitAccountUpdateView.as_view(), name='debit_account_edit'),
    path('system-admin/debit-accounts/<int:pk>/delete/', views.DebitAccountDeleteView.as_view(), name='debit_account_delete'),
    path('system-admin/debit-accounts/<int:pk>/toggle-status/', views.debit_account_toggle_status, name='debit_account_toggle_status'),
    path('system-admin/debit-accounts/export/', views.export_debit_accounts, name='debit_account_export'),
    path('system-admin/debit-accounts/bulk-activate/', views.debit_account_bulk_activate, name='debit_account_bulk_activate'),
    path('system-admin/debit-accounts/bulk-deactivate/', views.debit_account_bulk_deactivate, name='debit_account_bulk_deactivate'),
    path('system-admin/debit-accounts/bulk-delete/', views.debit_account_bulk_delete, name='debit_account_bulk_delete'),
    
    # ================ ACCOUNTS PERSONNEL URLS ================
    path('accounts/dashboard/', views.accounts_dashboard, name='accounts_dashboard'),
    path('accounts/batches/', views.batch_list, name='batch_list'),
    path('accounts/batches/create/', views.create_batch, name='create_batch'),
    path('accounts/batches/<int:batch_id>/edit/', views.edit_batch, name='edit_batch'),
    path('accounts/batches/<int:batch_id>/view/', views.view_batch, name='view_batch'),
    path('accounts/batches/<int:batch_id>/submit/', views.submit_for_approval, name='submit_batch'),
    path('accounts/batches/<int:batch_id>/delete/', views.delete_batch, name='delete_batch'),
    path('accounts/batches/<int:batch_id>/transaction/add/', views.add_transaction, name='add_transaction'),
    path('accounts/batches/<int:batch_id>/transaction/<int:transaction_id>/delete/', 
         views.delete_transaction, name='delete_transaction'),
    path('accounts/batches/<int:batch_id>/export/<str:format>/', views.export_batch, name='export_batch'),
    path('accounts/batches/<int:batch_id>/export-details/', views.export_batch_details, name='export_batch_details'),
    path('accounts/batches/export-all/', views.batch_export_all, name='batch_export_all'),
    path('accounts/batches/export-selected/', views.batch_export_selected, name='batch_export_selected'),
    path('accounts/batches/bulk-delete/', views.batch_bulk_delete, name='batch_bulk_delete'),
    
    # ================ AUTHORIZER URLS ================
    path('authorizer/dashboard/', views.authorizer_dashboard, name='authorizer_dashboard'),
    path('authorizer/batches/', views.authorizer_batch_list, name='authorizer_batch_list'),
    path('authorizer/batches/<int:batch_id>/review/', views.review_batch, name='review_batch'),
    path('authorizer/batches/<int:batch_id>/approve/', views.approve_batch, name='approve_batch'),
    path('authorizer/batches/<int:batch_id>/reject/', views.reject_batch, name='reject_batch'),
    
    # ================ API URLS ================
    path('api/supplier/<int:supplier_id>/details/', views.get_supplier_details, name='supplier_details'),
    path('api/scheme/<int:scheme_id>/zone/', views.get_scheme_zone, name='scheme_zone'),
    path('api/scheme/<int:scheme_id>/details/', views.get_scheme_details, name='scheme_details'),
    path('api/scheme/<str:scheme_id>/details/', views.get_scheme_details, name='scheme_details_str'),
]