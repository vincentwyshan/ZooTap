var editor = null;
$(document).ready(function(){
    editor = ace.edit("editor");
    editor.setTheme("ace/theme/xcode");
    // 显示 tap
    editor.setDisplayIndentGuides(true);
    editor.getSession().setMode("ace/mode/python");
    editor.getSession().setUseSoftTabs(true);
    editor.getSession().setTabSize(4);

    $('#new-para').click(newPara);
    $('#save-config').click(saveConfig);
    $('.delete-para').on('click', delPara);
    $('select[name=auth_type]').change(authChange);

    var hash = window.location.hash;
    if(window.location.hash == null || window.location.hash == ''){
        hash = '#client-config';
    }
    $('a[href='+hash+']').trigger('click');
    $('[data-toggle=collapse]').click(function(){window.location.hash = $(this).attr('href')});

    $('#refresh-token').click(refreshToken);
});


function newPara(){
    // actually this client_id is customauth.id
    var client_id = $(this).attr('client_id');
    var data = {id:client_id, 'action':'clientparanew'};

    $(this).attr('disabled', true);

    var me = this;
    function callback(response){
        if(response.success == 1){
            var html = $('#sample-para').html();
            html = html.replace(/{{para.id}}/g, response.para_id);
            html = html.replace(/{{para.name}}/g, response.para_name);
            html = html.replace(/{{para.default}}/g, '');
            html = $(html);
            html.removeAttr('id');
            $('#sample-para').before(html);
            html.show();
        }
        else {
            alert(response.message);
        }
        $(me).removeAttr('disabled');
    }

    $.post('/management/action', data, callback, 'json');
    return false;
}

function refreshToken(){
    var client_id = $(this).attr('client_id');

    var data = {client_id: client_id, 'action': 'clientrefreshtoken'};
    var request = $.post('/management/action', data);

    var success = function(response){
        if(response.success == 1){
            $('#token-block pre').text(response.token);
        }
        else{
            alert('更新失败:' + response.message);
        }
    };

    var fail = function(error){
        alert('服务器错误!');
    }

    $.when(request).then(success, fail);
}

function saveConfig(){
    var source = editor.getValue();
    $('[name=source]').val(source);

    var data = $(this).parents('form').serialize();
    console.info(data);

    $(this).attr('disabled', true);

    var me = this;
    function callback(response){
        if(response.success == 1){
            alert("保存成功");
        }
        else{
            alert(response.message);
        }
        $(me).removeAttr('disabled');
    }

    $.post('/management/action', data, callback, 'json');

    return false;
}

function delPara(){
    var paraId = $(this).attr('paraid');
    var data = {id: paraId, action: 'clientparadelete'}

    function callback(response){
        if(response.success == 1){
            $('[paraid='+paraId+']').parent().parent().remove();
        }
        else{
            alert(response.message);
        }
    }
    $.post('/management/action', data, callback, 'json');
    return false;
}

function authChange(){
    var val = $(this).val();
    if(val == 'CUSTOM'){
        $('#custom-settings').show();
        $('#new-para').show();
        // $('#refresh-token').hide();
        // $('#token-block').hide();
    }
    else{
        $('#custom-settings').hide();
        $('#new-para').hide();
        // $('#refresh-token').show();
        // $('#token-block').show();
    }
}
