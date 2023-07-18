import vk_api
import time
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
from config import comunity_token, acces_token
from core import VkTools
from datetime import datetime
from data_store import DataStore
from config import file_db

class BotInterface():
    def __init__(self, comunity_token, acces_token):
        self.vk = vk_api.VkApi(token=comunity_token)
        self.longpoll = VkLongPoll(self.vk)
        self.vk_tools = VkTools(acces_token)
        self.params = {}
        self.users = []
        self.offset = 0
        self.age = 0
        self.city_id = None
        self.city_name = None
        self.db = DataStore(file_db)

    def message_send(self, user_id, message, keyboard=None, attachment=None):

        query = {
            'user_id': user_id,
            'message': message,
            'attachment': attachment,
            'random_id': get_random_id()
            }
        self.vk.method('messages.send', query)

    def event_handler(self):
        context = 'standart'
        last_writer = None
        age_pass = False
        city_id_pass = False
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                self.params = self.vk_tools.get_profile_info(event.user_id)
                current_time = datetime.now()
                print(f'{current_time} id{self.params.get("id")} {self.params.get("first_name")} {self.params.get("last_name")} {event.text}')
                command = event.text.lower().split()
                if context == 'standart':
                    if self.params['id'] != last_writer:
                        self.users.clear()
                        self.offset = 0
                        age_pass = False
                        city_id_pass = False
                        self.city_id = None
                        self.city_name = None
                    if 'привет' in command:
                        self.message_send(event.user_id, f'Здравствуйте, {self.params["first_name"]}!')
                        self.message_send(event.user_id, 'Чтобы искать людей, нажмите кнопку "Поиск"!', key_search)
                    elif 'поиск' in command:
                        if age_pass:
                            current_year = datetime.now().year
                            user_year = current_year - self.age
                            self.params.update({'bdate': '1.1.{}'.format(user_year)})
                        if city_id_pass:
                            self.params.update({'city_id': self.city_id})
                        if self.params['bdate'] is None or len(self.params['bdate'].split('.')) != 3:
                            self.message_send(event.user_id, f'{self.params["first_name"]}, Введите ваш возраст числом')
                            context = 'input_age'
                        elif self.params['city_id'] is None:
                            self.message_send(event.user_id, f'''{self.params["first_name"]}, Напишите название вашего города (только Россия) и через запятую регион для точности''')
                            context = 'input_city'
                        else:
                            self.message_send(event.user_id, 'Начинаю поиск...')
                            if len(self.users) == 0:
                                self.users = self.vk_tools.search_users(self.params, offset=self.offset)
                                if self.users == []:
                                    self.message_send(event.user_id, 'Кончились анкеты в текущем городе... Выберите другой!')
                                    context = 'input_city'
                                    self.offset = 0
                                    continue
                                self.offset += 10
                            if len(self.users) > 0:
                                user = self.users.pop()
                            
                            while self.db.check_data(user['id'], event.user_id) is not None: # ПРОВЕРКА В БД
                                if len(self.users) == 0:
                                    self.users = self.vk_tools.search_users(self.params, offset=self.offset)
                                    if self.users == []:
                                        break
                                    self.offset += 10
                                if len(self.users) > 0:
                                    user = self.users.pop()
                            photos_user = self.vk_tools.get_photos(user['id'])
                            attachment = ''
                            for num, photo in enumerate(photos_user):
                                attachment += f'photo{photo["owner_id"]}_{photo["id"]},'
                                if num == 2:
                                    break
                            self.message_send(event.user_id, f'Встречайте {user["first_name"]} @id{user["id"]}', attachment=attachment)
                            self.message_send(event.user_id, 'Для продолджения поиска нажмите кнопку "Поиск"!', key_search)
                            print(self.users)
                            print(user)
                            print(self.offset)
                            print(attachment)
                            
                            self.db.add_data(user['id'], event.user_id)

                        last_writer = self.params.get('id')
                    elif 'пока' in command:
                        self.message_send(event.user_id, f'До свидания, {self.params["first_name"]}!')
                    elif 'reset' in command:
                        self.message_send(event.user_id, 'Сброс параметров...')
                        self.users.clear()
                        self.offset = 0
                        self.age = 0
                        self.city_id = None
                        age_pass = False
                        city_id_pass = False
                        self.city_name = None
                        self.message_send(event.user_id, 'Нажмите кнопку "Поиск"!', key_search)
                    else:
                        self.message_send(event.user_id, 'Неизвестная команда!', key_search)
                elif context == 'input_age':
                    if event.text.isdigit():
                        age = int(event.text)
                        if age >= 10 and age <= 100:
                            self.age = age
                            self.message_send(event.user_id, 'Нажмите кнопку "Поиск"', key_search)
                            context = 'standart'
                            age_pass = True
                        else:
                            self.message_send(event.user_id, 'Напишите возраст от 18 до 100!')
                    else:
                        self.message_send(event.user_id, 'Неверные данные. Проверьте данные!')
                elif context == 'input_city':
                    input_city = event.text.split(',')
                    if len(input_city) == 2:
                        name_city = input_city[0].strip().lower()
                        name_reg = input_city[1].strip().lower()
                        self.city_id = self.vk_tools.get_city_id(name_city, name_reg)
                        if self.city_id is not None:
                            self.message_send(event.user_id, 'Для поиска нажмите кнопку "Поиск"', key_search)
                            print(self.city_id)
                            context = 'standart'
                            city_id_pass = True
                        else:
                            self.message_send(event.user_id, 'Ошибка в названии города или региона. Проверьте данные!')
                    elif len(input_city) == 1:
                        name_city = input_city[0].strip().lower()
                        self.city_id = self.vk_tools.get_city_id(name_city)
                        if self.city_id is not None and self.city_id > 0:
                            self.message_send(event.user_id, 'Для поиска нажмите кнопку "Поиск', key_search)
                            print(self.city_id)
                            context = 'standart'
                            city_id_pass = True
                        if self.city_id is not None and self.city_id == 0:
                            self.city_name = name_city
                            self.message_send(event.user_id, f'Найдено несколько вариантов по запросу "{name_city}". Укажите ваш регион!')
                            context = 'input_region'
                        if self.city_id is None:
                            self.message_send(event.user_id, 'Ошибка в названии города или региона.')
                    else:
                        self.message_send(event.user_id, 'Пишите название города и через запятую регион!')
                elif context == 'input_region':
                    input_region = event.text.strip().lower()
                    self.city_id = self.vk_tools.get_city_id(self.city_name, input_region)
                    if self.city_id is not None:
                        self.message_send(event.user_id, 'Для поиска нажмите кнопку "Поиск', key_search)
                        print(self.city_id)
                        context = 'standart'
                        city_id_pass = True
                    else:
                        self.message_send(event.user_id, 'Проверьте данные')


if __name__ == '__main__':
    while True:
        try:
            current_time = datetime.now()
            print(current_time)
            bot = BotInterface(comunity_token, acces_token)
            bot.event_handler()
        except Exception as e:
            time.sleep(5)
            print(e)
    