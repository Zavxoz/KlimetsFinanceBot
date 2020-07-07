import calendar
import locale
import gspread
import httplib2
import apiclient.discovery
from telebot import AsyncTeleBot, types
from functools import wraps
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials



month_array = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
CREDENTIALS_FILE = 'credentials.json' 
locale.setlocale(locale.LC_ALL, 'ru_RU.UTF-8')
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']) 
httpAuth = credentials.authorize(httplib2.Http())
service = apiclient.discovery.build('sheets', 'v4', http = httpAuth)
gc = gspread.authorize(credentials)
to_myself = to_both = 0
bot = AsyncTeleBot("1272834678:AAHJ85rGTY8TXj8x9K5mcg7DzliwkKHMrRA")
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
            full_ex_info = '{func_name}() | {type} : {ex}'.format(type=type(ex).__name__, func_name=func.__name__,
                                                                  ex=ex)
            #logger.warning(full_ex_info)
            print(full_ex_info)
            return None
        return out_condition
    return decorated

@bot.message_handler(commands=["start"])
def start_message(message):
    bot.send_message(message.chat.id, "Hi! Данный бот упростит тебе жизнь. Пользуйся и не выпендривайся" + u"\U0001F618")
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
        atoday = str(today.day)+" "+calendar.month_name[today.month]
        try:
            purchase, price = message.text.split(" ")
            price = float(price)
        except ValueError:
            bot.send_message(message.chat.id, "Неверный формат. Повторите ввод")
            global wrong_format
            wrong_format = 1        
        else:
            worksheet = sh.get_worksheet(len(sh.worksheets())-1)
            if  worksheet.title != month_array[today.month % 12-1]:
                worksheet = new_worksheet(today, sh)
            if not worksheet.findall(atoday, in_column=4):
                    new_day(atoday, worksheet)               
            if message.from_user.username == "artyom_klimets":
                new_entry(worksheet, 5, purchase, price)
            elif message.from_user.username == "savagenassty":
                new_entry(worksheet, 1, purchase, price)     
            to_myself = to_both = 0
    else:
        bot.send_message(message.chat.id, "Не было выбрано куда тратятся деньги")

@bot.message_handler(content_types=["text"])
def main_loop(message):
    bot.send_message(message.chat.id, "Вы пишете что-то не то")  


def new_entry(sheet, client, purchase, price):
    next_row = next_available_row(sheet, client, client+2)
    sheet.update_cell(next_row, client, purchase)
    if to_myself:
        sheet.update_cell(next_row, client+1, price)
    elif to_both:
        sheet.update_cell(next_row, client+2, price)


def new_day(atoday, worksheet):    
    next_row = next_available_row(worksheet)
    worksheet.update_cell(next_row, 4, atoday)


def next_available_row(sheet, first_col=1, last_col=6):
  # looks for empty row based on values appearing in 1st N columns
  cols = sheet.range(1, first_col, sheet.row_count, last_col)
  return max([cell.row for cell in cols if cell.value]) + 1


def new_worksheet(today, sh):
    worksheet = sh.sheet1
    worksheet.duplicate(insert_sheet_index=len(sh.worksheets()), new_sheet_name=month_array[today.month % 12])
    return worksheet


bot.polling()
