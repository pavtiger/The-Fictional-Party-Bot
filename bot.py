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
 

# TODO: log errors


def check_admin(userid):
    q = f'SELECT "IsAdmin" FROM public.people WHERE "ID" = {userid};'
    cursor.execute(q)
    records = cursor.fetchall()
    return records[0][0]


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


def fetch(query):
    cursor.execute(query)
    return cursor.fetchall()


# function to handle the /start command
def start(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    user = update.message.from_user
    name = user["id"]
    
    records = fetch(f'SELECT "IsAdmin" FROM public.people WHERE "ID" = {user["id"]};')
    
    if records == []:
        q = f'INSERT INTO public.people("ID", "FirstName", "LastName", "Username") VALUES ({user["id"]}, \'{check_none(user["first_name"])}\', \'{check_none(user["last_name"])}\', \'{user["username"]}\');'
        cursor.execute(q)
        conn.commit()

        kb = [[KeyboardButton('/status')], [KeyboardButton('/tasks')], [KeyboardButton('/help')]]
        kb_markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=kb)
        update.message.bot.send_message(chat_id=update.message.chat_id,
            text="Здравствуйте, вы участник. Админ будет отправлять вам задания, и вы можете отправить картинку (можно с подписью) или просто текст ответом на выбранное задание. Чтобы поменять текущее задание напишите /tasks. У вас есть клавиратура с кнопками '/status' - выдает текущее задание и ваш рейтинг. По любым вопросам и предложениям пишите @pavTiger",
            reply_markup=kb_markup)
    else:
        if records[0][0]:  # Is Admin
            kb = [[KeyboardButton('/newtask')], [KeyboardButton('/list')], [KeyboardButton('/status')], [KeyboardButton('/tasks')], [KeyboardButton('/wall')], [KeyboardButton('/clear')]]
            kb_markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=kb)
            update.message.bot.send_message(chat_id=update.message.chat_id,
                text="Здравствуйте, теперь вы админ и можете проверять решения других. Вам будут приходить посылки. Участники не получают никакого штрафа за отклоненные решения.\nНажмите на кнопку '/newtask' чтобы отправить задание всем учатникам, '/clear' - очистить все рейтинги, '/wall' - сделать объявление всем участникам, '/tasks' - это сменить текущее задание, а '/list' - таблица всех участников",
                reply_markup=kb_markup)
        else:
            kb = [[KeyboardButton('/status')], [KeyboardButton('/tasks')], [KeyboardButton('/help')]]
            kb_markup = ReplyKeyboardMarkup(resize_keyboard=True, keyboard=kb)
            update.message.bot.send_message(chat_id=update.message.chat_id,
                text="Приятно снова вас видеть",
                reply_markup=kb_markup)


def button(update, context):
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery

    query.answer()
    query.edit_message_text(text=f"Ответ: {query.data}")


    if query.data == "no" or query.data == "yes":
        if query.data == "yes":
            q = f'UPDATE public.people SET "Reputation" = 0;'
            cursor.execute(q)
            conn.commit()
            bot.send_message(chat_id=query["message"]["chat"]["id"], text="Рейтинги очищены")
    else:
        records = fetch(f'SELECT "UserID", "TaskID", "TryID" FROM public.packages WHERE "MessageID" = {query["message"]["message_id"]} and "AdminID" = {query["message"]["chat"]["id"]};')

        if query.data == "comment":
            bot.send_message(chat_id=query["message"]["chat"]["id"], text="Напишите ваш коментарий")
            update_last_cmd("/comment_ok " + str(records[0][0]), query["message"]["chat"]["id"])

        if query.data == "ok" or query.data == "comment":
            t = fetch(f'SELECT * FROM public.packages WHERE "UserID" = {records[0][0]} and "TaskID" = {records[0][1]} and "Status" = 1;')

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
            bot.send_message(chat_id=query["message"]["chat"]["id"], text="Напишите коментарий к отклонению")
            update_last_cmd("/comment_reject " + str(records[0][0]), query["message"]["chat"]["id"])
            bot.send_message(chat_id=records[0][0], text="Ваше решение отклонили 😞")


        buttons = fetch(f'SELECT "AdminID", "MessageID" FROM public.packages WHERE "TryID" = {records[0][2]} and "UserID" = {records[0][0]};')
        for m in buttons:
            if m[0] != query["message"]["chat"]["id"]:
                bot.edit_message_text(text=f"Другой админ ответил: {query.data}", chat_id=m[0], message_id=m[1])


