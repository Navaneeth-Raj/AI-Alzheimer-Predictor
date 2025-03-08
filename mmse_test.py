from datetime import datetime
import re
import nltk
from nltk.corpus import words

def is_date(userdate):
    try:
        user_date = datetime.strptime(userdate, "%d %B %Y").date()
        return 1 if user_date == datetime.today().date() else 0
    except ValueError:
        return 0

def is_weekday(userday):
    return 1 if userday.strip().lower() == datetime.today().strftime("%A").lower() else 0

def is_month(usermonth):
    return 1 if usermonth.strip().lower() == datetime.today().strftime("%B").lower() else 0

def is_year(useryear):
    try:
        return 1 if int(useryear) == datetime.today().year else 0
    except ValueError:
        return 0

def is_noon(noon):
    current_hour = datetime.now().hour  
    if noon.strip().lower() in ["before noon", "am", "before"]:
        return 1 if current_hour < 12 else 0 
    elif noon.strip().lower() in ["afternoon", "pm", "after"]:
        return 1 if current_hour >= 12 else 0
    else:
        return 0 

def is_registering(answer):
    words = [word.strip().lower() for word in answer.split(",")]  
    valid_count = sum(1 for word in words if word in ["apple", "table", "penny"])
    return min(valid_count, 3)  

def is_attentive(numbers):
    expected_sequence = [100, 99, 98, 97, 96]  
    try:
        user_numbers = list(map(int, numbers.split(",")))  
        correct_count = sum(1 for i in range(min(len(user_numbers), 5)) if user_numbers[i] == expected_sequence[i])
        return correct_count  
    except ValueError:
        return 0  
    
def is_tools(answer):
    valid_tools = {"pen", "pencil", "marker", "chalk", "crayon"} 
    words = [word.strip().lower() for word in answer.split(",")]
    valid_count = sum(1 for word in words if word in valid_tools)
    return min(valid_count, 2)  

def is_sentence(sentence):
    nltk.download("words", quiet=True)
    valid_words = set(words.words())
    sentence = sentence.strip()
    if not sentence:
        return 0  

    starts_with_capital = sentence[0].isupper()
    ends_with_punctuation = sentence[-1] in ".!?"
    words_in_sentence = re.findall(r'\b\w+\b', sentence)
    word_count = len(words_in_sentence) > 1

    if words_in_sentence:
        validity = sum(1 for word in words_in_sentence if word.lower() in valid_words) / len(words_in_sentence)
        if validity < 0.6:
            return 0
    else:
        validity = 0


    score = (
        0.3 * validity +  0.2 * starts_with_capital +  0.2 * ends_with_punctuation +  0.3 * word_count 
    )

    return round(score, 2)

def is_pentagon(answer):
    descriptors = ["five", "sides", "angles", "edges", "corners", "vertices", "closed", "polygon", "shape"]
    words = {word.strip().lower() for word in answer.split(",")}  
    correct_words = list(word for word in words if word in descriptors) 
    return min(len(correct_words), 3) 

def is_tea_making(answer):
    valid_steps = {
        "boil water", "heat water", "add tea leaves", "add milk", "add sugar",
        "add tea bag", "stir sugar", "strain tea", "serve tea"
    }
    steps = {step.strip().lower() for step in answer.split(",")}
    correct_steps = [step for step in steps if step in valid_steps]
    return min(len(correct_steps), 3)  