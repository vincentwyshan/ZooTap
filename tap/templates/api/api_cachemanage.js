$(document).ready(function(){
    $('#version').change(function(){window.location.href = '?selected='+$(this).val();})
    $('#parameters input').keyup(getCache);
    $('#delete-cache').click(deleteCache);
    $('#gen-cache').click(genCache);
    getCache();
})

var getCache = function(){
    $('input[name=action]').val('cacheget')
    var data = $('#parameters').serialize();
    var callback = function(response){
        $("#jsonview").jJsonViewer(response.data);
        if(response.data == null){
            $('#delete-cache').attr('disabled', true);
        }
        else{
            $('#delete-cache').removeAttr('disabled');
        }
    }
    $.post('/management/action', data, callback, 'json');
}

var deleteCache = function(){
    $('input[name=action]').val('cachedelete')
    var data = $('#parameters').serialize();
    var callback = function(response){
        if(response.success == 1){
            getCache()
        }
        else{
            alert(response.message);
        }
    }
    $.post('/management/action', data, callback, 'json');
}

var genCache = function(){
   $('input[name=action]').val('cachegen')
    var data = $('#parameters').serialize();
    var callback = function(response){
        if(response.success == 1){
            getCache()
        }
        else{
            alert(response.message);
        }
    }
    $.post('/management/action', data, callback, 'json');
}