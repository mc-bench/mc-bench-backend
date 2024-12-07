class PERM:
    class PROMPT:
        READ = "prompt:read"
        WRITE = "prompt:write"
        ADMIN = "prompt:admin"

    class TEMPLATE:
        READ = "template:read"
        WRITE = "template:write"
        ADMIN = "template:admin"

    class MODEL:
        READ = "model:read"
        WRITE = "model:write"
        ADMIN = "model:admin"

    class GENERATION:
        READ = "generation:read"
        WRITE = "generation:write"
        ADMIN = "generation:admin"

    class RUN:
        READ = "run:read"
        WRITE = "run:write"
        ADMIN = "run:admin"
        PROGRESS_WRITE = "run:progress:write"
