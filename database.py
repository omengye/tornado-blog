# -*- coding: utf-8 -*-
import tornado
import tornado.web
import json
import math

from tornado.options import define
define("mysql_host", default="10.9.1.188:3306", help="blog database host")	# 请修改数据库ip地址及端口
define("mysql_database", default="请填入数据库名", help="blog database name")
define("mysql_user", default="请填入数据库用户名", help="blog database user")
define("mysql_password", default="请填入数据库密码", help="blog database password")

class DataBase(tornado.web.RequestHandler):
    @property
    def database(self):
        return self.application.database

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_tags(self, item_id):
        tags = self.database.query("SELECT tag_name FROM tags WHERE article_id = %s", int(item_id))
        tag_name = ''
        if tags:
            for tag in tags:
                tag_name += ' ' + tag['tag_name']
        else:
            tag_name = None

        return tag_name

'''
处理datetime满足json
'''
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        return o.strftime("%Y-%m-%dT%H:%M:%S")


class Paginator(object):
    def page_renders(self, page, page_size, total):
        if total % page_size == 0:
            pages = int(math.ceil(total / page_size))
        else:
            pages = int(math.ceil(total / page_size)) + 1

        next = page + 1 if page < pages else None
        previous = page - 1 if page > 1 else None

        return  pages, next, previous

