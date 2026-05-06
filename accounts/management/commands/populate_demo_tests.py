"""
Management command to populate demo test data for the exam system.
Usage: python manage.py populate_demo_tests
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Test, Question, Answer, TestCategory


class Command(BaseCommand):
    help = 'Populates the database with demo test data for GUI testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing test data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing test data...'))
            Test.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('Existing tests cleared.'))

        self.stdout.write(self.style.SUCCESS('Creating demo test data...'))

        category_definitions = {
            'Programming Foundations': 'Fundamental programming concepts and language basics.',
            'Web Development': 'HTML, CSS, and JavaScript essentials for building modern web pages.',
            'Data & Databases': 'Core database principles, SQL, and data modeling best practices.',
            'General Knowledge': 'Mixed topics including history, geography, science, and current affairs.',
        }

        category_objects = {}
        for name, description in category_definitions.items():
            category_obj, created = TestCategory.objects.get_or_create(
                name=name,
                defaults={'description': description}
            )
            if (created or not category_obj.description) and description:
                category_obj.description = description
                category_obj.save(update_fields=['description'])
            category_objects[name] = category_obj

        # Test 1: Python Programming Basics
        now = timezone.now()

        test1 = Test.objects.create(
            title="Python Programming Basics",
            description="Test your knowledge of fundamental Python programming concepts including variables, data types, and basic operations.",
            duration_minutes=30,
            passing_score=60,
            is_active=True,
            category=category_objects.get('Programming Foundations'),
            status='published',
            published_at=now,
            instructions="""Instructions:
1. This test contains 10 questions.
2. You have 30 minutes to complete the test.
3. Each question has 4 options, only one is correct.
4. You can mark questions for review and come back to them later.
5. Click 'Submit' button when you are done.
6. Make sure to answer all questions before submitting."""
        )

        questions_data_1 = [
            {
                'text': 'What is the output of: print(type(5))?',
                'marks': 1,
                'answers': [
                    ('<class "int">', True),
                    ('<class "str">', False),
                    ('<class "float">', False),
                    ('<class "number">', False),
                ]
            },
            {
                'text': 'Which of the following is used to create a list in Python?',
                'marks': 1,
                'answers': [
                    ('[]', True),
                    ('{}', False),
                    ('()', False),
                    ('<>', False),
                ]
            },
            {
                'text': 'What does the len() function do in Python?',
                'marks': 1,
                'answers': [
                    ('Returns the length of an object', True),
                    ('Returns the last element', False),
                    ('Returns the first element', False),
                    ('Sorts the elements', False),
                ]
            },
            {
                'text': 'Which keyword is used to define a function in Python?',
                'marks': 1,
                'answers': [
                    ('def', True),
                    ('function', False),
                    ('define', False),
                    ('fun', False),
                ]
            },
            {
                'text': 'What is the correct way to create a dictionary in Python?',
                'marks': 1,
                'answers': [
                    ('{"key": "value"}', True),
                    ('("key": "value")', False),
                    ('["key": "value"]', False),
                    ('<"key": "value">', False),
                ]
            },
            {
                'text': 'What does the range(5) function return?',
                'marks': 1,
                'answers': [
                    ('Numbers from 0 to 4', True),
                    ('Numbers from 1 to 5', False),
                    ('Numbers from 0 to 5', False),
                    ('Numbers from 1 to 4', False),
                ]
            },
            {
                'text': 'Which operator is used for exponentiation in Python?',
                'marks': 1,
                'answers': [
                    ('**', True),
                    ('^', False),
                    ('exp', False),
                    ('pow', False),
                ]
            },
            {
                'text': 'What is the output of: "Hello" + "World"?',
                'marks': 1,
                'answers': [
                    ('HelloWorld', True),
                    ('Hello World', False),
                    ('Error', False),
                    ('"Hello" + "World"', False),
                ]
            },
            {
                'text': 'Which method is used to add an element to a list?',
                'marks': 1,
                'answers': [
                    ('append()', True),
                    ('add()', False),
                    ('insert()', False),
                    ('push()', False),
                ]
            },
            {
                'text': 'What is the correct syntax to import a module in Python?',
                'marks': 1,
                'answers': [
                    ('import module_name', True),
                    ('include module_name', False),
                    ('require module_name', False),
                    ('load module_name', False),
                ]
            },
        ]

        for idx, q_data in enumerate(questions_data_1):
            question = Question.objects.create(
                test=test1,
                question_text=q_data['text'],
                marks=q_data['marks'],
                order=idx
            )
            for ans_idx, (ans_text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=ans_text,
                    is_correct=is_correct,
                    order=ans_idx
                )

        test1.total_questions = len(questions_data_1)
        test1.save()

        self.stdout.write(self.style.SUCCESS(f'Created test: {test1.title} with {test1.total_questions} questions'))

        # Test 2: Web Development Fundamentals
        test2 = Test.objects.create(
            title="Web Development Fundamentals",
            description="Test your understanding of HTML, CSS, and JavaScript basics used in web development.",
            duration_minutes=45,
            passing_score=70,
            is_active=True,
            category=category_objects.get('Web Development'),
            status='published',
            published_at=now,
            instructions="""Instructions:
