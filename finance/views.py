from django.http import JsonResponse
from django.db.models import Sum
from .models import Sale, Expense 
from . models import *
from django.shortcuts import render, get_object_or_404
import datetime, json
from loguru import logger
from . forms import (
    ExpensesForm,
    ExpenseCategoryForm
)
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from datetime import  timedelta


def get_current_month():
    return datetime.datetime.now().month

def get_current_year():
    return datetime.datetime.now().year

def sale(request):
    sales = Sale.objects.all()
    return render(request, 'finance/sales.html', 
        {
            'sales':sales
        }    
    )
    
def finance(request):
    sales = Sale.objects.filter(date__month = get_current_month()).order_by('-date')[:8]
    expenses = Expense.objects.filter(date__month = get_current_month()).order_by('-date')[:8]
    
    return render(request, 'finance/finance.html', 
        {
            'sales':sales,
            'expenses':expenses
        }
    )
    
def get_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id)
    data = {
        'id': expense.id,
        'amount': expense.amount,
        'description': expense.description,
        'category': expense.category.id
    }
    return JsonResponse({'success': True, 'data': data})

@transaction.atomic
def expenses(request):
    form = ExpensesForm()
    cat_form = ExpenseCategoryForm()
    if request.method == 'GET':
        expenses = Expense.objects.all().order_by('-date')
        return render(request, 'finance/expenses.html', 
            {
                'form':form,
                'cat_form':cat_form,
                'expenses':expenses
            }
        )
    
    if request.method == 'POST':
        #payload
        """
            {
                amount:float
                description:str
                category:id (int)
            }
        """
        try:
            data = json.loads(request.body)
            
            amount = data.get('amount')
            description = data.get('description')
            category = data.get('category')
            
            if not amount or not description or not category:
                return JsonResponse({'success':False, 'message':'Missing fields: amount, description, category.'})
            
            try:
                category = ExpenseCategory.objects.get(id=category)
            except ExpenseCategory.DoesNotExist:
                return JsonResponse({'success':False, 'message':f'Category with ID: {category}, doesn\'t exists.'})
            
            expense = Expense.objects.create(
                amount = amount,
                category = category,
                user = User.objects.get(id=1),
                cancel = False,
                description = description
            )
            
            CashBook.objects.create(
                amount = amount,
                expense = expense,
                credit = True,
                description=f'Expense ({expense.description[:20]})'
            )
      
            return JsonResponse({'success': True, 'messages':'Expense successfully created'}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
        
def add_or_edit_expense(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            amount = data.get('amount')
            description = data.get('description')
            category_id = data.get('category')
            expense_id = data.get('id')

            if not amount or not description or not category_id:
                return JsonResponse({'success': False, 'message': 'Missing fields: amount, description, category.'})
            
            category = get_object_or_404(ExpenseCategory, id=category_id)

            if expense_id:  
                expense = get_object_or_404(Expense, id=expense_id)
                expense.amount = amount
                expense.description = description
                expense.category = category
                expense.save()
                message = 'Expense successfully updated'
            else:  
                expense = Expense.objects.create(
                    amount=amount,
                    description=description,
                    category=category,
                    user=request.user,  
                )
                message = 'Expense successfully created'

            return JsonResponse({'success': True, 'message': message}, status=201)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)

@transaction.atomic
def delete_expense(request, expense_id):
    if request.method == 'DELETE':
        try:
            expense = get_object_or_404(Expense, id=expense_id)
            expense.cancel = True
            expense.save()
            
            CashBook.objects.create(
                amount=expense.amount,
                debit=True,
                credit=False,
                description=f'Expense ({expense.description}): cancelled'
            )
            return JsonResponse({'success': True, 'message': 'Expense successfully deleted'})
        except Exception as e:
             return JsonResponse({'success': False, 'message': str(e)}, status=400)
    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=400)


def cashbook(request):
    filter_option = request.GET.get('filter', 'this_week')
    now = datetime.datetime.now()

    if filter_option == 'this_week':
        start_date = now - timedelta(days=now.weekday()) 
    elif filter_option == 'yesterday':
        start_date = now - timedelta(days=1)
    elif filter_option == 'this_month':
        start_date = now.replace(day=1)
    elif filter_option == 'last_month':
        start_date = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
    elif filter_option == 'this_year':
        start_date = now.replace(month=1, day=1)
    else:
        start_date = now - timedelta(days=now.weekday())

    entries = CashBook.objects.filter(date__gte=start_date).order_by('-date')
    
    debit_entries = entries.filter(debit=True)
    credit_entries = entries.filter(credit=True)

    return render(request, 'finance/cashbook.html', {
        'filter_option': filter_option,
        'debit_entries': debit_entries,
        'credit_entries': credit_entries,
    })


def add_expense_category(request):
    categories = ExpenseCategory.objects.all().values()
    
    if request.method == 'POST':
        data = json.loads(request.body)
        category = data['name']
        logger.info(data)
        
        if ExpenseCategory.objects.filter(name=category).exists():
            return JsonResponse({'success':False, 'message':f'Category with ID {category} Exists.'}, status=400)
        
        ExpenseCategory.objects.create(
            name=category
        )
        return JsonResponse({'success':True}, status=201)
    return JsonResponse(list(categories), safe=False)

def income_json(request):
    current_month = get_current_month()
    month = request.GET.get('month', current_month)
    sales_total = Sale.objects.filter(date__month=month).aggregate(Sum('total_amount'))
    logger.info(f'Sales: {sales_total}')
    return JsonResponse({'sales_total': sales_total['total_amount__sum'] or 0})

def expense_json(request):
    current_month = get_current_month()
    month = request.GET.get('month', current_month)
    expense_total = Expense.objects.filter(date__month=month, cancel=False).aggregate(Sum('amount'))
    logger.info(f'Sales: {expense_total}')
    return JsonResponse({'expense_total': expense_total['amount__sum'] or 0})

def income_graph(request):
    current_year = get_current_year()
    monthly_sales = Sale.objects.filter(date__year=current_year).values('date__month').annotate(total=Sum('total_amount')).order_by('date__month')
    data = {month['date__month']: month['total'] for month in monthly_sales}
    return JsonResponse(data)

def expense_graph(request):
    current_year = get_current_year()
    monthly_expenses = Expense.objects.filter(date__year=current_year).values('date__month').annotate(total=Sum('amount')).order_by('date__month')
    data = {month['date__month']: month['total'] for month in monthly_expenses}
    return JsonResponse(data)