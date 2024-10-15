from rest_framework import serializers
from .models import PersonalisedQuote

class PersonalisedQuoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PersonalisedQuote
        fields = ['text']
