INSERT INTO specification.template (created_by,
                                    active,
                                    name,
                                    description,
                                    content)
VALUES ((select id
         from auth.user
         where
             username =
             'SYSTEM'),
        true,
        'Default JS Output w/ Guidelines',
        'Default JS Output w/ Guidelines',
        'You are an expert Minecraft architect, designer, and JavaScript coder tasked with creating structures in a flat Minecraft Java 1.20.1 server. Your goal is to produce a Minecraft structure via code, considering aspects such as accents, block variety, symmetry and asymmetry, overall aesthetics, and most importantly, adherence to the platonic ideal of the requested creation.

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
async function buildCreation(startX, startY, startZ) {
  // JavaScript code implementing the structure
  // using safeFill and safeSetBlock functions
}
</code>

Remember:
- Pay close attention to the details in the build specification.
- Ensure your code is syntactically correct and only uses allowed block types.
- Be creative and aim for a wide dynamic range in your builds.
- The code must work in a one-shot manner, as there is no opportunity for iteration.
- The code MUST be enclosed in <code></code> tags.') ON CONFLICT DO NOTHING;

INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'gpt-4o-2024-11-20', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'gemini-2.0-flash-exp', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (1, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'claude-3-5-sonnet-20241022'), 'ANTHROPIC_SDK', '"{\"model\": \"claude-3-5-sonnet-20241022\", \"max_tokens\": 4000}"', 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (2, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gpt-4o-2024-11-20'), 'OPENAI_SDK', '{"model": "gpt-4o-2024-11-20", "max_tokens": 4000}', 'OpenAI', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (3, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'llama-3.1-405b-instruct'), 'OPENROUTER_SDK', '"{\"model\": \"meta-llama/llama-3.1-405b-instruct\", \"max_tokens\": 4000}"', 'openrouter meta-llama/llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (4, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gemini-2.0-flash-exp'), 'GEMINI_SDK', '"{\"model\": \"gemini-2.0-flash-exp\", \"max_tokens\": 8192}"', 'Google', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.prompt (id, created_by, name, build_specification, active) VALUES (1, (select id from auth.user where username = 'SYSTEM'), 'Structure: a small wooden platform', 'a small wooden platform', true) ON CONFLICT DO NOTHING;
