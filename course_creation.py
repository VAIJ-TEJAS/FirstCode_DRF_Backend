import random
from course.models import Course, Track, Chapter, Lesson, Task, Category  # Make sure to use your actual app name
from django.contrib.auth.models import User

# Assuming there is a category with id=1 already in the database
category = Category.objects.get(id=1)  # Get the category you want to use

# Define the main category choices
MAIN_CATEGORY_CHOICES = ["Professional", "Personal"]

# Create 20 courses
for i in range(1, 21):
    # Randomly select a main category and is_paid status
    main_category = random.choice(MAIN_CATEGORY_CHOICES)
    is_paid = random.choice([True, False])  # Randomly choose between True and False

    # Create a Course
    course = Course.objects.create(
        category=category,  # Use the retrieved category
        name=f"Course {i}",
        short_description=f"Short description for Course {i}",
        long_description=f"Long description for Course {i}",
        requirements="Basic knowledge required.",
        main_category=main_category,  # Set random main category
        is_paid=is_paid,  # Set random is_paid status
        cover_image=None,  # Set to None or a valid path to an image
    )

    # Create a Track for each Course
    track = Track.objects.create(
        course=course,  # Associate the track with the course
        pattern_id=1,  # Assuming pattern with id=1 already exists
        name=f"Track for Course {i}",
        description=f"Description for Track of Course {i}",
    )

    # Create 5 chapters for each course
    for j in range(1, 6):
        chapter = Chapter.objects.create(
            track=track,  # Associate the chapter with the created track
            name=f"Chapter {j} for Course {i}",
            description=f"Description for Chapter {j} of Course {i}",
        )

        # Create 3 lessons for each chapter
        for k in range(1, 4):
            lesson = Lesson.objects.create(
                chapter=chapter,
                name=f"Lesson {k} for Chapter {j} of Course {i}",
                short_description=f"Short description for Lesson {k}",
                long_description=f"Long description for Lesson {k}",
                requirements="No specific requirements.",
                playground_type="Python",  # Adjust as necessary
                video_url=None,  # Optionally provide a video URL
                blog_link=None,  # Optionally provide a blog link
                quote=None,  # Optionally provide a quote
                iframe_url=None,  # Optionally provide an iframe URL
            )

            # Create 4 tasks for each lesson
            for l in range(1, 5):
                task = Task.objects.create(
                    lesson=lesson,
                    name=f"Task {l} for Lesson {k}",
                    description=f"Description for Task {l}",
                )

    print(f"Created Course {i} with a Track, Chapters, Lessons, and Tasks.")
