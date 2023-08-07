import threading
import telebot
from time import sleep
from telebot import types
from datetime import datetime, timedelta
import time
import requests
import csv, io

registred_id = []
primary_id = []
with open('primary_id.txt', 'r') as file:
    lines = file.readlines()
    primary_id = [int(line.split('#')[0].strip()) for line in lines if line.split('#')[0].strip()]
print(primary_id)
with open('registred_id.txt', 'r') as file:
    lines = file.readlines()
    registred_id = [int(line.split('#')[0].strip()) for line in lines if line.split('#')[0].strip()]
print(registred_id)

class Settings:
    token = '......'

    my_id = 746828525

    service_url = 'http://194.87.94.203/api/v1/tgbot/'
    new_notifier_url = service_url + 'new/'
    database_url = service_url + 'csvdatabase/'
    stats_url = service_url + 'stats/'

def try_request(url, data=None, json=None) -> requests.Response:
    print(url, data, json, sep='\n')
    for t in range(7):
        response = requests.get(url=url, data=data, json=json)
        if response.status_code == 200:
            return(response)
        print(f"sleep {2**t} seconds")
        time.sleep(2**t)
    raise Exception(f"request failed {response.status_code}") 

BOT = telebot.TeleBot(Settings.token)

def monitoring_func():
    BOT.send_message(Settings.my_id, 'Мониторинг включен')
    BOT.send_message(Settings.my_id, 'primary_id: ' + str(primary_id))
    BOT.send_message(Settings.my_id, 'registred_id: ' + str(registred_id))
    while True:
        response = requests.get(url=Settings.new_notifier_url)
        if response.status_code == 304:
            print("No content 304")
            sleep(1)
        elif response.status_code == 200:
            print(200)
            data = response.json()
            for notifier in data:
                tg_id = int(notifier["tg_id"])
                message = notifier["massage"]
                for person in registred_id:
                    if tg_id == person:
                        BOT.send_message(tg_id, message)
                    else:
                        BOT.send_message(person, "Только что вы упустили клиента!")
        else:
            print(f"Some exception {response.status_code}")
            sleep(1)

def start_thread():
  threading.Thread(target=monitoring_func).start()

def buttons(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton("Помощь")
    markup.add(btn1)
    if message.chat.id in primary_id:
        btn2 = types.KeyboardButton("Получить отчет")
        btn3 = types.KeyboardButton("Выгрузить базу")
        markup.add(btn2, btn3)
    return markup

def help_text(message):
    text_not_primary = 'Я бот для получения уведомлений по входящим звонкам MANGO OFFICE.\nТеперь вы будуте получать уведомления.'
    text_primary = 'А также: как администратор вы можете получить отчет по всем совершенным звонкам и выгрузить базу обьявлений с сервера'
    if message.chat.id in primary_id:
        return text_not_primary + '\n' + text_primary
    else:
        return text_not_primary

def get_reply(message, date:datetime = datetime.today()):
    BOT.send_chat_action(message.chat.id, action="upload_document")
    reply_date = date.date().strftime('%d.%m.%Y')
    try:
        response = try_request(url=Settings.stats_url, data={"date": reply_date})
        buf = io.BytesIO(response.content)
        buf.seek(0)
        buf.name = f'{date.strftime("%d-%m-%Y")}stats.csv'
        BOT.send_document(message.chat.id, document=buf)
    except:
        BOT.send_message(message.chat.id, "Не удалось загрузить статистику, попробуйте позже", reply_markup=buttons(message))

def get_database(message):
    BOT.send_chat_action(message.chat.id, action="upload_document")
    try:
        response = try_request(url=Settings.database_url)
        buf = io.BytesIO(response.content)
        buf.seek(0)
        buf.name = f'{datetime.today().date()}base.csv'
        BOT.send_document(message.chat.id, document=buf)
    except:
        BOT.send_message(message.chat.id, "Не удалось загрузить базу, попробуйте позже", reply_markup=buttons(message))


def get_any_date(message):
    try:
        date_message = datetime.strptime(message.text, '%d.%m.%Y')
    except:
        if message.text == "Отмена":
            BOT.send_message(message.chat.id, "Действие отменено", reply_markup=buttons(message))
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        key_today = types.KeyboardButton("Отмена")
        markup.add(key_today)
        BOT.send_message(message.chat.id, "Некоректный ввод, введите дату отчета в формате дд.мм.гггг", reply_markup=markup)
        BOT.register_next_step_handler(message, get_any_date)
    else:
        reply = get_reply(message, date_message)
        BOT.send_message(message.chat.id, "Отчет за " + date_message.strftime("%d.%m.%Y"), reply_markup=buttons(message))

def register_user(message):
    if message.chat.id not in registred_id:
        with open('registred_id.txt', 'a') as file:
            file.write('\n'+str(message.chat.id))
        registred_id.append(message.chat.id)

@BOT.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    register_user(call.message)
    if call.data == "today": #call.data это callback_data, которую мы указали при объявлении кнопки
        reply = get_reply(call.message, datetime.today())
        BOT.send_message(call.message.chat.id, "Отчет за сегодня")
    elif call.data == "yesterday":
        reply = get_reply(call.message, datetime.today() - timedelta(days=1))
        BOT.send_message(call.message.chat.id, "Отчет за вчера")
    elif call.data == "any":
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        key_today = types.KeyboardButton("Отмена")
        markup.add(key_today)
        BOT.send_message(call.message.chat.id, "Введите дату отчета в формате дд.мм.гггг", reply_markup=markup)
        BOT.register_next_step_handler(call.message, get_any_date)

@BOT.message_handler(commands=['start'])
def send_test(message):
    register_user(message)
    BOT.send_message(message.chat.id, text='Привет, {0.first_name}! '.format(message.from_user) + help_text(message), reply_markup=buttons(message))

@BOT.message_handler(commands=['help'])
def help_message(message):
    register_user(message)
    BOT.send_message(message.chat.id, text=help_text(message), reply_markup=buttons(message))

@BOT.message_handler(content_types=['text'])
def main_message(message):
    register_user(message)
    if(message.text == "Помощь"):
        BOT.send_message(message.chat.id, text=help_text(message), reply_markup=buttons(message))
    
    elif(message.text == "Получить отчет"):
        if message.chat.id in primary_id:
            keyboard = types.InlineKeyboardMarkup()

            key_today = types.InlineKeyboardButton(text='Сегодня', callback_data='today')
            key_yesterday= types.InlineKeyboardButton(text='Вчера', callback_data='yesterday')
            key_any = types.InlineKeyboardButton(text='Другой день', callback_data='any')

            keyboard.add(key_today)
            keyboard.add(key_yesterday)
            keyboard.add(key_any)

            BOT.send_message(message.chat.id, "Выберите дату отчета", reply_markup=keyboard)
        else:
            BOT.send_message(message.chat.id, "Нет доступа", reply_markup=buttons(message))
    elif(message.text == "Выгрузить базу"):
        if message.chat.id in primary_id:
            get_database(message)
            BOT.send_message(message.chat.id, "Выгруженная база", reply_markup=buttons(message))
        else:
            BOT.send_message(message.chat.id, "Нет доступа", reply_markup=buttons(message))
    else:
        BOT.send_message(message.chat.id, text='Неверный ввод, для помощи нажмите на кнопку "Помощь" или введите /help', reply_markup=buttons(message))

start_thread()
BOT.infinity_polling()