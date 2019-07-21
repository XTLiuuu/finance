# Import necessary modules
from rasa_nlu.training_data import load_data
from rasa_nlu.config import RasaNLUModelConfig
from rasa_nlu.model import Trainer
from rasa_nlu import config
from iexfinance.stocks import Stock
from datetime import datetime
from iexfinance.stocks import get_historical_data
from iexfinance.refdata import get_symbols
import matplotlib.pyplot as plt
from dateutil import parser
import sqlite3
import sys
import re
import random

conn = sqlite3.connect('favorate.db')
c = conn.cursor()

# Create a trainer that uses this config
trainer = Trainer(config.load("config_spacy.yml"))
# Load the training data
training_data = load_data('demo-rasa-iefinance.json')
# Create an interpreter by training the model
interpreter = trainer.train(training_data)

stocks = {"apple": "AAPL", "microsoft": "MSFT",  "amazon": "AMZN", "netflix": "NFLX", "salesforce": "CRM", "adidas": "ADDYY", "facebook": "FB", "uber": "UBER"
          ,"exxonmobil": "XOM", "intel": "INTC", "oracle":"ORCL", "bank of america": "BAC", "home depot": "HD",
          "jpmorgan": "JPM", "at&t": "T", "verizon": "VZ", "walmart": "WMT", "china mobile": "CHL", "visa": "V"}
blackList = []
INIT = 0
DONE = 1

def main():
    print("hello, what can i do for you")
    msg = input("USER: ")
    while msg != '' and msg.lower() != 'bye':
        print(respond(msg))
        print("what else do you want to know")
        msg = input("USER: ")
    print("Bye! See you next time")

def historyStock(params, state, intent, entities):
    company = ''
    if (not "company" in params):
        while (company == '' and state != DONE):
            (state, response) = policy_rules[(state, intent)]
            print(response)
            company = input("USER: ")
    else:
        company = params["company"]

    fromTime = ''
    toTime = ''
    tempTime = ''
    if (not "from" in params):
        while (fromTime == '' and state != DONE):
            print("which time period are you asking about")
            tempTime = input("USER: ")
            if ("from" in tempTime):
                fromTime = getFromTime(tempTime)
    else:
        fromTime = params["from"]

    if (not "to" in params):
        if ("to" in tempTime or "end" in tempTime):
            toTime = getToTime(tempTime)
        else:
            while (toTime == '' and state != DONE):
                print("which time would it end")
                tempTime = input("USER: ")
                if ("to" in tempTime):
                    toTime = getToTime(tempTime)
    else:
        toTime = params["to"]
    return getHistoryData(company, fromTime, toTime)


# Define respond()
def respond(message):
    # Extract the entities
    response = chitchat_response(message)
    if response is not None:
        return response

    state = INIT
    intent = interpreter.parse(message)["intent"]["name"]
    entities = interpreter.parse(message)["entities"]
    # Initialize an empty params dictionary
    params = {}
    # Fill the dictionary with entities
    for ent in entities:
        params[ent["entity"]] = str(ent["value"])
    results = ""
    if (intent == "current_stock_price"):
        results = currentStock(params, state, intent, entities)

    elif (intent == "historical_stock_price"):
        results = historyStock(params, state, intent, entities)

    elif (intent == "add_fav"):
        results = addFav(params, state, intent, entities)
        c.execute("SELECT * FROM favorate")
    elif (intent == "check_fav"):
        results = checkFav(message)
    elif (intent == "recommend_stock"):
        results = recommendStock(message)
    return (results)

def recommendStock(message):
    satisfy = False
    responses = [
        "would you like to know about {0}",
        "how about {0}",
        "are you interested in {0}",
        "i have {0} in my mind. do you want to know about it",
        "would you like to hear more about {0}"
    ]
    potential_choices = {
        "current_stock_price": "do you want to know the current stock price of it",
        "balance_sheet": "do you want to take a look at its balance sheet",
        "income_statement": "can I show you its income statement",
        "historical_price": "may I show you its price fluctuation during this year",
    }
    recommendation = ''
    while (not satisfy):
        recommendation = random.choice(list(stocks))
        while (recommendation in blackList):
            recommendation = random.choice(list(stocks))
        response = random.choice(responses)
        response = response.format(recommendation)
        print(response)
        userInput = input("USER: ")
        if (negated(userInput)):
            blackList.append(recommendation)
        else:
            satisfy = True

    for intent, message in potential_choices.items():
        print(message)
        userInput = input("USER: ")
        if (negated(userInput)):
            continue
        else:
            return perform(intent, recommendation)

def perform(intent, recommendation):
    if (intent == "current_stock_price"):
        return getPrice(stocks[recommendation])
    elif (intent == 'balance_sheet'):
        return getBalanceSheet(stocks[recommendation])
    elif (intent == 'income_statement'):
        return getIncomeStatement(stocks[recommendation])
    else:
        return getHistoryData(recommendation, fromTime = "january 1st", toTime = datetime.today().strftime("%m/%d"))


def negated(userInput):
    return "no" in userInput or "dis" in userInput or "never" in userInput or "n't" in userInput


def checkFav(message):
    if ("highest" in message):
        return getHighest()
    elif ("lowest" in message):
        return getLowest()
    else:
        return showAll()

def showAll():
    c.execute("SELECT * FROM favorate")
    companies = c.fetchall()
    result = ''
    for company in companies:
        curStock = company[0].lower()
        if (curStock not in stocks):
            continue
        result += getPrice(stocks[curStock]) + "\n" + "\n"

    return result


