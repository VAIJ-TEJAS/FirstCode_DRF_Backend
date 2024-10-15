import random
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import PersonalisedQuote

class RandomPersonalisedQuoteView(APIView):
    def get(self, request):
        user_name = request.user.first_name if request.user.first_name else "Friend"  # Assuming the user is authenticated

        # Get all quotes from the database
        quotes = PersonalisedQuote.objects.all()

        if not quotes.exists():
            return Response({"error": "No quotes available"}, status=404)

        # Randomly select a quote
        selected_quote = random.choice(quotes)

        # Replace the placeholder {name} with the user's name
        personalised_text = selected_quote.text.replace("{name}", user_name)

        return Response({"quote": personalised_text})
