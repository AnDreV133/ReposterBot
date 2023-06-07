import os
import random

import vk_api
import sqlite3
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType

DFT_amount = 2
DFT_SIZE = 200
RANGE_OF_DOMAINS = 20
user_id = 0

help_com_see = " Команда имеет вид:\n/see\n/see size <значение>\n/see amount <значение>"
help_com_set = " Команда имеет вид:\n/set size <значение настройки>\n/set amount <значение настройки>"
help_com_show = " Команда имеет вид:\n/show"
help_com_add = " Команда имеет вид:\n/add <домен/ссылка> ..."
help_com_del = " Команда имеет вид:\n/del\n/del <домен/ссылка> ..."

load_dotenv()

session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
longpoll = VkLongPoll(session)
vk = session.get_api()
app = vk_api.VkApi(token=os.getenv("VK_APP_TOKEN")).get_api()

db = sqlite3.connect("mainDB.db")
sql = db.cursor()

sql.execute("BEGIN;")
# sql.execute("drop table usersT")
# sql.execute("drop table linksT")
# user_id | amount | size
# table of users with personal settings
sql.execute(
    """
    CREATE TABLE IF NOT EXISTS usersT ( 
      user_id UNSIGNED BIG INT PRIMARY KEY NOT NULL,
      amount UNSIGNED BIG INT,
      size INT
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
      
      FOREIGN KEY (user_id) REFERENCES usersT(user_id) ON DELETE CASCADE 
    );
    """
)

# fields of domains becomes unique for each user
sql.execute("DROP INDEX IF EXISTS idx_domains;")
sql.execute("CREATE UNIQUE INDEX idx_domains ON domainsT (domain);")
sql.execute("COMMIT;")

print(sql.execute("SELECT * FROM usersT").fetchall())
print(sql.execute("SELECT * FROM domainsT").fetchall())


def test():
    pass


def get_user_domains():
    return list(map(lambda x: x[0], sql.execute(f"SELECT domain FROM domainsT WHERE user_id={user_id};").fetchall()))


def get_domain_from_domain(domain):
    return domain[domain.rfind('/') + 1:]


def add_path(domain):
    return "https://vk.com/" + domain


def handle_error(err_msg, execute, log_msg):
    send_msg(err_msg)
    sql.execute(execute)
    print(log_msg)


