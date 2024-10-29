# 第一次大作业：书店  实验报告

### 小组成员与分工

| 学号        | 姓名   | 分工                                          |
| :---------- | ------ | --------------------------------------------- |
| 10225501423 | 黄冠富 | 用户权限接口，共同完成后40%功能，实验报告撰写 |
| 10225501427 | 袁滨   | 买家用户接口，共同完成后40%功能，实验报告撰写 |
| 10225501454 | 何俊彦 | 卖家用户接口，共同完成后40%功能，实验报告撰写 |

## 1. 功能

- 实现一个提供网上购书功能的网站后端。<br>

- 网站支持书商在上面开商店，购买者可以通过网站购买。<br>
- 买家和卖家都可以注册自己的账号。<br>
- 一个卖家可以开一个或多个网上商店。
- 买家可以为自已的账户充值，在任意商店购买图书。<br>
- 支持 下单->付款->发货->收货 流程。<br>

**1.1 实现对应接口的功能，见项目的 doc 文件夹下面的 .md 文件描述 （60%）<br>**

其中包括：

1)用户权限接口，如注册、登录、登出、注销<br>

2)买家用户接口，如充值、下单、付款<br>

3)卖家用户接口，如创建店铺、填加书籍信息及描述、增加库存<br>

通过对应的功能测试，所有 test case 都 pass <br>

**1.2 为项目添加其它功能 ：（40%）<br>**

1)实现后续的流程 ：发货 -> 收货

2)搜索图书 <br>

- 用户可以通过关键字搜索，参数化的搜索方式；
- 如搜索范围包括，题目，标签，目录，内容；全站搜索或是当前店铺搜索。
- 如果显示结果较大，需要分页
- (使用全文索引优化查找)

3)订单状态，订单查询和取消订单<br>

- 用户可以查自已的历史订单，用户也可以取消订单。<br>
- 取消订单可由买家主动地取消，或者买家下单后，经过一段时间超时仍未付款，订单也会自动取消。 <br>


## 2. bookstore目录结构
```
bookstore
  |-- be                            后端
        |-- model                     后端逻辑代码
        |-- view                      访问后端接口
        |-- ....
  |-- doc                           JSON API规范说明
  |-- fe                            前端访问与测试代码
        |-- access
        |-- bench                     效率测试
        |-- data                    
            |-- book.db                 
            |-- scraper.py              从豆瓣爬取的图书信息数据的代码
        |-- test                      功能性测试（包含对前60%功能的测试，不要修改已有的文件，可以提pull request或bug）
        |-- conf.py                   测试参数，修改这个文件以适应自己的需要
        |-- conftest.py               pytest初始化配置，修改这个文件以适应自己的需要
        |-- ....
  |-- ....
```

## 3. 文档数据库结构设计

![](.\schema.png)

具体文档集合及其属性详见 doc 文件夹。

## 4. 基础功能实现(60%)

### 4.0 大致思路

对于基础的功能实现，简而言之就是按照 doc 文件夹中的指示，将 SQLite 框架中原本 SQL 语言修改为 MongoDB 所使用的语言，例如将

```sqlite
	cursor = self.conn.execute(
                    "SELECT book_id, stock_level, book_info FROM store "
                    "WHERE store_id = ? AND book_id = ?;",
                    (store_id, book_id),
                )
```

改为：

```
book = self.conn["store"].find_one({"store_id": store_id, "book_id": book_id})
```

此外，我们需要在`fe/access`下的`book.py`完成对 MongoDB 数据库的连接：

```python
	def __init__(self, large: bool = False):
        # parent_path = os.path.dirname(os.path.dirname(__file__))
        db_path = "mongodb://localhost:27017"
        db_name = "bookstore"
        self.client = pymongo.MongoClient(db_path)
        self.db = self.client[db_name]
```

对`be/model`下的`store.py`进行数据库连接并初始化表格信息：

```python
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
```

