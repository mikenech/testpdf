from django.shortcuts import render, redirect
import pdfkit, os
import threading
import signal
import tempfile
from threading import Thread, Timer
from functools import wraps
import re
import asyncio

from xhtml2pdf import pisa
from django.template.loader import render_to_string
from django.http import HttpResponse, JsonResponse
from django.utils.safestring import mark_safe
import random
from datetime import datetime
#from .forms import variantForm
from .models import Task, Category, Variant
from django.db.models import Q
from django.views.generic import ListView, DetailView
from .utils import CategoriesMixin
from django.template.loader import get_template

# Импортируем Playwright вместо WeasyPrint
from playwright.async_api import async_playwright

# Функция для предварительной обработки математических формул
def process_math_formulas(html_content):
    """
    Обрабатывает LaTeX формулы в HTML и заменяет их на более простое HTML представление
    """
    print(">>> Обработка математических формул")
    
    # Обработка дробей \frac{числитель}{знаменатель}
    def replace_frac(match):
        num = match.group(1)
        den = match.group(2)
        return f'<span class="fraction"><span class="num">{num}</span><span class="den">{den}</span></span>'
    
    # Обработка корней \sqrt{выражение}
    def replace_sqrt(match):
        expr = match.group(1)
        return f'<span class="sqrt">{expr}</span>'
    
    # Обработка степеней x^{степень}
    def replace_power(match):
        base = match.group(1)
        power = match.group(2)
        return f'{base}<sup>{power}</sup>'
    
    # Обработка индексов x_{индекс}
    def replace_index(match):
        base = match.group(1)
        index = match.group(2)
        return f'{base}<sub>{index}</sub>'
        
    # Обработка вложенных фигурных скобок для более сложных выражений
    def process_nested_braces(text):
        # Рекурсивная функция для обработки вложенных скобок
        def find_matching_brace(text, start):
            level = 1
            i = start
            while i < len(text):
                if text[i] == '{':
                    level += 1
                elif text[i] == '}':
                    level -= 1
                    if level == 0:
                        return i
                i += 1
            return -1
            
        # Обработка \frac с поддержкой вложенности
        i = 0
        result = ""
        while i < len(text):
            if text[i:i+5] == '\\frac' and i+5 < len(text) and text[i+5] == '{':
                num_start = i + 6
                num_end = find_matching_brace(text, num_start)
                if num_end > -1:
                    den_start = num_end + 2  # Пропускаем закрывающую и открывающую скобки
                    if den_start < len(text) and text[den_start-1] == '{':
                        den_end = find_matching_brace(text, den_start)
                        if den_end > -1:
                            num = text[num_start:num_end]
                            den = text[den_start:den_end]
                            # Рекурсивно обрабатываем числитель и знаменатель
                            num = process_nested_braces(num)
                            den = process_nested_braces(den)
                            result += f'<span class="fraction"><span class="num">{num}</span><span class="den">{den}</span></span>'
                            i = den_end + 1
                            continue
            elif text[i:i+5] == '\\sqrt' and i+5 < len(text) and text[i+5] == '{':
                expr_start = i + 6
                expr_end = find_matching_brace(text, expr_start)
                if expr_end > -1:
                    expr = text[expr_start:expr_end]
                    # Рекурсивно обрабатываем выражение под корнем
                    expr = process_nested_braces(expr)
                    result += f'<span class="sqrt">{expr}</span>'
                    i = expr_end + 1
                    continue
            elif i+1 < len(text) and text[i+1] == '^' and i+2 < len(text) and text[i+2] == '{':
                base = text[i]
                pow_start = i + 3
                pow_end = find_matching_brace(text, pow_start)
                if pow_end > -1:
                    power = text[pow_start:pow_end]
                    # Рекурсивно обрабатываем степень
                    power = process_nested_braces(power)
                    result += f'{base}<sup>{power}</sup>'
                    i = pow_end + 1
                    continue
            elif i+1 < len(text) and text[i+1] == '_' and i+2 < len(text) and text[i+2] == '{':
                base = text[i]
                idx_start = i + 3
                idx_end = find_matching_brace(text, idx_start)
                if idx_end > -1:
                    index = text[idx_start:idx_end]
                    # Рекурсивно обрабатываем индекс
                    index = process_nested_braces(index)
                    result += f'{base}<sub>{index}</sub>'
                    i = idx_end + 1
                    continue
            
            result += text[i]
            i += 1
            
        return result
    
    # Обрабатываем вложенные структуры
    html_content = process_nested_braces(html_content)
    
    # Затем применяем обычные регулярные выражения для оставшихся простых случаев
    patterns = [
        (r'\\frac\{([^{}]*)\}\{([^{}]*)\}', replace_frac),  # Дроби
        (r'\\sqrt\{([^{}]*)\}', replace_sqrt),  # Корни
        (r'([a-zA-Z0-9])\^\{([^{}]*)\}', replace_power),  # Степени
        (r'([a-zA-Z0-9])_\{([^{}]*)\}', replace_index),  # Индексы
        # Дополнительные паттерны для простых выражений
        (r'\\sum_\{([^{}]*)\}\^\{([^{}]*)\}', lambda m: f'<span class="sum"><span class="symbol">∑</span><sub>{m.group(1)}</sub><sup>{m.group(2)}</sup></span>'),  # Сумма
        (r'\\int_\{([^{}]*)\}\^\{([^{}]*)\}', lambda m: f'<span class="integral"><span class="symbol">&#8747;</span><sub>{m.group(1)}</sub><sup>{m.group(2)}</sup></span>'),  # Интеграл с пределами
        (r'\\int', lambda m: f'<span class="integral"><span class="symbol">&#8747;</span></span>'),  # Простой интеграл
        (r'\\lim_\{([^{}]*)\}', lambda m: f'<span class="lim">lim<sub>{m.group(1)}</sub></span>'),  # Предел
    ]
    
    # Замена других часто используемых LaTeX символы и операторы
    latex_replacements = {
        r'\pi': 'π',
        r'\alpha': 'α',
        r'\beta': 'β',
        r'\gamma': 'γ',
        r'\delta': 'δ',
        r'\Delta': 'Δ',
        r'\theta': 'θ',
        r'\lambda': 'λ',
        r'\mu': 'μ',
        r'\sigma': 'σ',
        r'\Sigma': 'Σ',
        r'\phi': 'φ',
        r'\Phi': 'Φ',
        r'\Omega': 'Ω',
        r'\omega': 'ω',
        r'\times': '×',
        r'\div': '÷',
        r'\cdot': '·',
        r'\pm': '±',
        r'\mp': '∓',
        r'\infty': '∞',
        r'\approx': '≈',
        r'\equiv': '≡',
        r'\leq': '≤',
        r'\geq': '≥',
        r'\neq': '≠',
        r'\sim': '∼',
        r'\cong': '≅',
        r'\perp': '⊥',
        r'\parallel': '∥',
        r'\partial': '∂',
        r'\nabla': '∇',
        r'\forall': '∀',
        r'\exists': '∃',
        r'\in': '∈',
        r'\notin': '∉',
        r'\subset': '⊂',
        r'\supset': '⊃',
        r'\cup': '∪',
        r'\cap': '∩',
        r'\rightarrow': '→',
        r'\leftarrow': '←',
        r'\Rightarrow': '⇒',
        r'\Leftarrow': '⇐',
        r'\Leftrightarrow': '⇔',
        r'\sum': '∑',
        r'\prod': '∏',
        # Интегралы удалены из словаря, теперь они обрабатываются через паттерны
        r'\iint': '&#8748;',  # Двойной интеграл
        r'\iiint': '&#8749;', # Тройной интеграл
        r'\oint': '&#8750;',  # Контурный интеграл
        r'\mathbb{R}': 'ℝ',
        r'\mathbb{Z}': 'ℤ',
        r'\mathbb{N}': 'ℕ',
        r'\mathbb{Q}': 'ℚ',
        r'\mathbb{C}': 'ℂ',
    }
    
    for pattern, replacement_func in patterns:
        html_content = re.sub(pattern, replacement_func, html_content)
    
    for latex, symbol in latex_replacements.items():
        html_content = html_content.replace(latex, symbol)
    
    # Замена простых выражений с \text
    html_content = re.sub(r'\\text\{([^{}]*)\}', r'\1', html_content)
    
    # Простая замена выражений без фигурных скобок
    simple_patterns = [
        (r'([a-zA-Z0-9])\^([a-zA-Z0-9])', r'\1<sup>\2</sup>'),  # простая степень x^2
        (r'([a-zA-Z0-9])_([a-zA-Z0-9])', r'\1<sub>\2</sub>'),   # простой индекс x_1
    ]
    
    for pattern, replacement in simple_patterns:
        html_content = re.sub(pattern, replacement, html_content)
    
    # Обработка формул, заключенных в $ и $$
    def process_latex_dollars(html_content):
        # Обработка инлайн формул $...$
        def replace_inline_formula(match):
            formula = match.group(1)
            # Обрабатываем формулу внутри долларов
            processed_formula = process_nested_braces(formula)
            for pattern, replacement_func in patterns:
                processed_formula = re.sub(pattern, replacement_func, processed_formula)
            for latex, symbol in latex_replacements.items():
                processed_formula = processed_formula.replace(latex, symbol)
            return f'<span class="latex">{processed_formula}</span>'
        
        # Обработка блочных формул $$...$$
        def replace_block_formula(match):
            formula = match.group(1)
            # Обрабатываем формулу внутри двойных долларов
            processed_formula = process_nested_braces(formula)
            for pattern, replacement_func in patterns:
                processed_formula = re.sub(pattern, replacement_func, processed_formula)
            for latex, symbol in latex_replacements.items():
                processed_formula = processed_formula.replace(latex, symbol)
            return f'<div class="latex-display">{processed_formula}</div>'
        
        # Сначала обрабатываем блочные формулы $$...$$
        html_content = re.sub(r'\$\$(.*?)\$\$', replace_block_formula, html_content, flags=re.DOTALL)
        # Затем обрабатываем инлайн формулы $...$
        html_content = re.sub(r'\$(.*?)\$', replace_inline_formula, html_content)
        
        return html_content
    
    # Применяем обработку формул в долларах
    html_content = process_latex_dollars(html_content)
    
    return html_content

