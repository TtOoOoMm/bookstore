import pytest
import json
from fe.access import book
from fe.access import auth
from fe import conf
from be.model import store
import random


class TestSearch:
    @pytest.fixture(autouse=True)
    def pre_run_initialization(self):
        self.auth = auth.Auth(conf.URL)
        book_db = book.BookDB()
        self.books = book_db.get_book_info(0, 2)
        self.db = store.get_db_conn()
        self.a_book_in_store = self.db["store"].find_one({})
        self.store_id = self.a_book_in_store["store_id"]
        self.book_info = json.loads(self.a_book_in_store["book_info"])
        self.title_in_store = self.book_info['title']
        self.tag_in_store = self.book_info['tags'][random.randint(0,len(self.book_info['tags'])-1)]
        self.content_in_store = self.book_info['content'].split("\n")[0]
        yield

    def test_search_global(self):
        print(self.books)
        for b in self.books:
            title, content, tag= b.title, b.content.split("\n")[0], random.choice(b.tags)
            assert self.auth.search_book(title=title) == 200
            assert self.auth.search_book(content=content) == 200
            assert self.auth.search_book(tag=tag) == 200
    def test_search_global_not_exist(self):
        not_exist = "Do not exist ^o^"
        assert self.auth.search_book(title=not_exist) == 529
        assert self.auth.search_book(content=not_exist) == 529
        assert self.auth.search_book(tag=not_exist) == 529    
    def test_search_in_store(self):
        assert self.auth.search_book(title=self.title_in_store, store_id=self.store_id) == 200
        assert self.auth.search_book(content=self.content_in_store, store_id=self.store_id) == 200
        assert self.auth.search_book(tag=self.tag_in_store, store_id=self.store_id) == 200
    def test_search_not_exist_store_id(self):
        not_exist = "Do not exist ^o^"
        assert self.auth.search_book(title=self.title_in_store, store_id=not_exist) == 513
        assert self.auth.search_book(content=self.content_in_store, store_id=not_exist) == 513
        assert self.auth.search_book(tag=self.tag_in_store, store_id=not_exist) == 513
    def test_search_in_store_not_exist(self):
        not_exist = "Do not exist ^o^"
        assert self.auth.search_book(title=not_exist, store_id=self.store_id) == 529
        assert self.auth.search_book(content=not_exist, store_id=self.store_id) == 529
        assert self.auth.search_book(tag=not_exist, store_id=self.store_id) == 529
        
    def test_search_global_not_exist(self):
        not_exist = "Do not exist ^o^"
        assert self.auth.search_book(title=not_exist) == 529
        assert self.auth.search_book(content=not_exist) == 529
        assert self.auth.search_book(tag=not_exist) == 529    
        