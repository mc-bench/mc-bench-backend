class PERM:
    class PROMPT:
        READ = "prompt:read"
        WRITE = "prompt:write"
        ADMIN = "prompt:admin"
        REVIEW = "prompt:review"

        class EXPERIMENT:
            PROPOSE = "prompt:experiment:propose"
            APPROVE = "prompt:experiment:approve"

    class TEMPLATE:
        READ = "template:read"
        WRITE = "template:write"
        ADMIN = "template:admin"
        REVIEW = "template:review"

        class EXPERIMENT:
            PROPOSE = "template:experiment:propose"
            APPROVE = "template:experiment:approve"

    class MODEL:
        READ = "model:read"
        WRITE = "model:write"
        ADMIN = "model:admin"
        REVIEW = "model:review"

        class EXPERIMENT:
            PROPOSE = "model:experiment:propose"
            APPROVE = "model:experiment:approve"

    class GENERATION:
        READ = "generation:read"
        WRITE = "generation:write"
        ADMIN = "generation:admin"

    class RUN:
        READ = "run:read"
        WRITE = "run:write"
        ADMIN = "run:admin"
        PROGRESS_WRITE = "run:progress:write"

    class SAMPLE:
        READ = "sample:read"
        REVIEW = "sample:review"
        ADMIN = "sample:admin"

    class VOTING:
        ADMIN = "voting:admin"
