import gspread
import httplib2
import apiclient.discovery
import os
from flask import Flask, request
from telebot import AsyncTeleBot, types, logger, logging
from functools import wraps
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials


month_array = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
month_array_2 = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'] 
CREDENTIALS_FILE = 'credentials.json' 
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']) 
httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http = httpAuth)
gc = gspread.authorize(credentials)
to_myself = to_both = 0
bot = AsyncTeleBot("1272834678:AAHJ85rGTY8TXj8x9K5mcg7DzliwkKHMrRA", threaded=True)
markup = types.ReplyKeyboardMarkup(True, True)
markup.row('На себя', 'Обоим')


def exception(func):
    """
    Wrap up function with try-except.
    """
    @wraps(func)
    def decorated(*args, **kwargs):
        try:
            out_condition = func(*args, **kwargs)
        except Exception as ex:
            full_ex_info = '{func_name}() | {type} : {ex}'.format(type=type(ex).__name__, func_name=func.__name__, ex=ex)
            #logger.warning(full_ex_info)
            print(full_ex_info)
            return None
        return out_condition
    return decorated


@bot.message_handler(commands=["start"])
def start_message(message):
    bot.send_message(message.chat.id, "Hi! Данный бот упростит тебе жизнь. Пользуйся и не выпендривайся" + u"\U0001F618")
    import time
    time.sleep(1)
    bot.send_message(message.chat.id, "На кого потратила?", reply_markup=markup)


@bot.message_handler(regexp="На себя")
def to_myself_message(message):
    global to_myself
    to_myself = 1
    bot.send_message(message.chat.id, "Введите, что было куплено и цену. Пример: еда 8,61")
    

@bot.message_handler(regexp="Обоим")
def to_both_message(message):
    global to_both
    to_both = 1 
    bot.send_message(message.chat.id, "Введите, что было куплено и цену. Пример: еда 8,61")


@bot.message_handler(regexp="\w+\s[0-9]+([,.][0-9]+)?")
@exception
def adding_entry(message):
    global to_both, to_myself
    if to_myself or to_both:
        sh = gc.open("Расходы")
        today = datetime.today()
        atoday = str(today.day)+" "+month_array_2[today.month-1]
        try:
            purchase, price = message.text.split(" ")
            price = float(price)
        except ValueError:
            bot.send_message(message.chat.id, "Неверный формат. Повторите ввод")       
        else:
            worksheet = sh.get_worksheet(len(sh.worksheets())-1)
            if  worksheet.title != month_array[today.month % 12-1]:
                worksheet = new_worksheet(today, sh)
            month_cell = worksheet.findall(atoday, in_column=4)
            if not month_cell:
                new_day(atoday, worksheet)               
            if message.from_user.username == "artyom_klimets":
                new_entry(worksheet, 5, purchase, price, month_cell[0])
            elif message.from_user.username == "savagenassty":
                new_entry(worksheet, 1, purchase, price, month_cell[0])
            bot.send_message(message.chat.id, "Запись сохранена")   
            to_myself = to_both = 0
    else:
        bot.send_message(message.chat.id, "Не было выбрано куда тратятся деньги")


@bot.message_handler(content_types=["text"])
def main_loop(message):
    bot.send_message(message.chat.id, "Вы пишете что-то не то")  


def new_entry(sheet, client, purchase, price, month_cell):
    next_row = next_available_row(sheet, client, client+2, month_cell.row)
    sheet.update_cell(next_row, client, purchase)
    if to_myself:
        sheet.update_cell(next_row, client+1, price)
    elif to_both:
        sheet.update_cell(next_row, client+2, price)


def new_day(atoday, worksheet):    
    next_row = next_available_row(worksheet)
    worksheet.update_cell(next_row, 4, atoday)


def next_available_row(sheet, first_col=1, last_col=7, month_row=0):
    # looks for empty row based on values appearing in 1st N columns
    cols = sheet.range(1, first_col, sheet.row_count, last_col)
    last_row = max([cell.row for cell in cols if cell.value])
    if month_row > last_row:
        return month_row
    else:
        return last_row+1


def new_worksheet(today, sh):
    worksheet = sh.sheet1
    worksheet.duplicate(insert_sheet_index=len(sh.worksheets()), new_sheet_name=month_array[today.month % 12])
    return worksheet


if "HEROKU" in list(os.environ.keys()):
    log = logger
    logger.setLevel(logging.INFO)

    server = Flask(__name__)
    @server.route("/bot", methods=['POST'])
    def getMessage():
        bot.process_new_updates([types.Update.de_json(request.stream.read().decode("utf-8"))])
        return "!", 200
    @server.route("/")
    def webhook():
        bot.remove_webhook()
        bot.set_webhook(url="https://klimetsfinance.herokuapp.com/bot") # этот url нужно заменить на url вашего Хероку приложения
        return "?", 200
    server.run(host="0.0.0.0", port=os.environ.get('PORT', 80))
else:
    # если переменной окружения HEROKU нету, значит это запуск с машины разработчика.  
    # Удаляем вебхук на всякий случай, и запускаем с обычным поллингом.
    bot.remove_webhook()
    bot.polling(none_stop=True)
