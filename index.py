# -*- coding: utf-8 -*-
import tornado.web
import torndb
import tornado.httpserver
import tornado.ioloop
import os
import json
from database import DataBase, DateTimeEncoder
from DoubanLoginAuth import DoubanOAuth2Mixin
import tornado.auth
import tornado.httputil
import tornado.gen
import tornado.httpclient
import markdown
import qiniu.conf
import qiniu.io
import qiniu.rs
import qiniu.fop
import unicodedata
import re

from tornado.options import define, options
define("port", default=8000, help="run on the given port", type=int)

class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", HomeHandler),
            (r"/api", ApiHandler),
            (r'/items$', EditItemsHandler),
            (r"/items/([^/]+)", ItemsHandler),
            (r'/edit', EditHandler),
            (r"/auth/login", AuthLoginHandler),
            (r"/auth/logout", AuthLogoutHandler),
            (r"/delete/items", DeleteItemsHandler),
            (r"/file", UploadFileHandler),
            (r"/pics$", EditPicsHandler),
            (r"/delete/file", DeleteFileHandler),
            ]

        settings = dict(
            blog_title = "test tornado blog",
            template_path = os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            douban_api_key='请填入豆瓣api key',
            douban_api_secret='请填入豆瓣api secret',
            redirect_uri='http://127.0.0.1:8000/auth/login',    # 修改回调地址
            cookie_secret="bZBc2sEbQLKqv7GkJD/VB8YuTC3eC0R0kRvJ5/xX37P=",   # 请生成随机值
            xsrf_cookies=True,
            qiniu_access_key="请填入qiniu access key",
            qiniu_secret_key="请填入qiniu secret key",
            qiniu_policy="请填入qiniu bucket",
            login_url="/auth/login",
            debug=True,
            )
        tornado.web.Application.__init__(self, handlers, **settings)

        self.database = torndb.Connection(
            host=options.mysql_host, database=options.mysql_database,
            user=options.mysql_user, password=options.mysql_password)

class AuthLogoutHandler(DataBase):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))

class AuthLoginHandler(DoubanOAuth2Mixin, tornado.web.RequestHandler):
    @tornado.gen.coroutine
    def get(self):
        if self.get_argument('code', False):
            user = yield self.get_authenticated_user(
                redirect_uri=self.settings['redirect_uri'],
                code=self.get_argument('code')
            )
            if user['name'] == user['uid']:
                self.set_secure_cookie("user", str(user['uid']))
                self.redirect(self.get_argument("next", "/"))
        else:
            yield self.authorize_redirect(
                redirect_uri=self.settings['redirect_uri'],
                client_id=self.settings['douban_api_key'],
                scope=None,
                response_type='code'
            )

class ApiHandler(DataBase):
    def get(self):
        posts = self.database.query("SELECT * FROM entries")
        home_json = json.dumps(posts, indent=4, cls=DateTimeEncoder)
        self.set_header("Content-Type", "application/json")
        self.write(home_json)

class HomeHandler(DataBase):
    def get(self):
        # self.write("hello world! <br> welcome " + self.current_user + " !")
        entries = self.database.query("SELECT * FROM entries ORDER BY published "
                                "DESC")
        if not entries:
            self.redirect("/edit")
            return
        self.render("index.html", entries=entries)

class ItemsHandler(DataBase):
    def get(self, slug):
        item = self.database.get("SELECT * FROM entries WHERE slug = %s", slug)
        if not item:
            raise tornado.web.HTTPError(404)
            # 使用 locale.format_date(entry.published, full_format=True, shorter=True) 在html解析时间
            # self.set_header("Content-Type", "application/json")
            # item_json = json.dumps(item, indent=4, cls=DateTimeEncoder)
        else:
            self.render('article.html', item=item)

class EditItemsHandler(DataBase):
    @tornado.web.authenticated
    def get(self):
        entries = self.database.query("SELECT * FROM entries ORDER BY published "
                                      "DESC")
        self.render('edititems.html', entries=entries)