def keyboard_for_delete_domains():
    kb = VkKeyboard(one_time=True)
    domains_list = get_user_domains()
    length = len(domains_list)
    add_del_button = lambda x: kb.add_button("/del " + x)
    for i in range((length if length < RANGE_OF_DOMAINS else RANGE_OF_DOMAINS) // 2 - 2):
        add_del_button(domains_list[i])
        add_del_button(domains_list[i + 1])
        kb.add_line()

    if length >= 2:
        add_del_button(domains_list[length - 3])
        add_del_button(domains_list[length - 2])

    if length % 2 == 1:
        add_del_button(domains_list[length - 1])

    send_msg("Домены групп для удаления, нажмите, чтобы удалить:", keyboard=kb.get_keyboard())


def keyboard_for_see_posts_one_group():
    kb = VkKeyboard(one_time=True)
    domains_list = get_user_domains()
    length = len(domains_list)
    add_del_button = lambda x: kb.add_button("/see " + x)
    for i in range((length if length < RANGE_OF_DOMAINS else RANGE_OF_DOMAINS) // 2 - 2):
        add_del_button(domains_list[i])
        add_del_button(domains_list[i + 1])
        kb.add_line()

    if length >= 2:
        add_del_button(domains_list[length - 3])
        add_del_button(domains_list[length - 2])

    if length % 2 == 1:
        add_del_button(domains_list[length - 1])

    send_msg("Домены групп для просмотра постов, нажмите, чтобы посмотреть:", keyboard=kb.get_keyboard())


def send_msg(msg, keyboard=None):
    # функция для отправки сообщения пользователю
    min_rand_int = -9223372036854775807
    max_rand_int = 9223372036854775807
    post = {
        "peer_id": user_id,
        "message": msg,
        "keyboard": keyboard,
        "random_id": random.randint(min_rand_int, max_rand_int)
    }

    session.method("messages.send", post)


def send_repost(domain, settings_of_user):
    # функция для отправки текста публикации
    amount = settings_of_user[0]
    size = settings_of_user[1]

    items = app.wall.get(domain=domain, count=amount)['items']
    msg_text = app.groups.getById(group_id=domain)[0][
                   'name'] + '\n' + domain + f" - {add_path(domain)}" + "\n\n----\n\n"
    for item in items:
        domain_to_post = add_path(f"wall{item['owner_id']}_{item['id']}") + '\n'
        text_of_post = item['text'][:size].replace('\n', ' ') + "...\n\n"
        msg_text += domain_to_post + text_of_post
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
    if list_of_domains_for_del:
        sql.execute("BEGIN;")
        for domain in list_of_domains_for_del:
            sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id} AND domain='{get_domain_from_domain(domain)}';")
        sql.execute("COMMIT;")
    else:
        keyboard_for_delete_domains()


def repost_by_domains(size=None, amount=None):
    # get settings
    settings_of_user = list(sql.execute(f"SELECT amount, size FROM usersT WHERE user_id={user_id};").fetchone())

    if amount:
        settings_of_user[0] = amount
    if size:
        settings_of_user[1] = size

    # получаем список ссылок сообществ
    domains = get_user_domains()

    print(domains)
    for domain in domains:
        send_repost(domain, settings_of_user)


def clean_history():
    sql.execute("BEGIN;")
    sql.execute(f"DELETE FROM usersT WHERE user_id={user_id} LIMIT 1")
    sql.execute("COMMIT;")


def set_amount(amount):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET amount={amount} WHERE user_id={user_id} LIMIT 1;")
    sql.execute("COMMIT;")

    send_msg(f"Количество отображаемых постов: {amount}.")


def set_size(size):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET size={size} WHERE user_id={user_id} LIMIT 1;")
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
            text_msg += f"• {add_path(domain)} - {domain} - {app.groups.getById(group_id=domain)[0]['name']}\n"
    else:
        text_msg = "Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add"

    send_msg(text_msg)


def del_all_domains_sql_execute():
    sql.execute("BEGIN;")
    sql.execute(f"DELETE FROM domainsT WHERE user_id={user_id};")
    sql.execute("COMMIT;")

    send_msg("Все группы удалены.")


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # получаем текст сообщения
            temp = event.text.split()
            command = temp[0]
            list_arg = temp[1:] if temp[1:] else [""]
            print("command:", command, "| list of arguments:", list_arg)

            # получаем ID написавшего
            global user_id
            user_id = event.user_id
            print("user ID:", user_id)

            # обрабатываем сообщение
            match command:
                case "/start", "/help":
                    send_msg("<описание команд>")
                case "/see":
                    if not list_arg[0]:
                        repost_by_domains()
                    elif list_arg[0] == "size" and list_arg[1].isdigit() and len(list_arg) == 2:
                        repost_by_domains(size=list_arg[1])
                    elif list_arg[0] == "amount" and list_arg[1].isdigit() and len(list_arg) == 2:
                        repost_by_domains(amount=list_arg[1])
                    elif list_arg[0] == "one" and len(list_arg) == 1:
                        keyboard_for_see_posts_one_group()
                    elif not get_user_domains():
                        send_msg("Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add.")
                    else:
                        send_msg("Ошибка введения постфикса." + help_com_see)
                case "/show":
                    if not list_arg[0]:
                        show_tracked_domains()
                    else:
                        send_msg("Присутствуют лишние аргументы." + help_com_show)
                case "/add":
                    if list_arg[0]:
                        add_domains_sql_execute(list_arg)
                    else:
                        send_msg("Вы ничего не ввели." + help_com_add)
                case "/del":
                    if get_user_domains() and list_arg[0] == "/all":
                        del_all_domains_sql_execute()
                    elif get_user_domains():
                        del_domains_sql_execute(list_arg)
                    else:
                        send_msg("Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add.")
                case "/set":
                    if list_arg[0] == "amount" and list_arg[1].isdigit():
                        set_amount(int(list_arg[1]))
                    elif list_arg[0] == "size" and list_arg[1].isdigit():
                        set_size(int(list_arg[1]))
                    elif list_arg[0] == "/show":
                        show_settings()
                    else:
                        send_msg("Ошибка считывания команды." + help_com_set)
                    # ...
                case "/delete_self":
                    clean_history()


if __name__ == '__main__':
    while (True):
        try:
            main()
        except:
            pass

# питон? как красивая речка, дно которой усеяно битыми стёклами, неразорвавшимися снарядами и просто плавающими минами.
