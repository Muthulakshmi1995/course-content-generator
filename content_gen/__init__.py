# Optional PyMySQL adapter, so MySQL can be used without compiling mysqlclient.
try:
    import pymysql
    pymysql.install_as_MySQLdb()
except ImportError:
    pass
