$(document).ready(function() {
	$('#email').placeholder();
  	$('#signup_submit').click(function() { 
    	$('#beta_signup').submit();
    	return false;
  	});
  	$('#ref_link').click(function() {
    	$(this).focus().select();
  	});
});