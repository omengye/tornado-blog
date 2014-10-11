###简易的tornado blog，采用douban oauth2 登录，附带了一个可上传图片至qiniu云的功能，未完成，还差分页、标签和前端优化
####见 [demo](http://mytornadoblog.coding.io/)
####index.py里  

	douban_api_key='请填入豆瓣api key'  
	douban_api_secret='请填入豆瓣api secret'  
	qiniu_access_key="请填入qiniu access key"  
	qiniu_secret_key="请填入qiniu secret key"  
	qiniu_policy="请填入qiniu bucket"  
	redirect_uri='http://127.0.0.1:8000/auth/login',    # 修改回调地址

####database.py里  
利用coding绑定的mysql数据库  

	define("mysql_host", default="10.9.1.188:3306", help="blog database host")	# 请修改数据库ip地址及端口  
	define("mysql_database", default="请填入数据库名", help="blog database name")  
	define("mysql_user", default="请填入数据库用户名", help="blog database user")  
	define("mysql_password", default="请填入数据库密码", help="blog database password")  

####mysql设置  

		CREATE TABLE `entries` (
		`id` INT(11) NOT NULL AUTO_INCREMENT,
		`author` VARCHAR(50) NOT NULL,
		`slug` VARCHAR(100) NOT NULL,
		`title` VARCHAR(512) NOT NULL,
		`markdown` MEDIUMTEXT NOT NULL,
		`html` MEDIUMTEXT NOT NULL,
		`published` DATETIME NOT NULL,
		`updated` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
		PRIMARY KEY (`id`),
		UNIQUE INDEX `slug` (`slug`),
		INDEX `published` (`published`)
	)
	COLLATE='utf8_general_ci'
	ENGINE=InnoDB


	CREATE TABLE `pictures` (
		`id` INT(11) NOT NULL AUTO_INCREMENT,
		`bucket` VARCHAR(50) NOT NULL,
		`pic_name` VARCHAR(50) NOT NULL,
		`pic_title` VARCHAR(50) NULL DEFAULT NULL,
		`pic_details` MEDIUMTEXT NULL,
		`pic_hash` VARCHAR(50) NOT NULL,
		`published` DATETIME NOT NULL,
		`updated` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
		PRIMARY KEY (`id`),
		UNIQUE INDEX `pic_hash` (`pic_hash`)
	)
	COLLATE='utf8_general_ci'
	ENGINE=InnoDB;

