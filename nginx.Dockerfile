FROM nginx:stable-alpine

# Replace default nginx config with your own
COPY nginx.conf /etc/nginx/nginx.conf
