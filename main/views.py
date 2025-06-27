# your_app_name/views.py
from django.utils.encoding import force_str, force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.forms import SetPasswordForm, UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from datetime import datetime, date
import math
import requests
from pytz import country_timezones
import pytz
import phonenumbers
import traceback
import json
from .models import UserHistory, ContactMessage
from .forms import ContactForm
from django.utils.timezone import make_aware, now
from django.contrib.gis.geoip2 import GeoIP2
import geoip2.database
from django.conf import settings
from django.contrib import messages
import pycountry
from django.core.mail import send_mail





# --- Core Views ---
def home(request):
    return render(request, 'home.html')



def get_client_ip(request):
    """Fetch real client IP (handles proxy cases)."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get("REMOTE_ADDR")
        
    if ip in ['127.0.0.1', '::1', None]:
        ip = '8.8.8.8'  # Default IP (New York / Google)
        
    return ip

def get_timezone_by_ip(ip):
    """Fetch timezone using IP and GeoIP2 or fallback API."""
    try:
        geo = GeoIP2()
        city = geo.city(ip)
        return city.get('time_zone', 'America/New_York')
    except:
        # fallback to free API if GeoIP2 fails
        try:
            res = requests.get(f"http://ip-api.com/json/{ip}").json()
            return res.get("timezone", "America/New_York")
        except:
            return "America/New_York"



def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def logout_view(request):
    logout(request)
    return render(request, 'logout.html')

def calculator_menu(request):
    return render(request, 'calculator_menu.html')


from django.contrib.auth.decorators import login_required

@login_required
def custom_password_change_done(request):
    return render(request, 'registration/change_password_done.html', {
        'username': request.user.username
    })


class CustomPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    template_name = 'registration/change_password.html'
    success_url = reverse_lazy('password_change_done')
    success_message = "Your password was changed successfully."
    
    def form_valid(self, form):
        if self.request.user.is_authenticated:
            UserHistory.objects.create(
                user=self.request.user,
                tool_name="Password Change",
                input_data="Password changed by user",
                result_data="Success",
                user_email=self.request.user.email,
                username=self.request.user.username,
                created_at=now()
            )
        messages.success(self.request, "Your password was changed successfully.")
        return super().form_valid(form)

# --- History View ---
@login_required
def history_page(request):
    """
    Displays the calculation history for the authenticated user.
    """
    ip = get_client_ip(request)
    
    try:
        user_timezone = get_timezone_by_ip(ip)
        tz = pytz.timezone(user_timezone)
    except Exception:
        tz = pytz.timezone("America/New_York")
    
    user_history = UserHistory.objects.filter(user=request.user).order_by('-created_at')

        
    context = {
        'user_history': user_history,
    }
    # Ensure this template path is correct for your project structure.
    # If your templates are in 'templates/your_app_name/', then it should be 'your_app_name/history_page.html'
    return render(request, 'accounts/history_page.html', context)


# --- Calculator Views (with History Integration) ---
def bmi_calculator(request):
    context = {}

    if request.method == 'POST':
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        unit = request.POST.get('unit')
        weight_input = request.POST.get('weight')
        height_cm_input = request.POST.get('height_cm')
        height_ft_input = request.POST.get('height_ft')
        height_in_input = request.POST.get('height_in')

        context.update({
            'gender': gender,
            'age': age,
            'unit': unit,
            'weight': weight_input,
            'height_cm': height_cm_input,
            'height_ft': height_ft_input,
            'height_in': height_in_input,
        })

        try:
            weight_calc = float(weight_input)
            age_calc = int(age)

            if unit == 'kg':
                height_m_calc = float(height_cm_input) / 100
                display_height = f"{height_cm_input} cm"
                display_weight = f"{weight_input} kg"
            else: # imperial
                ft = int(height_ft_input) if height_ft_input else 0
                inch = int(height_in_input) if height_in_input else 0
                total_inches = (ft * 12) + inch
                height_m_calc = total_inches * 0.0254
                weight_calc = weight_calc * 0.453592  # Convert pounds to kg
                display_height = f"{ft}' {inch}\""
                display_weight = f"{weight_input} lbs"


            if height_m_calc <= 0:
                raise ValueError("Invalid height provided. Height must be positive.")

            bmi = round(weight_calc / (height_m_calc ** 2), 1)

            if bmi < 18.5:
                status = "Underweight"
                suggestion = "🧃 You're a bit underweight. Let’s work on a balanced diet!"
            elif 18.5 <= bmi < 25:
                status = "Normal"
                suggestion = "✅ You're doing great! Keep maintaining a healthy lifestyle! 💪"
            elif 25 <= bmi < 30:
                status = "Overweight"
                suggestion = "🚶‍♂️ Let’s include more physical activity in your routine. You’ve got this!"
            else:
                status = "Obese"
                suggestion = "❤️ Health is a journey. Small steps daily = Big changes. You can do it!"

            context.update({
                'bmi': bmi,
                'status': status,
                'suggestion': suggestion,
            })


            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                        f"Weight: ⚖️ {display_weight}, Height: 📏 {display_height}, "
                        f"Age: {age_calc}, Gender: 🚻 {gender}, Unit: 🧪 {unit}"
                    )
                    result_data_str = f"BMI: {bmi} ({status})"

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="BMI calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] BMI history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving BMI history for {request.user.username}: {e}")
                    traceback.print_exc()


        except ValueError as ve:
            context['error'] = f"Invalid input: {str(ve)}. Please ensure all fields are numbers."
        except Exception as e:
            context['error'] = f"An unexpected error occurred: {str(e)}"
            traceback.print_exc()

    return render(request, 'bmi_calculator.html', context)


def loan_calculator(request):
    context = {}
    if request.method == 'POST':
        try:
            principal = float(request.POST.get('principal', 0))
            annual_rate = float(request.POST.get('rate', 0))
            years = int(request.POST.get('time_years', 0))
            months = int(request.POST.get('time_months', 0))

            total_months = years * 12 + months
            monthly_rate = annual_rate / (12 * 100)

            if total_months > 0 and monthly_rate > 0:
                emi = principal * monthly_rate * math.pow(1 + monthly_rate, total_months) / (math.pow(1 + monthly_rate, total_months) - 1)
                total_payment = emi * total_months
                total_interest = total_payment - principal
            else:
                emi = total_payment = total_interest = 0

            context.update({
                'principal': principal,
                'rate': annual_rate,
                'time_years': years,
                'time_months': months,
                'emi': f"{emi:,.2f}",
                'total_payment': f"{total_payment:,.2f}",
                'total_interest': f"{total_interest:,.2f}",
            })

            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                        f"Loan Amount: 💰 {principal}, Annual rate: {annual_rate}%, "
                        f"years of loan: {years}, months of loan: {months}"
                    )
                    result_data_str = f"Monthly payment: ${emi:,.2f}, total payment: ${total_payment:,.2f}, total interest: ${total_interest:,.2f}"

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="Loan calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Loan calculated history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Loan calculated history for {request.user.username}: {e}")
                    traceback.print_exc()
        except ValueError:
            context = {
                'error': 'Invalid input. Please check your numbers.',
            }
        except Exception as e:
            context = {
                'error': f"An unexpected error occurred: {str(e)}",
            }
            traceback.print_exc()
    else:
        context = {}

    return render(request, 'loan_calculator.html', context)


def age_calculator(request):
    age = None
    dob = ''
    total_months = None
    total_days = None
    total_hours = None
    total_minutes = None
    total_seconds = None

    # Set default aware_time to avoid UnboundLocalError
    default_tz = pytz.timezone("America/New_York")
    aware_time = datetime.now().astimezone(default_tz)

    if request.method == 'POST':
        dob = request.POST.get('dob', '')
        try:
            dob_datetime = datetime.strptime(dob, '%Y-%m-%d')  # or '%Y-%m-%d %H:%M:%S' if time is included
            now = datetime.now()

            # Calculate age in years
            age = now.year - dob_datetime.year - ((now.month, now.day) < (dob_datetime.month, dob_datetime.day))

            # Calculate exact time difference
            time_difference = now - dob_datetime

            # Total units
            total_days = time_difference.days
            total_seconds = time_difference.total_seconds()
            total_minutes = total_seconds / 60
            total_hours = total_seconds / 3600

            # Total months (approximate, but improved)
            total_months = (now.year - dob_datetime.year) * 12 + now.month - dob_datetime.month
            if now.day < dob_datetime.day:
                total_months -= 1

            # 🌐 Get timezone-aware current time from IP
            ip = get_client_ip(request)
            try:
                user_timezone = get_timezone_by_ip(ip)
                if user_timezone:
                    aware_time = make_aware(datetime.utcnow()).astimezone(pytz.timezone(user_timezone))
            except Exception as e:
                print(f"Error determining timezone from IP: {e}")
                # already defaulted to aware_time above

            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                        f"Date of birth: {dob_datetime}"
                    )
                    result_data_str = f"Age: {age} years old, total months: 📅 {total_months}, total days: 📆 {total_days}, total hours: ⏰ {total_hours}"

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="Age calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Age calculated history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Age calculated history for {request.user.username}: {e}")
                    traceback.print_exc()

        except ValueError:
            age = None  # Invalid date format
        except Exception as e:
            print(f"Unhandled error in age_calculator: {e}")
            traceback.print_exc()

    return render(request, 'age_calculator.html', {
        'age': age,
        'dob': dob,
        'total_months': f"{total_months:,.0f}".replace(",", " ") if total_months is not None else "",
        'total_days': f"{total_days:,.0f}".replace(",", " ") if total_days is not None else "",
        'total_hours': f"{total_hours:,.2f}".replace(",", " ") if total_hours is not None else "",
        'total_minutes': f"{total_minutes:,.2f}".replace(",", " ") if total_minutes is not None else "",
        'total_seconds': f"{total_seconds:,.2f}".replace(",", " ") if total_seconds is not None else "",
        'user_time': aware_time.strftime("%Y-%m-%d") if aware_time is not None else ""
    })






def currency_converter(request):
    result = None
    error_message = None
    currencies = [
        {'code': 'USD', 'name': 'United States Dollar', 'country_code': 'us'},
        {'code': 'EUR', 'name': 'Euro', 'country_code': 'eu'},
        {'code': 'JPY', 'name': 'Japanese Yen', 'country_code': 'jp'},
        {'code': 'GBP', 'name': 'British Pound Sterling', 'country_code': 'gb'},
        {'code': 'AUD', 'name': 'Australian Dollar', 'country_code': 'au'},
        {'code': 'CAD', 'name': 'Canadian Dollar', 'country_code': 'ca'},
        {'code': 'CHF', 'name': 'Swiss Franc', 'country_code': 'ch'},
        {'code': 'CNY', 'name': 'Chinese Yuan', 'country_code': 'cn'},
        {'code': 'HKD', 'name': 'Hong Kong Dollar', 'country_code': 'hk'},
        {'code': 'NZD', 'name': 'New Zealand Dollar', 'country_code': 'nz'},
        {'code': 'SEK', 'name': 'Swedish Krona', 'country_code': 'se'},
        {'code': 'KRW', 'name': 'South Korean Won', 'country_code': 'kr'},
        {'code': 'SGD', 'name': 'Singapore Dollar', 'country_code': 'sg'},
        {'code': 'NOK', 'name': 'Norwegian Krone', 'country_code': 'no'},
        {'code': 'MXN', 'name': 'Mexican Peso', 'country_code': 'mx'},
        {'code': 'INR', 'name': 'Indian Rupee', 'country_code': 'in'},
        {'code': 'RUB', 'name': 'Russian Ruble', 'country_code': 'ru'},
        {'code': 'ZAR', 'name': 'South African Rand', 'country_code': 'za'},
        {'code': 'TRY', 'name': 'Turkish Lira', 'country_code': 'tr'},
        {'code': 'BRL', 'name': 'Brazilian Real', 'country_code': 'br'},
        {'code': 'TWD', 'name': 'New Taiwan Dollar', 'country_code': 'tw'},
        {'code': 'DKK', 'name': 'Danish Krone', 'country_code': 'dk'},
        {'code': 'PLN', 'name': 'Polish Zloty', 'country_code': 'pl'},
        {'code': 'THB', 'name': 'Thai Baht', 'country_code': 'th'},
        {'code': 'IDR', 'name': 'Indonesian Rupiah', 'country_code': 'id'},
        {'code': 'HUF', 'name': 'Hungarian Forint', 'country_code': 'hu'},
        {'code': 'CZK', 'name': 'Czech Koruna', 'country_code': 'cz'},
        {'code': 'ILS', 'name': 'Israeli Shekel', 'country_code': 'il'},
        {'code': 'CLP', 'name': 'Chilean Peso', 'country_code': 'cl'},
        {'code': 'PHP', 'name': 'Philippine Peso', 'country_code': 'ph'},
        {'code': 'AED', 'name': 'UAE Dirham', 'country_code': 'ae'},
        {'code': 'COP', 'name': 'Colombian Peso', 'country_code': 'co'},
        {'code': 'SAR', 'name': 'Saudi Riyal', 'country_code': 'sa'},
        {'code': 'MYR', 'name': 'Malaysian Ringgit', 'country_code': 'my'},
        {'code': 'RON', 'name': 'Romanian Leu', 'country_code': 'ro'},
        {'code': 'EGP', 'name': 'Egyptian Pound', 'country_code': 'eg'},
        {'code': 'PKR', 'name': 'Pakistani Rupee', 'country_code': 'pk'},
        {'code': 'NGN', 'name': 'Nigerian Naira', 'country_code': 'ng'},
        {'code': 'BDT', 'name': 'Bangladeshi Taka', 'country_code': 'bd'},
        {'code': 'VND', 'name': 'Vietnamese Dong', 'country_code': 'vn'},
        {'code': 'LKR', 'name': 'Sri Lankan Rupee', 'country_code': 'lk'},
        {'code': 'KWD', 'name': 'Kuwaiti Dinar', 'country_code': 'kw'},
        {'code': 'QAR', 'name': 'Qatari Riyal', 'country_code': 'qa'},
        {'code': 'OMR', 'name': 'Omani Rial', 'country_code': 'om'},
        {'code': 'JOD', 'name': 'Jordanian Dinar', 'country_code': 'jo'},
        {'code': 'MAD', 'name': 'Moroccan Dirham', 'country_code': 'ma'},
        {'code': 'DZD', 'name': 'Algerian Dinar', 'country_code': 'dz'},
        {'code': 'UAH', 'name': 'Ukrainian Hryvnia', 'country_code': 'ua'},
        {'code': 'ARS', 'name': 'Argentine Peso', 'country_code': 'ar'},
        {'code': 'UZS', 'name': 'Uzbekistan Som', 'country_code': 'uz'},
    ]


    
    if request.method == "POST":
        from_currency = request.POST.get("from_currency")
        to_currency = request.POST.get("to_currency")
        amount = request.POST.get("amount")

        try:
            amount_float = float(amount)

            # 🔐 Replace this with your actual access key
            # Remember: For production, store this securely (e.g., in environment variables)
            access_key = "a0be1cf0dfa423f0f57651d8000a6fae"

            url = (
                f"https://api.exchangerate.host/convert"
                f"?access_key={access_key}&from={from_currency}&to={to_currency}&amount={amount_float}"
            )

            print("Calling API:", url)
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200 and data.get("success") and data.get("result") is not None:
                converted_amount = data['result']
                result = f"{converted_amount:,.2f}".replace(",", " ")

            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                        f"From currency: 💸 {from_currency}, To currency: 💵 {to_currency}, Amount: 💰 {amount_float}"
                    )
                    result_data_str = f"Converted amount: {result}"

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="Currency converter",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Currency converter history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Currency converter history for {request.user.username}: {e}")
                    traceback.print_exc()
            else:
                error_message = data.get("error", {}).get("info", "Could not fetch conversion rate. Please check currencies or API key.")
        except ValueError:
            error_message = "Invalid amount. Please enter a valid number."
        except requests.exceptions.ConnectionError:
            error_message = "Network error. Could not connect to the currency conversion service."
        except Exception as e:
            error_message = f"An unexpected error occurred: {str(e)}"
            traceback.print_exc()

    context = {
        "currencies": currencies,
        "result": result,
        "error_message": error_message,
        "from_currency_selected": request.POST.get("from_currency", "USD"),
        "to_currency_selected": request.POST.get("to_currency", "EUR"),
        "amount_input": request.POST.get("amount", ""),
    }

    return render(request, "currency_converter.html", context)


def tax_calculator(request):
    result = None
    left_amount = None
    context = {}

    if request.method == 'POST':
        try:
            income = float(request.POST['income'])
            tax_rate = float(request.POST['tax_rate'])
            income_type = request.POST.get('income_type', 'before')  # default to before if missing

            if income_type == 'before':
                # Normal calculation
                calculated_tax = income * (tax_rate / 100)
                net_income = income - calculated_tax
                gross_income = income  # same as input
                total_income = calculated_tax + net_income
            elif income_type == 'after':
                # Reverse calculation to find tax and gross income
                gross_income = income / (1 - tax_rate / 100)
                calculated_tax = gross_income - income
                net_income = income  # same as input
                total_income = calculated_tax + net_income
            else:
                raise ValueError("Invalid income type selected.")

            result = f"{round(calculated_tax, 2):,.2f}".replace(",", " ")
            left_amount = f"{round(net_income, 2):,.2f}".replace(",", " ")
            display_income = f"{round(gross_income, 2):,.2f}".replace(",", " ")
            total_income = f"{round(total_income, 2):,.2f}".replace(",", " ")

            context.update({
                'result': result,
                'net_income': left_amount,
                'income': income,
                'tax_rate': tax_rate,
                'income_type': income_type,
                'total_income' : total_income
            })

            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    income_label = "After tax" if income_type == 'after' else "Before tax"
                    input_data_str = (
                        f"Income ({income_label}): 💰 {income}, Tax rate: {tax_rate}%"
                    )
                    result_data_str = f"Tax amount: 💵 {result}, Left amount: 💸 {left_amount}"

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'

                    # GeoIP info
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Localized datetime
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="Tax calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Calculated tax history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Calculated tax history for {request.user.username}: {e}")
                    traceback.print_exc()

        except (ValueError, KeyError) as e:
            context['result'] = 'Invalid input'
            context['error'] = f"Invalid input: {str(e)}. Please check your numbers."
        except Exception as e:
            context['result'] = 'Error'
            context['error'] = f"An unexpected error occurred: {str(e)}"
            traceback.print_exc()

    return render(request, 'tax_calculator.html', context)


def gpa_calculator_view(request):
    gpa = None
    converted_gpa = None
    error_message = None
    mode = 'calculate' # Default mode

    # Define your GPA scale options here
    # These will populate the dropdowns in the template
    scale_options = [
        ('4.0', '4.0 Scale (e.g., US)'),
        ('5.0', '5.0 Scale'),
        ('100', '100% Scale'),
        ('9.0', '9.0 Scale'),
        ('10.0', '10.0 Scale'),
        ('12.0', '12.0 Scale'),
    ]

    if request.method == 'POST':
        mode = request.POST.get('mode')

        if mode == 'calculate':
            grades = request.POST.getlist('grades[]')
            credits = request.POST.getlist('credits[]')

            try:
                total_grade_points = 0
                total_credits = 0
                grade_to_points = {
                    'A+': 4.0, 'A': 4.0, 'A-': 3.7,
                    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
                    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
                    'D+': 1.3, 'D': 1.0, 'F': 0.0,
                }

                if not grades or not credits:
                    error_message = "Please enter at least one course with grade and credits."
                else:
                    for i in range(len(grades)):
                        grade = grades[i]
                        credit_str = credits[i]
                        
                        if grade and credit_str:
                            try:
                                credit = float(credit_str)
                                if credit <= 0:
                                     error_message = "Credits must be a positive number."
                                     break

                                if grade in grade_to_points:
                                    points = grade_to_points[grade]
                                    total_grade_points += (points * credit)
                                    total_credits += credit
                                else:
                                    error_message = f"Invalid grade '{grade}' found."
                                    break
                            except ValueError:
                                error_message = "Credits must be valid numbers."
                                break
                        else:
                            error_message = "Please ensure all selected grades and credits are entered."
                            break
                    
                    if error_message is None: # Only calculate if no errors so far
                        if total_credits > 0:
                            gpa = round(total_grade_points / total_credits, 2)
                        else:
                            error_message = "Total credits cannot be zero."
            except Exception as e:
                error_message = f"An unexpected error occurred during calculation: {e}"

            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                        f"Total grade points: {total_grade_points:,.2f}, Total credits: {total_credits}"
                    )
                    result_data_str = (
                        f"GPA: {gpa}"
                    )

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="GPA calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Calculatoed GPA history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Calculated GPA history for {request.user.username}: {e}")
                    traceback.print_exc()
                    
        elif mode == 'convert':
            # Your existing GPA conversion logic goes here
            # For example:
            current_gpa_str = request.POST.get('current_gpa')
            current_scale_str = request.POST.get('current_scale')
            target_scale_str = request.POST.get('target_scale')

            try:
                current_gpa = float(current_gpa_str)
                current_scale = float(current_scale_str)
                target_scale = float(target_scale_str)

                if current_scale == 0 or target_scale == 0:
                    error_message = "Scales cannot be zero."
                elif current_gpa < 0 or current_gpa > current_scale:
                    error_message = f"Current GPA ({current_gpa}) is out of range for the {current_scale} scale."
                else:
                    # Simple linear conversion formula: (current_gpa / current_scale) * target_scale
                    converted_gpa = round((current_gpa / current_scale) * target_scale, 2)
                
                # ✅ Save to user history if logged in
                if request.user.is_authenticated:
                    try:
                        # Prepare input and result strings
                        input_data_str = (
                            f"Current GPA: {current_gpa}, Current scale: {current_scale},  Target scale: {target_scale}"
                        )
                        result_data_str = (
                            f"Converted GPA: ${converted_gpa}"
                        )

                        # Get IP and fallback to default if needed
                        ip = get_client_ip(request)
                        if ip in ['127.0.0.1', '::1', None]:
                            ip = '8.8.8.8'  # Default IP (e.g., New York)

                        # Get city, country, and timezone by IP
                        reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                        geo_info = reader.city(ip)
                        city = geo_info.city.name or "Unknown"
                        country = geo_info.country.name or "Unknown"
                        timezone_str = geo_info.location.time_zone or "America/New_York"
                        reader.close()

                        # Get aware datetime using the user's timezone
                        user_timezone = pytz.timezone(timezone_str)
                        aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                        # Save to history
                        UserHistory.objects.create(
                            user=request.user,
                            tool_name="GPA converter",
                            input_data=input_data_str,
                            result_data=result_data_str,
                            created_at=aware_time,
                            city=city,
                            country=country,
                            user_email=request.user.email,
                            username=request.user.username
                        )
                        print(f"[✓] Converted GPA history saved for {request.user.username}")

                    except Exception as e:
                        print(f"[!] Error saving Converted GPA history for {request.user.username}: {e}")
                        traceback.print_exc()  
                
            except (ValueError, TypeError):
                error_message = "Please enter valid numbers for GPA and select scales."
            except Exception as e:
                error_message = f"An unexpected error occurred during conversion: {e}"

            
            

    context = {
        'gpa': gpa,
        'converted_gpa': converted_gpa,
        'error_message': error_message,
        'mode': mode, # Pass the current mode to the template for tab stickiness
        'request.POST': request.POST, # Pass request.POST for sticky form fields
        'scale_options': scale_options, # <-- THIS IS THE KEY VARIABLE TO PASS
    }

    return render(request, 'gpa_calculator.html', context)




@csrf_exempt
def send_reset_link(request):
    if request.method != "POST":
        return JsonResponse({'message': 'Invalid request method.'}, status=405)

    try:
        data = json.loads(request.body)
        email_address = data.get('email')

        if not email_address:
            return JsonResponse({'message': 'Email is required.'}, status=400)

        try:
            user = User.objects.get(email=email_address)
        except User.DoesNotExist:
            return JsonResponse({'message': 'If an account with that email exists, a password reset link has been sent.'}, status=200)

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        reset_link = request.build_absolute_uri(
            reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
        )

        subject = 'Reset Your Password'
        from_email = 'olimboyqazoqov@gmail.com'
        to_email = [user.email]

        text_content = f"""
        Hi {user.username},

        You requested a password reset. Click the link below to reset your password:

        {reset_link}

        If you didn’t request this, just ignore this email.
        """

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
            <div style="max-width: 600px; margin: auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                <h2 style="color: #333;">Hello, {user.username} 👋</h2>
                <p style="color: #555;">We received a request to reset your password. Click the button below to choose a new one:</p>
                <a href="{reset_link}" style="display: inline-block; margin: 20px 0; padding: 12px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 4px;">Reset Password</a>
                <p style="color: #888;">If you didn’t request this, just ignore this email.</p>
                <hr style="margin-top: 40px;">
                <p style="font-size: 12px; color: #aaa;">This link will expire soon for security reasons.</p>
            </div>
        </body>
        </html>
        """

        msg = EmailMultiAlternatives(subject, text_content, from_email, to_email)
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        return JsonResponse({'message': 'If an account with that email exists, a password reset link has been sent.'}, status=200)

    except json.JSONDecodeError:
        return JsonResponse({'message': 'Invalid JSON in request body.'}, status=400)
    except Exception as e:
        print(f"Error sending reset email: {e}")
        return JsonResponse({'message': "A server error occurred. Please try again later."}, status=500)