在这个项目中调用接口完成请求的过程，就是在前端`fe/access`首先产生一个请求，然后在`be/view`中的接口识别并接收这些请求，发送给`be/model`中的相应函数，从而对数据库执行相应操作并返回结果。以用户权限中的注册功能为例，位于`fe/access/auth.py`中的`register()`函数首先把用户设置的用户ID和密码并入请求体并发起POST请求，接着`be/view/auth.py`中的`register()`函数会根据路径`"/register"`识别并接收前端的注册请求，提取请求体中的用户ID和密码传给`be/model/user.py`中的`register()`函数，最终由`register()`函数来对数据库完成相关操作。

下面会逐一介绍基础接口的实现方法，省略函数末尾的exception处理与正常结果返回：

```python
		except pymongo.errors.PymongoError as e:
            return 528, "{}".format(str(e))
        except BaseException as e:
            return 530, "{}".format(str(e))
        return 200, "ok"
```

主要介绍`try:`中对数据正常性的检查与对数据库的操作。

### 4.1 用户权限接口

##### 4.1.1 注册

修改`be/model`下`user.py`中的`register()`函数：

```python
def register(self, user_id: str, password: str):
        if self.user_id_exist(user_id):
            return error.error_exist_user_id(user_id)
        try:
            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            user_key = {
                "user_id": user_id,
                "password": password,
                "balance": 0,
                "token": token,
                "terminal": terminal,
            }
            self.conn['user'].insert_one(user_key)
        except pymongo.errors.PymongoError as e:
            return 528, str(e)
        return 200, "ok"
```

首先应确保用户id唯一，使用`find_one`查询该 user_id ，若 user_id 已存在就报错，然后就可以使用`insert_one`向数据库插入新的用户数据。

##### 4.1.2 登录

对于登录与登出，还要使用到检查 password 和 token的函数，分别对应`check_password()`与`check_token()`。以`check_password()`为例：

```python
def check_password(self, user_id: str, password: str) -> (int, str):
        cursor = self.conn['user'].find_one({"user_id": user_id})
        if cursor is None:
            return error.error_authorization_fail()

        if password != cursor.get('password'):
            return error.error_authorization_fail()

        return 200, "ok"
```

查询数据库中该 user_id 的信息，若不存在则报错；获取其正确密码，进行验证：密码错误则报错，正确则返回操作码 200 和 "ok"。对于`check_token()`同理。

修改`login()`：

```python
 try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message, ""

            token = jwt_encode(user_id, terminal)
            cursor = self.conn['user'].update_one(
                {'user_id': user_id},{'$set':{'token': token,'terminal':terminal}}
            )
            if cursor.matched_count == 0:
                return error.error_authorization_fail() + ("",)
```

主要流程为：

1. 调用 `check_password() `函数验证用户名和密码是否正确；
2. 生成新的 token；
3. 更新数据库中该账户的信息，包括 token 和 terminal。

##### 4.1.3 登出

修改`logout()`函数，过程与`login()`相似：

```python
try:
            code, message = self.check_token(user_id, token)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            dummy_token = jwt_encode(user_id, terminal)

            cursor = self.conn['user'].update_one(
                {'user_id': user_id}, {'$set': {'token': dummy_token, 'terminal': terminal}}
            )
            if cursor.matched_count == 0:
                return error.error_authorization_fail()
```

调用`check_token()`检查用户是否处于登陆状态中，如果不是则报错；然后使用`update_one`更新相应用户的 token 和 terminal 属性（`"$set"`）。

##### 4.1.4 注销

修改`unregister()`函数：

```python
 try:
            code, message = self.check_password(user_id, password)
            if code != 200:
                return code, message

            cursor = self.conn['user'].delete_one({"user_id": user_id})
            if cursor.deleted_count != 1:
                return error.error_authorization_fail()
```

调用`check_password()`验证密码，密码正确则使用`delete_one`删除相应 user_id。

##### 4.1.5修改密码

修改`change_password()`函数：

```python
try:
            code, message = self.check_password(user_id, old_password)
            if code != 200:
                return code, message

            terminal = "terminal_{}".format(str(time.time()))
            token = jwt_encode(user_id, terminal)
            cursor = self.conn['user'].update_one(
                {'user_id': user_id},
                {'$set': {
                    'password': new_password,
                    'token': token,
                    'terminal': terminal
                }}
            )
            if cursor.matched_count == 0:
                return error.error_authorization_fail()
```

