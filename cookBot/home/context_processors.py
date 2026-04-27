from .models import UserStreak


def streak_context(request):
    """Ensure UserStreak exists for authenticated users before template rendering"""
    if request.user.is_authenticated:
        streak, _ = UserStreak.objects.get_or_create(user=request.user)
        return {"user_streak": streak}
    return {}
