FROM node:18-slim

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

CMD sh -c 'echo "$BUILD_SCRIPT" > build-script.js && node build-script.js'
