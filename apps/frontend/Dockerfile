FROM 192.168.0.237/booking_ticket/node:22-alpine

WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
