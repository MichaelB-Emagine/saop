# tools.py
import random
import datetime


def multiply_numbers(a: float, b: float) -> float:
    """Multiplies two numbers together."""
    return a * b


def get_presidents() -> list[str]:
    """Returns a list of the last 20 US presidents."""
    presidents = [
        "Joe Biden",
        "Donald Trump",
        "Barack Obama",
        "George W. Bush",
        "Bill Clinton",
        "George H.W. Bush",
        "Ronald Reagan",
        "Jimmy Carter",
        "Gerald Ford",
        "Richard Nixon",
        "Lyndon B. Johnson",
        "John F. Kennedy",
        "Dwight D. Eisenhower",
        "Harry S. Truman",
        "Franklin D. Roosevelt",
        "Herbert Hoover",
        "Calvin Coolidge",
        "Warren G. Harding",
        "Woodrow Wilson",
        "William Howard Taft",
    ]
    return presidents


def generate_random_number() -> int:
    """Returns a random number between 0 and 100."""
    return random.randint(0, 100)


def get_daily_message() -> str:
    """Returns a daily warm, encouraging message."""
    messages = [
        "You're doing great! Keep up the amazing work.",
        "Remember to take a moment for yourself today. You deserve it.",
        "Your hard work will pay off. Stay focused and positive!",
        "Each new day is a chance to start fresh. Make it a good one.",
        "Believe in yourself and all that you are. You have so much to offer.",
    ]
    day_of_week = datetime.date.today().weekday()
    return messages[day_of_week % len(messages)]


def greet_user(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"
