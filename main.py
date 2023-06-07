import os
import random

import vk_api
import sqlite3
from dotenv import load_dotenv
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType

DFT_NUM_OF_POSTS = 2
DFT_SIZE = 200
RANGE_OF_DOMAINS = 20
user_id = 0

load_dotenv()

session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
longpoll = VkLongPoll(session)
vk = session.get_api()
app = vk_api.VkApi(token=os.getenv("VK_APP_TOKEN")).get_api()

db = sqlite3.connect("mainDB.db")
sql = db.cursor()

sql.execute("BEGIN;")
# user_id | num_of_posts | size
# table of users with personal settings
sql.execute(
    """
    CREATE TABLE IF NOT EXISTS usersT ( 
      user_id UNSIGNED BIG INT PRIMARY KEY NOT NULL,
      num_of_posts UNSIGNED BIG INT,
      size INT
    );
    """
)

# user_id | link
# table stores links for user
sql.execute(
    """
    CREATE TABLE IF NOT EXISTS linksT (
      user_id UNSIGNED BIG INT NOT NULL,
      link VARCHAR(50),
      
      FOREIGN KEY (user_id) REFERENCES usersT(user_id) ON DELETE CASCADE 
    );
    """
)

# fields of links becomes unique for each user
sql.execute("DROP INDEX IF EXISTS idx_links;")
sql.execute("CREATE UNIQUE INDEX idx_links ON linksT (link);")
sql.execute("COMMIT;")

print(sql.execute("SELECT * FROM usersT").fetchall())
print(sql.execute("SELECT * FROM linksT").fetchall())


def test():
    pass


def get_user_domains():
    return list(map(lambda x: x[0], sql.execute(f"SELECT link FROM linksT WHERE user_id={user_id};").fetchall()))


def get_domain_from_link(link):
    return link[link.rfind('/') + 1:]


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


def send_repost(link, settings_of_user):
    # функция для отправки текста публикации
    num_of_posts = settings_of_user[1]
    size = settings_of_user[2]

    items = app.wall.get(domain=link, count=num_of_posts)['items']
    msg_text = app.groups.getById(group_id=link)[0][
                   'name'] + '\n' + link + f" - {add_path(link)}" + "\n\n----\n\n"
    for item in items:
        link_to_post = add_path(f"wall{item['owner_id']}_{item['id']}") + '\n'
        text_of_post = item['text'][:size].replace('\n', ' ') + "...\n\n"
        msg_text += link_to_post + text_of_post
    msg_text += "----"

    send_msg(msg_text)


def add_links_sql_execute(list_of_links):
    if not sql.execute(f"SELECT * FROM usersT WHERE user_id={user_id};").fetchone():
        sql.execute("BEGIN;")
        sql.execute(
            f"INSERT INTO usersT (user_id, num_of_posts, size) VALUES ({user_id}, {DFT_NUM_OF_POSTS}, {DFT_SIZE});"
        )
        sql.execute("COMMIT;")

    sql.execute("BEGIN;")
    counter_of_new_domains = 0
    cur_amount_domains = len(get_user_domains())
    for link in list_of_links:
        link = get_domain_from_link(link)
        try:
            app.groups.getById(group_id=link)  # проверка домен группы или чего-то иного
            if cur_amount_domains + counter_of_new_domains < RANGE_OF_DOMAINS:
                sql.execute(f"INSERT OR IGNORE INTO linksT (user_id, link) VALUES ({user_id}, '{link}');")
            else:
                break

            counter_of_new_domains += 1
        except vk_api.exceptions.ApiError:
            pass
    sql.execute("COMMIT;")

    print(sql.execute("SELECT * FROM usersT").fetchall())
    print(sql.execute("SELECT * FROM linksT").fetchall())


def del_links_sql_execute(list_of_links_for_del):
    if not len(get_user_domains()):
        send_msg("Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add")
        return

    if list_of_links_for_del:
        sql.execute("BEGIN;")
        for link in list_of_links_for_del:
            sql.execute(f"DELETE FROM linksT WHERE user_id={user_id} AND link='{get_domain_from_link(link)}';")
        sql.execute("COMMIT;")
    else:
        keyboard_for_delete_domains()


def repost_by_links(size=None, num_of_posts=None):
    # get settings
    settings_of_user = sql.execute(f"SELECT * FROM usersT WHERE user_id={user_id};").fetchone()

    if size:
        settings_of_user[1] = size
    if num_of_posts:
        settings_of_user[2] = num_of_posts

    # получаем список ссылок сообществ
    links = get_user_domains()

    print(links)
    for link in links:
        send_repost(link, settings_of_user)


def clean_history():
    sql.execute("BEGIN;")
    sql.execute(f"DELETE FROM usersT WHERE user_id={user_id} LIMIT 1")
    sql.execute("COMMIT;")


def set_num_of_posts(num_of_posts):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET num_of_posts={num_of_posts} WHERE user_id={user_id} LIMIT 1;")
    sql.execute("COMMIT;")


def set_size_text_of_posts(num_of_posts):
    sql.execute("BEGIN;")
    sql.execute(f"UPDATE usersT SET size={num_of_posts} WHERE user_id={user_id} LIMIT 1;")
    sql.execute("COMMIT;")


def show_tracked_domains():
    list_of_domains = get_user_domains()
    if list_of_domains:
        text_msg = "Ваши отслеживаемые группы:\n\n"
        for domain in list_of_domains:
            text_msg += f"• {add_path(domain)} - {domain} - {app.groups.getById(group_id=domain)[0]['name']}\n"
    else:
        text_msg = "Вы ещё не добавили сообщества. Сделайте это с помощью команды: /add"

    send_msg(text_msg)


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
                        repost_by_links()
                    elif list_arg[0] == "size" and list_arg[1].isdigit():
                        repost_by_links(size=list_arg[1])
                    elif list_arg[0] == "amount" and list_arg[1].isdigit():
                        repost_by_links(num_of_posts=list_arg[1])
                    else:
                        send_msg("""
                        Ошибка введения постфикса. Команда имеет вид:
                        /see
                        /see size <значение> 
                        /see amount <значение>
                        """)
                case "/show":
                    show_tracked_domains()
                case "/add":
                    if list_arg[0]:
                        add_links_sql_execute(list_arg)
                    else:
                        send_msg("""
                        Вы ничего не ввели. Команда имеет вид:
                        /add <домен или ссылка на сообщество> 
                        """)
                case "/del":
                    del_links_sql_execute(list_arg)

                case "/set":
                    if list_arg[0] == "amount" and list_arg[1].isdigit():
                        set_num_of_posts(int(list_arg[1]))
                    if list_arg[0] == "size" and list_arg[1].isdigit():
                        set_size_text_of_posts(int(list_arg[1]))
                    else:
                        send_msg("""
                        Ошибка считывания команды. Команда имеет вид:
                        /set size <значение настройки>
                        /set amount <значение настройки>
                        """)
                    # ...
                case "/delete_self":
                    clean_history()


if __name__ == '__main__':
    main()

# питон? как красивая речка, дно которой усеяно битыми стёклами, неразорвавшимися снарядами и просто плавающими минами.