传入 user_id，旧密码与新密码，先检查旧密码输入是否正确，验证成功后更新对应 user_id 的 password, token, terminal。

用户权限接口的测试对应`fe/test`中的`test_login.py`,`test_password.py`与`test_register.py`。

### 4.2 买家用户接口

##### 4.2.1 充值

修改`buyer.py`中的`add_funds()`函数：

```python
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
```

首先需验证用户密码信息，成功后用`"$inc"`语法来更新用户的 balance 属性来表示充值金额，最后要检查更新操作是否成功匹配了一个用户，如果没有匹配成功，返回错误码和错误信息，表示用户不存在。

##### 4.2.2 下单

修改`new_order()`函数：

```python
try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id) + (order_id,)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id) + (order_id,)
           
```

对于传入的 user_id 与 store_id，先要检查其是否存在；

```python
			uid = "{}_{}_{}".format(user_id, store_id, str(uuid.uuid1()))
			order = {"order_id": uid, "user_id": user_id, "store_id": store_id}
            order_details = []
```

生成订单 uid 与订单信息；

```python
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
```

对于每个商品 id 和数量的元组，执行以下操作：

1. 查询数据库，查找商店中指定商品 id 的信息。如果找不到该商品，返回错误码和错误信息，并将空字符串作为订单 id 的一部分返回。
2. 查找指定商品 id 的价格并获取商品的库存水平。
3. 检查库存是否足够以满足购买数量，如果库存不足，返回错误码和错误信息，并将空字符串作为订单 id 的一部分返回。
4. 更新商店中指定商品的库存水平，减去购买数量，并检查更新操作是否成功修改了库存。如果没有修改成功，返回错误码和错误信息，并将空字符串作为订单 id 的一部分返回。
5. 将订单详细信息插入到订单详细信息集合中，包括订单 id、商品 id、数量和价格。

##### 4.2.3 付款

修改`payment()`函数：

```python
 conn = self.conn
        try:
            cursor = conn["new_order"].find_one({"order_id": order_id})

            if cursor is None:
                return error.error_invalid_order_id(order_id)
```

订单集合中必须包含该订单；

```python
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
```

检查买家 user_id 及其 password 是否存在、匹配，商店 store_id 是否存在，卖家 user_id 是否存在；

```python
			cursor = conn["new_order_detail"].find({"order_id": order_id})
            total_price = 0
            for order in cursor:
                count = order["count"]
                price = order["price"]
                total_price = total_price + price * count

            if balance < total_price:
                return error.error_not_sufficient_funds(order_id)
```

对订单信息进行检查，计算订单价格，如果价格大于买家的余额就报错；

```python
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
```

更新买家与卖家所拥有金额`"balance"`属性，并使用`delete_one`将该订单移出新增订单集合，使用`delete_many`将其具体信息移出新增订单信息集合。对于买家的权限操作，包含了很多错误检查，确保数据更新的准确性。

买家用户接口测试对应`fe/test`中的`test_new_order.py`,`test_add_funds.py`与`test_payment.py`。

### 4.3 卖家用户接口

##### 4.3.1 创建店铺

修改`seller.py`中的`create_store()`函数：

```python
 try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if self.store_id_exist(store_id):
                return error.error_exist_store_id(store_id)
            user_store_doc = {
                'store_id': store_id,
                'user_id': user_id
            }
            self.conn['user_store'].insert_one(user_store_doc)
```

检查卖家、商店 id 是否存在，若不存在则返回错误信息；使用`insert_one`将新商店的信息插入`user_store_doc`。

##### 4.3.2 填加书籍信息

修改`add_book()`函数：

```python
 try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if self.book_id_exist(store_id, book_id):
                return error.error_exist_book_id(book_id)

            book_doc = {
                'store_id': store_id,
                'book_id': book_id,
                'book_info': book_json_str,
                'stock_level': stock_level
            }
            self.conn['store'].insert_one(book_doc)
```

