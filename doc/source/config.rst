=======================
功能介绍
=======================

:Author: vincent.wen

.. Note::

    文档介绍 Cada Tap  的基本软件功能

.. contents:: 


-------------
首页
-------------

#. 趋势图展示，显示所有项目API响应时间、访问量
#. 响应时间：在最近时间段内所有项目API响应时间最高值（MAX）和最低值（MIN）以及平均值（AVG）
#. 访问量：统计整个项目API的访问量，以及项目API调用过程中的错误量

----------
数据库
----------

数据库管理
=============

#. 点击数据库 可以添加新数据库 创建数据库链接 （名称 、类型、 连接字符串）
    - 数据库名称 为英文加数字加下滑线的组合（不可更改）
    - 数据库类型 目前支持 MYSQL SQLSEVER PSSQL ORACLE 
    - 连接字符串 以下有详细说明：
        #. MySQL 连接字符串 驱动为mysqldb： ``host=localhost;user=tap;passwd=tap;db=test;charset=utf8 (数据库地址;用户名;密码;数据库名称)``
        #. Oracle 连接字符串 驱动为cx_Oracle： ``tap/tap@localhost/capitalvue（数据库/用户名@链接地址/id名称）``
        #. MSSQL(sqlsever)连接字符串 驱动为pyodbc： ``DSN=tap;DATABASE=tap;UID=tap;PWD=capitalvue（ODBC中DSN;链接名;数据库名;id名称;密码）``
        #. PGSQL(postgresql)： ``host=hostname  dbname=test user=postgres password=secret port=5432``


数据库查询
==============

#. 点击数据库名称 进入后可以执行SQL语句 点击运行 查询相关数据，同时支持选中部分代码执行SQL语句，支持自动保存代码等功能
#. 查询窗口下方两个tab页面，数据窗口显示查询语句的执行结果，信息窗口显示该数据库的数据表列表

-----------
项目
-----------

创建项目
==========

#. 点击项目 可以添加新项目（项目标识、名称） 
    - 项目标示 格式为英文、数字组合
    - 项目名称 格式为中文
#. 点击项目名称 可进入项目详情 可添加和编辑API

项目详情
==========

#. 可编辑和修改项目名称 搜索API和编辑API
#. 项目详情 可见API列表 
#. 点击API名称，可进入API编辑界面
#. 考虑到项目代码的安全性，目前没有提供项目删除功能

API
====

#. 配置基本信息 API名称 功能名称 数据库选择需要的数据库 
#. 可支持同时连接多个数据库，通过``cfn_dbswitch``命令可以在配置的脚本代码中选择多个数据库查询
#. 可支持数据库负载均衡配置，该功能主要是支持使用数据库主从复制功能来增加整个项目的负载能力。其中，**数据库** 栏目配置的是主数据库，**负债均衡**
   栏目配置的从数据库，**负载均衡配置** 栏目配置的是主从分配策略（placeholder="PRIMARYDB=PRIMARYDB:20,SECONDARYDB1:40,SECONDARYDB2:40;" 数据库名称=数据库：比例，总值为100）
#. 缓存时间根据缓存策略配置，值应当是已秒为单位的数字
#. 缓存持久化，可支持缓存永不过期，可支持的缓存数据库是MongoDB(该功能当前未测试)
#. 操作类型，该配置项用于指定API是否能够对数据库执行修改操作，应当谨慎设置，项目负责人也应当对这一选项进行审查
#. 参数列表 为API所传数据配置 顺序为名称 默认值 类型 可选参数（如是必须的 可不设默认值，可选的 需要填写默认值）
#. 代码：目前可配置为SQL语句或者python语句，其中SQL语句中可混合执行一些扩展控制流操作，详细请参考 `SQL扩展说明`_

.. highlight:: mysql
- SQL语句调用实例:
    @innercode为SQL语句参数 SQL传参(API参数) 参数前加@

    ::
        
        select (case c.chargeratetype when 8 then '管理费' when 9 then '托管费' end) as FLLX
        where c.innercode=@innercode and c.ifexecuted=1 and c.chargeratetype in (8,9)
        
.. highlight:: python
- python语句调用实例:    
    userid, lastid, typeii为python语句参数(API参数) python语句最后以return list未结束

    ::

        def main():
            tpp = 20
            g_cursor.execute("""SELECT TOP %s × FROM ASS_CALLEVENT WHERE (USERID = ? OR EVENTTYPEII IN(1101, 1103))AND id < ?
            AND EVENTTYPEII = ? ORDER BY id DESC""" % (tpp,), (userid, lastid, typeii) )  
            result = g_cursor.fetchall()
            datalist = list()
            for row in result:
                row = list(row)
                datalist.append(row)
            datalist.insert(0, [c[0] for c in g_cursor.description])
            return datalist


- API发布

#. 发布选项 授权类型 OPEN为开发 无需验证    
#. AUTH为需要验证 需要KEY值 设置好后可进行发布
#. 所有版本 显示的为所有发布的项目和信息

- API授权

#. 通过添加 可对添加的客户端进行授权

- API统计

#. 统计所有项目的响应时间和访问量 以及所有错误信息

- API缓存管理

#. 可以通过项目名称 加入项目 生成缓存

------------
客户端
------------

客户端信息
===========

#. 点击添加 可以添加新客户端 可见客户端相关信息
#. 添加新客户端（客户端名称、说明）

添加新客户端
==============

#. 添加客户端名称和描述

------------
管理
------------


用户权限管理
===============

#. 可见用户列表和用户的相关权限


添加新用户
============

#. 添加新用户


-------------
命令行工具
-------------
- tap_initdb 初始化数据库
- tap_dump, tap_import 导入导出所有数据
- tap_dbconnupdate 更新数据库配置
- tap_stats 后台统计服务
