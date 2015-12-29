===========
SQL扩展说明
===========



SQL方言
========

Cada Tap 目前支持 MySQL, Oracle, SQLServer, PostgreSQL 四种关系型数据库后台，
各种关系型数据库有其自身的方言体系，默认支持正在使用数据库的方言语法。比如：MySQL通
过limit 语句实现分页，Oracle 通过rownum实现分页，SqlServer通过top实现分页，
Postgresql 通过 limit、offset 实现分页。

对应以上数据库，我们使用不同的连接驱动：
    - MySQL: python-mysql
    - Oracle: cx_oracle
    - SQLServer: pyodbc
    - PostgreSQL: psycopg2

执行SQL过程中，先解析出完整的SQL语句（以;作为语句结束符），然后逐句执行。不可避免地，
需要考虑使用的连接驱动是否支持session变量保存的问题。比如，第一句执行 ``set @a=1``，
第二句可以使用 ``select @a`` 选择上一个语句中保存的变量@a。python-mysql 和 psycopg2
可以支持session中保存的变量， cx_oracle 和 pyodbc 对session 不支持。推荐使用
`cfn_export`_ 控制流语句来导出变量。

变量绑定
=========
不同的数据库或者数据库驱动，有不同的变量绑定标志，比如 mysql 是 ``@variable``，Oracle
是 ``:variable`` 。在Cada Tap 的SQL编辑模式中统一使用 ``@variable`` 进行变量绑定。

扩展函数
=========

cfn_export
------------
导出变量

cfn_bind
---------
绑定结果集

cfn_case
---------
逻辑判断

cfn_dbswitch
-------------
数据库切换


.. highlight:: mysql

示例
-----

    ::

        cfn_export(@c): -- 导出变量 @c
            select 'b' as c;

        cfn_case(@c=='a')      -- 判断 @c 值是否等于 'a'
        cfn_bind(tablea):      -- 若执行下面SQL，将结果集绑定到 tablea
            select 'a', 'a1';
            
        cfn_case(@c=='b')      -- 判断 @c 值是否等于 'b'
        cfn_bind(tableb):      -- 若执行下面SQL，将结果集绑定到 tableb
            select 'b', 'b1';
            
        cfn_bind(test):          -- 绑定以下结果集到 test
            select 'c' c, 'd' d;
            
        -- 股票数据
        cfn_dbswitch(CADA140) -- 使用数据库 CADA140, CADA140应当在API配置的数据库选项中
        cfn_bind(table):      -- 绑定结果集到 table
            select * from sthk_security limit 100;
