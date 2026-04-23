FROM node:20-slim

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Environment variable for the backend URL
ARG NEXT_PUBLIC_ENV_URL
ENV NEXT_PUBLIC_ENV_URL=${NEXT_PUBLIC_ENV_URL}

RUN npm run build

EXPOSE 3000

CMD ["npm", "run", "start"]
