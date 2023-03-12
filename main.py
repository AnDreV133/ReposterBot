import threading
from libs.vk_api import vk_api
from libs.vk_api.keyboard import VkKeyboard
from libs.vk_api.longpoll import VkLongPoll, VkEventType

# while True
session = vk_api.VkApi(
    token="vk1.a.hqK9U9K4SrHjy2HmLvTMiT0ngKhc6qaI-fy4pIBi0zKTbR6Jv_bT5zTy2XxPC3sR6CVBy27Q22rJs7q1L7YYG6iOcYINxPf1H_JeyRMvJxRyNfLbOcvwM2ttvdeLu5lIitHEi6xxi10qHBUvXPnuDwB3N4-9QWXcQshSXGlUd2O7eoTJDHoT8nd2EH_QlbT5n1OTwzDQgI50aRbTgg87CA"
)
session_api = session.get_api()
longpoll = VkLongPoll(session)


def send_msg(user_id, msg, keyboard=None):
    post = {
        "user_id": user_id,
        "message": msg,
        "random_id": 0
    }

    if keyboard is not None:
        post["keyboard"] = keyboard

    session.method("messages.send", post)


# def show_keyboard_welcome():
#     kb = VkKeyboard
#     kb.get_empty_keyboard()
#     kb.add_button("Hello")
#     kb.get_keyboard()

def get_keyboard():
    kb = VkKeyboard(one_time=True)
    kb.add_button("Add link/s")
    kb.add_line()
    kb.add_button("Del link/s")
    kb.add_button("Settings")

    return kb.get_keyboard()


def create_file_for_links(user_id, links):
    # проверка ссылки
    # запись

    links.replace(",", " ").replace(";", " ").replace(".", " ").split()



    return []


def add_link(user_id):
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            if event.user_id == user_id:
                #

                send_msg(user_id, f"результаты:\n {text}", keyboard=get_keyboard())


# хорошее отображение прошедших ссылок

if __name__ == '__main__':
    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:
            text = event.text
            user_id = event.user_id
            if text == "start":
                send_msg(user_id, "добавьте ссылочки", get_keyboard())
            elif text == "Add link/s":
                threading.Thread(target=add_link, args=event.obj.from_id).start()
            elif text == "Del link/s":
                pass
            elif text == "Settings":
                pass
