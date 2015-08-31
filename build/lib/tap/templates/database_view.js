
function executeSQL(){
    var source = editor.getValue();

    $('#btn-run-sql').attr('disabled', true);
    $('#home3').empty();
    $('#home3').append('<center style="margin:50px 0"><i class="ace-icon fa fa-spinner fa-spin orange bigger-300"></i></center>');

     function callback(response){
        $('#home3').empty();
        $('#home3').append(response);
        $('#btn-run-sql').removeAttr('disabled');
     }

     $.get('/management/database/${dbconn.id}/execute', {source:source}, callback);
}

var infoTable = null;
function initTableInfo(){
    infoTable = $('#table-info').dataTable( {
        "aaSorting":[],
        "bAutoWidth": true,//自动宽度
        sScrollY: "300px",//enable vertical scrolling
        sScrollX: "100%",
        bScrollCollapse: true,
        "oLanguage": {
            "sLengthMenu": "每页显示 _MENU_ 条记录",
            "sZeroRecords": "抱歉， 没有找到",
            "sInfo": "从 _START_ 到 _END_ /共 _TOTAL_ 条数据",
            "sInfoEmpty": "没有数据",
            "sInfoFiltered": "(从 _MAX_ 条数据中检索)",
            "oPaginate": {
            "sFirst": "首页",
            "sPrevious": "<",
            "sNext": ">",
            "sLast": "尾页"
            },
            "sZeroRecords": "没有检索到数据",
            "sProcessing": "<img src='./loading.gif' />"
        }
    } );
}

$(document).ready(function(){
    editor = ace.edit("editor");
    editor.setTheme("ace/theme/xcode");
    editor.getSession().setMode("ace/mode/sql");

    $('#btn-run-sql').click(executeSQL);
    initTableInfo();
});

