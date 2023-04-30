import os
import vk_api
import sqlite3
from dotenv import load_dotenv
from vk_api.longpoll import VkLongPoll, VkEventType

DEFAULT_NUM_OF_POSTS = 2
DEFAULT_SIZE = 200

load_dotenv()

session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
longpoll = VkLongPoll(session)
vk = session.get_api()
app = vk_api.VkApi(token=os.getenv("VK_APP_TOKEN")).get_api()

db = sqlite3.connect("mainDB.db")
sql = db.cursor()

sql.execute(
    """
    create table if not exists usersT (
      user_id unsigned big int primary key not null,
      num_of_posts unsigned big int,
      size int
    );
    """)
sql.execute(
    """
    create table if not exists linksT (
      links_id unsigned big int not null,
      link text,
      foreign key (links_id) references usersT(user_id) on delete cascade 
    );
    """
)

print(sql.execute("select * from usersT").fetchall())
print(sql.execute("select * from linksT").fetchall())


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


def send_msg(user_id, msg):
    # функция для отправки сообщения пользователю
    post = {
        "peer_id": user_id,
        "message": msg,
        "random_id": 0
    }

    session.method("messages.send", post)


def send_repost(user_id, link, settings_of_user):
    # функция для отправки текста публикации
    domain = link[link.rfind('/') + 1:]
    num_of_posts = settings_of_user[1]
    size = settings_of_user[2]
    items = app.wall.get(domain=domain, count=num_of_posts)['items']
    msg_text = app.groups.getById(group_id=domain)[0]['name'] + '\n' + link + "\n\n----\n"
    for item in items:
        link_to_post = f"https://vk.com/wall{item['owner_id']}_{item['id']}" + '\n'
        text_of_post = item['text'][:size].replace('\n', ' ') + "...\n\n"
        msg_text += link_to_post + text_of_post
    msg_text += "----"

    send_msg(user_id, msg_text)


def add_links_sql_execute(user_id, list_of_links):
    if not sql.execute(f"select * from usersT where user_id={user_id};").fetchone():
        sql.execute(f"insert into usersT (user_id, num_of_posts, size) values ({user_id}, {DEFAULT_NUM_OF_POSTS}, {DEFAULT_SIZE});")

    for link in list_of_links:
        sql.execute(f"insert into linksT (links_id, link) values ({user_id}, '{link}');")

    print(sql.execute("select * from usersT").fetchall())
    print(sql.execute("select * from linksT").fetchall())


def del_links_sql_execute(user_id, list_of_links_for_del):
    for link in list_of_links_for_del:
        sql.execute(f"delete from linksT where links_id={user_id} and link='{link}';")


def repost_by_links(user_id, size=None, num_of_posts=None):
    # определяем время за которое вышли посты
    settings_of_user = sql.execute(f"select * from usersT where user_id={user_id};").fetchone()

    if size:
        settings_of_user[1] = size
    if num_of_posts:
        settings_of_user[2] = num_of_posts

    # получаем список ссылок сообществ
    links = list(map(lambda x: x[0], sql.execute(f"select link from linksT where links_id={user_id};").fetchall()))

    print(links)
    for link in links:
        send_repost(user_id, link, settings_of_user)


def clean_history(user_id):
    sql.execute(f"delete from usersT where user_id={user_id}")


def set_num_of_posts(user_id, num_of_posts):
    sql.execute(f"update usersT set num_of_posts={num_of_posts} where user_id={user_id};")


def main():
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            # получаем текст сообщения
            temp = event.text.split()
            command = temp[0]
            list_arg = temp[1:] if temp[1:] else [""]
            print("command:", command, "| list of arguments:", list_arg)
            # получаем ID написавшего
            user_id = event.user_id
            print("user ID:", user_id)
            # обрабатываем сообщение
            match command:
                case "/start", "/help":
                    send_msg(user_id, "<описание команд>")
                case "/see":
                    if not list_arg[0]:
                        repost_by_links(user_id)
                    elif list_arg[0] == "size" and list_arg[1].isdigit():
                        repost_by_links(user_id, size=list_arg[1])
                    elif list_arg[0] == "amount" and list_arg[1].isdigit():
                        repost_by_links(user_id, num_of_posts=list_arg[1])
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
                    if list_arg[0] != "amount" and list_arg[1].isdigit():
                        set_num_of_posts(user_id, int(list_arg[1]))
                    else:
                        send_msg(user_id, "<ошибка>")
                    # ...


if __name__ == '__main__':
    main() # сделать сохранение в базу данных

# питон как красивая речка, только в этой речке битые стёкла, неразорвавшиеся снаряды и просто мины плавают.
# в коде повторяются названия переменных, на что жалуется IDE, с этим надо быть аккуратнее