class EditHandler(DataBase):
    @tornado.web.authenticated
    def get(self):
        entry = None
        item_id = self.get_argument("id", None)
        if item_id:
            entry = self.database.get("SELECT * FROM entries WHERE id = %s", item_id)
            if entry:
                # self.set_header("Content-Type", "text/html")
                self.render("edit.html", entry=entry)
            else:
                raise tornado.web.HTTPError(404)
        else:
            self.render("edit.html", entry=entry)

    @tornado.web.authenticated
    def post(self):
        id = self.get_argument("id", None)
        title = self.get_argument("title")
        text = self.get_argument("markdown")
        html = markdown.markdown(text)
        if id:
            entry = self.database.get("SELECT * FROM entries WHERE id = %s", int(id))
            if not entry:
                raise tornado.web.HTTPError(404)
            slug = entry.slug
            self.database.execute(
                "UPDATE entries SET title = %s, markdown = %s, html = %s "
                "WHERE id = %s", title, text, html, int(id))
        else:
            slug = unicodedata.normalize("NFKD", title).encode(
                "ascii", "ignore")
            slug = re.sub(r"[^\w]+", " ", slug)
            slug = "-".join(slug.lower().strip().split())
            if not slug:
                slug = "entry"
            while True:
                url_title = self.database.get("SELECT * FROM entries WHERE slug = %s", slug)
                if not url_title:
                    break
                slug += "-2"
            self.database.execute(
                "INSERT INTO entries (author,title,slug,markdown,html,"
                "published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                str(self.current_user), title, slug, text, html)
        self.redirect("/items/" + slug)

class DeleteItemsHandler(DataBase):
    @tornado.web.authenticated
    def post(self):
        id = self.get_argument('id', None)
        if id:
            self.database.execute("DELETE FROM entries WHERE id = %s", int(id))
            self.write("delete success<br>"
                       "<a href='/items'>返回</a>")
        else:
            raise tornado.web.HTTPError(404)

class UploadFileHandler(DataBase):
    @tornado.web.authenticated
    def get(self):
        pictures = None
        pic_id = self.get_argument('id',None)
        if pic_id:
            pictures = self.database.get("SELECT * FROM pictures WHERE id = %s", pic_id)
            if pictures:
                self.render("file.html", pictures=pictures)
            else:
                raise tornado.web.HTTPError(404)
        else:
            self.render("file.html", pictures=pictures)

    @tornado.web.authenticated
    def post(self):
        id = self.get_argument("id", None)
        pic_name = self.get_argument("pic_name", None)
        pic_name = unicode(pic_name)
        pic_details = self.get_argument("pic_details", None)
        pic_details = unicode(pic_details)

        qiniu.conf.ACCESS_KEY = self.settings['qiniu_access_key']
        qiniu.conf.SECRET_KEY = self.settings['qiniu_secret_key']
        bucket = self.settings['qiniu_policy']
        tokenObj = qiniu.rs.PutPolicy(bucket)
        extra = qiniu.io.PutExtra()
        extra.mime_type = "image/jpeg"

        if id:
            pictures = self.database.get("SELECT * FROM pictures WHERE id = %s", int(id))
            if not pictures:
                raise tornado.web.HTTPError(404)

            if self.request.files:
                ret, err = qiniu.rs.Client().delete(bucket, pictures['pic_title'].encode('utf-8'))
                if err is not None:
                    self.write('error delete: ' + err)
                else:
                    file_metas=self.request.files['file'][0]    # 提取表单中'name'为'file'的文件元数据
                    filename=file_metas['filename']   # 图片名称
                    filename=unicode(filename)
                    file=file_metas['body']
                    uploadtoken = tokenObj.token()
                    ret, err = qiniu.io.put(uploadtoken, str(filename), file, extra)
                    if err is not None:
                        self.write('error put: ' + err)
                    else:
                        self.database.execute(
                            "UPDATE pictures SET pic_name=%s, pic_title=%s, pic_details=%s, pic_hash=%s"
                            "WHERE id = %s", pic_name, ret['key'], pic_details, ret['hash'], int(id))
                        self.render("pic.html", bucket=bucket, filename=ret['key'],
                                    pic_name=pic_name, pic_details=pic_details)
            else:
                self.database.execute(
                    "UPDATE pictures SET pic_name=%s, pic_details=%s"
                    "WHERE id = %s", pic_name, pic_details, int(id))
                self.render("pic.html", bucket=bucket, filename=pictures['pic_title'],
                            pic_name=pic_name, pic_details=pic_details)

        else:
            file_metas=self.request.files['file'][0]    # 提取表单中'name'为'file'的文件元数据
            filename=file_metas['filename']   # 图片名称
            filename=unicode(filename)
            file=file_metas['body']
            uploadtoken = tokenObj.token()
            ret, err = qiniu.io.put(uploadtoken, filename, file, extra)
            if err is not None:
                self.write('error: ' + err)
            else:
                self.database.execute(
                    "INSERT INTO pictures (bucket,pic_name,pic_title,pic_details,pic_hash,"
                    "published) VALUES (%s,%s,%s,%s,%s,UTC_TIMESTAMP())",
                    bucket, pic_name, ret['key'], pic_details, ret['hash'])
                self.render("pic.html", bucket=bucket, filename=filename,
                            pic_name=pic_name, pic_details=pic_details)

class EditPicsHandler(DataBase):
    @tornado.web.authenticated
    def get(self):
        pictures = self.database.query("SELECT * FROM pictures ORDER BY published "
                                      "DESC")
        if pictures:
            self.render('pics.html', pictures=pictures)
        else:
            self.redirect('/file')

class DeleteFileHandler(DataBase):
    @tornado.web.authenticated
    def post(self):
        id = self.get_argument('id', None)
        key = self.get_argument('pic_title', None)

        if id:
            qiniu.conf.ACCESS_KEY = self.settings['qiniu_access_key']
            qiniu.conf.SECRET_KEY = self.settings['qiniu_secret_key']
            bucket = self.settings['qiniu_policy']
            bucket = unicode(bucket)
            ret, err = qiniu.rs.Client().delete(bucket, key.encode('utf-8'))
            if err is not None:
                self.write('error delete: ' + err)
            else:
                self.database.execute("DELETE FROM pictures WHERE id = %s", int(id))
                self.write("delete success<br>"
                           "<a href='/pics'>返回</a>")
        else:
            raise tornado.web.HTTPError(404)

def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()