from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Bot, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, CallbackContext
import psycopg2
import pandas as pd
import pandas.io.sql as sqlio
import telegram

from my_token import my_token

conn = psycopg2.connect(dbname='TelegramActivities', user='sa', 
                        password='1qaz3edc5tgb', host='192.168.1.81', port=5433)
cursor = conn.cursor()

# TODO: Usernames 

def update_last_cmd(text, user):
    q = f'UPDATE public.people SET "LastCommand" = \'{text}\' WHERE "ID" = {user};'
    cursor.execute(q)
    conn.commit()


def get_last_task_id():
    q = f'SELECT MAX("ID") FROM public.tasks;'
    cursor.execute(q)
    records = cursor.fetchall()
    if records[0][0] == None:
        return -1
    return records[0][0]


def get_last_try(userid):
    q = f'SELECT MAX("TryID") FROM public.packages WHERE "UserID" = {userid};'
    cursor.execute(q)
    records = cursor.fetchall()
    if records[0][0] == None:
        return -1
    return records[0][0]


def check_none(name):
    if name == None:
        return ""
    return name


# function to handle the /start command
def start(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    user = update.message.from_user
    name = user["id"]
    
    q = f'SELECT "IsAdmin" FROM public.people WHERE "ID" = {user["id"]};'
    cursor.execute(q)
    records = cursor.fetchall()
    
    if records == []:
        q = f'INSERT INTO public.people("ID", "FirstName", "LastName", "Username") VALUES ({user["id"]}, \'{check_none(user["first_name"])}\', \'{check_none(user["last_name"])}\', \'{user["username"]}\');'
        cursor.execute(q)
        conn.commit()

        kb = [[KeyboardButton('/help')], [KeyboardButton('/list')]]
        kb_markup = ReplyKeyboardMarkup(kb)
        update.message.bot.send_message(chat_id=update.message.chat_id,
            text="Здравствуйте, вы участник. Админ будет отправлять вам задания, и вы можете отправить картинку (можно с подписью) или просто текст ответом на самое последнее задание. У вас есть клавиратура с кнопками '/list' - это списток всех участников с их баллами. По любым вопросам и предложениям пишите @pavTiger",
            reply_markup=kb_markup)
    else:
        if records[0][0]:
            kb = [[KeyboardButton('/task')], [KeyboardButton('/list')]]
            kb_markup = ReplyKeyboardMarkup(kb)
            update.message.bot.send_message(chat_id=update.message.chat_id,
                text="Здравствуйте, теперь вы админ и можете проверять решения других. Теперь вам будут приходить посылки. Админов может быть несколько. Участники не ограниченны в посылках, и не получают никакого штрафа за отклоненные решения. \n Нажмите на кнопку '/task' чтобы задать задание (оно сразу отошлется всем участникам)",
                reply_markup=kb_markup)
        else:
            kb = [[KeyboardButton('/help')], [KeyboardButton('/list')]]
            kb_markup = ReplyKeyboardMarkup(kb)
            update.message.bot.send_message(chat_id=update.message.chat_id,
                text="Приятно снова вас видеть",
                reply_markup=kb_markup)        


def button(update, context):
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery

    query.answer()
    query.edit_message_text(text=f"Ответ: {query.data}")


    q = f'SELECT "UserID", "TaskID", "TryID" FROM public.packages WHERE "MessageID" = {query["message"]["message_id"]} and "AdminID" = {query["message"]["chat"]["id"]};'
    cursor.execute(q)
    records = cursor.fetchall()

    if query.data == "ok":
        q = f'SELECT * FROM public.packages WHERE "UserID" = {records[0][0]} and "TaskID" = {records[0][1]} and "Status" = 1;'
        cursor.execute(q)
        t = cursor.fetchall()

        if t == []:
            q = f'UPDATE public.people SET "Reputation" = "Reputation" + 1 WHERE "ID" = {records[0][0]};'
            cursor.execute(q)
            conn.commit()

            q = f'UPDATE public.packages SET "Status" = 1 WHERE "MessageID" = {query["message"]["message_id"]} and "AdminID" = {query["message"]["chat"]["id"]}'
            cursor.execute(q)
            conn.commit()

        bot.send_message(chat_id=records[0][0], text="Ваше решение одобрили 👍")
    else:
        q = f'UPDATE public.packages SET "Status" = -1 WHERE "MessageID" = {query["message"]["message_id"]} and "AdminID" = {query["message"]["chat"]["id"]}'
        cursor.execute(q)
        conn.commit()
        bot.send_message(chat_id=records[0][0], text="Ваше решение отклонили 😞")


    q = f'SELECT "AdminID", "MessageID" FROM public.packages WHERE "TryID" = {records[0][2]} and "UserID" = {records[0][0]};'
    cursor.execute(q)
    buttons = cursor.fetchall()
    for m in buttons:
        if m[0] != query["message"]["chat"]["id"]:
            bot.edit_message_text(text=f"Другой админ ответил: {query.data}", chat_id=m[0], message_id=m[1])


# function to handle the /help command
def help(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    update.message.reply_text("У вас есть клавиратура с кнопками '/list' - это списток всех участников с их баллами, '/task' - это установка задания (только для админов)")


# submit
def submit(update, context):
    # triggered by user

    user = update.message.from_user


    q = f'SELECT "LastCommand" FROM public.people WHERE "ID" = {user["id"]};'
    cursor.execute(q)
    records = cursor.fetchall()

    if records[0][0] != None and records[0][0].split()[0] == "/task":
        q = f'SELECT "IsAdmin" FROM public.people WHERE "ID" = {user["id"]};'
        cursor.execute(q)
        records = cursor.fetchall()
        if update.message.text == None:
            update_last_cmd(update.message.caption, user["id"])
        else:
            update_last_cmd(update.message.text, user["id"])


        if records[0][0] == True:  # If he is admin
            q = f'SELECT "ID" FROM public.people WHERE not "ID" = {user["id"]};'
            cursor.execute(q)
            records = cursor.fetchall()

            for name in records:
                m = update.message.bot.forward_message(chat_id=name[0],
                    from_chat_id=update.message.chat_id,
                    message_id=update.message.message_id)

            if update.message.text == None:
                q = f'INSERT INTO public.tasks("ID", "Text") VALUES ({get_last_task_id() + 1}, \'{update.message.caption}\');'
                cursor.execute(q)
                conn.commit()
            else:
                q = f'INSERT INTO public.tasks("ID", "Text") VALUES ({get_last_task_id() + 1}, \'{update.message.text}\');'
                cursor.execute(q)
                conn.commit()

            update.message.reply_text('Разослал ваше задание всем')
        else:
            update.message.reply_text('Вы не админ')

    else:

        q = f'SELECT "ID" FROM public.people WHERE "IsAdmin" = true;'
        cursor.execute(q)
        records = cursor.fetchall()


        update_last_cmd(update.message.text, user["id"])
        last_try = get_last_try(user["id"])

        for name in records:
            task = get_last_task_id()
            if task == -1:
                update.message.reply_text('Вы не можете сдать задачу, потому что админ еще не выложил ни одного задания.')
                return;

            m = update.message.bot.forward_message(chat_id=name[0],
                                    from_chat_id=update.message.chat_id,
                                    message_id=update.message.message_id,
                                    disable_notification=True)

            keyboard = [
                [InlineKeyboardButton("Хорошо", callback_data='ok')],
                [InlineKeyboardButton("Отклонить", callback_data='reject')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)
            message_reply_text = check_none(user["first_name"]) + ' ' + check_none(user["last_name"])

            button = update.message.bot.send_message(chat_id=m["chat"]["id"],
                text=message_reply_text,
                reply_markup=reply_markup,
                disable_notification=True)

            q = f'INSERT INTO public.packages("UserID", "TaskID", "MessageID", "AdminID", "TryID") VALUES ({user["id"]}, \'{task}\', \'{button["message_id"]}\', \'{button["chat"]["id"]}\', \'{last_try + 1}\');'
            cursor.execute(q)
            conn.commit()

        update.message.reply_text('Отправил ваще сообщение админу')


# function to handle errors occured in the dispatcher 
def error(update, context):
    update.message.reply_text('Произошла ошибка, напишите @pavtiger')


def task(update, context):
    q = f'SELECT "IsAdmin" FROM public.people WHERE "ID" = {update.message.from_user["id"]};'
    cursor.execute(q)
    records = cursor.fetchall()

    if records[0][0] == True:  # If he is admin
        update_last_cmd(update.message.text, update.message.from_user["id"])
        update.message.reply_text('Введите задание')
    else:
        update.message.reply_text('Вы не админ')
        

def score(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])

    q = f'SELECT * FROM public.people'
    dat = sqlio.read_sql_query(q, conn)
    
    ans = ""
    for index, row in dat.iterrows():
        ans += f'{str(row["Reputation"])} - {"".join(row["FirstName"].rstrip())} {"".join(row["LastName"].rstrip())}\n';

    update.message.reply_text(ans)


def main():
    # create the updater, that will automatically create also a dispatcher and a queue to 
    # make them dialoge

    global bot
    bot = telegram.Bot(token=my_token)

    updater = Updater(my_token, use_context=True)
    dispatcher = updater.dispatcher

    # add handlers for start and help commands
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help))
    dispatcher.add_handler(CommandHandler("task", task))
    dispatcher.add_handler(CommandHandler("list", score))


    dispatcher.add_handler(CallbackQueryHandler(button))

    # add an handler for normal text (not commands)
    dispatcher.add_handler(MessageHandler(Filters.text, submit))
    dispatcher.add_handler(MessageHandler(Filters.photo, submit))

    # add an handler for errors
    # dispatcher.add_error_handler(error)

    # start your shiny new bot
    updater.start_polling()

    # run the bot until Ctrl-C
    updater.idle()


if __name__ == '__main__':
    main()
