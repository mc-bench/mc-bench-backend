FROM mcbenchmark/minecraft-builder-base:2024-12-11

RUN apt-get update && apt-get install -y procps && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY package.json package-lock.json ./

RUN npm install

COPY command.sh ./

RUN chmod +x command.sh

ENTRYPOINT ["./command.sh"]
