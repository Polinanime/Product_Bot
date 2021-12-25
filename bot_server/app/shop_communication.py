# -*- coding: utf-8 -*-

import psycopg2
import requests
from app.models import *
from psycopg2.extras import DictCursor
from requests.auth import HTTPBasicAuth


class DeliveryBot:
    """
    Класс общается с API магазина, обрабатывает строки, рекомендации пользователей
    Если короче то отвечает за алгоритмы в проекте, связанные с заказом продуктов
    """

    def __init__(self, db_name, db_user, db_pass, db_host, http_auth: tuple, server_ip: str, server_port: str):
        self.conn_db = psycopg2.connect(dbname=db_name, user=db_user, password=db_pass, host=db_host)
        self.user_http = http_auth[0]
        self.pass_http = http_auth[1]
        self.basicAuthCredentials = HTTPBasicAuth(self.user_http, self.pass_http)
        self.server_ip = server_ip
        self.server_port = server_port
        self.http_url = f'http://{self.server_ip}:{self.server_port}'

    def request_by_category(self, category: str, user_id: int):
        """ Делает заказ, основываясь на выбранной категории и рекомендациях для данного пользователя """
        product_id = -1

        url = self.http_url + f'/search/product/category/{category}'
        all_data = requests.get(url, auth=self.basicAuthCredentials).json()

        ids = [i['id'] for i in all_data]
        with self.conn_db.cursor(cursor_factory=DictCursor) as cursor:
            sql_str = 'SELECT product_id FROM product_recommendations WHERE product_id IN %s ORDER BY (-1 *  purchases_number) LIMIT 1;'
            cursor.execute(sql_str, (tuple(ids),))

            try:
                for elem in cursor:
                    product_id = elem[0]
                    break
            except IndexError:  # не существует рекомендации на эту категорию для данного пользователя
                return False, None

        if product_id == -1:
            return False, None

        url = self.http_url + f'/bag/{user_id}/{product_id}'  # запрос на добавление в корзину
        is_ok = requests.get(url, auth=self.basicAuthCredentials).json()

        url = self.http_url + f'/product/{product_id}'       # запрос на получение товара
        product = requests.get(url, auth=self.basicAuthCredentials).json()

        if not is_ok:  # отловили ошибку (пипец го-стайл)
            return False, None

        with self.conn_db.cursor(cursor_factory=DictCursor) as cursor:
            # обновлем количество покупок данного товара
            sql_str = 'UPDATE product_recommendations SET purchases_number = purchases_number+1 WHERE  product_id=%s;'
            cursor.execute(sql_str, (product_id,))
        self.conn_db.commit()
        return True, product  # все круто сделали ребята вообще ребята молодцы отправляем отчет

    def get_id_by_tg(self, tg_id: int):
        """ Возращает id в системе магазина по id в телеге """
        with self.conn_db.cursor(cursor_factory=DictCursor) as cursor:
            cursor.execute('SELECT shop_id FROM bot_users WHERE tg_id=%s;', (str(tg_id),))

            try:
                for elem in cursor:
                    return elem[0]
            except Exception:
                return NoUserError
        return None

    def create_user(self, tg_id: int):
        """ Создает пустого пользователя как в системе магазина, так и в системе бота, связывая с данных тг аккаунтом """
        with self.conn_db.cursor(cursor_factory=DictCursor) as cursor:
            sql_str = 'SELECT * FROM bot_users WHERE tg_id=%s LIMIT 1;'
            cursor.execute(sql_str, (tg_id,))

            is_used = False
            for _ in cursor: # проверяем есть ли такой пользователь уже
                is_used = True

        if is_used:
            return False

        url = self.http_url + f'/new/user/demo'
        shop_id = requests.get(url, auth=self.basicAuthCredentials).json()

        with self.conn_db.cursor(cursor_factory=DictCursor) as cursor:  # соответственно слздаем пользователя
            sql_str = 'INSERT INTO bot_users (shop_id, tg_id) VALUES(%s, %s);'
            cursor.execute(sql_str, (shop_id, tg_id, ))
        self.conn_db.commit()

        return True

    def request_bag(self):
        pass


if __name__ == '__main__':
    basicAuthCredentials = HTTPBasicAuth('testtest', 'testtest')

    # print(requests.get(f'http://localhost:5445/search/product/молоко', auth=basicAuthCredentials).json())
    # print(requests.get(f'http://localhost:5445/bag/1/88', auth=basicAuthCredentials).json())

    # print(test.request_by_category('молоко', 1))
