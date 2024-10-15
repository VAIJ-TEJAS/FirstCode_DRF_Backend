from django.db import models
from django.contrib.auth.models import User
from user.models import Pattern


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    MAIN_CATEGORY_CHOICES = [
        ("Professional", "Professional"),
        ("Personal", "Personal"),
    ]

    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    tags = models.ManyToManyField(Tag, blank=True)
    main_category = models.CharField(max_length=50, choices=MAIN_CATEGORY_CHOICES)
    name = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500)
    long_description = models.TextField()
    requirements = models.TextField()
    cover_image = models.ImageField(upload_to="courses/", blank=True, null=True)
    is_paid = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True) 

    def __str__(self):
        return self.name


class Track(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='tracks')
    pattern = models.ForeignKey(Pattern, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Chapter(models.Model):
    track = models.ForeignKey(Track, on_delete=models.CASCADE, related_name='chapters')
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class Lesson(models.Model):
    PLAYGROUND_TYPE_CHOICES = [
        ("Python", "Python"),
        ("Jupyter", "Jupyter"),
    ]

    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE, related_name='lessons')
    name = models.CharField(max_length=255)
    short_description = models.CharField(max_length=500)
    long_description = models.TextField()
    requirements = models.TextField()
    video_url = models.URLField(blank=True, null=True)
    blog_link = models.URLField(blank=True, null=True)
    playground_type = models.CharField(max_length=50, choices=PLAYGROUND_TYPE_CHOICES)
    quote = models.CharField(max_length=255, blank=True, null=True)
    iframe_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name


class Task(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='tasks')
    name = models.CharField(max_length=255)
    description = models.TextField()

    def __str__(self):
        return self.name


class UserCourse(models.Model):
    STATUS_CHOICES = [
        ('Enrolled', 'Enrolled'),
        ('Started', 'Started'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    certificate_id = models.CharField(max_length=255, blank=True, null=True)
    certificate = models.FileField(upload_to='certificates/', blank=True, null=True)
    completed_chapters = models.IntegerField(default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES) 
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.course.name}"


class UserChapter(models.Model):
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE)
    completed_lessons = models.IntegerField(default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='In Progress')
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.chapter.name}"


class UserLesson(models.Model):
    STATUS_CHOICES = [
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE)
    completed_tasks = models.IntegerField(default=0)
    progress = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='In Progress')
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.lesson.name}"


class UserTask(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    last_modified = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.task.name}"