def getPrice(stock):
    tempStock = Stock(stock, token="pk_5ee7dec9383e4659920ffad0ac066692")
    priceQuote = tempStock.get_quote()
    if (priceQuote["high"]):
        return "company name: " + priceQuote["companyName"] + "\n" + "latest price: " + "%.f" % priceQuote["latestPrice"] + "\n" + "low price: " + "%.f" % priceQuote["low"] + "\n" \
                     + "high price: " + "%.f" % priceQuote["high"]
    return "company name: " + priceQuote["companyName"] + "\n" + "latest price: " + "%.f" % priceQuote["latestPrice"] + "\n"


def getBalanceSheet(stock):
    tempStock = Stock(stock, token="pk_5ee7dec9383e4659920ffad0ac066692")
    balance_sheet = tempStock.get_balance_sheet()['balancesheet'][0]
    result = ''
    for title, content in balance_sheet.items():
        result += title + ": " + str(content) + "\n"
    return result


def getIncomeStatement(stock):
    tempStock = Stock(stock, token="pk_5ee7dec9383e4659920ffad0ac066692")
    income_statement = tempStock.get_income_statement()[0]
    result = ''
    for title, content in income_statement.items():
        result += title + ": " + str(content) + "\n"
    return result



def getLowest():
    c.execute("SELECT * FROM favorate")
    companies = c.fetchall()
    lowest = ''
    lowestPrice = sys.maxsize
    for company in companies:
        curStock = company[0].lower()
        if (curStock not in stocks):
            continue
        tempStock = Stock(stocks[curStock], token="pk_5ee7dec9383e4659920ffad0ac066692")
        priceQuote = tempStock.get_quote()
        if (priceQuote["latestPrice"] < lowestPrice):
            lowest = curStock
            lowestPrice = priceQuote["latestPrice"]
    return (lowest + " has the lowest price at " + str(lowestPrice))


def getHighest():
    c.execute("SELECT * FROM favorate")
    companies = c.fetchall()
    highest = ''
    highestPrice = -1
    for company in companies:
        curStock = company[0].lower()
        if (curStock not in stocks):
            continue
        tempStock = Stock(stocks[curStock], token="pk_5ee7dec9383e4659920ffad0ac066692")
        priceQuote = tempStock.get_quote()
        if (priceQuote["latestPrice"] > highestPrice) :
            highest = curStock
            highestPrice = priceQuote["latestPrice"]
    return (highest + " has the highest price at " + str(highestPrice))


def addFav(params, state, intent, entities):
    c.execute("CREATE TABLE IF NOT EXISTS favorate(name text, date text)")
    if (not "company" in params):
        while (company == '' and state != DONE):
            (state, response) = policy_rules[(state, intent)]
            print(response)
            company = input("USER: ")
    else:
        company = params["company"]
    command = "INSERT INTO favorate(name, date) VALUES ('{}', {})".format(company, datetime.today().strftime("%m/%d/%y"))
    c.execute(command)
    c.execute("commit")
    return ("{} is added to your list".format(company))


def currentStock(params, state, intent, entities):
    company = ''
    if (not "company" in params):
        while (company == '' and state != DONE):
            (state, response) = policy_rules[(state, intent)]
            print(response)
            company = input("USER: ")
    else:
        company = params["company"]

    return get_price(company)

def getFromTime(tempTime):
    tempTime = tempTime.lower()
    indexBegin = tempTime.index("from") + len("from") + 1
    tempTime = tempTime[indexBegin:]
    if("to" in tempTime):
        indexEnd = tempTime.index("to")
        tempTime = tempTime[:indexEnd - 1]
    return tempTime


def getToTime(tempTime):
    indexBegin = tempTime.index("to") + len("to") + 1
    tempTime = tempTime[indexBegin:]
    return tempTime




def getHistoryData(company, fromTime, toTime):
    if (company.lower() not in stocks) :
        return "Please try to ask another company"
    stockID = stocks[company.lower()]
    fromTime = parser.parse(fromTime)
    toTime = parser.parse(toTime)
    df = get_historical_data(stockID, fromTime, toTime, output_format='pandas',
                             token="pk_5ee7dec9383e4659920ffad0ac066692")
    df.plot()
    plt.show()
    return df


policy_rules = {
    (INIT, "current_stock_price"): (INIT, "which company would you like to ask about"),
    (INIT, "historical_stock_price"): (INIT, "which company would you like to ask about"),
    (INIT, "add_fav"): (INIT, "which company would you like to add")
}


def get_price(company):
    stockID = stocks[company.lower()]
    result = getPrice(stockID)
    return result

def match_rule(rules, message):
    for pattern, responses in rules.items():
        match = re.search(pattern, message)
        if match is not None:
            response = random.choice(responses)
            var = match.group(1) if '{0}' in response else None
            return response, var
    return "default", None

def chitchat_response(message):
    response, phrase = match_rule(rules, message)
    if response == "default":
        return None
    if '{0}' in response:
        phrase = replace_pronouns(phrase)
        response = response.format(phrase)
    return response


rules = {
    'what can you do': ["I can do a lot of things about managing stocks",
                 'I am your stock helper bot',
                 'Try to ask me about the stock prices'],
    'do you think (.*)': ['if {0}? Absolutely.',
                          'I guess not',
                          'What do you think'],
    'do you like (.*)': ['I like {0} if you like',
                        "Why do you ask me this question",
                        'Not really'],
    'can you (.*)': ["I can if you train me", "You guess"]
}


def replace_pronouns(message):
    message = message.lower()
    if 'me' in message:
        return re.sub('me', 'you', message)
    if 'i' in message:
        return re.sub('i', 'you', message)
    elif 'my' in message:
        return re.sub('my', 'your', message)
    elif 'your' in message:
        return re.sub('your', 'my', message)
    elif 'you' in message:
        return re.sub('you', 'me', message)
    return message


main()