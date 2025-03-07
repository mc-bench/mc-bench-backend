const mineflayer = require("mineflayer");
const { Vec3 } = require("vec3");
const { Buffer } = require("buffer");
const fs = require("fs").promises;
const path = require("path");
const minecraftData = require("minecraft-data");

// Environment variables with defaults
const HOST = process.env.HOST || "127.0.0.1";
const PORT = parseInt(process.env.PORT) || 25565;
const VERSION = process.env.VERSION || "1.21.1";
const USERNAME = process.env.USERNAME || "builder";
const DELAY = parseInt(process.env.DELAY) || 250;
const STRUCTURE_NAME =
  process.env.STRUCTURE_NAME ||
  `structure_${new Date().toISOString().replace(/[:.]/g, "-")}`;
const OUTDIR = process.env.OUTDIR || "out";

const mcdata = minecraftData(VERSION);
// Create Set of valid block names for O(1) lookup
const validBlocks = new Set(
  Object.values(mcdata.blocks).map((block) => block.name),
);

async function buildCreation(startX, startY, startZ) {}

function getValidatedBlock(blockType) {
  if (!validBlocks.has(blockType)) {
    throw new Error(`Invalid block type: ${blockType}`);
  }
  return blockType;
}

class CommandTracker {
  constructor() {
    this.commands = [];
    this.startingLocation = null;
    this.boundingBox = null;
  }

  setStartingLocation(x, y, z) {
    this.startingLocation = { x, y, z };
  }

  setBoundingBox(box) {
    this.boundingBox = box;
  }

  addSetBlockCommand(command, x, y, z) {
    this.commands.push({
      command,
      kind: "setblock",
      coordinates: { x, y, z },
    });
  }

  addFillCommand(command, x1, y1, z1, x2, y2, z2) {
    this.commands.push({
      command,
      kind: "fill",
      coordinates: [
        { x: x1, y: y1, z: z1 },
        { x: x2, y: y2, z: z2 },
      ],
    });
  }

  addFillBiomeCommand(command, x1, y1, z1, x2, y2, z2, biome) {
    this.commands.push({
      command,
      kind: "fillbiome",
      coordinates: [x1, y1, z1, x2, y2, z2],
      biome,
    });
  }

  async saveToFiles() {
    await fs.mkdir(OUTDIR, { recursive: true });

    const commandList = this.commands.filter(
      (cmd) => cmd.kind === "setblock" || cmd.kind === "fill" || cmd.kind === "fillbiome",
    );

    await fs.writeFile(
      path.join(OUTDIR, "commandList.json"),
      JSON.stringify(commandList, null, 2),
    );

    const summary = {
      startingLocation: this.startingLocation,
      boundingBox: this.boundingBox,
    };

    await fs.writeFile(
      path.join(OUTDIR, "summary.json"),
      JSON.stringify(summary, null, 2),
    );
  }
}

// Coordinate tracking system
class CoordinateTracker {
  constructor() {
    this.coordinates = [];
    this.boundingBox = null;
  }

  addCoordinate(x, y, z) {
    this.coordinates.push({ x, y, z });
    this.updateBoundingBox();
  }

  updateBoundingBox() {
    if (this.coordinates.length === 0) return;

    const xs = this.coordinates.map((c) => c.x);
    const ys = this.coordinates.map((c) => c.y);
    const zs = this.coordinates.map((c) => c.z);

    this.boundingBox = {
      min: {
        x: Math.min(...xs),
        y: Math.min(...ys),
        z: Math.min(...zs),
      },
      max: {
        x: Math.max(...xs),
        y: Math.max(...ys),
        z: Math.max(...zs),
      },
    };
  }

  getBoundingBox() {
    return this.boundingBox;
  }

  getDimensions() {
    if (!this.boundingBox) return null;
    return {
      width: this.boundingBox.max.x - this.boundingBox.min.x + 1,
      height: this.boundingBox.max.y - this.boundingBox.min.y + 1,
      depth: this.boundingBox.max.z - this.boundingBox.min.z + 1,
    };
  }
}

// Command queue system
class CommandQueue {
  constructor(delay = DELAY) {
    this.queue = [];
    this.isProcessing = false;
    this.DELAY = delay;
    this.activePromises = new Set();
  }

  async add(command, coordinates = null) {
    if (command.startsWith("/setblock") && coordinates) {
      commandTracker.addSetBlockCommand(command, ...coordinates);
    } else if (command.startsWith("/fill") && coordinates) {
      commandTracker.addFillCommand(command, ...coordinates);
    } else if (command.startsWith("/fillbiome") && coordinates) {
      commandTracker.addFillBiomeCommand(command, ...coordinates);
    }

    const promise = new Promise((resolve, reject) => {
      this.queue.push({ command, resolve, reject });
      if (!this.isProcessing) {
        this.processQueue();
      }
    });
    this.activePromises.add(promise);
    promise.finally(() => this.activePromises.delete(promise));
    return promise;
  }

