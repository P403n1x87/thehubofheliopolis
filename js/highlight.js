function resize()
{
  var width = $(".post").width();

  $('.highlight').each(function(i, obj) {
    $(this).width(width + "px");
    console.log($(this).width());
  });
}

resize();