def timeout(seconds):
    """
    Декоратор для установки таймаута выполнения функции
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            error = [None]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    error[0] = e
            
            thread = Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)
            
            if thread.is_alive():
                print(f">>> ТАЙМАУТ: Функция {func.__name__} выполняется дольше {seconds} секунд")
                return HttpResponse(f"Превышено время ожидания ({seconds} секунд) при создании PDF. Возможно, слишком много данных или проблемы с рендерингом.")
            
            if error[0]:
                raise error[0]
                
            return result[0]
        return wrapper
    return decorator

class HomeView(ListView, CategoriesMixin):
    model = Task
    def get_queryset(self):
        search_query = self.request.GET.get('search', None)
        if search_query:
            return self.model.objects.filter(
                Q(title__iconteins=search_query)
            )
        return Task.objects.all()


class TaskView(DetailView, CategoriesMixin):
    model = Task

class CategoryView(DetailView, CategoriesMixin):
    model = Category

class VariantListView(ListView, CategoriesMixin):
    model = Variant
    template_name = 'tasks/variant_list.html'
    context_object_name = 'variants'

@timeout(30)  # Устанавливаем таймаут 30 секунд
async def playwright_pdf_generation_async(html_content, base_url=None):
    """
    Функция для генерации PDF с использованием Playwright с таймаутом
    """
    print(">>> Начало генерации PDF в отдельной функции...")
    
    # Создаем временный HTML-файл
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
        f.write(html_content)
        temp_html = f.name
    
    pdf_data = None
    try:
        # Запускаем Playwright
        async with async_playwright() as p:
            # Запускаем браузер
            browser = await p.chromium.launch()
            page = await browser.new_page()
            
            # Загружаем HTML из временного файла
            await page.goto(f'file://{temp_html}', wait_until='networkidle')
            
            # Добавляем скрипт, который будет проверять, что MathJax завершил рендеринг
            await page.evaluate("""
            () => {
                return new Promise((resolve) => {
                    function checkMathJax() {
                        if (window.MathJax && window.MathJax.typesetPromise) {
                            window.MathJax.typesetPromise()
                            .then(() => {
                                console.log('MathJax rendering complete');
                                resolve();
                            })
                            .catch(err => {
                                console.error('MathJax error:', err);
                                resolve(); // Resolve anyway to prevent hanging
                            });
                        } else if (document.querySelector('.MathJax')) {
                            // MathJax rendered something already
                            console.log('MathJax elements found');
                            resolve();
                        } else {
                            console.log('Waiting for MathJax...');
                            setTimeout(checkMathJax, 500);
                        }
                    }
                    
                    checkMathJax();
                });
            }
            """)
            
            # Даем дополнительное время для рендеринга (увеличиваем с 1000мс до 2000мс)
            await page.wait_for_timeout(2000)
            
            # Генерируем PDF
            pdf_data = await page.pdf(
                format='A4',
                print_background=True,
                margin={
                    'top': '1cm',
                    'right': '1cm',
                    'bottom': '1cm', 
                    'left': '1cm'
                }
            )
            
            await browser.close()
    finally:
        # Удаляем временный файл
        os.unlink(temp_html)
    
    return pdf_data

# Обертка для асинхронной функции
def playwright_pdf_generation(html_content, base_url=None):
    """
    Синхронная обертка для асинхронной функции генерации PDF
    """
    return asyncio.run(playwright_pdf_generation_async(html_content, base_url))

def generate_pdf(request, context, template_name='tasks/variant_pdf.html'):
    """
    Полноценная функция для генерации PDF с использованием Playwright
    """
    print(">>> Начало генерации PDF...")
    try:
        # Проверим контекст и его содержимое
        variant = context.get('variant')
        category = context.get('category')
        tasks = context.get('tasks')
        if variant:
            print(f">>> Вариант ID: {variant.id}, Название: {variant.name}")
        if category:
            print(f">>> Категория ID: {category.id}, Название: {category.name}")
        if tasks:
            print(f">>> Количество заданий: {len(tasks)}")
            for task in tasks:
                # Проверяем, является ли task уже словарем с title или объектом Task
                if isinstance(task, dict):
                    task_id = task.get('id')
                    task_title = task.get('title')
                else:
                    task_id = task.id
                    task_title = task.title
                print(f">>> Задание ID: {task_id}, Название: {task_title}")
        
        
        
        # Получаем шаблон и рендерим HTML с контекстом
        print(">>> Получение шаблона...")
        template = get_template(template_name)
        print(">>> Шаблон получен, рендеринг HTML...")
        html_content = template.render(context, request)
        
        print(">>> Шаблон успешно отрендерен")
        
        # Больше не обрабатываем формулы через process_math_formulas,
        # так как используем MathJax для рендеринга в PDF
        # html_content = process_math_formulas(html_content)
        print(">>> Формулы будут обработаны через MathJax при генерации PDF")
        
        try:
            # Упрощенная проверка - сохраним простой текстовый файл
            if False:  # Этот код не выполнится, но оставим для будущего
                response = HttpResponse(
                    f"Тестовый документ вместо PDF\nВариант: {variant.name if variant else 'Нет'}\nКатегория: {category.name if category else 'Нет'}\nЗаданий: {len(tasks) if tasks else 0}",
                    content_type='text/plain'
                )
                response['Content-Disposition'] = 'attachment; filename="test.txt"'
                return response
                
            # Генерируем PDF с использованием Playwright и таймаутом
            print(">>> Начало генерации PDF с Playwright с таймаутом...")
            pdf_file = playwright_pdf_generation(html_content, request.build_absolute_uri())
            print(">>> PDF успешно создан")
            
            # Создаем имя файла, используя только ASCII символы
            if variant and category:
                # Транслитерация русских символов и замена пробелов на подчеркивания
                safe_category_name = ''.join(c if c.isalnum() or c == '_' else '_' for c in str(category.name))
                filename = f"variant_{variant.id}_{safe_category_name}.pdf"
            else:
                filename = "document.pdf"
            
            print(f">>> Имя файла: {filename}")
            
            # Настраиваем HTTP-ответ для скачивания
            print(">>> Настройка HTTP-ответа...")
            response = HttpResponse(pdf_file, content_type='application/pdf')
            # Используем простое имя файла без специальных символов
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            print(">>> PDF готов к отправке")
            return response
        except Exception as e:
            print(f">>> Ошибка при генерации PDF: {str(e)}")
            # Возвращаем HTML вместо сообщения об ошибке для диагностики
            return HttpResponse(f"<h1>Ошибка при создании PDF</h1><p>{str(e)}</p><pre>{html_content[:1000]}...</pre>")
            
    except Exception as e:
        print(f">>> Общая ошибка: {str(e)}")
        return HttpResponse(f'<h1>Ошибка при создании PDF</h1><p>{str(e)}</p>')

def Variant_HTML(reqiest,pk):
    print(f">>> Запрос HTML для варианта с ID {pk}")
    try:
        variant = Variant.objects.get(pk=int(pk))
        category = variant.category
        tasks = list(variant.tasks.all())  # Преобразуем QuerySet в list
        
        # Создаем контекст для шаблона
        context = {'variant': variant, 'category': category, 'tasks': tasks}
        print(f">>> Создан контекст для варианта {variant.name}")
        
        # Прямой рендеринг шаблона - MathJax будет обрабатывать формулы в браузере
        return render(reqiest, 'tasks/variant_pdf.html', context=context)
    except Exception as e:
        print(f">>> Ошибка при получении HTML дляварианта: {str(e)}")
        return HttpResponse(f'Ошибка при получении HTML дляварианта: {str(e)}')

def Variant_PDF(reqiest,pk):
    print(f">>> Запрос PDF для варианта с ID {pk}")
    try:
        variant = Variant.objects.get(pk=int(pk))
        category = variant.category
        tasks = list(variant.tasks.all())  # Преобразуем QuerySet в list
        
        # Создаем контекст для шаблона
        context = {'variant': variant, 'category': category, 'tasks': tasks}
        print(f">>> Создан контекст для варианта {variant.name}")
        
        # Используем Playwright для генерации PDF
        return generate_pdf(reqiest, context)
    except Exception as e:
        print(f">>> Ошибка при получении варианта: {str(e)}")
        return HttpResponse(f'Ошибка при получении варианта: {str(e)}')

def Variant_new(reqiest):
    print(">>> Начало создания нового варианта...")
    try:
        print(">>> Получение данных из формы...")
        
        # Проверяем, существует ли уже вариант с такими параметрами
        variant_id = int(reqiest.POST['variant_id'])
        category_id = int(reqiest.POST['category_id'])
        name = str(reqiest.POST['name'])
        
        existing_variant = Variant.objects.filter(
            variant_id=variant_id,
            category_id=category_id,
            name=name
        ).first()
        
        if existing_variant:
            # Если вариант существует, используем его
            print(f">>> Вариант уже существует: {name}, ID: {existing_variant.id}")
            variant = existing_variant
        else:
            # Создаем новый вариант
            variant = Variant()
            variant.category = Category.objects.get(pk=category_id)
            variant.variant_id = variant_id
            variant.name = name
            _tasks_num = int(reqiest.POST['tasks_num'])
            variant.created_at = datetime.now()
            
            print(f">>> Сохранение варианта: {variant.name}, категория: {variant.category.name}, задания: {_tasks_num}")
            variant.save()
            
            print(">>> Выборка заданий...")
            _l = list(variant.category.tasks.all())
            _l = random.sample(_l,min(_tasks_num,len(_l)))
            variant.tasks.set(_l)
            print(f">>> Добавлено {len(_l)} заданий")

        # Создаем контекст для шаблона
        context = {'variant': variant,
                   'category': variant.category, 
                   'tasks': list(variant.tasks.all())}
        
        # Если запрос требует вернуть PDF, генерируем его с Playwright
        if reqiest.POST.get('generate_pdf', False):
            print(">>> Запрошена генерация PDF...")
            return generate_pdf(reqiest, context)
        
        # По умолчанию возвращаем HTML-страницу
        print(">>> Возвращаем HTML...")
        return render(reqiest, 'tasks/variant_pdf.html', context)
    except Exception as e:
        print(f">>> Ошибка при создании варианта: {str(e)}")
        return HttpResponse(f'<h1>Ошибка при создании варианта</h1><p>{str(e)}</p>')

def test_template_tags(request):
    """Simple view to test template tags"""
    return render(request, 'tasks/test_template.html')

def task_edit(request):
    """Handle AJAX requests to edit task fields"""
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        field = request.POST.get('field')
        value = request.POST.get('value')
        
        # Проверяем, что все необходимые данные присутствуют
        if not all([task_id, field, value]):
            return JsonResponse({'success': False, 'error': 'Не все необходимые данные предоставлены'})
        
        # Проверяем, что поле допустимо для редактирования
        valid_fields = ['title', 'description', 'answer', 'solution', 'difficulty']
        if field not in valid_fields:
            return JsonResponse({'success': False, 'error': 'Недопустимое поле для редактирования'})
        
        try:
            # Получаем задание для обновления
            task = Task.objects.get(pk=int(task_id))
            
            # Обновляем указанное поле
            setattr(task, field, value)
            task.save()
            
            # Для полей с формулами возвращаем обработанный HTML
            response_data = {'success': True}
            if field in ['description', 'answer', 'solution']:
                # Получаем HTML с обработанными формулами
                processed_html = mark_safe(value)
                response_data['html'] = processed_html
            
            return JsonResponse(response_data)
            
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Задание не найдено'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    # Если запрос не POST
    return JsonResponse({'success': False, 'error': 'Метод не поддерживается'})

