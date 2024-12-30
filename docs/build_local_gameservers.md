# Build local gameservers

The Minecraft benchmark runs ephemeral minecraft game servers. For licensing reasons we cannot ship or make these publicably available.

You can however build your own locally.
The easiest way to do this is to checkout [gameservers](https://github.com/mc-bench/gameservers).

This repository contains Dockerfiles for building various versions of the minecraft server.

Each version is on a different branch.

Current versions (branches) in use:
- [Java Minecraft 1.21.1](https://github.com/mc-bench/gameservers/tree/minecraft-1.21.1)


# Build the server (Java Minecraft 1.21.1)

```bash
cd ../gameservers
git checkout minecraft-1.21.1
docker build -t registry.digitalocean.com/mcbench/gameservers:minecraft-1.21.1-latest .
```

That's it! You can now run ephemeral game servers locally.
