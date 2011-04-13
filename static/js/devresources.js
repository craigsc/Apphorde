$(document).ready(function() {
    var $nav_items = $('.sidebar a');
    $nav_items.click(function() {
        $nav_items.parent().removeClass('active');
        $(this).parent().addClass('active');

        var index = $nav_items.index($(this));
        $('.devtopic > div').hide().eq(index).show();
    });
});