1. This test contains 15 questions.
2. You have 45 minutes to complete the test.
3. Read each question carefully before answering.
4. You can navigate between questions using the question navigation panel.
5. Review your answers before submitting.
6. Passing score is 70%."""
        )

        questions_data_2 = [
            {
                'text': 'What does HTML stand for?',
                'marks': 1,
                'answers': [
                    ('HyperText Markup Language', True),
                    ('High Tech Modern Language', False),
                    ('Hyper Transfer Markup Language', False),
                    ('Home Tool Markup Language', False),
                ]
            },
            {
                'text': 'Which HTML tag is used to create a hyperlink?',
                'marks': 1,
                'answers': [
                    ('<a>', True),
                    ('<link>', False),
                    ('<href>', False),
                    ('<url>', False),
                ]
            },
            {
                'text': 'What does CSS stand for?',
                'marks': 1,
                'answers': [
                    ('Cascading Style Sheets', True),
                    ('Computer Style Sheets', False),
                    ('Creative Style Sheets', False),
                    ('Colorful Style Sheets', False),
                ]
            },
            {
                'text': 'Which property is used to change the background color in CSS?',
                'marks': 1,
                'answers': [
                    ('background-color', True),
                    ('bg-color', False),
                    ('color-background', False),
                    ('background', False),
                ]
            },
            {
                'text': 'What is the correct way to include JavaScript in HTML?',
                'marks': 1,
                'answers': [
                    ('<script src="file.js"></script>', True),
                    ('<javascript src="file.js"></javascript>', False),
                    ('<js src="file.js"></js>', False),
                    ('<link rel="javascript" href="file.js">', False),
                ]
            },
            {
                'text': 'Which HTML element is used for the largest heading?',
                'marks': 1,
                'answers': [
                    ('<h1>', True),
                    ('<head>', False),
                    ('<heading>', False),
                    ('<h6>', False),
                ]
            },
            {
                'text': 'What is the purpose of the <div> tag?',
                'marks': 1,
                'answers': [
                    ('Container for grouping HTML elements', True),
                    ('Creates a division in math', False),
                    ('Links to external stylesheets', False),
                    ('Creates a table', False),
                ]
            },
            {
                'text': 'Which CSS property is used to make text bold?',
                'marks': 1,
                'answers': [
                    ('font-weight: bold', True),
                    ('text-bold: true', False),
                    ('bold: yes', False),
                    ('font-style: bold', False),
                ]
            },
            {
                'text': 'What is the correct way to select an element with id "header" in CSS?',
                'marks': 1,
                'answers': [
                    ('#header', True),
                    ('.header', False),
                    ('header', False),
                    ('id:header', False),
                ]
            },
            {
                'text': 'Which JavaScript method is used to add an element to an array?',
                'marks': 1,
                'answers': [
                    ('push()', True),
                    ('add()', False),
                    ('append()', False),
                    ('insert()', False),
                ]
            },
            {
                'text': 'What is the purpose of localStorage in JavaScript?',
                'marks': 1,
                'answers': [
                    ('Store data in the browser', True),
                    ('Store data on the server', False),
                    ('Store cookies', False),
                    ('Store session data', False),
                ]
            },
            {
                'text': 'Which HTML attribute is used to define inline styles?',
                'marks': 1,
                'answers': [
                    ('style', True),
                    ('css', False),
                    ('stylesheet', False),
                    ('design', False),
                ]
            },
            {
                'text': 'What does the box model in CSS include?',
                'marks': 1,
                'answers': [
                    ('Content, Padding, Border, Margin', True),
                    ('Width, Height, Color, Font', False),
                    ('Top, Bottom, Left, Right', False),
                    ('Header, Body, Footer, Sidebar', False),
                ]
            },
            {
                'text': 'Which JavaScript function is used to parse a string to an integer?',
                'marks': 1,
                'answers': [
                    ('parseInt()', True),
                    ('toInt()', False),
                    ('integer()', False),
                    ('convertInt()', False),
                ]
            },
            {
                'text': 'What is the purpose of the <meta> tag in HTML?',
                'marks': 1,
                'answers': [
                    ('Provide metadata about the document', True),
                    ('Create a table', False),
                    ('Link external stylesheets', False),
                    ('Embed JavaScript code', False),
                ]
            },
        ]

        for idx, q_data in enumerate(questions_data_2):
            question = Question.objects.create(
                test=test2,
                question_text=q_data['text'],
                marks=q_data['marks'],
                order=idx
            )
            for ans_idx, (ans_text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=ans_text,
                    is_correct=is_correct,
                    order=ans_idx
                )

        test2.total_questions = len(questions_data_2)
        test2.save()

        self.stdout.write(self.style.SUCCESS(f'Created test: {test2.title} with {test2.total_questions} questions'))

        # Test 3: Database Concepts
        test3 = Test.objects.create(
            title="Database Concepts",
            description="Test your knowledge of database fundamentals including SQL queries, normalization, and database design principles.",
            duration_minutes=40,
            passing_score=65,
            is_active=True,
            category=category_objects.get('Data & Databases'),
            status='published',
            published_at=now,
            instructions="""Instructions:
1. This test contains 12 questions.
2. You have 40 minutes to complete the test.
3. All questions are multiple choice with single correct answer.
4. Use the question panel to navigate between questions.
5. You can mark questions for review.
6. Passing score is 65%."""
        )

        questions_data_3 = [
            {
                'text': 'What does SQL stand for?',
                'marks': 1,
                'answers': [
                    ('Structured Query Language', True),
                    ('Structured Question Language', False),
                    ('Simple Query Language', False),
                    ('Standard Query Language', False),
                ]
            },
            {
                'text': 'Which SQL statement is used to retrieve data from a database?',
                'marks': 1,
                'answers': [
                    ('SELECT', True),
                    ('GET', False),
                    ('FETCH', False),
                    ('RETRIEVE', False),
                ]
            },
            {
                'text': 'What is a primary key in a database?',
                'marks': 1,
                'answers': [
                    ('A unique identifier for each record', True),
                    ('A foreign key', False),
                    ('A duplicate key', False),
                    ('An index key', False),
                ]
            },
            {
                'text': 'Which SQL clause is used to filter records?',
                'marks': 1,
                'answers': [
                    ('WHERE', True),
                    ('FILTER', False),
                    ('CONDITION', False),
                    ('IF', False),
                ]
            },
            {
                'text': 'What is the purpose of the JOIN clause in SQL?',
                'marks': 1,
                'answers': [
                    ('Combine rows from multiple tables', True),
                    ('Sort data', False),
                    ('Filter data', False),
                    ('Group data', False),
                ]
            },
            {
                'text': 'Which SQL statement is used to insert new records?',
                'marks': 1,
                'answers': [
                    ('INSERT', True),
                    ('ADD', False),
                    ('CREATE', False),
                    ('UPDATE', False),
                ]
            },
            {
                'text': 'What does ACID stand for in database transactions?',
                'marks': 1,
                'answers': [
                    ('Atomicity, Consistency, Isolation, Durability', True),
                    ('Access, Control, Integrity, Data', False),
                    ('Add, Create, Insert, Delete', False),
                    ('Analyze, Check, Index, Delete', False),
                ]
            },
            {
                'text': 'Which SQL function is used to count rows?',
                'marks': 1,
                'answers': [
                    ('COUNT()', True),
                    ('SUM()', False),
                    ('TOTAL()', False),
                    ('NUMBER()', False),
                ]
            },
            {
                'text': 'What is normalization in database design?',
                'marks': 1,
                'answers': [
                    ('Organizing data to reduce redundancy', True),
                    ('Making data more complex', False),
                    ('Adding more tables', False),
                    ('Deleting duplicate records', False),
                ]
            },
            {
                'text': 'Which SQL statement is used to update existing records?',
                'marks': 1,
                'answers': [
                    ('UPDATE', True),
                    ('MODIFY', False),
                    ('CHANGE', False),
                    ('ALTER', False),
                ]
            },
            {
                'text': 'What is a foreign key?',
                'marks': 1,
                'answers': [
                    ('A field that references a primary key in another table', True),
                    ('A duplicate primary key', False),
                    ('A key that is not unique', False),
                    ('A backup key', False),
                ]
            },
            {
                'text': 'Which SQL clause is used to sort records?',
                'marks': 1,
                'answers': [
                    ('ORDER BY', True),
                    ('SORT BY', False),
                    ('ARRANGE BY', False),
                    ('GROUP BY', False),
                ]
            },
        ]

        for idx, q_data in enumerate(questions_data_3):
            question = Question.objects.create(
                test=test3,
                question_text=q_data['text'],
                marks=q_data['marks'],
                order=idx
            )
            for ans_idx, (ans_text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=ans_text,
                    is_correct=is_correct,
                    order=ans_idx
                )

        test3.total_questions = len(questions_data_3)
        test3.save()

        self.stdout.write(self.style.SUCCESS(f'Created test: {test3.title} with {test3.total_questions} questions'))

        # Test 4: General Knowledge Quiz
        test4 = Test.objects.create(
            title="General Knowledge Quiz",
            description="A fun quiz covering various topics including history, geography, science, and current affairs.",
            duration_minutes=25,
            passing_score=50,
            is_active=True,
            category=category_objects.get('General Knowledge'),
            status='published',
            published_at=now,
            instructions="""Instructions:
