FROM nginx:1.21-alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

# Create directory for static files if needed
RUN mkdir -p /var/www/static

# Expose port 8000
EXPOSE 8000

# Start Nginx
CMD ["nginx", "-g", "daemon off;"]