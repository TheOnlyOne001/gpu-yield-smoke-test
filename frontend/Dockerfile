FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy application code
COPY . .

# Build the application
RUN npm run build

# Remove devDependencies after build (optional, saves space)
RUN npm prune --production

# Expose port
EXPOSE 3000

# Default command - use start for production built app
CMD ["npm", "run", "start"]