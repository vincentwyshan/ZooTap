版本记录
========


0.3.5
-----
- Fix bug: can't get cache data in the page API->CONFIG->TAB[CACHE]


0.3.4
-----
- 登录部分增加验证码验证登录
- 增加替换类参数绑定(替换类绑定参数如果类型是TEXT, 可能引起SQL代码注入)


0.3.1
-----
- 增加 Excel 文件上传功能
- 调整了部分样式（橙色改为蓝色）


0.3.0
-----

- 增加 cfn_export, cfn_bind, cfn_case 三个控制流函数
    + cfn_export(@variable, @variable1...)
    + cfn_bind(bind_name)
    + cfn_case((@variable=='1' and @variable1=='2') or @variable=='2'), 仅仅支持值比较
- 增加 对多个数据源查询的机制 cfn_dbswitch, cfn_dbswitch(dbname)
- 增加 客户端 自定义 auth 的方法
    + 在客户端处，设置一个认证选择方式：TOKEN、自定义
    + 自定义认证方式配置代码，可接收参数，根据参数进行验证，若验证成功，返回可用的access_key，否则验证失败
- 增加 发布版本管理中查看历史版本代码的功能
- 增加 通过首页快速定位错误来源的功能
- 修复一些 bug
- 提升 python 模式下 API 编译的性能, 解决字符集设定不能很好处理的问题
- 代码字符集统一为 utf8
- 增加 Excel 文件上传功能[尚未完成]
- 增加内部API相互调用机制


0.0
---

-  Initial version

