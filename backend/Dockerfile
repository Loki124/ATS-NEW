# backend/Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install --production

COPY prisma ./prisma
RUN npx prisma generate

COPY . .

EXPOSE 5125

CMD ["node", "src/app.js"]