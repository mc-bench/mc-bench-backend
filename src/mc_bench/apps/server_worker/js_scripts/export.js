const mineflayer = require("mineflayer");
const { Vec3 } = require("vec3");
const { Buffer } = require("buffer");
const { createCanvas } = require("node-canvas-webgl/lib");
const { world } = require("prismarine-world");
const { Viewer, WorldView, getBufferFromStream } =
  require("prismarine-viewer").viewer;
const path = require("path");
const fs = require("fs").promises;
const { exec } = require("child_process");
const gl = require("gl");

// Initialize headless GL context globally before any canvas creation
const glContext = gl(1920, 1080); // Match your desired dimensions
if (!glContext) {
  throw new Error("Failed to initialize GL context");
}

// Environment variables with defaults
const HOST = process.env.HOST || "127.0.0.1";
const PORT = parseInt(process.env.PORT) || 25565;
const VERSION = process.env.VERSION || "1.20.1";
const USERNAME = process.env.USERNAME || "builder";
const DELAY = parseInt(process.env.DELAY) || 250;
const STRUCTURE_NAME =
  process.env.STRUCTURE_NAME ||
  `structure_${new Date().toISOString().replace(/[:.]/g, "-")}`;
const OUTDIR = process.env.OUTDIR || "out";
const COMMANDS_PER_FRAME = parseInt(process.env.COMMANDS_PER_FRAME || "1");

class Recorder {
  constructor(options = {}) {
    this.width = options.width || 1920;
    this.height = options.height || 1080;
    this.viewDistance = options.viewDistance || 12;
    this.version = options.version || "1.20.1";
    this.outputDir = options.outputDir || OUTDIR;
    this.frameCount = 0;
    this.canvas = createCanvas(this.width, this.height);
    this.frameCountInterval = 30;
    this.countFile = process.env.FRAME_COUNT_FILE || "frame_count.txt";

    const context = this.canvas.getContext("webgl2", {
      preserveDrawingBuffer: true,
      antialias: true,
      alpha: true,
      premultipliedAlpha: false,
      depth: true,
      stencil: true,
      context: glContext,
    });

    if (!context) {
      throw new Error("Failed to get WebGL context from canvas");
    }

    this.renderer = new THREE.WebGLRenderer({
      canvas: this.canvas,
      context: context,
      antialias: true,
      alpha: true,
      preserveDrawingBuffer: true,
    });

    this.viewer = new Viewer(this.renderer, false);

    if (!this.viewer.setVersion(this.version)) {
      throw "Could not set version on viewer";
    }

    this.pendingUpdate = false;

    this.framesPerSecond = 30;
    this.rotationPeriodSeconds = 30;
    this.totalRotationFrames =
      this.framesPerSecond * this.rotationPeriodSeconds;
    this.anglePerFrame = (2 * Math.PI) / this.totalRotationFrames;
    this.cameraDistance = 35;

    this.videoProcessor = new StreamingVideoProcessor({
      outputDir: path.join(this.outputDir, "processed"),
      fps: this.framesPerSecond,
      outputFileName: `${STRUCTURE_NAME}_timelapse.mp4`,
    });
  }

  async writeFrameCount() {
    try {
      await fs.mkdir(OUTDIR, { recursive: true });
      await fs.writeFile(
        path.join(OUTDIR, this.countFile),
        this.frameCount.toString(),
        "utf8",
      );
      console.log(`Wrote frame count ${this.frameCount} to ${this.countFile}`);
    } catch (err) {
      console.error("Error writing frame count:", err);
    }
  }

  async init(bot, position, lookAt, cameraDistance) {
    this.position = position;
    this.lookAt = lookAt;
    this.cameraDistance = cameraDistance;

    await fs.mkdir(this.outputDir, { recursive: true });

    const worldView = new WorldView(bot.world, this.viewDistance, position);
    this.worldView = worldView;
    this.viewer.listen(this.worldView);
    this.worldView.init(this.lookAt);

    this.updateCameraPosition(0);

    bot.on("chunkColumnLoad", (pos) => {
      worldView.loadChunk(pos);
    });

    bot.on("blockUpdate", async (oldBlock, newBlock) => {
      const stateId = newBlock.stateId
        ? newBlock.stateId
        : (newBlock.type << 4) | newBlock.metadata;
      worldView.emitter.emit("blockUpdate", {
        pos: oldBlock.position,
        stateId,
      });
    });

    this.worldView.on("blockUpdate", () => {
      this.pendingUpdate = true;
    });
  }

