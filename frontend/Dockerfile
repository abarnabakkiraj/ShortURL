FROM node:22-slim

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173

# Development server (hot reload). vite.config.js makes it listen on all interfaces.
CMD ["npm", "run", "dev"]
