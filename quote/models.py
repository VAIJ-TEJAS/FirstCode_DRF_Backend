from django.db import models

class PersonalisedQuote(models.Model):
    text = models.TextField(help_text="Quote text with a placeholder for the name, e.g., 'Hello, {name}, have a great day!'")
    
    def __str__(self):
        return self.text
