from django.db import models
from django.shortcuts import reverse


class Category(models.Model):
    name = models.CharField('Название категории', max_length=50, default='Название')
    description = models.TextField('Описание категории', default='Описание')

    def __str__(self):
        return f'{self.id}. {self.name}'

    def get_absolute_url(self):
        return reverse('category_detail_url', kwargs={'pk': self.id})

    class Meta:
        ordering = ['id']
        verbose_name = 'Категория задания'
        verbose_name_plural = 'Категории заданий'
def default_head_answers():
    return {'questions': 'ВОПРОСЫ','answers': 'ОТВЕТЫ'}

class Task(models.Model):
    title = models.CharField('Название', max_length=50, db_index=True)
    description = models.TextField('Текст задания')
    difficulty_level = models.IntegerField('Сложность')
    max_score = models.IntegerField('Макс.балл')
    categories = models.ManyToManyField('Category', blank=True, related_name='tasks')
    head_answers = models.JSONField('Заголовки вопросов-ответов', blank=True, default=default_head_answers)
    answers = models.ManyToManyField('Answer', blank=True, related_name='tasks')

    def __str__(self):
        return f'{self.id}. {self.title}'

    def get_absolute_url(self):
        return reverse('task_detail_url', kwargs={'pk': self.id})

    class Meta:
        ordering = ['-id']
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'

class Assessment_criteria(models.Model):
    name = models.CharField('Название', max_length=50)
    description = models.TextField('Описание')

    def __str__(self):
        return f'{self.id}. {self.name} ({self.description})'

    def get_absolute_url(self):
        return f'/tasks/{self.id}'

    class Meta:
        ordering = ['id']
        verbose_name = 'Критерий оценивания'
        verbose_name_plural = 'Критерии оценивания'

class Task_criteria_mapping(models.Model):
    task_id = models.fields.IntegerField('ссылка на Задание')
    criteria_id = models.fields.IntegerField('ссылка на Критерий')
    weight = models.fields.DecimalField('Вес', max_digits=5,decimal_places=2)
    max_points = models.fields.IntegerField('Максимально пунктов')

    def __str__(self):
        return f'({self.task_id}, {self.criteria_id}, {self.weight}, {self.max_points})'

    def get_absolute_url(self):
        return f'/tasks/{self.id}'

    class Meta:
        ordering = ['task_id', 'criteria_id']
        verbose_name = 'Связь между заданиями и критериями с весами'
        verbose_name_plural = 'Связи между заданиями и критериями с весами'

class Answer(models.Model):
    task_id = models.IntegerField('task_id')
    question = models.TextField('Вопрос', blank=True, default='Вопрос..')
    answer_key = models.TextField('Правильный ответ')
    alternative_answers = models.TextField('Прочие ответы')
    explanation = models.TextField('Объяснение')

    def __str__(self):
        return f'{self.task_id}, {self.answer_key}, {self.alternative_answers}, {self.explanation}'

    def get_absolute_url(self):
        return f'/tasks/{self.id}'
    class Meta:
        ordering = ['task_id']
        verbose_name = 'Ключи/ответы к заданию'
        verbose_name_plural = 'Ключи/ответы к заданиям'

class Variant(models.Model):
    variant_id = models.fields.IntegerField('Номер варианта')
    name = models.TextField('Название')
    created_at = models.DateTimeField('Дата создания',auto_created=True)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='variants', null=True)
    tasks = models.ManyToManyField('Task', blank=True, related_name='variants')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('variant_detail_url', kwargs={'pk': self.id})

    class Meta:
        ordering = ['-created_at', '-variant_id']
        verbose_name = 'Вариант'
        verbose_name_plural = 'Варианты'

class Student_task_resuts(models.Model):
    result_id = models.fields.IntegerField('Результат')
    student_id = models.fields.IntegerField('Студент')
    task_id = models.fields.IntegerField('Задание')
    submission_date = models.DateTimeField('Дата выполнения')
    total_score = models.fields.DecimalField('Всего баллов', max_digits=5,decimal_places=2)
    feedback = models.TextField('Обратная связь')

    def __str__(self):
        return f'student_id={self.student_id})'

    def get_absolute_url(self):
        return f'/tasks/{self.id}'

    class Meta:
        ordering = ['student_id', 'task_id']
        verbose_name = 'Результат выполнения заданий по студенту'
        verbose_name_plural = 'Результаты выполнения заданий по студенту'

class Result_criteria_scores(models.Model):
    result_id = models.fields.IntegerField('Результат')
    criteria_id = models.fields.IntegerField('Критерий')
    score = models.fields.DecimalField('Баллы', max_digits=5,decimal_places=2)
    comment = models.TextField('Комментарий')

    def __str__(self):
        return self.comment

    def get_absolute_url(self):
        return f'/tasks/{self.id}'

    class Meta:
        verbose_name = 'Детализация оценок по критерию'
        verbose_name_plural = 'Детализации оценок по критериям'