  async processQueue() {
    if (this.isProcessing || this.queue.length === 0) return;

    this.isProcessing = true;

    while (this.queue.length > 0) {
      const { command, resolve, reject } = this.queue.shift();

      try {
        bot.chat(command);
        resolve();
      } catch (err) {
        reject(err);
      }

      if (this.DELAY > 0) {
        await new Promise((resolve) => setTimeout(resolve, this.DELAY));
      }
    }

    this.isProcessing = false;
  }

  async waitForAll() {
    // Wait for current queue to process
    while (this.queue.length > 0 || this.isProcessing) {
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    // Wait for all active promises to complete
    if (this.activePromises.size > 0) {
      await Promise.all(Array.from(this.activePromises));
    }
  }
}

/**
 * Places a block at specified coordinates for Minecraft Java 1.20.4
 * @param {number} x - X coordinate
 * @param {number} y - Y coordinate
 * @param {number} z - Z coordinate
 * @param {string} blockType - The block type to place (e.g. "stone", "oak_planks")
 * @param {Object} [options] - Additional options for block placement
 * @param {Object} [options.blockStates] - Block states as key-value pairs (e.g. { facing: "north", half: "top" })
 * @param {string} [options.mode="replace"] - Block placement mode: "replace", "destroy", or "keep"
 * @returns {Promise<void>}
 */
async function safeSetBlock(x, y, z, blockType, options = {}) {
  // Ensure coordinates are integers
  x = Math.floor(x);
  y = Math.floor(y);
  z = Math.floor(z);

  const validatedBlock = getValidatedBlock(blockType);

  try {
    // Add minecraft: namespace if not present
    const fullBlockType = validatedBlock.includes(":")
      ? validatedBlock
      : `minecraft:${validatedBlock}`;
    let command = `/setblock ${x} ${y} ${z} ${fullBlockType}`;

    // Add block states if provided
    if (options.blockStates && Object.keys(options.blockStates).length > 0) {
      const stateString = Object.entries(options.blockStates)
        .map(([key, value]) => `${key}=${value}`)
        .join(",");
      command += `[${stateString}]`;
    }

    // Add placement mode if provided
    if (options.mode) {
      const validModes = ["replace", "destroy", "keep"];
      if (!validModes.includes(options.mode)) {
        throw new Error(
          `Invalid placement mode: ${options.mode}. Must be one of: ${validModes.join(", ")}`,
        );
      }
      command += ` [${options.mode}]`;
    }

    await commandQueue.add(command, [x, y, z]);
    coordinateTracker.addCoordinate(x, y, z);
  } catch (err) {
    console.error(`Error placing block at ${x} ${y} ${z}: ${err.message}`);
    throw err;
  }
}

/**
 * Fills a region with blocks in Minecraft Java 1.20.4
 * @param {number} x1 - First corner X coordinate
 * @param {number} y1 - First corner Y coordinate
 * @param {number} z1 - First corner Z coordinate
 * @param {number} x2 - Second corner X coordinate
 * @param {number} y2 - Second corner Y coordinate
 * @param {number} z2 - Second corner Z coordinate
 * @param {string} blockType - The block type to fill with (e.g. "stone", "oak_planks")
 * @param {Object} [options] - Additional options for fill operation
 * @param {string} [options.mode] - Fill mode: "destroy", "hollow", "keep", "outline", "replace"
 * @param {Object} [options.blockStates] - Block states as key-value pairs (e.g. { facing: "north" })
 * @param {string} [options.replaceFilter] - Block to replace when using "replace" mode
 * @param {Object} [options.replaceFilterStates] - Block states for replace filter
 * @returns {Promise<void>}
 */
async function safeFill(x1, y1, z1, x2, y2, z2, blockType, options = {}) {
  // Ensure coordinates are integers
  x1 = Math.floor(x1);
  y1 = Math.floor(y1);
  z1 = Math.floor(z1);
  x2 = Math.floor(x2);
  y2 = Math.floor(y2);
  z2 = Math.floor(z2);

  const validatedBlock = getValidatedBlock(blockType);

  try {
    // Add minecraft: namespace if not present
    const fullBlockType = validatedBlock.includes(":")
      ? validatedBlock
      : `minecraft:${validatedBlock}`;
    let command = `/fill ${x1} ${y1} ${z1} ${x2} ${y2} ${z2} ${fullBlockType}`;

    // Add block states if provided
    if (options.blockStates && Object.keys(options.blockStates).length > 0) {
      const stateString = Object.entries(options.blockStates)
        .map(([key, value]) => `${key}=${value}`)
        .join(",");
      command += `[${stateString}]`;
    }

    // Handle fill modes and replace filter
    if (options.mode) {
      const validModes = ["destroy", "hollow", "keep", "outline", "replace"];
      if (!validModes.includes(options.mode)) {
        throw new Error(
          `Invalid fill mode: ${options.mode}. Must be one of: ${validModes.join(", ")}`,
        );
      }

      command += ` ${options.mode}`;

      // Handle replace filter if specified
      if (options.mode === "replace" && options.replaceFilter) {
        const fullReplaceFilter = options.replaceFilter.includes(":")
          ? options.replaceFilter
          : `minecraft:${options.replaceFilter}`;
        command += ` ${fullReplaceFilter}`;

        // Add replace filter block states if provided
        if (
          options.replaceFilterStates &&
          Object.keys(options.replaceFilterStates).length > 0
        ) {
          const filterStateString = Object.entries(options.replaceFilterStates)
            .map(([key, value]) => `${key}=${value}`)
            .join(",");
          command += `[${filterStateString}]`;
        }
      }
    }

    await commandQueue.add(command, [x1, y1, z1, x2, y2, z2]);

    // Track corners of the filled region
    // Note: This is a simplified tracking. Consider if you need to track all blocks in the region
    for (let x of [x1, x2]) {
      for (let y of [y1, y2]) {
        for (let z of [z1, z2]) {
          coordinateTracker.addCoordinate(x, y, z);
        }
      }
    }
  } catch (err) {
    console.error(
      `Error filling from (${x1},${y1},${z1}) to (${x2},${y2},${z2}): ${err.message}`,
    );
    throw err;
  }
}


/**
 * Sets the biome for a region
 * @param {number} x1 - First corner X coordinate
 * @param {number} y1 - First corner Y coordinate
 * @param {number} z1 - First corner Z coordinate
 * @param {number} x2 - Second corner X coordinate
 * @param {number} y2 - Second corner Y coordinate
 * @param {number} z2 - Second corner Z coordinate
 * @param {string} biome - The biome to set (e.g. "plains", "desert")
 * @returns {Promise<void>}
 */
async function safeFillBiome(x1, y1, z1, x2, y2, z2, biome) {
  x1 = Math.floor(x1);
  y1 = Math.floor(y1);
  z1 = Math.floor(z1);
  x2 = Math.floor(x2);
  y2 = Math.floor(y2);
  z2 = Math.floor(z2);

  const biomeName = biome.includes(":") ? biome : `minecraft:${biome}`;
  const command = `/fillbiome ${x1} ${y1} ${z1} ${x2} ${y2} ${z2} ${biomeName}`;
  await commandQueue.add(command, [x1, y1, z1, x2, y2, z2]);
}


const bot = mineflayer.createBot({
  host: HOST,
  port: PORT,
  version: VERSION,
  username: USERNAME,
});

const commandQueue = new CommandQueue();
const coordinateTracker = new CoordinateTracker();
const commandTracker = new CommandTracker();

// Update the spawn handler
bot.once("spawn", async () => {
  try {
    const startPos = bot.entity.position.offset(0, -1, 0);
    commandTracker.setStartingLocation(
      Math.floor(startPos.x),
      Math.floor(startPos.y),
      Math.floor(startPos.z),
    );

    await buildCreation(
      Math.floor(startPos.x),
      Math.floor(startPos.y),
      Math.floor(startPos.z),
    );
    const boundingBox = coordinateTracker.getBoundingBox();
    commandTracker.setBoundingBox(boundingBox);
    await commandTracker.saveToFiles();

    const {
      min: { x: minX, y: minY, z: minZ },
      max: { x: maxX, y: maxY, z: maxZ },
    } = boundingBox;

    console.log("Waiting 10 seconds to be sure all build chunks are loaded!");
    await new Promise((resolve) => setTimeout(resolve, 10000));

    console.log("Exporting structure(s) to schem file!");
    // Add commands to queue
    await commandQueue.add(`//pos1 ${minX},${minY},${minZ}`);
    await commandQueue.add(`//pos2 ${maxX},${maxY},${maxZ}`);
    await commandQueue.add("//copy");

    // Save the copied selection to a schematic file
    await commandQueue.add(`//schem save ${STRUCTURE_NAME}`);

    // Verify the save worked
    await commandQueue.add(`//schem list`);

    await commandQueue.waitForAll();
    // TODO: Fix waitForAll() to definitely work. We are seeing exits before //schem save command actually executes!
    console.log("Waiting 30 seconds to be sure everything is done!");
    await new Promise((resolve) => setTimeout(resolve, 30000));
    console.log("Done! Exiting...");
    process.exit(0);
  } catch (error) {
    console.error("Error in spawn handler:", error);
    process.exit(1);
  }
});

bot.on("error", (err) => {
  console.error("Bot error:", err);
});

bot.on("kicked", (reason) => {
  console.error("Bot was kicked:", reason);
});
