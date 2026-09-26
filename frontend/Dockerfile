# Ubuntu Terra — Vite React frontend image
FROM node:20-alpine

WORKDIR /app

# Install dependencies first so Docker can cache the layer when package files don't change
COPY package.json package-lock.json ./
RUN npm ci

# Copy the rest of the frontend source
COPY . .

# Expose the Vite dev server port
EXPOSE 5173

# Start the Vite dev server and bind to all interfaces
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
