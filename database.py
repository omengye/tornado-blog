# -*- coding: utf-8 -*-
import tornado
import tornado.web
import json

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

'''
处理datetime满足json
'''
class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        return o.strftime("%Y-%m-%dT%H:%M:%S")