1. This test contains 8 questions.
2. You have 25 minutes to complete the test.
3. Questions cover various topics.
4. Answer all questions to the best of your knowledge.
5. Passing score is 50%."""
        )

        questions_data_4 = [
            {
                'text': 'What is the capital of France?',
                'marks': 1,
                'answers': [
                    ('Paris', True),
                    ('London', False),
                    ('Berlin', False),
                    ('Madrid', False),
                ]
            },
            {
                'text': 'Which planet is known as the Red Planet?',
                'marks': 1,
                'answers': [
                    ('Mars', True),
                    ('Venus', False),
                    ('Jupiter', False),
                    ('Saturn', False),
                ]
            },
            {
                'text': 'Who painted the Mona Lisa?',
                'marks': 1,
                'answers': [
                    ('Leonardo da Vinci', True),
                    ('Pablo Picasso', False),
                    ('Vincent van Gogh', False),
                    ('Michelangelo', False),
                ]
            },
            {
                'text': 'What is the largest ocean on Earth?',
                'marks': 1,
                'answers': [
                    ('Pacific Ocean', True),
                    ('Atlantic Ocean', False),
                    ('Indian Ocean', False),
                    ('Arctic Ocean', False),
                ]
            },
            {
                'text': 'In which year did World War II end?',
                'marks': 1,
                'answers': [
                    ('1945', True),
                    ('1944', False),
                    ('1946', False),
                    ('1943', False),
                ]
            },
            {
                'text': 'What is the chemical symbol for gold?',
                'marks': 1,
                'answers': [
                    ('Au', True),
                    ('Go', False),
                    ('Gd', False),
                    ('Ag', False),
                ]
            },
            {
                'text': 'Which is the longest river in the world?',
                'marks': 1,
                'answers': [
                    ('Nile', True),
                    ('Amazon', False),
                    ('Mississippi', False),
                    ('Yangtze', False),
                ]
            },
            {
                'text': 'What is the smallest prime number?',
                'marks': 1,
                'answers': [
                    ('2', True),
                    ('1', False),
                    ('3', False),
                    ('0', False),
                ]
            },
        ]

        for idx, q_data in enumerate(questions_data_4):
            question = Question.objects.create(
                test=test4,
                question_text=q_data['text'],
                marks=q_data['marks'],
                order=idx
            )
            for ans_idx, (ans_text, is_correct) in enumerate(q_data['answers']):
                Answer.objects.create(
                    question=question,
                    answer_text=ans_text,
                    is_correct=is_correct,
                    order=ans_idx
                )

        test4.total_questions = len(questions_data_4)
        test4.save()

        self.stdout.write(self.style.SUCCESS(f'Created test: {test4.title} with {test4.total_questions} questions'))

        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('Demo test data populated successfully!'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS(f'\nTotal tests created: 4'))
        total_questions = sum([test1.total_questions, test2.total_questions, test3.total_questions, test4.total_questions])
        self.stdout.write(self.style.SUCCESS(f'Total questions created: {total_questions}'))
        self.stdout.write(self.style.SUCCESS('\nYou can now test the exam feature in your application!'))

