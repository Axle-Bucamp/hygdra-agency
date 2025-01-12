# Step 1: Build the React application
# Use official Node.js image to build the React app
FROM node:18 AS build

# Set the working directory inside the container
WORKDIR /app

# Copy the package.json and package-lock.json (if available) to the container
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code to the container
COPY . .

# Build the React app for production
RUN npm run build

# Step 2: Serve the built app using Nginx
# Use official Nginx image to serve the build folder
FROM nginx:alpine

# Copy the built React app from the previous build stage to the nginx container
COPY --from=build /app/build /usr/share/nginx/html

# Expose port 80 to the host machine
EXPOSE 3000

# Start Nginx to serve the app
CMD ["nginx", "-g", "daemon off;"]