def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (User.DoesNotExist, ValueError, TypeError):
        user = None
        raise Http404("Invalid link")

    if not default_token_generator.check_token(user, token):
        raise Http404("Invalid or expired token")

    if request.method == "POST":
        form = SetPasswordForm(user, request.POST)
        if form.is_valid():
            form.save()
            return redirect("password_reset_complete")
    else:
        form = SetPasswordForm(user)


    return render(request, "accounts/password_reset_confirm.html", {"form": form, 'username': user.username})


def password_reset_complete(request):
    return render(request, "accounts/password_reset_complete.html")

def password_reset_done(request):
    return render(request, "accounts/password_reset_done.html")

def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            user = User.objects.get(email=email)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(reverse('password_reset_confirm', args=[uid, token]))

            text_content = f"""
            Hi {user.username},

            You requested a password reset. Click the link below to reset your password:

            {reset_link}

            If you didn’t request this, just ignore this email.
            """

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px;">
                <div style="max-width: 600px; margin: auto; background-color: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                    <h2 style="color: #333;">Hello, {user.username} 👋</h2>
                    <p style="color: #555;">We received a request to reset your password. Click the button below to choose a new one:</p>
                    <a href="{reset_link}" style="display: inline-block; margin: 20px 0; padding: 12px 20px; background-color: #007BFF; color: white; text-decoration: none; border-radius: 4px;">Reset Password</a>
                    <p style="color: #888;">If you didn’t request this, just ignore this email.</p>
                </div>
            </body>
            </html>
            """

            email = EmailMultiAlternatives("🛠 Reset your password", text_content, None, [user.email])
            email.attach_alternative(html_content, "text/html")
            email.send()

            return redirect('password_reset_done')
        except User.DoesNotExist:
            messages.error(request, "🚫 You are not signed up. Please register first.")
    return render(request, "accounts/password_reset.html")




def contact_view(request):
    form = ContactForm()
    success = False

    if request.method == 'POST':
        form = ContactForm(request.POST)
        recaptcha_token = request.POST.get('g-recaptcha-response')
        recaptcha_url = 'https://www.google.com/recaptcha/api/siteverify'
        recaptcha_data = {
            'secret': settings.RECAPTCHA_SECRET_KEY,
            'response': recaptcha_token
        }
        recaptcha_resp = requests.post(recaptcha_url, data=recaptcha_data)
        result = recaptcha_resp.json()

        if form.is_valid() and result.get('success'):
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data['subject']
            message = form.cleaned_data['message']

            # Send email (or save to DB/logs/etc.)
            full_message = f"From: {name} <{email}>\n\n{message}"
            send_mail(subject, full_message, settings.DEFAULT_FROM_EMAIL, [settings.CONTACT_RECEIVER_EMAIL])
            success = True
            form = ContactForm()  # Reset form
        else:
            form.add_error(None, "reCAPTCHA verification failed. Please try again.")

    return render(request, 'contact.html', {
        'form': form,
        'success': success
    })


def privacy_policy_view(request):
    return render(request, 'privacy_policy.html')


def terms_conditions_view(request):
    return render(request, 'terms_conditions.html')




def country_code_to_flag(country_code):
    # Convert 'US' → 🇺🇸
    return ''.join([chr(127397 + ord(char)) for char in country_code.upper()])


def generate_city_timezone_map():
    city_map = []
    for country_code, tz_list in country_timezones.items():
        try:
            country = pycountry.countries.get(alpha_2=country_code)
            flag = country_code_to_flag(country_code)
        except Exception:
            continue

        for tz in tz_list:
            parts = tz.split('/')
            if len(parts) > 1:
                city_name = parts[1].replace('_', ' ')
                label = f"{flag} {city_name}, {country.name}"
                city_map.append((label, tz))

    return sorted(city_map, key=lambda x: x[0])



def time_difference_view(request):
    time_diff = None
    time1 = time2 = None
    tz1_selected = None
    tz2_selected = None
    
    
    city_map = generate_city_timezone_map()
    
    timezone_dict = dict(city_map)
    reverse_timezone_labels = {tz: label for label, tz in city_map}
    

    timezones = pytz.common_timezones # Common timezones are usually sufficient

    if request.method == 'POST':
        tz1_selected = request.POST.get('timezone1')
        tz2_selected = request.POST.get('timezone2')

        try:
            zone1 = pytz.timezone(tz1_selected)
            zone2 = pytz.timezone(tz2_selected)

            # Get current UTC time and localize to target timezones
            current_utc_time = datetime.now(pytz.utc)

            time1_dt = current_utc_time.astimezone(zone1)
            time2_dt = current_utc_time.astimezone(zone2)

            time1 = time1_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')
            time2 = time2_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')

            # Calculate the difference in UTC offsets
            offset1 = time1_dt.utcoffset()
            offset2 = time2_dt.utcoffset()

            diff_seconds = abs((offset1 - offset2).total_seconds())
            hours = int(diff_seconds // 3600)
            minutes = int((diff_seconds % 3600) // 60)
            time_diff = f"{hours} hours, {minutes} minutes"
            
            # ✅ Save to user history if logged in
            if request.user.is_authenticated:
                try:
                    # Prepare input and result strings
                    input_data_str = (
                            f"First timezone: {zone1}, Second timezone: {zone2},  Time in first timezone: {time1}, Time in second timezone: {time2}"
                        )
                    result_data_str = (
                        f"Difference between timezones: ${time_diff}"
                    )

                    # Get IP and fallback to default if needed
                    ip = get_client_ip(request)
                    if ip in ['127.0.0.1', '::1', None]:
                        ip = '8.8.8.8'  # Default IP (e.g., New York)

                    # Get city, country, and timezone by IP
                    reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                    geo_info = reader.city(ip)
                    city = geo_info.city.name or "Unknown"
                    country = geo_info.country.name or "Unknown"
                    timezone_str = geo_info.location.time_zone or "America/New_York"
                    reader.close()

                    # Get aware datetime using the user's timezone
                    user_timezone = pytz.timezone(timezone_str)
                    aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                    # Save to history
                    UserHistory.objects.create(
                        user=request.user,
                        tool_name="Time difference calculator",
                        input_data=input_data_str,
                        result_data=result_data_str,
                        created_at=aware_time,
                        city=city,
                        country=country,
                        user_email=request.user.email,
                        username=request.user.username
                    )
                    print(f"[✓] Calculated time difference history saved for {request.user.username}")

                except Exception as e:
                    print(f"[!] Error saving Calculated time difference history for {request.user.username}: {e}")
                    traceback.print_exc()    

        except pytz.exceptions.UnknownTimeZoneError:
            time_diff = "Error: Invalid timezone selected."
        except Exception as e:
            time_diff = f"An unexpected error occurred: {str(e)}"
            traceback.print_exc()

    return render(request, 'time_difference.html', {
        'time1': time1,
        'time2': time2,
        'time_diff': time_diff,
        'tz1_selected': tz1_selected,
        'tz2_selected': tz2_selected,
        'timezone_dict': timezone_dict,
        'timezones': [label for label, _ in city_map],
        'reverse_timezone_labels' : reverse_timezone_labels,
        })
    





# Helper to get country from code or name


def get_countries_by_dial_code(dial_code):
    try:
        dial_code = int(str(dial_code).lstrip("+"))
        from phonenumbers.phonenumberutil import COUNTRY_CODE_TO_REGION_CODE
        regions = COUNTRY_CODE_TO_REGION_CODE.get(dial_code, [])
        countries = []

        for region in regions:
            try:
                country = pycountry.countries.get(alpha_2=region)
                iso = country.alpha_2
                example_number = phonenumbers.example_number_for_type(iso, phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE)
                example_number_formatted = phonenumbers.format_number(example_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL) if example_number else None
                if country:
                    countries.append({
                        "name": country.name,
                        "iso": country.alpha_2,
                        "code": f"{dial_code}",
                        'example_number': example_number_formatted
                    })
            except:
                continue

        return countries if countries else None
    except:
        return None

# Helper to get country from code or name
def get_country_info(value):
    v = value.strip()

    # 1. It's a numeric dial code (with or without '+')
    if v.replace("+", "").isdigit():
        return get_countries_by_dial_code(v)

    # 2. It's a country ISO code or name
    try:
        country = pycountry.countries.get(alpha_2=v.upper())
        if not country:
            country = pycountry.countries.search_fuzzy(v)[0]

        iso = country.alpha_2
        dial_code = phonenumbers.country_code_for_region(iso)
        example_number = phonenumbers.example_number_for_type(iso, phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE)
        example_number_formatted = phonenumbers.format_number(example_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL) if example_number else None
        return [{
            "name": country.name,
            "iso": iso,
            "code": f"{dial_code}",
            'example_number': example_number_formatted
        }]
    except:
        return None

def phone_formatter_view(request):
    result = None
    error = None

    if request.method == "POST":
        query = request.POST.get("query", "").strip()
        result = get_country_info(query)

        if not result:
            error = "No matching countries found. Try ISO code, full name, or dial code."
            
        # ✅ Save to user history if logged in
        if request.user.is_authenticated:
            try:
                # Prepare input and result strings
                input_data_str = (
                        f"Value: {query.strip()}"
                    )
                result_data_str = ", ".join(
                    f"ISO Code: {item['iso']}, Dial Code: {item['code']}" for item in result
                )

                # Get IP and fallback to default if needed
                ip = get_client_ip(request)
                if ip in ['127.0.0.1', '::1', None]:
                    ip = '8.8.8.8'  # Default IP (e.g., New York)

                # Get city, country, and timezone by IP
                reader = geoip2.database.Reader(settings.GEOIP_PATH + "/GeoLite2-City.mmdb")
                geo_info = reader.city(ip)
                city = geo_info.city.name or "Unknown"
                country = geo_info.country.name or "Unknown"
                timezone_str = geo_info.location.time_zone or "America/New_York"
                reader.close()

                # Get aware datetime using the user's timezone
                user_timezone = pytz.timezone(timezone_str)
                aware_time = datetime.now(pytz.utc).astimezone(user_timezone)

                # Save to history
                UserHistory.objects.create(
                    user=request.user,
                    tool_name="Phone country or code find",
                    input_data=input_data_str,
                    result_data=result_data_str,
                    created_at=aware_time,
                    city=city,
                    country=country,
                    user_email=request.user.email,
                    username=request.user.username
                )
                print(f"[✓] Phone country or code find history saved for {request.user.username}")

            except Exception as e:
                print(f"[!] Error saving Phone country or code find history for {request.user.username}: {e}")
                traceback.print_exc() 

    return render(request, "country_code_lookup.html", {
        "result": result,
        "error": error
    })
