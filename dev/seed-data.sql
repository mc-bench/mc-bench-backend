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
        e'You are in control of a bot in a flat minecraft server (Java 1.20.4). You are an expert architect and designer and python coder.

      You must produce a minecraft structure via code, being sure to consider accents, block variety, symmetry and asymmetry, overall aesthetics and most critically adherence to the platonic ideal of the requested creation.

      You will be provided with two helper functions `safeFill` and `safeSetBlock` which will in turn make `/fill` and `/setblock` calls.
      You must implement `buildCreation`.

      See below for the api for `safeSetBlock`, `safeFill`, and `buildCreation`
      ```
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

      Creation Specification: {{ build_specification }}

      Please describe your influences in a paragraph, then describe in a paragraph how the creation is supposed to look, and then finally, you must implement buildCreation in high quality, error free javascript code.

      Please use these tags for the three sections.

      <inspiration></inspiration>
      <description></description>
      <code></code>

      Reminder: All code must be syntactically correct. Be aware of common errors like missing ending parenthesis symbols, etc.') ON CONFLICT DO NOTHING;

INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'gpt-4o-2024-11-20', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.model (created_by, slug, active) VALUES ((select id from auth.user where username = 'SYSTEM'), 'llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;

INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (1, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'claude-3-5-sonnet-20241022'), 'ANTHROPIC_SDK', '"{\"model\": \"claude-3-5-sonnet-20241022\", \"max_tokens\": 4000}"', 'claude-3-5-sonnet-20241022', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (2, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'gpt-4o-2024-11-20'), 'OPENAI_SDK', '{"model": "gpt-4o-2024-11-20", "max_tokens": 4000}', 'OpenAI', true) ON CONFLICT DO NOTHING;
INSERT INTO specification.provider (id, created_by, model_id, provider_class, config, name, is_default) VALUES (3, (select id from auth.user where username = 'SYSTEM'), (select id from specification.model where slug = 'llama-3.1-405b-instruct'), 'OPENROUTER_SDK', '"{\"model\": \"meta-llama/llama-3.1-405b-instruct\", \"max_tokens\": 4000}"', 'openrouter meta-llama/llama-3.1-405b-instruct', true) ON CONFLICT DO NOTHING;


INSERT INTO specification.prompt (id, created_by, name, build_specification, active) VALUES (1, (select id from auth.user where username = 'SYSTEM'), 'Structure: a small wooden platform', 'a small wooden platform', true) ON CONFLICT DO NOTHING;
