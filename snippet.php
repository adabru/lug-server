if($_SERVER['HTTP_X_FORWARDED_PROTO'] == 'https'){
    $_SERVER['HTTPS'] = 'on';
    $_SERVER['SERVER_PORT'] = 443;
}