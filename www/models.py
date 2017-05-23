#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Models for user, blog, comment.
'''

__author__ = 'EveYoung'

#uuid是python中生成唯一ID的库
import time, uuid

from www.orm import Model, StringField, BooleanField, FloatField, TextField

#这个函数的作用是生成一个基于时间的独一无二的id， 来作为数据库表中的每一行的主键
def next_id():
    #time.time（）返回当前时间的时间戳（相对于1970.1.1 00:00:00以秒计算的偏移量）
    #uuid4（）--由伪随机数得到， 有一定的重复概率， 该概率可以计算出来。
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

#这是一个用户名的表：
class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')  #id为主键
    email = StringField(ddl='VARCHAR(50)')
    passwd = StringField(ddl='VARCHAR(50)')
    admin = BooleanField()    #管理员， True表示该用户是管理员， 否则不是
    name = StringField(ddl='VARCHAR(50)')
    image = StringField(ddl='VARCHAR(500)')  #头像
    created_at = FloatField(default=time.time)    #创建时间默认为是当前时间

#这是一个博客的表：
class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')    #id为主键
    user_id = StringField(ddl='VARCHAR(50)')    #作者id
    user_name = StringField(ddl='VARCHAR(50)')    #作者名
    user_image = StringField(ddl='VARCHAR(500)')    #作者上传的图片
    name = StringField(ddl='VARCHAR(50)')        #文章名
    summary = StringField(ddl='VARCHAR(200)')     #文章摘要
    content = TextField()                       #文章正文
    created_at = FloatField(default=time.time)   #创建时间


#这是一个评论的表:
class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='VARCHAR(50)')
    blog_id = StringField(ddl='VARCHAR(50)')    #博客id
    user_id = StringField(ddl='VARCHAR(50)')    #评论者id
    user_name = StringField(ddl='VARCHAR(50)')  #评论者名字
    user_image = StringField(ddl='VARCHAR(500)')    #评论者上传的图片(照片)
    content = TextField()
    created_at = FloatField(default=time.time)


