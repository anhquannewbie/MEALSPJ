from .models import MealPrice

def get_current_price() -> MealPrice:
    """
    Trả về bản MealPrice mới nhất (effective_date lớn nhất).
    """
    return MealPrice.objects.first()
