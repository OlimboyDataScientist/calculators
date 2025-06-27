from .views import send_reset_link, custom_password_change_done
from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib import admin 
from django.contrib.auth import views as auth_views
from .views import CustomPasswordChangeView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('calculators/', views.calculator_menu, name='calculator_menu'),

    path('register/', views.register_view, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),

    path('calculator/bmi/', views.bmi_calculator, name='bmi_calculator'),
    path('calculator/loan/', views.loan_calculator, name='loan_calculator'),
    path('calculator/age/', views.age_calculator, name='age_calculator'),
    path('calculator/currency/', views.currency_converter, name='currency_converter'),
    path('calculator/tax/', views.tax_calculator, name='tax_calculator'),

    path('contact/', views.contact_view, name='contact'),
    path('phone/', views.phone_formatter_view, name='country_code_lookup'),
    path('time-difference/', views.time_difference_view, name='time_difference'),

    path('history/', views.history_page, name='history_page'),

    path('password-reset/', views.password_reset_request, name='password_reset'),
    path('reset/<uidb64>/<token>/', views.password_reset_confirm, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_complete, name='password_reset_complete'),
    path('password-reset/done/', views.password_reset_done, name='password_reset_done'),
    
    path('gpa/', views.gpa_calculator_view, name='gpa_calculator'),
    path('api/send-reset-link', send_reset_link, name='send_reset_link'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html'
    ), name='password_reset_confirm'),
    path('password/change/', CustomPasswordChangeView.as_view(), name='password_change'),
    path('password/change/done/', custom_password_change_done, name='password_change_done'),
     path('privacy-policy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy_policy'),
    path('terms-conditions/', TemplateView.as_view(template_name='terms_conditions.html'), name='terms_conditions'),
    
]
