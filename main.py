import os

import telebot
import vk_api
import sqlite3
from dotenv import load_dotenv
from telebot import types
from telebot.types import ReplyKeyboardMarkup, Message

DFT_AMOUNT = 2
DFT_SIZE = 200
MAX_DOMAINS = 50
MAX_AMOUNT = 15
MAX_SIZE = 1000
MIN_AMOUNT = 1
MIN_SIZE = 50

# help_command = "Команда имеет вид:\n"
# help_see = "/see\n/see size <значение>\n/see amount <значение>\n"
# help_set = "/set size <значение настройки>\n/set amount <значение настройки>\n/set show\n"
# help_show = "/show\n"
# help_add = "/add <домен/ссылка> ...\n"
# help_del = "/del\n/del <домен/ссылка> ...\n"

dict_buf_coms = {}

load_dotenv()

bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
app = vk_api.VkApi(token=os.getenv("VK_APP_TOKEN")).get_api()

db = sqlite3.connect("mainDB.db", check_same_thread=False)
sql = db.cursor()

sql.execute("BEGIN;")
# user_id | amount | size
# table of users with personal settings
sql.execute(
    """
    CREATE TABLE IF NOT EXISTS usersT ( 
      user_id UNSIGNED BIG INT PRIMARY KEY NOT NULL,
      amount UNSIGNED BIG INT,
      size UNSIGNED BIG INT
    );
    """
)  # уникальность id

# user_id | domain
# table stores domains for user
sql.execute(
    """
    CREATE TABLE IF NOT EXISTS domainsT (
      user_id UNSIGNED BIG INT NOT NULL,
      domain VARCHAR(50),
      
      CONSTRAINT unique_pair UNIQUE (user_id, domain)
      FOREIGN KEY (user_id) REFERENCES usersT(user_id) ON DELETE CASCADE
    );
    """
)
sql.execute("COMMIT;")

print(sql.execute("SELECT * FROM usersT").fetchall())
print(sql.execute("SELECT * FROM domainsT").fetchall())


def test():
    pass


def parse_text_of_post(text: str, size: int):
    if text == '':
        return "[Пост без текста]"

    is_parse = False
    res_text = ""
    for c in text:
        if size == 0:
            break
        elif c == '[':
            is_parse = True
        elif c == '|' or c == ']':
            is_parse = False
        elif not is_parse:
            res_text += c
            size -= 1

    if not size:
        res_text += "..."

    return res_text


def get_user_domains(user_id: int):
    return list(map(lambda x: x[0], sql.execute(f"SELECT domain FROM domainsT WHERE user_id={user_id};").fetchall()))


def is_user_have_domain(user_id: int):
    return True if sql.execute(f"SELECT domain FROM domainsT WHERE user_id={user_id} LIMIT 1;").fetchone() else False


def get_domain_from_link(domain):
    return domain[domain.rfind('/') + 1:]


def get_keyboard_of_domains(user_id: int, is_ender: bool):
    kb = ReplyKeyboardMarkup()

    if is_ender:
        kb.row("Конец")

    domains_list = get_user_domains(user_id)
    length = len(domains_list) if len(domains_list) < MAX_DOMAINS else MAX_DOMAINS
    for i in range(length):
        kb.add(domains_list[i])

    return kb


def get_keyboard_yes_or_no():
    kb = ReplyKeyboardMarkup()
    kb.row("Да", "Нет")

    return kb


def send_msg(user_id, msg, keyboard=None):
    # функция для отправки сообщения пользователю
    bot.send_message(user_id, msg, reply_markup=keyboard)


def input_arg_del(user_id, definite_domain):
    global dict_buf_coms
    dict_buf_coms[user_id] += definite_domain + ' '
    # send_msg(
    #     user_id,
    #     "Продолжите выбирать домены или нажмите кнопку «Конец»."
    # )


def rlzn_del(user_id: int, str_of_list_domains: str):
    clean_buf_of_coms(user_id)

    list_domains = str_of_list_domains.split()
    if not list_domains:
        send_msg(user_id, "Вы ничего не удалили.", keyboard=types.ReplyKeyboardRemove())
        return

    text_msg = "Вы удалили:\n"
    sql.execute("BEGIN;")
    for domain in list_domains:
        sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id} AND domain='{get_domain_from_link(domain)}';")
        text_msg += f"• {domain}\n"
    sql.execute("COMMIT;")

    send_msg(user_id, text_msg, keyboard=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['add'])