  updateCameraPosition(frameNumber) {
    const angle = (frameNumber * this.anglePerFrame) % (2 * Math.PI);
    const x = this.lookAt.x + this.cameraDistance * Math.cos(angle);
    const z = this.lookAt.z + this.cameraDistance * Math.sin(angle);
    const y = this.position.y;

    this.viewer.camera.position.set(x, y, z);
    this.viewer.camera.lookAt(this.lookAt.x, this.lookAt.y, this.lookAt.z);
  }

  async captureFrame() {
    // Ensure WorldView has finished updating
    if (this.pendingUpdate) {
      this.viewer.update();
      this.pendingUpdate = false;
    }

    this.updateCameraPosition(this.frameCount);
    this.frameCount++;

    this.renderer.render(this.viewer.scene, this.viewer.camera);
    const buffer = this.canvas.toBuffer("image/png");

    try {
      await this.videoProcessor.processFrame(buffer);

      if (this.frameCount % this.frameCountInterval === 0) {
        await this.writeFrameCount();
      }

      console.log(`Processed frame: ${this.frameCount}`);
    } catch (err) {
      console.error(`Error processing frame: ${err}`);
      throw err;
    }
  }

  async captureCardinalView(direction) {
    const angle = {
      north: Math.PI, // Looking from south to north
      east: Math.PI * 1.5, // Looking from west to east
      south: 0, // Looking from north to south
      west: Math.PI * 0.5, // Looking from east to west
    }[direction];

    if (angle === undefined) {
      throw new Error(`Invalid direction: ${direction}`);
    }

    // Position camera for the cardinal view
    const x = this.lookAt.x + this.cameraDistance * Math.cos(angle);
    const z = this.lookAt.z + this.cameraDistance * Math.sin(angle);

    this.viewer.camera.position.set(x, this.position.y, z);
    this.viewer.camera.lookAt(this.lookAt.x, this.lookAt.y, this.lookAt.z);

    // Ensure view is updated
    if (this.pendingUpdate) {
      this.viewer.update();
      this.pendingUpdate = false;
    }

    // Render and save with direction-specific filename
    this.renderer.render(this.viewer.scene, this.viewer.camera);
    const filename = path.join(this.outputDir, `${direction}side_capture.png`);

    const buffer = this.canvas.toBuffer("image/png");
    try {
      await fs.writeFile(filename, buffer);
      console.log(`Saved cardinal view: ${filename}`);
    } catch (err) {
      console.error(`Error saving cardinal view: ${err}`);
    }
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
    this.lastExecutionTime = 0;
    this.commandCount = 0;
  }

  waitForBlockUpdate(x, y, z) {
    return new Promise((resolve) => {
      const handler = (oldBlock, newBlock) => {
        const pos = newBlock.position;
        if (pos.x === x && pos.y === y && pos.z === z) {
          bot.removeListener("blockUpdate", handler);
          resolve();
        }
      };
      bot.on("blockUpdate", handler);
      setTimeout(() => {
        bot.removeListener("blockUpdate", handler);
        resolve();
      }, 1000);
    });
  }

