#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'EveYoung'

import  asyncio,logging
# aiomysql是Mysql的python异步驱动程序, 操作数据库要用到
import aiomysql

#这个函数的作用是输出信息, 让你知道这个时间点程序在做什么
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# 创建全局连接池
# 这个函数将来会在app.py的init函数中引用
# 我们需要创建一个全局的连接池，每个HTTP请求都可以从连接池中直接获取数据库连接。使用连接池的好处是不必频繁地打开和关闭数据库连接，而是能复用就尽量复用。
#
# 连接池由全局变量__pool存储，缺省情况下将编码设置为utf8，自动提交事务：

@asyncio.coroutine
def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    #声明变量__pool是一个全局变量, 如果不加声明, __pool就会被默认为是一个私有变量. 不能被其他函数引用
    global __pool
    #调用一个协程来创建全局连接池, create_pool的返回值是一个pool实例对象
    __pool = yield from aiomysql.create_pool(
        #下面就是创建数据库链接需要用到的一些参数, 从**kw(关键字参数)中取出来
        #kw.get的作用应该是, 当没有传入参数时, 默认参数就是get函数的第二项
        host=kw.get('host', 'localhost'),   #数据库服务器位置, 默认设在本地
        port=kw.get('port', 3306),  #MySQL的端口, 默认为3306
        user=kw['user'],    #登录用户名, 通过关键参数词传进来
        password=kw['password'],    #登录密码, 通过关键词参数传进来
        db=kw['db'],    #当前数据库名
        charset=kw.get('charset', 'utf8'),  #设置 编码格式, 默认为utf-8
        autocommit=kw.get('autocommit', True),  #自动提交模式, 设置默认开启
        maxsize=kw.get('maxsize', 10),  #最大连接数, 默认设为10
        minsize=kw.get('minsize', 1),   #最小连接数, 默认设为1, 这样可以保证任何时候都会有一个数据库连接
        loop=loop   #传递消息循环对象, 用于异步执行
    )

#=====================================以下是sql函数处理区===========================================================================
#select 和 execute方法是实现其他Model类中sql语句都经常要用的方法
#将执行sql的代码封装进select函数, 调用的时候只要传入sql, 和sql所需要的一些参数就好
#size 用于指定最大的查询数量, 不指定将返回所有查询结果
# 要执行SELECT语句，我们用select函数执行，需要传入SQL语句和SQL参数
@asyncio.coroutine
def select(sql, args, size=None):
    log(sql, args)
    #声明全局变量, 这样才能引用create_pool函数创建的__pool变量
    global __pool

    #从连接池中获得一个数据库连接
    #用with语句可以封装清理(关闭conn)和处理异常工作
    with (yield from __pool) as conn:

        #等待连接对象返回DictCursor可以通过dict的方式获取数据库对象, 需要通过游标对象执行sql
        cur = yield from conn.cursor(aiomysql.DictCursor)

        #设置执行语句, 其中sql的占位符是?, 而python为%s, 这里要做一下替换
        #args是sql语句的参数
        yield from cur.execute(sql.replace('?', '%s'), args or ())

        #如果指定了查询数量, 则查询指定数量的结果, 如果不指定则查询所有结果
        if size:
            rs = yield from cur.fetchmany(size)     #从数据库获取指定的行数
        else:
            rs = yield from cur.fetchall()  #返回所有结果集
        yield from cur.close()
        logging.info('rows returned: %s' % len(rs))     #打印返回的行数
        return rs   #返回结果集


# Insert, Update, Delete
#
# 要执行INSERT、UPDATE、DELETE语句，可以定义一个通用的execute()函数，因为这3种SQL的执行都需要相同的参数，以及返回一个整数表示影响的行数：
#定义execute()函数执行insert update delete语句

