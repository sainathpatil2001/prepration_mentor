import os
import django
import random
from django.utils import timezone
from django.utils.text import slugify

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'exam_project.settings')
django.setup()

from accounts.models import TestCategory, Test, Question, Answer

def create_demo_data():
    print("Starting demo data creation...")
    
    # 1. Define 5 Categories
    category_names = ['General Knowledge', 'Mathematics', 'Science', 'English', 'Reasoning']
    categories = []
    
    print("Ensuring 5 Categories exist...")
    for name in category_names:
        # We use get_or_create to avoid errors if they exist, but we update them to be sure
        cat, created = TestCategory.objects.get_or_create(
            name=name,
            defaults={
                'description': f'Demo category for {name}',
                'slug': slugify(name)
            }
        )
        categories.append(cat)
        if created:
            print(f"  - Created Category: {name}")
        else:
            print(f"  - Found Category: {name}")
            
    # 2. Create Tests and Questions
    # Goal: Ensure 1000 Questions total are added.
    # Logic: 5 Categories * 10 Tests per Category * 20 Questions per Test = 1000 Questions.
    
    total_new_questions = 0
    total_new_tests = 0
    
    print("\nGenerating Tests and Questions...")
    
    for cat in categories:
        print(f"  Processing Category: {cat.name}")
        for t_idx in range(200): # 200 Tests per category = 1000 Tests total
            # Create a unique title for the test
            test_title = f"{cat.name} Demo Test {random.randint(1000, 9999)}"
            
            test = Test.objects.create(
                title=test_title,
                category=cat,
                description=f"This is a generated practice test for {cat.name}. Generated on {timezone.now().strftime('%Y-%m-%d %H:%M')}",
                duration_minutes=30,
                total_questions=20,
                passing_score=40,
                negative_marking_rule='none',
                is_active=True,
                status='published',
                published_at=timezone.now(),
                notifications_generated=True # Skip notification generation for bulk data
            )
            
            total_new_tests += 1
            
            # Create 20 Questions for this test
            for q_idx in range(20):
                question_text = f"Question {q_idx + 1}: What is the result of generated operation {random.randint(1, 100)}?"
                
                q = Question.objects.create(
                    test=test,
                    question_text=question_text,
                    marks=1,
                    explanation="This is a demo explanation for the question.",
                    order=q_idx + 1
                )
                
                # Create 4 Options
                options_base = ["Option A", "Option B", "Option C", "Option D"]
                correct_option_idx = random.randint(0, 3)
                
                for o_idx, option_label in enumerate(options_base):
                    is_correct = (o_idx == correct_option_idx)
                    val = random.randint(1, 1000)
                    Answer.objects.create(
                        question=q,
                        answer_text=f"{option_label} - Value {val}",
                        is_correct=is_correct,
                        order=o_idx + 1
                    )
                
                total_new_questions += 1
                
        print(f"    - Added 10 tests for {cat.name}")

    print("\n" + "="*50)
    print(f"COMPLETED:")
    print(f"Total Tests Added: {total_new_tests}")
    print(f"Total Questions Added: {total_new_questions}")
    print("="*50)

if __name__ == "__main__":
    create_demo_data()