  async add(command, coordinates = null) {
    const promise = new Promise((resolve, reject) => {
      this.queue.push({ command, coordinates, resolve, reject });
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
      const { command, coordinates, resolve, reject } = this.queue.shift();

      const now = Date.now();
      const timeSinceLastExecution = now - this.lastExecutionTime;
      if (timeSinceLastExecution < this.DELAY) {
        await new Promise((resolve) =>
          setTimeout(resolve, this.DELAY - timeSinceLastExecution),
        );
      }

      try {
        console.log(command);
        await bot.chat(command);
        this.lastExecutionTime = Date.now();

        if (coordinates) {
          this.commandCount++;

          if (this.commandCount >= COMMANDS_PER_FRAME) {
            this.commandCount = 0;
            await this.waitForBlockUpdate(
              coordinates.x,
              coordinates.y,
              coordinates.z,
            );
            await new Promise((resolve) => setTimeout(resolve, 16));

            // we take two frames per command set
            await recorder.captureFrame();
            await recorder.captureFrame();
          }
        }

        resolve();
      } catch (err) {
        reject(err);
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

class StreamingVideoProcessor {
  constructor(options = {}) {
    this.outputDir = options.outputDir || path.join(OUTDIR, "processed");
    this.fps = options.fps || 30;
    this.quality = options.quality || 23;
    this.outputFileName = options.outputFileName || "timelapse.mp4";
    this.ffmpegProcess = null;
    this.frameCount = 0;
    this.processingError = null;
  }

  async createOutputDir() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
      console.log(`Created output directory: ${this.outputDir}`);
    } catch (err) {
      console.error("Error creating output directory:", err);
      throw err;
    }
  }

  async startFFmpeg() {
    const outputPath = path.join(this.outputDir, this.outputFileName);
    console.log(`Starting FFmpeg process, output file: ${outputPath}`);

    const args = [
      "-y",
      "-f",
      "image2pipe",
      "-c:v",
      "png",
      "-r",
      this.fps.toString(),
      "-i",
      "-",
      "-c:v",
      "libx264",
      "-preset",
      "slow",
      "-crf",
      this.quality.toString(),
      "-profile:v",
      "high",
      "-pix_fmt",
      "yuv420p",
      "-movflags",
      "+faststart",
      outputPath,
    ];

    console.log("FFmpeg command:", "ffmpeg", args.join(" "));

    return new Promise((resolve, reject) => {
      const { spawn } = require("child_process");
      this.ffmpegProcess = spawn("ffmpeg", args);

      let ffmpegOutput = "";

      this.ffmpegProcess.stderr.on("data", (data) => {
        const output = data.toString();
        ffmpegOutput += output;
        console.log(`FFmpeg: ${output}`);
      });

      this.ffmpegProcess.on("error", (err) => {
        console.error("FFmpeg process error:", err);
        this.processingError = err;
        reject(err);
      });

      this.ffmpegProcess.on("close", (code) => {
        console.log(`FFmpeg process closed with code ${code}`);
        console.log("Full FFmpeg output:", ffmpegOutput);

        if (code === 0) {
          console.log("FFmpeg process completed successfully");
          resolve();
        } else {
          const error = new Error(
            `FFmpeg process exited with code ${code}\nOutput: ${ffmpegOutput}`,
          );
          this.processingError = error;
          reject(error);
        }
      });

      this.ffmpegProcess.stdin.on("error", (err) => {
        console.error("FFmpeg stdin error:", err);
        this.processingError = err;
        reject(err);
      });

      // Check if FFmpeg is actually running
      if (!this.ffmpegProcess.pid) {
        const error = new Error("Failed to start FFmpeg process");
        this.processingError = error;
        reject(error);
      }

      resolve();
    });
  }

  async processFrame(buffer) {
    if (this.processingError) {
      throw new Error(
        `Cannot process frame: previous error occurred: ${this.processingError.message}`,
      );
    }

    if (!this.ffmpegProcess) {
      console.log("Starting new FFmpeg process...");
      await this.createOutputDir();
      await this.startFFmpeg();
    }

    return new Promise((resolve, reject) => {
      try {
        const canWrite = this.ffmpegProcess.stdin.write(buffer);

        if (canWrite) {
          this.frameCount++;
          console.log(`Successfully wrote frame ${this.frameCount}`);
          resolve();
        } else {
          console.log("Buffer full, waiting for drain...");
          this.ffmpegProcess.stdin.once("drain", () => {
            this.frameCount++;
            console.log(
              `Successfully wrote frame ${this.frameCount} after drain`,
            );
            resolve();
          });
        }
      } catch (err) {
        console.error("Error writing frame:", err);
        this.processingError = err;
        reject(err);
      }
    });
  }

  async finish() {
    if (this.processingError) {
      throw new Error(
        `Cannot finish: previous error occurred: ${this.processingError.message}`,
      );
    }

    if (this.ffmpegProcess) {
      console.log("Finishing video processing...");

      return new Promise((resolve, reject) => {
        try {
          this.ffmpegProcess.stdin.end();
          console.log("FFmpeg stdin closed");

          this.ffmpegProcess.on("close", (code) => {
            if (code === 0) {
              console.log(
                `Video processing completed successfully. Total frames: ${this.frameCount}`,
              );
              resolve();
            } else {
              const error = new Error(
                `FFmpeg process exited with code ${code}`,
              );
              this.processingError = error;
              reject(error);
            }
          });
        } catch (err) {
          console.error("Error finishing video:", err);
          this.processingError = err;
          reject(err);
        }
      });
    } else {
      console.warn("No FFmpeg process to finish");
      return Promise.resolve();
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

  try {
    // Add minecraft: namespace if not present
    const fullBlockType = blockType.includes(":")
      ? blockType
      : `minecraft:${blockType}`;
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

    await commandQueue.add(command, { x, y, z });
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

  try {
    // Add minecraft: namespace if not present
    const fullBlockType = blockType.includes(":")
      ? blockType
      : `minecraft:${blockType}`;
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

      command += ` [${options.mode}]`;

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

    await commandQueue.add(command, {
      x: Math.max(x1, x2),
      y: Math.max(y1, y2),
      z: Math.max(z1, z2),
    });

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

const bot = mineflayer.createBot({
  host: HOST,
  port: PORT,
  version: VERSION,
  username: USERNAME,
});

const commandQueue = new CommandQueue();
const coordinateTracker = new CoordinateTracker();
const recorder = new Recorder();

function calculateCenter(boundingBox) {
  return new Vec3(
    (boundingBox.min.x + boundingBox.max.x) / 2,
    (boundingBox.min.y + boundingBox.max.y) / 2,
    (boundingBox.min.z + boundingBox.max.z) / 2,
  );
}

function calculateCameraPosition(boundingBox) {
  // First calculate the center as before
  const center = {
    x: (boundingBox.min.x + boundingBox.max.x) / 2,
    y: (boundingBox.min.y + boundingBox.max.y) / 2,
    z: (boundingBox.min.z + boundingBox.max.z) / 2,
  };

  const diffX = center.x - boundingBox.max.x;
  const diffY = center.y - boundingBox.max.y;
  const diffZ = center.z - boundingBox.max.z;

  const diagonal = Math.sqrt(diffX * diffX + diffY * diffY + diffZ * diffZ);
  const targetDistanceFromCenter = diagonal + 5;

  const angleInRadians = Math.PI / 4;

  // Calculate the vertical component (y-axis)
  const verticalDistance = targetDistanceFromCenter * Math.sin(angleInRadians);

  // Calculate the horizontal component (in the x-z plane)
  const horizontalDistance =
    targetDistanceFromCenter * Math.cos(angleInRadians);

  return {
    position: new Vec3(
      center.x,
      center.y + verticalDistance,
      center.z + horizontalDistance,
    ),
    lookAt: new Vec3(center.x, center.y, center.z),
    cameraDistance: targetDistanceFromCenter,
  };
}

// Update the spawn handler
bot.once("spawn", async () => {
  try {
    const startingCameraPosition = calculateCameraPosition(summary.boundingBox);

    await commandQueue.add(
      `/tp builder ${startingCameraPosition.lookAt.x} ${startingCameraPosition.lookAt.y} ${startingCameraPosition.lookAt.z}`,
    );
    await commandQueue.waitForAll();

    await bot.setControlState("jump", true);

    console.log("Waiting 10 seconds for blocks to load");
    await new Promise((resolve) => setTimeout(resolve, 1000 * 10));
    console.log("Blocks should be loaded. Starting!");

    await recorder.init(
      bot,
      startingCameraPosition.position,
      startingCameraPosition.lookAt,
      startingCameraPosition.cameraDistance,
    );

    // 1 second of initial video
    for (let i = 0; i < 30; i++) {
      await recorder.captureFrame();
      // Small delay between frames to prevent overwhelming the system
      await new Promise((resolve) => setTimeout(resolve, 50));
    }

    for (const command of commandList) {
      if (command.kind === "fill") {
        commandQueue.add(
          command.command,
          command.coordinates[0].x,
          command.coordinates[0].y,
          command.coordinates[0].z,
          command.coordinates[1].x,
          command.coordinates[1].y,
          command.coordinates[1].z,
        );
      } else {
        commandQueue.add(
          command.command,
          command.coordinates.x,
          command.coordinates.y,
          command.coordinates.z,
        );
      }
    }
    await commandQueue.waitForAll();

    // After building is complete, capture a full rotation
    console.log("Build complete, starting rotation capture...");

    // Calculate how many frames we need for a full rotation
    const framesForFullRotation = recorder.totalRotationFrames;

    // Capture frames for the full rotation
    for (let i = 0; i < framesForFullRotation; i++) {
      await recorder.captureFrame();
      // Small delay between frames to prevent overwhelming the system
      await new Promise((resolve) => setTimeout(resolve, 50));
    }

    console.log("Rotation capture complete, capturing cardinal views...");

    // Capture cardinal direction views
    const directions = ["north", "east", "south", "west"];
    for (const direction of directions) {
      await recorder.captureCardinalView(direction);
      // Small delay between captures
      await new Promise((resolve) => setTimeout(resolve, 100));
    }

    console.log("Cardinal views captured, processing video...");

    await commandQueue.waitForAll();

    // Add video processing after everything else is done
    console.log("finalizing video...");
    await recorder.videoProcessor.finish();
    console.log("Video processing completed");

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

const summary = {};

const commandList = [];
