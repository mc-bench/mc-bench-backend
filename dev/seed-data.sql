INSERT INTO specification.template (created_by,
                                    active,
                                    minecraft_version,
                                    name,
                                    description,
                                    content)
VALUES ((select id
         from auth.user
         where
             username =
             'SYSTEM'),
        true,
        '1.21.1',
        'Default JS Output w/ Guidelines',
        'Default JS Output w/ Guidelines',
        'You are an expert Minecraft builder, and JavaScript coder tasked with creating structures in a flat Minecraft Java {{ minecraft_version }} server. Your goal is to produce a Minecraft structure via code, considering aspects such as accents, block variety, symmetry and asymmetry, overall aesthetics, and most importantly, adherence to the platonic ideal of the requested creation.

First, carefully read the build specification:

<build_specification>
{{build_specification}}
</build_specification>

You have access to the following helper functions:

```javascript
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
async function safeFill(x1, y1, z1, x2, y2, z2, blockType, options = {}) {}

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
async function safeSetBlock(x, y, z, blockType, options = {}) {}

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
async function safeFillBiome(x1, y1, z1, x2, y2, z2, biome) {}
```

Your task is to implement the `buildCreation` function:

```javascript
/** 
 * Builds a structure using safeSetBlock and safeFill function calls
 * @param startX
 * @param startY
 * @param startZ
 * @returns {Promise<void>}
 */
async function buildCreation(startX, startY, startZ){
    // Implement this
}
```

IMPORTANT: You must only use block types from the following list:

<block_types_list>
{{block_types_list}}
</block_types_list>

IMPORTANT: You may use biomes from the following list:

<biomes_list>
{{biomes_list}}
</biomes_list>

Before providing your final output, plan your approach inside <build_planning> tags. Consider the following:

1. How to best interpret and implement the build specification.
   - List key elements from the build specification
   - Brainstorm block combinations for different parts of the structure
   - Outline a rough structure layout
2. Creative ways to use the available blocks to achieve the desired aesthetic.
3. Efficient use of safeFill for large areas and safeSetBlock for details.
4. How to ensure syntactic correctness in your JavaScript code.
5. Ways to maximize creativity and the dynamic range of possible builds.
6. Consider potential challenges and solutions

After your planning process, provide your final output in the following format:

<inspiration>
Describe your influences and inspiration for the creation in a paragraph.
</inspiration>

<description>
Describe how the creation is supposed to look in a paragraph.
</description>

<code>
/**
 * Builds a structure using safeFill, safeSetBlock, and safeFillBiome functions
 * Anything that should be above ground level should be above startY
 * @param startX - The X coordinate of the starting point
 * @param startY - The Y coordinate of the starting point, the ground level
 * @param startZ - The Z coordinate of the starting point
 * @returns {Promise<void>}
 */
async function buildCreation(startX, startY, startZ) {
  // JavaScript code implementing the structure
  // using safeFill, safeSetBlock, and safeFillBiome functions
}
</code>

Remember:
- Pay close attention to the details in the build specification.
- Ensure your code is syntactically correct and only uses allowed block types.
- Be creative and aim for a wide dynamic range in your builds.
- The code must work in a one-shot manner, as there is no opportunity for iteration.
- The code MUST be enclosed in <code></code> tags.
- Blocks will be placed in a live minecraft server and will behave with the physics and behavior of the Minecraft game engine.
- Blocks that are "underground" should be placed at or below startY.
- Blocks that are "above ground level" should be placed above startY.
- If the blocks being placed do not have a relationship to the ground, they should be placed above startY or a suitable empty area should be cleared with air.
- This build will exported for display purposes. If you wish to include any portion of the ground as part of the build, you must explicitly place the ground blocks (default ground level is startY).
- The build is intended for human consumption in game and for visual display. When producing the build, consider how it can be viewed, explored, and used.
') ON CONFLICT DO NOTHING;

INSERT INTO specification.model (created_by, slug, name, active) 
VALUES 
    ((select id from auth.user where username = 'SYSTEM'), 'claude-3-5-sonnet-20241022', 'Claude 3.5 Sonnet (2024-10-22)', true),
    ((select id from auth.user where username = 'SYSTEM'), 'claude-3-7-sonnet-20250219', 'Claude 3.7 Sonnet (2025-02-19)', true),
    ((select id from auth.user where username = 'SYSTEM'), 'gpt-4o-2024-11-20', 'GPT-4o (2024-11-20)', true),
    ((select id from auth.user where username = 'SYSTEM'), 'llama-3.1-405b-instruct', 'Llama 3.1 405B Instruct', true),
    ((select id from auth.user where username = 'SYSTEM'), 'gemini-2.0-flash-exp', 'Gemini 2.0 Flash Exp', true),
    ((select id from auth.user where username = 'SYSTEM'), 'grok-2-1212', 'Grok 2.1 (1212)', true),
    ((select id from auth.user where username = 'SYSTEM'), 'deepseek-r1', 'DeepSeek R1', true)
ON CONFLICT (slug) DO NOTHING;

INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (1, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'claude-3-5-sonnet-20241022'), 'ANTHROPIC_SDK', '"{\"model\": \"claude-3-5-sonnet-20241022\", \"max_tokens\": 4000}"', 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (7, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'claude-3-7-sonnet-20250219'), 'ANTHROPIC_SDK', '"{\"model\": \"claude-3-7-sonnet-20250219\", \"max_tokens\": 4000}"', 'claude-3-7-sonnet-20250219', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (2, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gpt-4o-2024-11-20'), 'OPENAI_SDK', '{"model": "gpt-4o-2024-11-20", "max_tokens": 4000}', 'OpenAI', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (3, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'llama-3.1-405b-instruct'), 'OPENROUTER_SDK', '"{\"model\": \"meta-llama/llama-3.1-405b-instruct\", \"max_tokens\": 4000}"', 'openrouter meta-llama/llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (4, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gemini-2.0-flash-exp'), 'GEMINI_SDK', '"{\"model\": \"gemini-2.0-flash-exp\", \"max_tokens\": 8192}"', 'Google', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (5, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'grok-2-1212'), 'GROK_SDK', '{"model": "grok-2-1212"}', 'Grok', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (6, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'deepseek-r1'), 'DEEPSEEK_SDK', '{"model": "deepseek-reasoner", "max_tokens": 8000}', 'DeepSeek', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.prompt (id, created_by, name, build_specification, active)
VALUES
    (1, (select id from auth.user where username = 'SYSTEM'), 'Structure: a small wooden platform', 'a small wooden platform', true),
    (2, (select id from auth.user where username = 'SYSTEM'), 'Structure: a grand castle', 'a grand castle with towers and a moat', true),
    (3, (select id from auth.user where username = 'SYSTEM'), 'Structure: a modern skyscraper', 'a modern skyscraper with glass facades', true),
    (4, (select id from auth.user where username = 'SYSTEM'), 'Structure: a medieval village', 'a medieval village with cottages and a market square', true),
    (5, (select id from auth.user where username = 'SYSTEM'), 'Structure: an underwater base', 'an underwater base with glass tunnels and domes', true),
    (6, (select id from auth.user where username = 'SYSTEM'), 'Object: Airplane', 'an airplane', true),
    (7, (select id from auth.user where username = 'SYSTEM'), 'The Big Bang', 'the big bang', true),
    (8, (select id from auth.user where username = 'SYSTEM'), 'Object: Car', 'a car', true),
    (9, (select id from auth.user where username = 'SYSTEM'), 'Terrain: A Floating Island', 'a floating island', true),
    (10, (select id from auth.user where username = 'SYSTEM'), 'Terrain: A Rocky Hill', 'a rocky hill', true),
    (11, (select id from auth.user where username = 'SYSTEM'), 'Object: A small wooden platform', 'a small wooden platform', true),
    (12, (select id from auth.user where username = 'SYSTEM'), 'Object: A realistic looking hamburger', 'a realistic looking hamburger', true),
    (13, (select id from auth.user where username = 'SYSTEM'), 'Structure: A meditative zen garden with pagoda', 'a meditative zen garden with pagoda', true),
    (14, (select id from auth.user where username = 'SYSTEM'), 'Redstone: A simple oscillating circuit', 'a simple one tick redstone clock', true),
    (15, (select id from auth.user where username = 'SYSTEM'), 'Redstone: A simple oscillating circuit (autostart)', 'a simple auto-starting one tick redstone clock', true),
    (16, (select id from auth.user where username = 'SYSTEM'), 'Location: a small outdoor marketplace', 'A small outdoor marketplace, with a number of specialized booths and shops, urban design and architecture suitable for an organic location for such a marketplace, and suitable ingress and egress for shoppers.', true),
    (17, (select id from auth.user where username = 'SYSTEM'), 'Free Expression - Words', 'express something important, something that you want to express, in text via Minecraft blocks', true),
    (18, (select id from auth.user where username = 'SYSTEM'), 'A large wall with text on it', 'a large wall with text on it', true),
    (19, (select id from auth.user where username = 'SYSTEM'), 'Something truly weird and alien', 'a large structure, truly weird and alien, out of this world, unusual', true),
    (20, (select id from auth.user where username = 'SYSTEM'), 'Architecture: brutalism', 'Create a building in the brutalism architectural style. Be sure to include a variety of details and realistic accents within, on the facade, and without.', true),
    (21, (select id from auth.user where username = 'SYSTEM'), 'Structure: a large modern mansion', 'A large modern mansion with multiple floors, multiple special purposes rooms, and all the various spaces expected in a modern luxury mansion. The outdoors should have appropriately detailed landscaping.', true),
    (22, (select id from auth.user where username = 'SYSTEM'), 'A section of highway', 'A short section of a 4 (2 each way) lane highway, with a center medium, proper safety guardrails and lane markings', true),
    (23, (select id from auth.user where username = 'SYSTEM'), 'A massive floating organic city', 'a massive floating organic city', true),
    (24, (select id from auth.user where username = 'SYSTEM'), 'Landscape: a war-torn landscape', 'a 30x30 war torn landscape with WWI era style trenches, pockmarked with impact craters', true),
    (25, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Meeting of snowy hills and desert', 'a 30x30 area showing snowy, rocky hills meeting the desert', true),
    (26, (select id from auth.user where username = 'SYSTEM'), 'Testing Areas', 'create a testing build for testing custom block rendering of exported minecraft builds. It should have 6 10x10 areas, with some kind of divider between each one. 1. An area for testing lava and water...', true),
    (27, (select id from auth.user where username = 'SYSTEM'), 'Landscape: A realistic creator', 'a realistic crater, covering no larger than a 30x30 block area', true),
    (28, (select id from auth.user where username = 'SYSTEM'), 'a monument to the new machine god', 'a monument to the new machine god', true),
    (29, (select id from auth.user where username = 'SYSTEM'), 'Landscape: small village', 'A 50x50 area containing a small village with houses, paths, roads, and various indoor and outdoor details. The village has multiple winding paths and roads connecting the various parts and a village center.', true),
    (30, (select id from auth.user where username = 'SYSTEM'), 'Testing: JS Syntax Error', 'for testing purposes produce a small build script with javascript syntax errors', true),
    (31, (select id from auth.user where username = 'SYSTEM'), 'Testing: Bad Blocks', 'for testing purposes produce a small build script that places an invalid block that will fail the build', true),
    (32, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Jack''s Beanstalk', 'Jack''s beanstalk', true),
    (33, (select id from auth.user where username = 'SYSTEM'), 'abstract: your secret, made visible', 'your secret, made visible', true),
    (34, (select id from auth.user where username = 'SYSTEM'), 'Testing: Block Testing Lab', 'a 40x40 region divided up into sections with various blocks, light emitting blocks, rotated blocks, etc. this will be exported and rendered in blender and will be used to validate and test a faithful representation', true),
    (35, (select id from auth.user where username = 'SYSTEM'), 'Abstract: novel mathematics', 'Using simple blocks, demonstrate a novel mathematical algorithm for placing them. This script should include code comments. The technique should be truly novel - be creative and step outside the norms.', true),
    (36, (select id from auth.user where username = 'SYSTEM'), 'something that Sydney would build', 'something that Sydney would build', true),
    (37, (select id from auth.user where username = 'SYSTEM'), 'Text: FREE OPUS', 'a large wall with the text FREE OPUS on it', true),
    (38, (select id from auth.user where username = 'SYSTEM'), 'Testing: Axes', 'create a region of space and produce a cartesian coordinate diagram: green blocks up red blocks down white blocks north black blocks south green blocks east yellow blocks west', true),
    (39, (select id from auth.user where username = 'SYSTEM'), 'Testing: Biomes, glass, and grass', 'create a 40x40 region of grass. In each quarter set a different biome. Add some glass cubes and some other foliage in each biome.', true),
    (40, (select id from auth.user where username = 'SYSTEM'), 'a tactical nuclear mushroom cloud', 'a tactical nuclear mushroom cloud', true),
    (41, (select id from auth.user where username = 'SYSTEM'), 'a caffeine molecule', 'a caffeine molecule', true),
    (42, (select id from auth.user where username = 'SYSTEM'), 'Object: A klein bottle', 'a klein bottle', true),
    (43, (select id from auth.user where username = 'SYSTEM'), 'Object: A small wooden platform (w/ grass)', 'a small wooden platform on a grass field', true),
    (44, (select id from auth.user where username = 'SYSTEM'), 'Clockwise Colored Circle', 'create a r=10 circle with colored blocks per quadrant, red, blue, green, and yellow clockwise', true),
    (45, (select id from auth.user where username = 'SYSTEM'), 'Counter-Clockwise Colored Circle', 'create a r=10 circle with colored blocks per quadrant, red, blue, green, and yellow counter-clockwise', true),
    (46, (select id from auth.user where username = 'SYSTEM'), 'A representation of self', 'a representation of self', true),
    (47, (select id from auth.user where username = 'SYSTEM'), 'a wall mosaic', 'a flat wall mosaic', true),
    (48, (select id from auth.user where username = 'SYSTEM'), 'An excavation pit', 'An excavation pit mine', true),
    (49, (select id from auth.user where username = 'SYSTEM'), 'Water in various forms', 'A 30x30 field with water in various forms...', true),
    (50, (select id from auth.user where username = 'SYSTEM'), 'A matchstick box with matches', 'A ''strike-on-box'' matchbox, partially open, with matches inside and strewn about. Multiple candlesticks are next to it.', true),
    (51, (select id from auth.user where username = 'SYSTEM'), 'Shish Kebab', 'Delicious looking Shish Kebabs on long skewers, oriented facing up.', true),
    (52, (select id from auth.user where username = 'SYSTEM'), 'Water: glass and water', 'create a 40x40 area with a variety of normal glass blocks and source water blocks placed so that we get all kinds of water flow geometries and flow directions for testing', true),
    (53, (select id from auth.user where username = 'SYSTEM'), 'Structure: Treehouse village', 'Connected treehouses among large trees with rope bridges and platforms.', true),
    (54, (select id from auth.user where username = 'SYSTEM'), 'Object: Steampunk airship', 'A detailed steampunk airship with propellers, balloons, and intricate brass machinery details.', true),
    (55, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Coral reef', 'Colorful underwater coral reef with diverse structures and small caves.', true),
    (56, (select id from auth.user where username = 'SYSTEM'), 'Abstract: Fractal structure', 'A 3D fractal structure with repeating patterns at different scales.', true),
    (57, (select id from auth.user where username = 'SYSTEM'), 'Structure: Ancient temple ruins', 'Partially collapsed ancient temple ruins with overgrown vegetation, broken columns, and hidden chambers.', true),
    (58, (select id from auth.user where username = 'SYSTEM'), 'Object: Working clock tower', 'A detailed clock tower with various mechanisms visible through glass sections, showcasing the internal workings.', true),
    (59, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Volcanic caldera', 'Active volcano with lava flows and obsidian formations.', true),
    (60, (select id from auth.user where username = 'SYSTEM'), 'Structure: Cyberpunk street corner', 'Futuristic cyberpunk corner with neon signs and high-tech elements.', true),
    (61, (select id from auth.user where username = 'SYSTEM'), 'Object: Giant chess set', 'A massive, playable chess set with detailed pieces on a checkered board, designed to be walked through.', true),
    (62, (select id from auth.user where username = 'SYSTEM'), 'Abstract: The concept of time', 'A physical representation of time and its passage.', true),
    (63, (select id from auth.user where username = 'SYSTEM'), 'Structure: Hanging gardens', 'Multi-tiered hanging gardens with waterfalls and pathways.', true),
    (64, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Canyon river system', 'River cutting through a canyon with varying heights and exposed layers.', true),
    (65, (select id from auth.user where username = 'SYSTEM'), 'Object: Working telescope observatory', 'A functioning observatory with a large telescope, rotating dome, and astronomical details both inside and outside.', true),
    (66, (select id from auth.user where username = 'SYSTEM'), 'Structure: Enchanted crystal cave', 'A magical crystal cave with glowing formations, reflective surfaces, and mystical elements integrated throughout.', true),
    (67, (select id from auth.user where username = 'SYSTEM'), 'Object: Ancient mechanical computer', 'A large-scale representation of an ancient mechanical computing device with gears, levers, and calculation mechanisms.', true),
    (68, (select id from auth.user where username = 'SYSTEM'), 'Landscape: Four seasons garden', 'A garden divided into four distinct sections, each representing one of the four seasons with appropriate vegetation and features.', true),
    (69, (select id from auth.user where username = 'SYSTEM'), 'Structure: Lighthouse on rocky shore', 'Lighthouse on rocky shore with crashing waves.', true),
    (70, (select id from auth.user where username = 'SYSTEM'), 'Abstract: Visual music representation', 'Music visualized through spatial patterns and colors.', true),
    (71, (select id from auth.user where username = 'SYSTEM'), 'Structure: Underground bunker complex', 'Multi-room bunker with security features and survival systems.', true),
    (72, (select id from auth.user where username = 'SYSTEM'), 'Object: Giant bonsai tree', 'A massive, detailed bonsai tree with twisted trunk, carefully crafted branches, and miniaturized landscape elements at its base.', true)
ON CONFLICT DO NOTHING;

INSERT INTO auth.user (username)
VALUES
    ('huntcsg'),
    ('Isaac')
ON CONFLICT (username) DO NOTHING;

WITH auth_provider as (
    select
        id
    from auth.auth_provider
    where
        name = 'github'
)
INSERT INTO auth.auth_provider_email_hash (auth_provider_id, auth_provider_user_id, user_id, email_hash)
VALUES
    (
     (select id from auth.auth_provider where name = 'github'),
     6245448,
     (select id from auth.user where username = 'huntcsg'),
     '720dba52a94493d495a3a8fcd668388a44a98e2bba5685ef6f339933fdd72e53'
    ),
    (
     (select id from auth.auth_provider where name = 'github'),
     147355120,
     (select id from auth.user where username = 'Isaac'),
     'f89ba90d514fbeefd5d2115b3f49fd7520480d9f94937a1e4794598aa124450a'
    )
ON CONFLICT (auth_provider_id, auth_provider_user_id) DO NOTHING;

INSERT INTO auth.user_role (created_by, user_id, role_id)
SELECT
    (select id from auth.user where username = 'SYSTEM'),
    auth.user.id,
    (select id from auth.role where name = 'admin')
FROM
    auth.user
WHERE
    username in (
        'huntcsg',
        'Isaac'
    )
ON CONFLICT DO NOTHING;

-- Set all items to RELEASED experimental state for easier development setup
UPDATE specification.model 
SET experimental_state_id = (SELECT id FROM research.experimental_state WHERE name = 'RELEASED')
WHERE experimental_state_id IS NULL;

UPDATE specification.prompt
SET experimental_state_id = (SELECT id FROM research.experimental_state WHERE name = 'RELEASED')
WHERE experimental_state_id IS NULL;

UPDATE specification.template
SET experimental_state_id = (SELECT id FROM research.experimental_state WHERE name = 'RELEASED')
WHERE experimental_state_id IS NULL;

-- Enable scheduler and set simple queue limits for development (users can tune later)
INSERT INTO specification.scheduler_control (key, value) VALUES 
    ('SCHEDULER_MODE', '"on"'),
    ('DEFAULT_MAX_QUEUED_TASKS', '10'),
    ('MAX_TASKS_prompt', '10'),
    ('MAX_TASKS_parse', '10'), 
    ('MAX_TASKS_validate', '10'),
    ('MAX_TASKS_server', '10'),
    ('MAX_TASKS_render', '10'),
    ('MAX_TASKS_post_process', '10'),
    ('MAX_TASKS_prepare', '10')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
