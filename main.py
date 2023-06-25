import os

import telebot
import vk_api
import sqlite3
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, Message

DFT_amount = 2
DFT_SIZE = 200
RANGE_OF_DOMAINS = 50
user_id = 0

help_command = "Команда имеет вид:\n"
help_see = "/see\n/see size <значение>\n/see amount <значение>\n"
help_set = "/set size <значение настройки>\n/set amount <значение настройки>\n/set show\n"
help_show = "/show\n"
help_add = "/add <домен/ссылка> ...\n"
help_del = "/del\n/del <домен/ссылка> ...\n"

load_dotenv()

# session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
# longpoll = VkLongPoll(session)
# vk = session.get_api()
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
      user_id UNSIGNED BIG INT NOT NULL,
      amount UNSIGNED BIG INT,
      size UNSIGNED BIG INT
    );
    """
)

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
            res_text += (c if c != '\n' else ' ')
            size -= 1

    return res_text + "..."


def get_user_domains():
    return list(map(lambda x: x[0], sql.execute(f"SELECT domain FROM domainsT WHERE user_id={user_id};").fetchall()))


def is_user_have_domain():
    return True if sql.execute(f"SELECT domain FROM domainsT WHERE user_id={user_id} LIMIT 1;").fetchone() else False


def get_domain_from_domain(domain):
    return domain[domain.rfind('/') + 1:]


def add_path(domain):
    return "https://vk.com/" + domain


def handle_error(err_msg, execute, log_msg):
    send_msg(err_msg)
    sql.execute(execute)
    print(log_msg)


def get_keyboard_by_groups_with_command(command):
    kb = ReplyKeyboardMarkup(one_time_keyboard=True)
    domains_list = get_user_domains()
    length = len(domains_list) if len(domains_list) < RANGE_OF_DOMAINS else RANGE_OF_DOMAINS
    for i in range(length):
        kb.add(command + " " + domains_list[i])

    return kb


def send_msg(msg, keyboard=None):
    # функция для отправки сообщения пользователю
    bot.send_message(user_id, msg, reply_markup=keyboard)


def send_repost(domain, settings_of_user):
    # функция для отправки текста публикации
    amount = settings_of_user[0]
    size = settings_of_user[1]

    # получаем объект из которых получим публикации
    try:
        items = app.wall.get(domain=domain, count=amount)['items']
    except vk_api.exceptions.ApiError:
        send_msg(f"Не удалось получить публикации группы по домену: {domain}.")
        return

    # ссылка на сообщество
    msg_text = app.groups.getById(group_id=domain)[0][
                   'name'] + '\n' + domain + f" - {'https://' + domain}" + "\n\n----\n\n"
    for item in items:
        # создание текста из ссылки и текста поста
        msg_text += f"https://wall{item['owner_id']}_{item['id']}" + '\n' \
                    + parse_text_of_post(item['text'], size)
    msg_text += "----"

    send_msg(msg_text)


def add_domains_sql_execute(list_of_domains):
    if not sql.execute(f"SELECT * FROM usersT WHERE user_id={user_id};").fetchone():
        sql.execute("BEGIN;")
        sql.execute(
            f"INSERT INTO usersT (user_id, amount, size) VALUES ({user_id}, {DFT_amount}, {DFT_SIZE});"
        )
        sql.execute("COMMIT;")

    sql.execute("BEGIN;")
    counter_of_new_domains = 0
    cur_amount_domains = len(get_user_domains())
    list_of_domains = set(list_of_domains)
    text_msg = "Результаты добавления групп:\n"
    for domain in list_of_domains:
        domain = get_domain_from_domain(domain)
        try:
            app.groups.getById(group_id=domain)  # проверка; домен - это группа или что-то другое
            if cur_amount_domains + counter_of_new_domains < RANGE_OF_DOMAINS:
                text_msg += f"• {domain} - добавлено\n"
                sql.execute(f"INSERT OR IGNORE INTO domainsT (user_id, domain) VALUES ({user_id}, '{domain}');")
            else:
                break

            counter_of_new_domains += 1
        except vk_api.exceptions.ApiError:
            text_msg += f"• {domain} - ненайдено или не является группой\n"
    sql.execute("COMMIT;")

    send_msg(text_msg)

    print(sql.execute("SELECT * FROM usersT").fetchall())
    print(sql.execute("SELECT * FROM domainsT").fetchall())


def del_domains_sql_execute(list_of_domains_for_del):
    if list_of_domains_for_del[0] == '':
        send_msg(
            "Домены групп для удаления появились на панели клавиатуры, нажмите на домен, чтобы удалить:",
            keyboard=get_keyboard_by_groups_with_command("/del")
        )
    else:
        text_msg = "Вы удалили:\n"
        sql.execute("BEGIN;")
        for domain in list_of_domains_for_del:
            sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id} AND domain='{get_domain_from_domain(domain)}';")
            text_msg += f"• {domain}\n"
        sql.execute("COMMIT;")

        send_msg(text_msg)


# @bot.message_handler(commands=["/see"])
def repost_by_domains(mod=None):
    # получаем настройки
    try:
        settings_of_user = list(sql.execute(f"SELECT amount, size FROM usersT WHERE user_id={user_id};").fetchone())
    except TypeError:
        show_tracked_domains()
        return

    if mod == "amount":
        settings_of_user[0] = mod
    elif mod == "size":
        settings_of_user[1] = mod

    # получаем список доменов сообществ
    domains = get_user_domains()

    print(domains)
    for domain in domains:
        send_repost(domain, settings_of_user)


def clean_history():
    sql.execute("BEGIN;")
    sql.execute(f"DELETE FROM usersT WHERE user_id={user_id} LIMIT 1")
    sql.execute("COMMIT;")


def set_amount(amount: int):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET amount={amount} WHERE user_id={user_id};")
    sql.execute("COMMIT;")

    send_msg(f"Количество отображаемых постов: {amount}.")


def set_size(size: int):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET size={size} WHERE user_id={user_id};")
    sql.execute("COMMIT;")

    send_msg(f"Количество отображаемых сиволов: {size}.")


def show_settings():
    sql.execute("BEGIN;")
    settings_of_user = sql.execute(f"SELECT amount, size FROM usersT WHERE user_id={user_id};").fetchone()
    sql.execute("COMMIT;")

    msg_text = f"""
    Текущие настройки:
    • кол-во отображаемых постов: {settings_of_user[0]}
    • кол-во отображаемых символов: {settings_of_user[1]}
    """
    send_msg(msg_text)


def show_tracked_domains():
    list_of_domains = get_user_domains()
    if list_of_domains:
        text_msg = "Ваши отслеживаемые группы:\n\n"
        for domain in list_of_domains:
            text_msg += f"• {'https://' + domain} - {domain} - {app.groups.getById(group_id=domain)[0]['name']}\n"
    else:
        text_msg = "Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add"

    send_msg(text_msg)


def del_all_domains_sql_execute():
    sql.execute("BEGIN;")
    sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id};")
    sql.execute("COMMIT;")

    send_msg("Все группы удалены.")


def to_help_info():
    send_msg("Список команд:\n"
             + help_add
             + help_show
             + help_see
             + help_set
             + help_del)


def to_start():
    send_msg("________________________________________________________")
    to_help_info()


@bot.message_handler()
def main(message: Message):
    # получаем текст сообщения
    temp = message.text.split()
    command = temp[0]
    list_arg = temp[1:] if temp[1:] else [""]
    print("command:", command, "| list of arguments:", list_arg)

    # получаем ID написавшего
    global user_id
    user_id = message.chat.id
    print("user ID:", user_id)

    # обрабатываем сообщение
    match command:
        case "/see":
            if not list_arg[0]:
                repost_by_domains()
            elif list_arg[1].isdigit() and len(list_arg) == 2:
                repost_by_domains(mod=list_arg[1])
            elif list_arg[0] == "one" and len(list_arg) == 1:
                send_msg(
                    "Домены групп для просмотра постов появились на панели клавиатуры, нажмите на домен, чтобы посмотреть.",
                    keyboard=get_keyboard_by_groups_with_command("/see"))
            elif not get_user_domains():
                send_msg("Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add.")
            else:
                send_msg("Ошибка введения постфикса. " + help_command + help_see)
        case "/show":
            if not list_arg[0]:
                show_tracked_domains()
            else:
                send_msg("Присутствуют лишние аргументы. " + help_command + help_show)
        case "/add":
            if list_arg[0]:
                add_domains_sql_execute(list_arg)
            else:
                send_msg("Вы ничего не ввели. " + help_command + help_add)
        case "/del":
            if is_user_have_domain() and list_arg[0] == "/all":
                del_all_domains_sql_execute()
            elif is_user_have_domain():  # ----------------------------------------------------------------------------------------
                del_domains_sql_execute(list_arg)
            else:
                send_msg("Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add.")
        case "/set":
            if list_arg[0] == "amount" and list_arg[1].isdigit():
                set_amount(int(list_arg[1]))
            elif list_arg[0] == "size" and list_arg[1].isdigit():
                set_size(int(list_arg[1]))
            elif list_arg[0] == "show":
                show_settings()
            else:
                send_msg("Ошибка считывания команды. " + help_command + help_set)
            # ...
        case "/delete_self":
            clean_history()
        case "/start":
            to_start()
        case "/help":
            to_help_info()
        case "/info":
            to_help_info()


if __name__ == '__main__':
    # while (True):
    #     try:
    bot.polling(none_stop=True)
# except:
#     print("\n----------------exception--------------\n")

# Давай сделай меня хостом: https://beget.com/ru/hosting/free
