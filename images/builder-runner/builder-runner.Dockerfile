FROM mcbenchmark/minecraft-builder-base:2024-12-11

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

CMD cp /build-scripts/build-script.js build-script.js && xvfb-run -a node build-script.js
