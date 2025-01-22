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

INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'gpt-4o-2024-11-20', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'gemini-2.0-flash-exp', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'grok-2-1212', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'deepseek-r1', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (1, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'claude-3-5-sonnet-20241022'), 'ANTHROPIC_SDK', '"{\"model\": \"claude-3-5-sonnet-20241022\", \"max_tokens\": 4000}"', 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (2, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gpt-4o-2024-11-20'), 'OPENAI_SDK', '{"model": "gpt-4o-2024-11-20", "max_tokens": 4000}', 'OpenAI', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (3, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'llama-3.1-405b-instruct'), 'OPENROUTER_SDK', '"{\"model\": \"meta-llama/llama-3.1-405b-instruct\", \"max_tokens\": 4000}"', 'openrouter meta-llama/llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (4, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gemini-2.0-flash-exp'), 'GEMINI_SDK', '"{\"model\": \"gemini-2.0-flash-exp\", \"max_tokens\": 8192}"', 'Google', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (5, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'grok-2-1212'), 'GROK_SDK', '{"model": "grok-2-1212", "max_tokens": 131072}', 'Grok', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (6, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'deepseek-r1'), 'DEEPSEEK_SDK', '{"model": "deepseek-reasoner", "max_tokens": 8000}', 'DeepSeek', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.prompt (id, created_by, name, build_specification, active) VALUES (1, (select id from auth.user where username = 'SYSTEM'), 'Structure: a small wooden platform', 'a small wooden platform', true) ON CONFLICT DO NOTHING;

INSERT INTO auth.user (username)
VALUES
    ('huntcsg'),
    ('Isaac');

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
     (select id from auth.user where username = 'IsaacGemal'),
     'f89ba90d514fbeefd5d2115b3f49fd7520480d9f94937a1e4794598aa124450a'
    );

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
