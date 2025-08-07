# SSO
After deployment and setting up domain name, SSO stuff on google developer console should be updated:
- Authorized JavaScript origins. For use with requests from a browser
- Authorized redirect URIs. For use with requests from a web server

# WSGI
Because of OrderListeners mechanics, WSGI currently can't have more than 1 worker, as each worker process will have its own
OrderListener which causes multiplication of operations executed on data receiving from server