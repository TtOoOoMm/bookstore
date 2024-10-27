import pytest

from fe.access.buyer import Buyer
from fe.test.gen_book_data import GenBook
from fe.access.new_buyer import register_new_buyer
from fe.access.book import Book
from fe.access.seller import Seller
import uuid


class TestExpressOrder:
    seller_id: str
    buyer_id: str
    store_id: str
    order_id: str
    password: str
    total_price: int
    buyer: Buyer
    seller: Seller
    buy_book_info_list: [Book]

    @pytest.fixture(autouse=True)
    def initialization(self):
        self.seller_id = "test_payment_seller_id_{}".format(str(uuid.uuid1()))
        self.store_id = "test_payment_store_id_{}".format(str(uuid.uuid1()))
        self.buyer_id = "test_payment_buyer_id_{}".format(str(uuid.uuid1()))
        self.password = 123456

        b = register_new_buyer(self.buyer_id, self.password)
        self.buyer = b
        gen_book = GenBook(self.seller_id, self.store_id)
        self.seller = gen_book.seller
        self.buy_book_info_list = []
        self.order_id = []

        for i in range(2):
            ok, buy_book_id_list = gen_book.gen(
                non_exist_book_id=False, low_stock_level=False, max_book_count=5
            )
            self.buy_book_info_list.extend(gen_book.buy_book_info_list)
            assert ok

            code, order_id = b.new_order(self.store_id, buy_book_id_list)
            self.order_id.append(order_id)
            assert code == 200

        self.total_price = 0

        for item in self.buy_book_info_list:
            book: Book = item[0]
            num = item[1]
            if book.price is None:
                continue
            else:
                self.total_price = self.total_price + book.price * num
        self.buyer.add_funds(self.total_price)
        self.buyer.payment(self.order_id[0])
        yield

    def test_express_ok(self):
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code == 200

    def test_receive_ok(self):
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code == 200
        code = self.buyer.receive_order(self.order_id[0])
        assert code == 200

    def test_error_store_id(self):
        code = self.seller.express_order(self.store_id + "_test", self.order_id[0])
        assert code != 200

    def test_error_order_id(self):
        code = self.seller.express_order(self.store_id, self.order_id[0] + "_test")
        assert code != 200

    def test_error_seller_id(self):
        self.seller.seller_id = self.seller.seller_id + "_test"
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code != 200

    def test_error_buyer_id(self):
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code == 200
        self.buyer.user_id = self.buyer.user_id + "_test"
        code = self.buyer.receive_order(self.order_id[0])
        assert code != 200

    def test_express_not_paid(self):
        code = self.seller.express_order(self.store_id, self.order_id[1])
        assert code != 200

    def test_receive_not_express(self):
        code = self.buyer.receive_order(self.order_id[1])
        assert code != 200

    def test_repeat_express(self):
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code == 200
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code != 200

    def test_repeat_receive(self):
        code = self.seller.express_order(self.store_id, self.order_id[0])
        assert code == 200
        code = self.buyer.receive_order(self.order_id[0])
        assert code == 200
        code = self.buyer.receive_order(self.order_id[0])
        assert code != 200