@asyncio.coroutine
def execute(sql, args, autocommit=True):
    # execute()函数只返回结果数, 不返回结果集, 适用于insert, update这些语句
    log(sql)
    with (yield from __pool) as conn:
        if not autocommit:
            yield from conn.begin()
        try:
            cur = yield from conn.cursor()

            yield from cur.execute(sql.replace('?', '%s'), args)
            affected = cur.rowcount     #返回受影响的行数
            yield from cur.close()
            if not autocommit:
                yield from conn.commit()
        except BaseException as e:
            if not autocommit:
                yield from conn.rollback()
            raise
        return affected
#execute()函数和select()函数所不同的是，cursor对象不返回结果集，而是通过rowcount返回结果数。

#这个函数在元类中被引用, 作用是创建一定数量的占位符
def create_args_string(num):
    L = []
    for n in range(num):
        L.append('?')
        #比如说num=3, 那L就是['?', '?', '?'], 通过下面这句代码返回一个字符串'?,?,?'
    return ', '.join(L)

#===================================Field定义域区======================================================
#首先来定义Field类, 他负责保存数据库表的字段名和字段类型

#父定义域: 可以被其他定义域继承
class Field(object):
    #定义域的初始化:包括属性(列)名, 属性(列)的类型, 主键, 默认值
    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default  #如果存在默认值, 在getOrDefault()中会被用到
#定制输出信息为类名, 列的类型, 列名
    def __str__(self):
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)


#映射道varchar的StringField：
class StringField(Field):
    #ddl是数据定义语言("data definition languages"), 默认值是'varchar(100)', 意思是 可变字符串, 长度为100
    #和char相对应, char是固定长度, 字符串长度不够会自动补齐, varchar则是多长就是多长, 但最长不超过规定长度
    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

#============================================Model基类区=======================================================
#注意到Model只是一个基类，如何将具体的子类如User的映射信息读取出来呢？答案就是通过metaclass：ModelMetaclass：
#编写元类:
class ModelMetaclass(type):

    def __new__(cls, name, bases, attrs):
        #排除Model类本身：
        if name=='Model':
            return type.__new__(cls, name, bases, attrs)
        #获取table的名称：
        tableName = attrs.get('__table__', None) or name
        logging.info('found model: %s (table: %s)' % (name, tableName))
        #获取所有的Field和主键名：
        mappings = dict()
        fields = []
        primaryKey = None
        for k, v in attrs.items():
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                #先判断找到的映射是不是主键
                if v.primary_key:
                    if primaryKey:  #若主键已存在, 又找到一个主键, 将报错, 每张表有且仅有一个主键
                        raise RuntimeError('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        #如果没有找到主键, 也会报错
        if not primaryKey:
            raise RuntimeError('Primary key is not found.')
        #定义域中的key值已经添加到fields里了,  就要在attrs中删除, 避免重名导致运行时错误
        for k in mappings.keys():
            attrs.pop(k)
        #将非主键的属性变形, 放入escaped_fields中, 方便sql语句的书写
        escaped_fields = list(map(lambda f: '`%s`' % f, fields))
        attrs['__mappings__'] = mappings #保存属性和列的映射关系
        attrs['__table__'] = tableName
        attrs['__primary_key__'] = primaryKey  #主键属性名
        attrs['__fields__'] = fields  #除主键外的属性名
        #构造默认的SELECT， INSERT， UPDATE， DELETE语句：
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)


