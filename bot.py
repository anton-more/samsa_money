import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ConversationHandler, ContextTypes, filters, CallbackQueryHandler
)
from sqlalchemy import create_engine, Column, Integer, String, Float, desc
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import pandas as pd

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Загрузка переменных окружения из .env файла
load_dotenv()

# Статусы для ConversationHandler
PAYER, AMOUNT, DESCRIPTION, PARTICIPANTS = range(4)

# Инициализация базы данных с использованием SQLAlchemy
Base = declarative_base()
DATABASE_URL = 'sqlite:///expenses.db'
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


class Expense(Base):
    __tablename__ = 'expenses'
    id = Column(Integer, primary_key=True)
    payer = Column(String)
    amount = Column(Float)
    description = Column(String)
    participants = Column(String)


def init_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def add_expense(payer, amount, description, participants):
    session.add(Expense(payer=payer, amount=amount, description=description, participants=participants))
    session.commit()


def delete_last_expense():
    last_expense = session.query(Expense).order_by(desc(Expense.id)).first()
    if last_expense:
        session.delete(last_expense)
        session.commit()
        return last_expense
    return None


# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /start була викликана")
    await update.message.reply_text(
        'Салам! Я бот який допомогає з відстеженням витрат. /add додати витрату /help список команд.'
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /help була викликана")
    await update.message.reply_text(
        'Команди:\n'
        '/add - Додати витрату\n'
        '/debts - Поточні борги\n'
        '/history - Історія витрат\n'
        '/undo - Скасувати останню витрату\n'
        '/report - Отримати звіт\n'
    )


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [['Антон', 'Олег', 'Севіль', 'Отмена']]
    await update.message.reply_text(
        'Хто сплатив?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return PAYER


async def add_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['payer'] = update.message.text
    reply_keyboard = [['Відмінити']]
    await update.message.reply_text(
        'Скільки було витрачено?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)
    )
    return AMOUNT


async def add_amount(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        amount = float(update.message.text)
        context.user_data['amount'] = amount
        await update.message.reply_text('На що ці гроші були витрачені?')
        return DESCRIPTION
    except ValueError:
        await update.message.reply_text('Бумласка, введіть число.')
        return AMOUNT


async def add_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['description'] = update.message.text
    inline_keyboard = [
        [InlineKeyboardButton("Антон", callback_data='Антон')],
        [InlineKeyboardButton("Олег", callback_data='Олег')],
        [InlineKeyboardButton("Севіль", callback_data='Севіль')],
        [InlineKeyboardButton("Готово", callback_data='done')],
    ]
    await update.message.reply_text(
        'Хто буде за це платити? Оберіть зі списку і натисніть "Готово".',
        reply_markup=InlineKeyboardMarkup(inline_keyboard)
    )
    context.user_data['participants'] = []
    context.user_data['done'] = False
    return PARTICIPANTS


async def add_participant(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if context.user_data['done']:
        await query.answer("Витрата вже записана.", show_alert=True)
        return ConversationHandler.END
    if query.data == 'done':
        participants = context.user_data['participants']
        if not participants:
            await query.edit_message_text('Оберіть учасників.')
            return PARTICIPANTS
        payer = context.user_data['payer']
        amount = context.user_data['amount']
        description = context.user_data['description']
        add_expense(payer, amount, description, ','.join(participants))
        logging.info(
            f"Витрату додано: {payer} сплачено, {amount} шекелів, {description}, учасники {participants}")
        context.user_data['done'] = True
        await query.edit_message_text('Витрату додано.')
        return ConversationHandler.END
    else:
        if query.data not in context.user_data['participants']:
            context.user_data['participants'].append(query.data)
        else:
            context.user_data['participants'].remove(query.data)
        selected_participants = ', '.join(context.user_data['participants'])
        inline_keyboard = [
            [InlineKeyboardButton("✔️ Антон" if "Антон" in context.user_data['participants'] else "Антон",
                                  callback_data='Антон')],
            [InlineKeyboardButton("✔️ Олег" if "Олег" in context.user_data['participants'] else "Олег",
                                  callback_data='Олег')],
            [InlineKeyboardButton("✔️ Севіль" if "Севіль" in context.user_data['participants'] else "Севіль",
                                  callback_data='Севіль')],
            [InlineKeyboardButton("Готово", callback_data='done')],
        ]
        await query.edit_message_text(
            f"Учасники: {selected_participants}\nНатисніть 'Готово' для завершеня.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard)
        )
        return PARTICIPANTS


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text('Добавление расхода отменено.', reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /undo была вызвана")
    last_expense = delete_last_expense()
    if last_expense:
        await update.message.reply_text(
            f'Останню витрату скасовано: {last_expense.payer} витратив {last_expense.amount:.2f} шек. на {last_expense.description} для {last_expense.participants}.'
        )
    else:
        await update.message.reply_text('Нет расходов для отмены.')


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /history була викликана")
    expenses = session.query(Expense).all()
    if not expenses:
        await update.message.reply_text('Історія витрат порожня.')
    else:
        history_messages = []
        for expense in expenses:
            history_messages.append(
                f'{expense.payer} витратив {expense.amount:.2f} шек. на {expense.description} для {expense.participants}')

        await update.message.reply_text('\n'.join(history_messages))


def calculate_debts():
    expenses = session.query(Expense).all()
    balances = {}
    for expense in expenses:
        payer = expense.payer
        amount = expense.amount
        participants = [p.strip() for p in expense.participants.split(',')]
        split_amount = amount / len(participants)

        if payer not in balances:
            balances[payer] = 0
        balances[payer] += amount

        for participant in participants:
            if participant not in balances:
                balances[participant] = 0
            balances[participant] -= split_amount

    net_balances = {person: balance for person, balance in balances.items() if balance != 0}
    logging.info(f"Поточні борги: {net_balances}")
    return net_balances

async def debts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /debts була викликана")
    debts = calculate_debts()
    if not debts:
        await update.message.reply_text('Нема боргів.')
    else:
        debt_messages = []
        for person, amount in debts.items():
            if amount < 0:
                debt_messages.append(f'{person} повинен {-amount:.2f} шек.')
            elif amount > 0:
                debt_messages.append(f'{person} повинен отримати {amount:.2f} шек.')

        await update.message.reply_text('\n'.join(debt_messages))


async def report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logging.info("Команда /report була викликана")
    expenses = session.query(Expense).all()
    if not expenses:
        await update.message.reply_text('Нема даних для звіту.')
    else:
        report_data = []
        for expense in expenses:
            report_data.append([expense.payer, expense.amount, expense.description, expense.participants])

        df = pd.DataFrame(report_data, columns=['Payer', 'Amount', 'Description', 'Participants'])
        file_path = 'expenses_report.csv'
        df.to_csv(file_path, index=False)

        await update.message.reply_document(document=open(file_path, 'rb'), filename='expenses_report.csv')


def main():
    init_db()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logging.error("Токен Telegram не найден в переменных окружения")
        return

    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("debts", debts))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("undo", undo))
    application.add_handler(CommandHandler("report", report))

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('add', add_start)],
        states={
            PAYER: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_payer)],
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_amount)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_description)],
            PARTICIPANTS: [CallbackQueryHandler(add_participant)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    application.add_handler(conv_handler)
    application.run_polling()


if __name__ == '__main__':
    main()