# function to handle the /help command
def help(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    update.message.reply_text("У вас есть клавиратура с кнопками /status' - дает информацию о текущей задаче и вашем рейтинге, а чтобы сдать задачу нужно просто написать текст или ")


def do_task(message):
    admin = check_admin(message.from_user["id"])

    if message.text == None:
        update_last_cmd(message.caption, message.from_user["id"])
    else:
        update_last_cmd(message.text, message.from_user["id"])


    if admin == True:  # If he/she is admin
        records = fetch(f'SELECT "ID" FROM public.people WHERE not "ID" = {message.from_user["id"]};')

        for name in records:
            message.bot.send_message(chat_id=name[0], text="Новое задание:")

            m = message.bot.forward_message(chat_id=name[0],
                from_chat_id=message.chat_id,
                message_id=message.message_id)

        if message.text == None:
            q = f'INSERT INTO public.tasks("ID", "Text") VALUES ({get_last_task_id() + 1}, \'{message.caption.replace("/task ", "")}\');'
            cursor.execute(q)
            conn.commit()
        else:
            q = f'INSERT INTO public.tasks("ID", "Text") VALUES ({get_last_task_id() + 1}, \'{message.text.replace("/task ", "")}\');'
            cursor.execute(q)
            conn.commit()

        message.reply_text('Разослал ваше задание всем')
    else:
        message.reply_text('Вы не админ')


def do_wall(message):
    admin = check_admin(message.from_user["id"])

    if message.text == None:
        update_last_cmd(message.caption, message.from_user["id"])
    else:
        update_last_cmd(message.text, message.from_user["id"])


    if admin == True:  # If he/she is admin
        records = fetch(f'SELECT "ID" FROM public.people WHERE not "ID" = {message.from_user["id"]};')

        for name in records:
            m = message.bot.forward_message(chat_id=name[0],
                from_chat_id=message.chat_id,
                message_id=message.message_id)

        message.reply_text('Разослал ваше сообщение всем')
    else:
        message.reply_text('Вы не админ')


# submit
def submit(update, context):
    # triggered by user (general text messages)
    user = update.message.from_user


    records = fetch(f'SELECT "LastCommand" FROM public.people WHERE "ID" = {user["id"]};')

    if records[0][0] != None and records[0][0].split()[0] in ["/comment_reject", "/comment_ok"]:
        bot.send_message(chat_id=records[0][0].split()[1], text=update.message.text)
        update_last_cmd(update.message.text, user["id"])

    elif records[0][0] != None and records[0][0].split()[0] == "/tasks":
        try:
            q = f'UPDATE public.people SET "ActiveTaskID" = {int(update.message.text)} WHERE "ID" = {user["id"]};'
            cursor.execute(q)
            conn.commit()
            update_last_cmd(update.message.text, user["id"])
            status(update, context)
        except:
            update.message.reply_text('Пожалуйста отправьте номер задания')

    elif records[0][0] != None and records[0][0].split()[0] == "/newtask":
        do_task(update.message)

    elif records[0][0] != None and records[0][0].split()[0] == "/wall":
        do_wall(update.message)

    else:
        records = fetch(f'SELECT "ID" FROM public.people WHERE "IsAdmin" = true;')

        if update.message.text != None and not update.message.text.split()[0] in ["/comment_reject", "/comment_ok"]:
            update_last_cmd(update.message.text, user["id"])

        last_try = get_last_try(user["id"])

        for name in records:
            task = get_last_task_id()
            if task == -1:
                update.message.reply_text('Вы не можете сдать задачу, потому что админ еще не выложил ни одного задания.')
                return;

            m = update.message.bot.forward_message(chat_id=name[0],
                                    from_chat_id=update.message.chat_id,
                                    message_id=update.message.message_id)

            keyboard = [
                [InlineKeyboardButton("Отлично", callback_data='ok')],
                [InlineKeyboardButton("Хорошо с комментарием", callback_data='comment')],
                [InlineKeyboardButton("Отклонить", callback_data='reject')]
            ]

            reply_markup = InlineKeyboardMarkup(keyboard)

            cnt = fetch(f'SELECT "ActiveTaskID" FROM public.people WHERE "ID" = {user["id"]};')

            if cnt[0][0] == None:
                current_task = get_last_task_id()
            else:
                current_task = cnt[0][0]

            thetask = fetch(f'SELECT "Text" FROM public.tasks WHERE "ID" = {current_task};')

            message_reply_text = check_none(thetask[0][0])

            button = update.message.bot.send_message(chat_id=m["chat"]["id"],
                text=message_reply_text,
                reply_markup=reply_markup)

            q = f'INSERT INTO public.packages("UserID", "TaskID", "MessageID", "AdminID", "TryID") VALUES ({user["id"]}, \'{current_task}\', \'{button["message_id"]}\', \'{button["chat"]["id"]}\', \'{last_try + 1}\');'
            cursor.execute(q)
            conn.commit()

        update.message.reply_text('Отправил ваше сообщение админу')


# function to handle errors occured in the dispatcher 
def error(update, context):
    update.message.reply_text('Произошла ошибка, напишите @pavtiger')


def task(update, context):
    admin = check_admin(update.message.from_user["id"])

    if admin == True:  # If he/she is admin
        update_last_cmd(update.message.text, update.message.from_user["id"])
        if len(update.message.text.split()) > 1:
            do_task(update.message)
        else:
            update.message.reply_text("Введите задание")
    else:
        update.message.reply_text("Вы не админ")
        

def score(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    admin = check_admin(update.message.from_user["id"])

    q = f'SELECT * FROM public.people'
    dat = sqlio.read_sql_query(q, conn)
    
    ans = ""
    for index, row in dat.iterrows():
        ans += f'{str(row["Reputation"])} - {"".join(row["FirstName"].rstrip())} {"".join(row["LastName"].rstrip())}\n';

    if admin == True:
        update.message.reply_text(ans)
    else:
        update.message.reply_text("Только админ может пользоваться этой командой")


def status(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])
    user = update.message.from_user

    cnt = fetch(f'SELECT "Reputation", "ActiveTaskID" FROM public.people WHERE "ID" = {user["id"]};')

    if cnt[0][1] == None:
        task = get_last_task_id()
    else:
        task = cnt[0][1]

    if task == -1:
        update.message.reply_text(f"Ваш рейтинг: {cnt[0][0]}\nЗаданий пока нет")
    else:
        records = fetch(f'SELECT "Text" FROM public.tasks WHERE "ID" = {task};')

        p = fetch(f'SELECT COUNT(*) FROM public.packages WHERE "Status" = 1 and "UserID" = {user["id"]} and "TaskID" = {task};')

        if p[0][0] == 0:
            update.message.reply_text(f"Ваш рейтинг: {cnt[0][0]}\nТекущее задание номер {task}:\n{records[0][0]}")
        else:
            update.message.reply_text(f"Ваш рейтинг: {cnt[0][0]}\nТекущее задание решено")


def clear(update, context):
    admin = check_admin(update.message.from_user["id"])
    if admin:
        keyboard = [
                [InlineKeyboardButton("Да, удалить", callback_data='yes')],
                [InlineKeyboardButton("Нет", callback_data='no')]
        ]

        reply_markup = InlineKeyboardMarkup(keyboard)

        button = update.message.bot.send_message(chat_id=update.message.chat_id,
            text="Вы уверены что хотите очистить баллы у всех участников?",
            reply_markup=reply_markup)
    else:
        update.message.reply_text("Только админ может пользоваться этой командой")


def problems(update, context):
    update_last_cmd(update.message.text, update.message.from_user["id"])

    q = f'SELECT * FROM public.tasks AS T WHERE not EXISTS( SELECT * FROM public.packages AS P WHERE P."TaskID" = T."ID" and "UserID" = {update.message.from_user["id"]} and "Status" = 1 )'
    dat = sqlio.read_sql_query(q, conn)
    
    ans = ""
    for index, row in dat.iterrows():
        ans += f'{str(row["ID"])}: {"".join(row["Text"].rstrip())}\n';
    ans += "Введите номер для смены текущего задания"

    update.message.reply_text(ans)


def wall(update, context):
    admin = check_admin(update.message.from_user["id"])

    if admin == True:  # If he/she is admin
        update_last_cmd(update.message.text, update.message.from_user["id"])
        if len(update.message.text.split()) > 1:
            do_wall(update.message)
        else:
            update.message.reply_text("Введите сообщение")
    else:
        update.message.reply_text("Вы не админ")


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
    dispatcher.add_handler(CommandHandler("newtask", task))
    dispatcher.add_handler(CommandHandler("list", score))
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("clear", clear))
    dispatcher.add_handler(CommandHandler("tasks", problems))
    dispatcher.add_handler(CommandHandler("wall", wall))


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