def com_add(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'add'

    send_msg(
        com.chat.id,
        "Введите один или несколько доменов или ссылок через пробел",
    )


def rlzn_add(user_id: int, str_of_list_domains: str):
    clean_buf_of_coms(user_id)

    counter_of_new_domains = 0
    cur_amount_domains = len(get_user_domains(user_id))
    list_domains = str_of_list_domains.split()
    text_msg = "Результаты добавления групп:\n"
    sql.execute("BEGIN;")
    for domain in list_domains:
        domain = get_domain_from_link(domain)
        try:
            app.groups.getById(group_id=domain)  # проверка; домен - это группа или что-то другое
            if cur_amount_domains + counter_of_new_domains < MAX_DOMAINS:
                sql.execute(f"INSERT OR IGNORE INTO domainsT (user_id, domain) VALUES ({user_id}, '{domain}');")
                text_msg += f"• {domain} - добавлено\n"
            else:
                break

            counter_of_new_domains += 1
        except vk_api.exceptions.ApiError:
            text_msg += f"• {domain} - ненайдено или не является группой\n"
    sql.execute("COMMIT;")

    send_msg(user_id, text_msg)

    print(sql.execute("SELECT * FROM usersT").fetchall())
    print(sql.execute("SELECT * FROM domainsT").fetchall())


@bot.message_handler(commands=['delete_user'])
def com_delete_user(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'delete_user'

    send_msg(
        com.chat.id,
        "Вы уверены, что хотите удалить все домены и вернуть первоначальные настройки?",
        keyboard=get_keyboard_yes_or_no()
    )


def rlzn_delete_user(user_id: int, is_confirm: bool):
    clean_buf_of_coms(user_id)

    if is_confirm:
        sql.execute("BEGIN;")
        sql.execute(f"DELETE FROM usersT WHERE user_id={user_id};")
        sql.execute("COMMIT;")

        send_msg(user_id, "Вы удалили сохранённые настройки и все домены.", keyboard=types.ReplyKeyboardRemove())
        to_start(user_id)
    else:
        send_msg(user_id, "Сохранённые настройки и все домены остались без изменений.",
                 keyboard=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['set_amount'])
def com_set_amount(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'set_amount'

    send_msg(com.chat.id, "Введите количество постов.")


def rlzn_set_amount(user_id: int, amount: str):
    if amount.isdigit():
        clean_buf_of_coms(user_id)
        amount = int(amount)
        if amount < MIN_AMOUNT:
            amount = MIN_AMOUNT
        elif amount > MAX_AMOUNT:
            amount = MAX_AMOUNT

        sql.execute("BEGIN;")
        sql.execute(f"UPDATE usersT SET amount={amount} WHERE user_id={user_id};")
        sql.execute("COMMIT;")

        send_msg(user_id, f"Количество отображаемых постов: {amount}.")
    else:
        send_msg(user_id, "Вы ввели не число.")


@bot.message_handler(commands=['set_size'])
def com_set_size(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'set_size'

    send_msg(com.chat.id, "Введите количество отображаемых символов.")


def rlzn_set_size(user_id: int, size: str):
    if size.isdigit():
        clean_buf_of_coms(user_id)
        size = int(size)
        if size < MIN_SIZE:
            size = MIN_SIZE
        elif size > MAX_SIZE:
            size = MAX_SIZE

        sql.execute("BEGIN;")
        sql.execute(f"UPDATE usersT SET size={size} WHERE user_id={user_id};")
        sql.execute("COMMIT;")

        send_msg(user_id, f"Количество отображаемых сиволов: {size}.")
    else:
        send_msg(user_id, "Вы ввели не число.")


@bot.message_handler(commands=['set_info'])
def rlzn_set_info(com: Message):
    sql.execute("BEGIN;")
    settings_of_user = sql.execute(f"SELECT amount, size FROM usersT WHERE user_id={com.chat.id};").fetchone()
    sql.execute("COMMIT;")

    msg_text = f"""
    Текущие настройки:
    • кол-во отображаемых постов: {settings_of_user[0]}
    • кол-во отображаемых символов: {settings_of_user[1]}
    """
    send_msg(com.chat.id, msg_text)


@bot.message_handler(commands=['show'])
def rlzn_show(com: Message):
    list_of_domains = get_user_domains(com.chat.id)
    if list_of_domains:
        text_msg = "Ваши отслеживаемые группы:\n\n"
        for domain in list_of_domains:
            text_msg += f"• {'https://vk.com/' + domain} - {domain} - {app.groups.getById(group_id=domain)[0]['name']}\n"
    else:
        text_msg = "Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add"

    send_msg(com.chat.id, text_msg)


@bot.message_handler(commands=['del'])
def com_del(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'del'

    send_msg(
        com.chat.id,
        "Нажимайте на домены, которые хотите удалить, чтобы закончить нажмите на кнопку «Конец».",
        keyboard=get_keyboard_of_domains(com.chat.id, is_ender=True)
    )


@bot.message_handler(commands=['del_all_domains'])
def com_del_all_domains(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'del_all_domains'

    send_msg(
        com.chat.id,
        "Вы уверены, что хотите удалить все сохранённые домены?",
        keyboard=get_keyboard_yes_or_no()
    )


def rlzn_del_all_domains(user_id: int, is_confirm: bool):
    clean_buf_of_coms(user_id)
    if is_confirm:
        sql.execute("BEGIN;")
        sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id};")
        sql.execute("COMMIT;")

        send_msg(user_id, "Все домены удалены.", keyboard=types.ReplyKeyboardRemove())
    else:
        send_msg(user_id, "Домены остались без изменений.", keyboard=types.ReplyKeyboardRemove())


@bot.message_handler(commands=['help'])
def com_help(com: Message):
    rlzn_help(com.chat.id)


def rlzn_help(user_id: int):
    send_msg(
        user_id,
        """
Список команд:
• /add - добавить список доменов или ссылок
• /see - увидеть посты сохранённых групп
• /see_one - увидеть посты одной группы 
• /see_few - увидеть посты несольких групп
• /see_few_in_amount - увидеть несколько постов в опредёленном количестве
• /show - показать сохранённые домены
• /del - удалить несколько доменов
• /del_all_domains - удалить все сохранённые домены
• /set_info - узнать текущие настройки 
• /set_size - установить количество выводимых символов
• /set_amount - установить количество выводимых публикаций
• /delete_user - сбросить домены и настройки
        """
    )


@bot.message_handler(commands=['start'])
def com_start(com: Message):
    # запрос на добавление
    to_start(com.chat.id)

    send_msg(com.chat.id, "________________________________________________________")
    rlzn_help(com.chat.id)


def to_start(user_id):
    sql.execute("BEGIN;")
    sql.execute(
        f"INSERT OR IGNORE INTO usersT (user_id, amount, size) VALUES ({user_id}, {DFT_AMOUNT}, {DFT_SIZE});"
    )
    sql.execute("COMMIT;")


def clean_buf_of_coms(user_id):
    try:
        dict_buf_coms.pop(user_id)
    except KeyError:
        pass


@bot.message_handler(commands=['see_one'])
def com_see_one(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'see_one'

    send_msg(
        com.chat.id,
        "Домены групп для просмотра постов появились на панели клавиатуры, нажмите на домен, чтобы посмотреть посты.",
        keyboard=get_keyboard_of_domains(com.chat.id, is_ender=False)
    )


def rlzn_see_one(user_id: int, definite_domain: str):
    rlzn_see(user_id, definite_domain)


@bot.message_handler(commands=['see_few'])
def com_see_few(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'see_few'

    send_msg(
        com.chat.id,
        "Домены групп для просмотра постов появились на панели клавиатуры, нажмите на домен, чтобы посмотреть.",
        keyboard=get_keyboard_of_domains(com.chat.id, is_ender=True)
    )


def input_arg_see_few(user_id, definite_domain):
    global dict_buf_coms
    dict_buf_coms[user_id] += definite_domain + ' '
    # send_msg(
    #     user_id,
    #     "Продолжите выбирать домены или нажмите кнопку «Конец»."
    # )


def rlzn_see_few(user_id: int, definite_domains: str):
    rlzn_see(user_id, definite_domains)


@bot.message_handler(commands=['see_few_in_amount'])
def com_see_few_in_amount(com: Message):
    global dict_buf_coms
    dict_buf_coms[com.chat.id] = 'see_few_in_amount'

    send_msg(
        com.chat.id,
        "Домены групп для просмотра постов появились на панели клавиатуры, нажмите на домен, чтобы посмотреть.",
        keyboard=get_keyboard_of_domains(com.chat.id, is_ender=False)
    )


def input_arg_see_few_in_amount(user_id, definite_domain):
    global dict_buf_coms
    dict_buf_coms[user_id] += definite_domain + ' '
    # send_msg(
    #     user_id,
    #     "Продолжите выбирать домены или введите число публикаций."
    # )


def rlzn_see_few_in_amount(user_id: int, definite_domain: str, amount: str = None):
    rlzn_see(user_id, definite_domain, amount)


@bot.message_handler(commands=['see'])
def com_see(com: Message):
    rlzn_see(com.chat.id)


def rlzn_see(user_id: int, definite_domain: str = None, amount: str = None):
    clean_buf_of_coms(user_id)

    # получаем настройки
    settings_of_user = list(sql.execute(f"SELECT amount, size FROM usersT WHERE user_id={user_id} LIMIT 1;").fetchone())
    if amount is not None and amount.isdigit():
        settings_of_user[0] = amount

    # получаем список доменов сообществ
    if definite_domain is None:
        domains = get_user_domains(user_id)
    elif definite_domain.isspace():
        send_msg(user_id, "В результате запроса ничего не выведено.")
        return
    else:
        domains = set(definite_domain.split())

    print(domains)
    send_msg(user_id, "Посты групп по вашему запросу:", keyboard=types.ReplyKeyboardRemove())
    for domain in domains:
        send_repost(user_id, domain, settings_of_user)


def send_repost(user_id, domain, settings_of_user):
    # функция для отправки текста публикации
    amount = settings_of_user[0]
    size = settings_of_user[1]

    # получаем объект из которых получим публикации
    try:
        items = app.wall.get(domain=domain, count=amount)['items']
    except vk_api.exceptions.ApiError:
        send_msg(user_id, f"Не удалось получить публикации группы по домену: {domain}.")
        return
    # ссылка на сообщество
    msg_text = app.groups.getById(group_id=domain)[0][
                   'name'] + '\n' + domain + f" - {'https://vk.com/' + domain}" + '\n\n'
    for item in items:
        # создание текста из ссылки и текста поста
        msg_text += '──────────────────\n' + f"https://vk.com/wall{item['owner_id']}_{item['id']}" + '\n' \
                    + parse_text_of_post(item['text'], size) + '\n\n'

    # разделить большой текст на несколько сообщений
    if len(msg_text) > 4095:
        for x in range(0, len(msg_text), 4095):
            send_msg(user_id, msg_text[x:x + 4095])
    else:
        send_msg(user_id, msg_text)


@bot.message_handler()
def handler_arg_of_com(arg: Message):
    user_id = arg.chat.id
    arg = arg.text
    com = dict_buf_coms.get(user_id)

    if com is None:
        send_msg(
            user_id,
            "Команда нераспознана. Воспользуйтесь /help, чтобы увидеть доступные команды."
        )
        return

    com_sep_val = com.find('|')
    if com_sep_val == -1:
        com_sep_val = len(com)

    print(dict_buf_coms, com[:com_sep_val])
    match com[:com_sep_val]:
        case 'del':
            if arg == "Конец":
                rlzn_del(user_id, com[(com_sep_val + 1):])
            else:
                input_arg_del(user_id, arg)
        case 'del_all_domains':
            if arg == "Да":
                rlzn_del_all_domains(user_id, True)
            elif arg == "Нет":
                rlzn_del_all_domains(user_id, False)
            else:
                send_msg(
                    user_id,
                    "Вы не дали конкретного ответа.",
                    keyboard=get_keyboard_yes_or_no()
                )
        case 'delete_user':
            if arg == "Да":
                rlzn_delete_user(user_id, True)
            elif arg == "Нет":
                rlzn_delete_user(user_id, False)
            else:
                send_msg(
                    user_id,
                    "Вы не дали конкретного ответа.",
                    keyboard=get_keyboard_yes_or_no()
                )
        case 'add':
            rlzn_add(user_id, arg)
        case 'see_one':
            rlzn_see_one(user_id, arg)
        case 'see_few_in_amount':
            if arg.isdigit():
                rlzn_see_few_in_amount(user_id, com[(com_sep_val + 1):], arg)
            else:
                input_arg_see_few_in_amount(user_id, arg)
        case 'see_few':
            if arg == "Конец":
                rlzn_see_few(user_id, com[(com_sep_val + 1):])
            else:
                input_arg_see_few(user_id, arg)
        case 'set_size':
            rlzn_set_size(user_id, arg)
        case 'set_amount':
            rlzn_set_amount(user_id, arg)


if __name__ == '__main__':
    try:
        bot.polling(none_stop=True)
    finally:
        print("bye, bye.")
        bot.close()
        sql.close()
        db.close()

# Давай сделай меня хостом: https://beget.com/ru/hosting/free
