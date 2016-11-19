function saveRelease(){
    var data = $('#form-release').serialize();
    $('#btn-save-release').attr('disabled', true);
    function callback(response){
        if(response.success == 1){
            alert("发布成功");
            window.location.reload();
        }
        else {
            alert(response.message);
        }
        $('#btn-save-release').removeAttr('disabled');
    }

    $.post('/management/action', data, callback, 'json');
    return false;
}

function apiTest(){

    var data = $('#form-api-test').serialize();
    $('#myModal .modal-body').empty();
    $('#myModal .modal-body').append('<center style="margin:50px 0"><i class="ace-icon fa fa-spinner fa-spin orange bigger-300"></i></center>')

    function callback(response){
        $('#myModal .modal-body').empty();
        $('#myModal .modal-body').append(response);
    }

    $.post('/management/api-test', data, callback);
}

$(document).ready(function(){
    $('#btn-save-release').click(saveRelease);

    $('#btn-api-test').click(apiTest);

    $('a[data-releaseid]').on('click', function(){
        $('#myModal1Label').text('Release - '+$(this).text());
        $('#release-version').attr('src', 'release/'+$(this).attr('data-releaseid'));
        $('#myModal1').modal();
        return false;
    })
});