检查卖家、商店、图书各自 id 是否存在，若不存在则返回错误信息；使用`insert_one`添加其书籍信息。

##### 4.3.3 描述、增加库存

修改`add_stock_level()`函数：

```python
try:
            if not self.user_id_exist(user_id):
                return error.error_non_exist_user_id(user_id)
            if not self.store_id_exist(store_id):
                return error.error_non_exist_store_id(store_id)
            if not self.book_id_exist(store_id, book_id):
                return error.error_non_exist_book_id(book_id)

            self.conn['store'].update_one(
                {"store_id": store_id, "book_id": book_id},
                {"$inc": {"stock_level": add_stock_level}},
            )
```

同样地，检查卖家、商店、图书各自 id 是否存在，若不存在则返回错误信息；使用`update_one`更新库存信息。

卖家用户接口对应测试为`fe/test`中的`test_create_store.py`,`test_add_book.py`与`test_add_stock_level.py`。

修改的文件还包含`db_conn.py`，主要就是简单的把 sql 语言改为文档数据库语言，不多赘述。

### 4.4 基础功能测试结果

![](.\base_test_result.jpg)

## 5. 其他功能(40%)
1)发货 -> 收货

要实现发货和收货，需要在`buyer`和`seller`中都添加接口。在seller中增加的是发货的接口，而在buyer中加入的是收货的接口。

当buyer创建新订单后，订单状态会变为pending，之后将订单储存到order_history中。当buyer调用payment函数并成功支付以后将
订单的状态变为paid。

卖家在收到钱之后再调用express_order函数将订单状态改变为express表示快递已经发出，当买家收到货之后调用receive_order将订单的状态改变为
received表明已经收到货物，这样整个发货和收货的流程就完成了。

在测试方面，在`fe/test`中添加了`test_express_order.py`的测试文件，初始化了两组订单数据，一组没有付钱，另一组付了钱。
分别测试了发货，收货，没有付钱，还没有发货就点击收货，重复发货收货等情况的测试。

## 6. 亮点

#### 6.1 索引

为了提升数据查询的速度，部分属性上可以建立索引。对于本次实验来说，索引的优点有以下几点：

1. 建立索引的列可以保证行的唯一性

2. 建立索引可以有效缩短数据的检索时间

3. 为用来排序或者是分组的字段添加索引可以加快分组和排序顺序

具体来说，在文档集合`user`、`user_store`和`store`中，`user_id`、[`user_id`, `store_id`]和[`book_id`, `store_id`]不容易重复，且经常被作为搜索条件进行搜索。因此，在`be/model`下的`store.py`里的`init_tables()`函数增加了给以上属性创建索引的功能。

```python
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
```

此外，文档集合 books 的 id 属性也经常被作为搜索条件进行搜索，且文档集合`books`不会被修改，因此也可以对`fe/access`下的`store.py`中的初始化函数里对其创建索引。

```python
	def __init__(self, large: bool = False):
        # parent_path = os.path.dirname(os.path.dirname(__file__))
        db_path = "mongodb://localhost:27017"
        db_name = "bookstore"
        self.client = pymongo.MongoClient(db_path)
        self.db = self.client[db_name]
        self.db.books.create_index([("id", pymongo.ASCENDING)])
```

而创建索引的缺点也不能忽视：

1. 创建索引和维护索引时间成本与空间成本增加，且成本随着数据量的增加而加大

2. 索引会降低表的增删改的效率，因为每次增删改索引需要进行动态维护，导致时间变长

#### 6.2  git 

本次实验采用线上线下合作的方式，线下频繁讨论，线上通过git对项目进行更新。git更新记录并不能完全反映小组对项目的改变，因为在每个接口完成的过程中都需要考虑代码的一致性问题与测试中遇到的问题，而git只对我们各自的更新做了大致的整合。

以下是本次实验项目的github仓库链接：[TtOoOoMm/bookstore (github.com)](https://github.com/TtOoOoMm/bookstore)
