# This was made by Roman and Claude on 4/16/26
from django.db import migrations

INITIAL_TAGS = [
    ('Vegan', 'dietary'),
    ('Vegetarian', 'dietary'),
    ('Pescatarian', 'dietary'),
    ('Gluten-Free', 'dietary'),
    ('Dairy-Free', 'dietary'),
    ('Nut-Free', 'dietary'),
    ('Soy-Free', 'dietary'),
    ('Egg-Free', 'dietary'),
    ('Halal', 'dietary'),
    ('Kosher', 'dietary'),
    ('Keto', 'dietary'),
    ('Paleo', 'dietary'),
    ('Low-Carb', 'dietary'),
    ('Low-Fat', 'dietary'),
    ('Low-Sodium', 'dietary'),
    ('High-Protein', 'dietary'),
    ('Sugar-Free', 'dietary'),

    ('French', 'cuisine'),
    ('Italian', 'cuisine'),
    ('Mexican', 'cuisine'),
    ('Thai', 'cuisine'),
    ('Japanese', 'cuisine'),
    ('Indian', 'cuisine'),
    ('Chinese', 'cuisine'),
    ('Korean', 'cuisine'),
    ('Vietnamese', 'cuisine'),
    ('Mediterranean', 'cuisine'),
    ('Greek', 'cuisine'),
    ('Spanish', 'cuisine'),
    ('Middle Eastern', 'cuisine'),
    ('American', 'cuisine'),
    ('Caribbean', 'cuisine'),

    ('Under 15 mins', 'cooktime'),
    ('15 to 20 mins', 'cooktime'),
    ('20 to 30 mins', 'cooktime'),
    ('30 to 45 mins', 'cooktime'),
    ('45 to 60 mins', 'cooktime'),
    ('Over 60 mins', 'cooktime'),

    ('Breakfast', 'meal'),
    ('Brunch', 'meal'),
    ('Lunch', 'meal'),
    ('Dinner', 'meal'),
    ('Snack', 'meal'),
    ('Dessert', 'meal'),
    ('Appetizer', 'meal'),
    ('Side Dish', 'meal'),
    ('Main Course', 'meal'),
    ('Soup', 'meal'),
    ('Salad', 'meal'),
    ('Beverage', 'meal'),

    ('Spicy', 'other'),
    ('Sweet', 'other'),
    ('Umami', 'other'),
    ('Smoky', 'other'),
    ('One-Pot', 'other'),
    ('One-Pan', 'other'),
    ('Slow Cooker', 'other'),
    ('No-Cook', 'other'),
    ('Air Fryer', 'other'),
    ('Instant Pot', 'other'),
    ('Easy to make', 'other'),
    ('Requires Technique', 'other'),
]

def seed_tags(apps, schema_editor):
    Tag = apps.get_model('home', 'Tag')
    for name, tag_type in INITIAL_TAGS:
        Tag.objects.get_or_create(name=name, defaults={'tag_type': tag_type})

class Migration(migrations.Migration):
    dependencies = [('home', '0010_alter_recipe_tags')]
    operations = [migrations.RunPython(seed_tags, migrations.RunPython.noop)]
