import os
import vk_api
import sqlite3
from dotenv import load_dotenv
from vk_api import utils
from vk_api.longpoll import VkLongPoll, VkEventType

DFT_NUM_OF_POSTS = 2
DFT_SIZE = 200

load_dotenv()

session = vk_api.VkApi(token=os.getenv("VK_GROUP_TOKEN"))
longpoll = VkLongPoll(session)
vk = session.get_api()
app = vk_api.VkApi(token=os.getenv("VK_APP_TOKEN")).get_api()

db = sqlite3.connect("mainDB.db")
sql = db.cursor()

sql.execute("begin;")
# user_id | num_of_posts | size
# table of users with personal settings
sql.execute(
    """
    create table if not exists usersT ( 
      user_id unsigned big int primary key not null,
      num_of_posts unsigned big int,
      size int
    );
    """)

# sql.execute("drop table linksT")

# user_id | link
# table stores links for user
sql.execute(
    """
    create table if not exists linksT (
      user_id unsigned big int not null,
      link varchar(50),
      
      foreign key (user_id) references usersT(user_id) on delete cascade 
    );
    """
)

# fields of links becomes unique for each user
sql.execute("DROP INDEX IF EXISTS idx_links;")
sql.execute("CREATE UNIQUE INDEX idx_links ON linksT (user_id, link);")

sql.execute("commit;")

print(sql.execute("select * from usersT").fetchall())
print(sql.execute("select * from linksT").fetchall())


def test():
    pass


def handle_error(user_id, err_msg, execute, log_msg):
    send_msg(user_id, err_msg)
    sql.execute(execute)
    print(log_msg)


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
    msg_text = app.groups.getById(group_id=domain)[0]['name'] + '\n' + link + "\n\n----\n\n"
    for item in items:
        link_to_post = f"https://vk.com/wall{item['owner_id']}_{item['id']}" + '\n'
        text_of_post = item['text'][:size].replace('\n', ' ') + "...\n\n"
        msg_text += link_to_post + text_of_post
    msg_text += "----"

    send_msg(user_id, msg_text)


def add_links_sql_execute(user_id, list_of_links):
    if not sql.execute(f"select * from usersT where user_id={user_id};").fetchone():
        sql.execute("begin;")
        sql.execute(
            f"insert into usersT (user_id, num_of_posts, size) values ({user_id}, {DFT_NUM_OF_POSTS}, {DFT_SIZE});"
        )
        sql.execute("commit;")

    sql.execute("begin;")
    for link in list_of_links:
        if app.groups.getById:
        sql.execute(f"insert or ignore into linksT (user_id, link) values ({user_id}, '{link}');")
    sql.execute("commit;")

    print(sql.execute("select * from usersT").fetchall())
    print(sql.execute("select * from linksT").fetchall())


def del_links_sql_execute(user_id, list_of_links_for_del):
    sql.execute("begin;")
    for link in list_of_links_for_del:
        sql.execute(f"delete from linksT where user_id={user_id} and link='{link}';")
    sql.execute("commit;")


def repost_by_links(user_id, size=None, num_of_posts=None):
    # get settings
    settings_of_user = sql.execute(f"select * from usersT where user_id={user_id};").fetchone()

    if size:
        settings_of_user[1] = size
    if num_of_posts:
        settings_of_user[2] = num_of_posts

    # получаем список ссылок сообществ
    links = list(map(lambda x: x[0], sql.execute(f"select link from linksT where user_id={user_id};").fetchall()))

    print(links)
    for link in links:
        send_repost(user_id, link, settings_of_user)


def clean_history(user_id):
    sql.execute("begin;")
    sql.execute(f"delete from usersT where user_id={user_id}")
    sql.execute("commit;")


def set_num_of_posts(user_id, num_of_posts):
    sql.execute("begin;")
    sql.execute(f"update usersT set num_of_posts={num_of_posts} where user_id={user_id};")
    sql.execute("commit;")


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
    main()

# питон? как красивая речка, дно которой усеяно битыми стёклами, неразорвавшимися снарядами и просто плавающими минами.
