FROM node:18-alpine

WORKDIR /app

# Create a non-root user
RUN addgroup -g 1001 -S nodejs
RUN adduser -S nextjs -u 1001

# Copy package files
COPY package*.json ./

# Install ALL dependencies (including devDependencies for build)
RUN npm ci

# Copy application code
COPY . .

# Change ownership of the app directory
RUN chown -R nextjs:nodejs /app

# Build the application
RUN npm run build

# Remove devDependencies after build (optional, saves space)
RUN npm prune --production

# Switch to non-root user
USER nextjs

# Expose port
EXPOSE 3000

# Default command - use start for production built app
CMD ["npm", "run", "start"]