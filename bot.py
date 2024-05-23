import telebot
from telebot import types
import sqlite3

# Ваш токен Telegram API
TOKEN = "7009129559:AAF4Ai_u6deROWCW7vDjK70U3eJsf7h1fRo"

# Создаем объект бота
bot = telebot.TeleBot(TOKEN)

# Инициализируем переменную expenses
expenses = {}

# Список пользователей
users = ['Антон', 'Олег', 'Севиль']

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.ReplyKeyboardMarkup(row_width=1)
    start_button = types.KeyboardButton('додати витрату')
    markup.add(start_button)
    bot.send_message(message.chat.id, 'салам!', reply_markup=markup)

# Обработчик нажатия кнопки "додати витрату"
@bot.message_handler(func=lambda message: message.text == 'додати витрату')
def ask_expense_amount(message):
    bot.send_message(message.chat.id, 'введи суму витрати')
    bot.register_next_step_handler(message, process_expense_amount)

# Обработчик ввода суммы расхода
def process_expense_amount(message):
    try:
        amount = float(message.text)
        expenses[message.chat.id] = {'amount': amount, 'users': []}
        markup = types.InlineKeyboardMarkup()
        for user in users:
            markup.add(types.InlineKeyboardButton(user, callback_data=f"user_{user}"))
        bot.send_message(message.chat.id, 'ок. на кого ця витрата?', reply_markup=markup)
    except ValueError:
        bot.send_message(message.chat.id, 'будь ласка, введи коректну суму')

# Обработчик нажатия кнопок выбора пользователя
@bot.callback_query_handler(func=lambda call: call.data.startswith('user_'))
def process_user_selection(call):
    user = call.data.split('_')[1]
    chat_id = call.message.chat.id
    if user in expenses[chat_id]['users']:
        expenses[chat_id]['users'].remove(user)
    else:
        expenses[chat_id]['users'].append(user)
    markup = types.InlineKeyboardMarkup()
    for user in users:
        if user in expenses[chat_id]['users']:
            markup.add(types.InlineKeyboardButton(user + ' ✅', callback_data=f"user_{user}"))
        else:
            markup.add(types.InlineKeyboardButton(user, callback_data=f"user_{user}"))
    markup.add(types.InlineKeyboardButton('записати витрату', callback_data='save_expense'))
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text='ок. на кого ця витрата?', reply_markup=markup)

# Обработчик нажатия кнопки "записати витрату"
@bot.callback_query_handler(func=lambda call: call.data == 'save_expense')
def save_expense(call):
    chat_id = call.message.chat.id
    if not expenses.get(chat_id):
        bot.send_message(chat_id, 'спочатку додайте витрату')
        return
    selected_users = ', '.join(expenses[chat_id]['users'])
    # Подключаемся к базе данных SQLite
    conn = sqlite3.connect('expenses.db')
    cursor = conn.cursor()
    # Записываем данные в базу данных
    cursor.execute("INSERT INTO expenses VALUES (?, ?, ?)", (chat_id, expenses[chat_id]['amount'], selected_users))
    conn.commit()
    conn.close()  # Закрываем соединение
    bot.send_message(chat_id, f'ок. витрату записано на: {selected_users}')

# Запускаем бота
bot.polling(none_stop=True)
