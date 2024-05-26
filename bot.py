import telebot
from telebot import types
import sqlite3
import logging
from contextlib import closing

# Ваш токен Telegram API
TOKEN = "7009129559:AAF4Ai_u6deROWCW7vDjK70U3eJsf7h1fRo"

# Создаем объект бота
bot = telebot.TeleBot(TOKEN)

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)

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
    payer = call.from_user.first_name
    selected_users = ', '.join(expenses[chat_id]['users'])
    try:
        with closing(sqlite3.connect('expenses.db')) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("INSERT INTO expenses (chat_id, amount, payer, users) VALUES (?, ?, ?, ?)",
                               (chat_id, expenses[chat_id]['amount'], payer, selected_users))
                conn.commit()
        bot.send_message(chat_id, f'ок. витрату записано на: {selected_users}')
    except sqlite3.Error as e:
        logging.error(f'Помилка бази даных: {e}')
        bot.send_message(chat_id, 'Виникла помилка. Спробуйте ще раз.')

# Добавление команды для просмотра всех расходов
@bot.message_handler(commands=['view_expenses'])
def view_expenses(message):
    try:
        with closing(sqlite3.connect('expenses.db')) as conn:
            with closing(conn.cursor()) as cursor:
                cursor.execute("SELECT amount, payer, users FROM expenses WHERE chat_id=?", (message.chat.id,))
                rows = cursor.fetchall()
                if rows:
                    debts = {user: 0 for user in users}
                    for row in rows:
                        amount, payer, user_str = row
                        involved_users = user_str.split(', ')
                        share = amount / len(involved_users)
                        for user in involved_users:
                            if user != payer:
                                debts[user] -= share
                                debts[payer] += share
                    response = "Долги:\n"
                    for user, amount in debts.items():
                        if amount > 0:
                            response += f"{user} повинен отримати {amount} шекелей\n"
                        elif amount < 0:
                            response += f"{user} повинен {abs(amount)} шекелей\n"
                else:
                    response = "Нема витрат."
        bot.send_message(message.chat.id, response)
    except sqlite3.Error as e:
        logging.error(f'Помилка бази даных: {e}')
        bot.send_message(message.chat.id, 'Помилка даних. Спробуйте ще раз.')

# Запускаем бота
if __name__ == '__main__':
    bot.polling(none_stop=True)