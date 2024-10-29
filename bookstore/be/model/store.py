#import sqlite3 as sqlite
import threading
import pymongo


class Store:
    database = None
    client = None

    def __init__(self):
        self.client = pymongo.MongoClient("localhost", 27017)
        self.database = self.client["bookstore"]
        self.init_tables()

    def init_tables(self):
        conn = self.get_db_conn()
        user_table = conn["user"]
        user_store_table = conn["user_store"]
        store_table = conn["store"]
        new_order_table = conn["new_order"]
        new_order_detail_table = conn["new_order_detail"]
        self.database["user"].create_index([("user_id", pymongo.ASCENDING)])
        self.database["user_store"].create_index([("user_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])
        self.database["store"].create_index([("book_id", pymongo.ASCENDING), ("store_id", pymongo.ASCENDING)])

    def get_db_conn(self):
        return self.database


database_instance: Store = None
# global variable for database sync
init_completed_event = threading.Event()


def init_database():
    global database_instance
    database_instance = Store()


def get_db_conn():
    global database_instance
    return database_instance.get_db_conn()