#=================================================Model基类区========================================
# 定义所有ORM映射的基类Model, 是他既可以想字典那样通过[]访问key值, 也可以通过.访问key值
#是继承dict是为了使用方便, 例如对象实例user['id']即可轻松地通过UserModel去数据库获取id
#元类自然是为了封装我们之前写的具体的sql处理函数, 从数据库获取数据
#orm映射基类, 通过ModelMetacalss元类来构造类
#
# 首先要定义的是所有ORM映射的基类Model：
class Model(dict, metaclass=ModelMetaclass):
    #这里直接调用了Model的父类dict的初始化方法, 把传入的关键字参数存入自身的dict中
    def __init__(self, **kw):
        super(Model, self).__init__(**kw)

    #获取dict的key
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError:
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    #设置dict的值, 通过d.k=v的方式
    def __setattr__(self, key, value):
        self[key] = value

    #获取某个具体的值即value, 如果不存在则返回None
    def getValue(self, key):
        #getattr(object, name[,default]) 根据name(属性名)返回属性值, 默认为None
        return getattr(self, key, None)

    #与上一个函数类似, 但是如果这个属性与之对应的值为None时, 就需要返回定义的默认值
    def getValueOrDefault(self, key):
        value = getattr(self, key, None)
        if value is None:
            #self.__mappings__在metaclass中, 用于保存不同实例属性在model基类中的映射关系
            #field是一个定义域!
            field = self.__mappings__[key]
            #如果field存在default属性, 那可以直接使用这个默认值
            if field.default is not  None:
                #如果field的default属性是可被调用的(callable), 就给value赋值他被调用后的值, 如果不可被调用直接返回这个值
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                #把默认值设为这个属性的值
                setattr(self, key, value)
        return  value


#==========================往Model里添加方法, 就可以让所有子类调用类方法==================================================
    @classmethod    #这个装饰器是类方法的意思, 即可以不创建实例直接调用类方法
    @asyncio.coroutine
    #findAll() - 根据where条件查找
    def findAll(cls, where=None, args=None, **kw):
        ' find objects by where clause. '
        sql = [cls.__select__]
        #如果有where参数的话就在sql语句中添加字符串where和where参数
        if where:
            sql.append('where')
            sql.append(where)
        if args is None:    #这个参数是在执行sql语句前嵌入到sql语句中的, 如果为None则定义一个空的list
            args = []
        #如果有orderby参数就在sql语句中添加字符串OrderBy和参数OrderBy, 但是OrderBy是在关键字参数中定义的
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy)
        limit = kw.get('limit', None)
        if limit is not None:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)  #extent()函数用于在列表末尾一次性追加另一个序列中的多个值(用新列表扩展原来的列表)
            else:
                raise  ValueError('Invalid limit value: %s' % str(limit))
        rs = yield from select(' '.join(sql), args)
        return [cls(**r) for r in rs]

    #findNumber() - 根据where条件查找, 但返回值是整数, 适用于select count(*)类型的sql
    @classmethod
    @asyncio.coroutine
    def findNumber(cls, selectField, where=None, args=None):
        'find number by select and where. '
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where)
        rs = yield from select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['__num__']


    @classmethod
    @asyncio.coroutine
    def find(cls, pk):
        'find object by primary key.'
        #select函数之前定义过, 这里传入了三个参数分别是之前定义的sql, args, size
        rs = yield from select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0])

#=========================往Model类添加实例方法, 就可以让所有子类调用实例方法========================================
#save,update,remove这三个方法需要管理员权限才能操作, 所以不定义为类方法, 需要创建实例之后才能调用

    @asyncio.coroutine
    def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__))      #将除主键外的属性名称列表中添加到args这个
        args.append(self.getValueOrDefault(self.__primary_key__))   #再把主键添加到这个列表的最后
        rows = yield from execute(self.__insert__, args)
        if rows != 1:   #插入记录受影响的行数应该是1, 如果不是1, 那就错了
            logging.warn('failed to insert record: affected rows: %s' % rows)


    @asyncio.coroutine
    def update(self):
        args = list(map(self.getValueOrDefault, self.__fields__))
        args.append(self.getValueOrDefault(self.__primary_key__))
        rows = yield from execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)


    @asyncio.coroutine
    def remove(self):
        args = [self.getValueOrDefault(self.__primary_key__)]
        rows = yield from execute(self.__delete__, args)
        if rows != 1:
            logging.warn('failed to remove by prinary key: affected rows: %s' % rows)

    def to_json(self, **kw):
        return self.copy()





