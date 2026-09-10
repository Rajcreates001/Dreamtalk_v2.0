FROM nginx:alpine
COPY dreamtalk/infrastructure/docker/nginx.conf /etc/nginx/nginx.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
