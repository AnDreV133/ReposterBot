import os
import vk_api
import sqlite3
from dotenv import load_dotenv
from vk_api.longpoll import VkLongPoll, VkEventType

DEFAULT_HOURS = 5

load_dotenv()
session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
longpoll = VkLongPoll(session)

db = sqlite3.connect("users.db")
sql = db.cursor()


def send_msg(user_id, msg):
    # функция для отправки сообщения пользователю
    post = {
        "peer_id": user_id,
        "message": msg,
        "random_id": 0
    }

    session.method("messages.send", post)


def create_new_file(user_id, frequency_per_days,
                    time_of_repost, mode_of_amount_reposts):
    # ready but it can add
    with open(f"configs_of_users/{user_id}.txt", "w") as file:
        file.write(f"""
                    frequency {frequency_per_days}|
                    time {time_of_repost}|
                    mode {mode_of_amount_reposts}|
                    """)


def test():
    pass


def add_links_sql_execute(user_id, list_of_links):
    if not sql.execute(f"select * from main.usersT where user_id={user_id};").fetchone():
        sql.execute(f"insert into main.usersT (user_id, range_in_hours) values ({user_id}, {DEFAULT_HOURS});")

    for link in list_of_links:
        sql.execute(f"insert into main.linksT (links_id, link) values ({user_id}, {link});")


def del_links_sql_execute(user_id, list_of_links_for_del):
    for link in list_of_links_for_del:
        sql.execute(f"delete from main.linksT where links_id={user_id}, link={link};")


def repost_by_links(user_id, hours=None):



def clean_history(user_id):
    sql.execute(f"delete from main.usersT where user_id={user_id}")


def set_hours(user_id, hours):
    sql.execute(f"update main.usersT set range_in_hours={hours} where user_id={user_id};")


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # получаем текст сообщения
            temp = event.text.split()
            command = temp[0]
            list_arg = temp[1:] if temp[1:] else [""]
            # получаем ID написавшего
            user_id = event.user_id
            # обрабатываем сообщение
            match command:
                case "/start", "/help":
                    send_msg(user_id, "<описание команд>")
                case "/see":
                    if not list_arg[0]:
                        repost_by_links(user_id)
                    elif list_arg[0].isdigit():
                        repost_by_links(user_id, int(list_arg[0]))
                    else:
                        send_msg(user_id, "<ошибка>")
                case "/add":
                    if list_arg[0]:
                        add_links_sql_execute(user_id, list_arg)
                    else:
                        send_msg(user_id, "<ошибка>")
                case "/del":
                    if list_arg[0]:
                        del_links_sql_execute(user_id, list_arg)
                    else:
                        send_msg(user_id, "<ошибка>")
                case "/set":
                    if list_arg[0] != "hours" and list_arg[1].isdigit():
                        set_hours(user_id, int(list_arg[1]))
                    else:
                        send_msg(user_id, "<ошибка>")
                    # ...


if __name__ == '__main__':
    main()
# питон как красивая речка, только в этой речке битые стёкла, неразорвавшиеся снаряды и просто мины плавают.
# в коде повторяются названия переменных, на что жалуется IDE, с этим надо быть аккуратнее
