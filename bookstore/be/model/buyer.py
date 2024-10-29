# import sqlite3 as sqlite
import threading
import pymongo
import uuid
import json
import logging
from be.model import db_conn
from be.model import error


class Buyer(db_conn.DBConn):
    def __init__(self):
        db_conn.DBConn.__init__(self)

    def new_order(
            self, user_id: str, store_id: str, id_and_count: [(str, int)]
    ) -> (int, str, str):
        order_id = ""
        try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
            uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))

            order = {"order_id": uid, "user_id": user_id, "store_id": store_id}
            order_details = []

            for book_id, count in id_and_count:
                book = self.conn["store"].find_one({"store_id": store_id, "book_id": book_id})
                if book is None:
                    return error.error_non_exist_book_id(book_id) + (order_id,)

                stock_level = book["stock_level"]

                if stock_level < count:
                    return error.error_stock_level_low(book_id) + (order_id,)

                result = self.conn["store"].update_one(
                    {"store_id": store_id, "book_id": book_id, "stock_level": {"$gte": count}},
                    {"$inc": {"stock_level": -count}},
                )
                if result.modified_count == 0:
                    return error.error_stock_level_low(book_id) + (order_id,)
                book_info = json.loads(book["book_info"])
                price = book_info.get("price")
                order_detail = {
                    "order_id": uid,
                    "book_id": book_id,
                    "count": count,
                    "price": price
                }
                order_details.append(order_detail)

            if order_details:
                self.conn["new_order_detail"].insert_many(order_details)

            self.conn["new_order"].insert_one(order)
            order_id = uid

            # 延迟队列

            # timer = threading.Timer(60.0, self.cancel_order, args=[user_id, order_id])
            # timer.start()

            # 存入历史订单
            order["status"] = "pending"
            self.conn["order_history"].insert_one(order)
            self.conn["order_history_detail"].insert_many(order_details)

        except pymongo.errors.PyMongoError as e:
            logging.info("528, {}".format(str(e)))
            return 528, "{}".format(str(e)), ""
        except BaseException as e:
            logging.info("530, {}".format(str(e)))
            return 530, "{}".format(str(e)), ""

        return 200, "ok", order_id

    def payment(self, user_id: str, password: str, order_id: str) -> (int, str):
        conn = self.conn
        try:
            cursor = conn["new_order"].find_one({"order_id": order_id})

            if cursor is None:
                return error.error_invalid_order_id(order_id)

            order_id = cursor["order_id"]
            buyer_id = cursor["user_id"]
            store_id = cursor["store_id"]

            if buyer_id != user_id:
                return error.error_authorization_fail()

            cursor = conn["user"].find_one({"user_id": buyer_id})
            if cursor is None:
                return error.error_non_exist_user_id(buyer_id)
            balance = cursor["balance"]
            if password != cursor["password"]:
                return error.error_authorization_fail()

            cursor = conn["user_store"].find_one({"store_id": store_id})
            if cursor is None:
                return error.error_non_exist_store_id(store_id)

            seller_id = cursor["user_id"]

            if not self.user_id_exist(seller_id):
                return error.error_non_exist_user_id(seller_id)

            cursor = conn["new_order_detail"].find({"order_id": order_id})
            total_price = 0
            for order in cursor:
                count = order["count"]
                price = order["price"]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)

            cursor = conn["user"].update_one(
                {"user_id": buyer_id, "balance": {"$gte": total_price}},
                {"$inc": {"balance": -total_price}},
            )
            if cursor.modified_count == 0:
                return error.error_not_sufficient_funds(order_id)

            cursor = conn["user"].update_one(
                {"user_id": seller_id},
                {"$inc": {"balance": total_price}},
            )

            if cursor.modified_count == 0:
                return error.error_non_exist_user_id(seller_id)

            cursor = conn["new_order"].delete_one({"order_id": order_id})
            if cursor.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            cursor = conn['new_order_detail'].delete_many({"order_id": order_id})
            if cursor.deleted_count == 0:
                return error.error_invalid_order_id(order_id)

            cursor = conn["order_history"].update_one(
                {"order_id": order_id},
                {"$set": {"status": "paid"}}
            )
            if cursor.modified_count == 0:
                return error.error_invalid_order_id(order_id)

        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))

        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def add_funds(self, user_id, password, add_value) -> (int, str):
        try:
            user = self.conn["user"].find_one({"user_id": user_id})
            if not user:
                return error.error_authorization_fail()

            if user["password"] != password:
                return error.error_authorization_fail()

            result = self.conn["user"].update_one(
                {"user_id": user_id},
                {"$inc": {"balance": add_value}}
            )
            if result.modified_count == 0:
                return error.error_non_exist_user_id(user_id)

        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def receive_order(self, user_id: str, order_id: str) -> (int, str):
        try:
            order = self.conn["order_history"].find_one({"order_id": order_id})
            if not order:
                return error.error_invalid_order_id(order_id)

            buyer_id = order["user_id"]
            if buyer_id != user_id:
                return error.error_authorization_fail()

            status = order["status"]
            if status != "express":
                return error.error_not_express(order_id)

            result = self.conn["order_history"].update_one(
                {"order_id": order_id},
                {"$set": {"status": "received"}}
            )
            if result.modified_count == 0:
                return error.error_invalid_order_id(order_id)
        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok"

    def search_history_order(self, user_id: str) -> (int, str, [dict]):
        try:
            history_orders = self.conn["order_history"].find({"user_id":user_id})
            if not list(history_orders):
                return error.error_non_exist_user_id(user_id) + ([],)
            
            results = []
            for order in list(history_orders):
                order_id = order["order_id"]
                details = self.conn["order_history_detail"].find({"order_id":order_id})
                detail_list = []
                for detail in details:
                    book_id = detail["book_id"]
                    count = detail["count"]
                    price = detail["price"]
                    order_detail = {
                        "book_id": book_id,
                        "count": count,
                        "price": price
                    }
                    detail_list.append(order_detail)

                result = {
                    "order_id":order_id,
                    "details":detail_list
                }
                results.append(result)

        except pymongo.errors.PyMongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))

        return 200, "ok", results