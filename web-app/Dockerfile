# Use the official Nginx image as the base image
FROM nginx:1.29.3-alpine

RUN rm -rf /usr/share/nginx/html

COPY ./nginx.conf /etc/nginx/nginx.conf
COPY ./dist/web-app/browser /usr/share/nginx/app
