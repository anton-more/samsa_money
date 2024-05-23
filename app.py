import telebot

bot = telebot.TeleBot("7009129559:AAF4Ai_u6deROWCW7vDjK70U3eJsf7h1fRo")


@bot.message_handler(commands=['start'])
def main(message):
    bot.send_message(message.chat.id, 'салам!')


bot.polling(none_stop=True)