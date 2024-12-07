FROM itzg/minecraft-server:latest as base

FROM scratch

COPY --from=base / /


WORKDIR /data
STOPSIGNAL SIGTERM
ENV TYPE=VANILLA VERSION=LATEST EULA=TRUE UID=1000 GID=1000

ENV EULA="TRUE" \
    VERSION="1.20.1" \
    TYPE="PAPER" \
    DIFFICULTY="peaceful" \
    VIEW_DISTANCE="10" \
    MODE="creative" \
    LEVEL_TYPE="flat" \
    GENERATOR_SETTINGS='{"biome":"minecraft:plains","layers":[{"block":"minecraft:bedrock","height":1},{"block":"minecraft:deepslate","height":20},{"block":"minecraft:stone","height":65},{"block":"minecraft:granite","height":37},{"block":"minecraft:dirt","height":3},{"block":"minecraft:grass_block","height":1}],"structures":{"structures":{}}}' \
    GENERATE_STRUCTURES="false" \
    SPAWN_PROTECTION="0" \
    MAX_PLAYERS="20" \
    ENABLE_COMMAND_BLOCK="true" \
    SPAWN_MONSTERS="false" \
    SPAWN_ANIMALS="false" \
    SPAWN_NPCS="false" \
    ALLOW_NETHER="false" \
    MOTD="Development Test Server" \
    OVERRIDE_SERVER_PROPERTIES="true" \
    TZ="UTC" \
    ENABLE_ROLLING_LOGS="false" \
    EXEC_DIRECTLY="true" \
    ALLOW_FLIGHT="true" \
    ONLINE_MODE="false" \
    MAX_WORLD_SIZE="1000" \
    INIT_MEMORY="1G" \
    MAX_MEMORY="2G" \
    ENABLE_RCON="true" \
    RCON_PASSWORD="rcon_password" \
    RCON_PORT="25575" \
    FORCE_GAMEMODE="true" \
    PLAYER_IDLE_TIMEOUT="0" \
    ALLOW_CHEATS="true" \
    DEFAULT_TIME="6000" \
    TIME_LOCK="6000" \
    EXISTING_OPS_FILE="SYNCHRONIZE" \
    PLUGINS="https://dev.bukkit.org/projects/worldedit/files/5168643/download"

ENV PAPER_SPIGOT_YAML='settings:\n\
  spam-limiter:\n\
    tab-spam-increment: 0\n\
    tab-spam-limit: 999999\n\
  limit-player-interactions: false\n\
  use-display-name-in-quit-message: false\n\
  unsupported-settings:\n\
    allow-permanent-block-break-exploits: true\n\
    allow-piston-duplication: true\n\
    perform-username-validation: false\n\
messages:\n\
  kick:\n\
    authentication-servers-down: false\n\
    connection-throttle: false\n\
    flying-player: false\n\
    flying-vehicle: false\n\
players:\n\
  disable-spam-limiter: true\n\
config-version: 12\n\
world-settings:\n\
  default:\n\
    tick-rates:\n\
      mob-spawner: 1\n\
    game-mechanics:\n\
      disable-player-interaction-limiter: true\n\
    misc:\n\
      disable-player-interaction-limiter: true\n\
    packet-limiter:\n\
      kick-threshold: 999999\n\
      incoming-packet-threshold: 999999\n\
      max-packet-rate: 999999\n\
      interval: 10.0\n\
    packet-limiting:\n\
      all-packets:\n\
        action: IGNORE\n\
        max-packet-rate: 999999\n\
        interval: 10.0\n\
    network-compression-threshold: -1\n\
network-compression-threshold: -1\n\
player-auto-save-rate: -1\n\
max-player-auto-save-per-tick: -1'

ENV SPIGOT_YAML='settings:\n\
  timeout-time: 3600000\n\
  restart-on-crash: false\n\
  spam-exclusions:\n\
    - /\n\
  connection-throttle: -1\n\
  netty-threads: 8\n\
commands:\n\
  spam-exclusions:\n\
    - /\n\
  silent-commandblock-console: true\n\
  log: false\n\
players:\n\
  disable-spam-limiter: true\n\
world-settings:\n\
  default:\n\
    mob-spawn-range: 0'

ENV BUKKIT_YAML='settings:\n\
  connection-throttle: -1\n\
  spam-exclusions:\n\
    - /\n\
  timeout-time: 3600000'

ENTRYPOINT [ "/start" ]
