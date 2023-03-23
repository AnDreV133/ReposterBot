import threading
import vk_api
from vk_api.keyboard import VkKeyboard
from vk_api.longpoll import VkLongPoll, VkEventType

# while True # чел с этуба сказал, что в цикл надо завернуть,
             # чтобы бот не лёг, когда лягут сервера
session = vk_api.VkApi(
    token="vk1.a.hqK9U9K4SrHjy2HmLvTMiT0ngKhc6qaI-fy4pIBi0zKTbR6Jv_bT5zTy2XxPC3sR6CVBy27Q22rJs7q1L7YYG6iOcYINxPf1H_JeyRMvJxRyNfLbOcvwM2ttvdeLu5lIitHEi6xxi10qHBUvXPnuDwB3N4-9QWXcQshSXGlUd2O7eoTJDHoT8nd2EH_QlbT5n1OTwzDQgI50aRbTgg87CA"
)
session_api = session.get_api()
longpoll = VkLongPoll(session)


def send_msg(user_id, msg, keyboard=None):
    # функция для отправки сообщения, клавиатура крепится вместе с сообщением,
    # так как отправка сообщения это запрос на сервер
    post = {
        "user_id": user_id,
        "message": msg,
        "random_id": 0
    }

    if keyboard is not None:
        post["keyboard"] = keyboard

    session.method("messages.send", post)

# пока редуцент авось пригодится
# def show_keyboard_welcome():
#     kb = VkKeyboard
#     kb.get_empty_keyboard()
#     kb.add_button("Hello")
#     kb.get_keyboard()

def get_keyboard():
    # клавиатура для вставки/удаления ссылок и настроек
    kb = VkKeyboard(one_time=True)
    kb.add_button("Add link/s")
    kb.add_line()
    kb.add_button("Del link/s")
    kb.add_button("Settings")

    return kb.get_keyboard()

# для настроек тоже нужна клавиатура, там будет обязательно настройка времени

def create_file_for_links(user_id, links):
    links.replace(",", " ").replace(";", " ").replace(".", " ").split()

    # так как полноценных баз данных я делать не хочу, будет учёт пользователей через файлы

    # - проверка ссылок
    # - запись ссылок в файл, где имеются ID пользователя и настройка
    # - возвращает список из ссылок с подписью найдена ссылка или нет

    return []


def add_link(user_id):
    # потоковая функция принимает список ссылок
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.user_id == user_id:
                #
                text_ = create_file_for_links(0, "") # тут будет текст сообщения с
                                                     # прошедшими и непрошедшими ссылками
                send_msg(user_id, f"результаты:\n {text_}", keyboard=get_keyboard())

def test():
    create_file_for_links(1, "https://vk.com/so_ieitus https://vk.com/gvozdibelgorod")

if __name__ == '__main__':
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            text = event.text
            user_id = event.user_id
            if text == "start":
                send_msg(user_id, "вот пульт управления", get_keyboard())
            elif text == "Add link/s":
                threading.Thread(target=add_link, args=event.obj.from_id).start()
            elif text == "Del link/s":
                pass
            elif text == "Settings":
                pass

# питон как красивая речка, только в этой речке битые стёкла, неразорвавшиеся снаряды и просто мины плавают.
# в коде повторяются названия переменных, на что жалуется IDE, с этим надо быть аккуратнее