"""Initial Role Creation

Revision ID: 1ddb45880af9
Revises: d75b6128c146
Create Date: 2024-11-12 00:21:09.372699

"""

import textwrap
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1ddb45880af9"
down_revision: Union[str, None] = "d75b6128c146"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        textwrap.dedent("""
        CREATE ROLE "api"
            WITH 
                NOLOGIN
                INHERIT
        ;
        
        GRANT USAGE ON SCHEMA auth TO "api";
        GRANT USAGE ON SCHEMA sample TO "api";
        GRANT USAGE ON SCHEMA scoring TO "api";
        GRANT USAGE ON SCHEMA specification TO "api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT SELECT, INSERT ON TABLES TO "api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT USAGE ON SEQUENCES TO "api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT EXECUTE ON FUNCTIONS TO "api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT ON TABLES TO "api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT SELECT, INSERT ON TABLES TO "api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT USAGE ON SEQUENCES TO "api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT EXECUTE ON FUNCTIONS TO "api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT ON TABLES TO "api";

        -- for testing only
        DO
        $do$
        BEGIN
           IF EXISTS (
              SELECT FROM pg_catalog.pg_roles
              WHERE  rolname = 'service-api') THEN

                GRANT "api" TO "service-api";
           ELSE
              CREATE ROLE "service-api" LOGIN PASSWORD 'service-api' in ROLE api;
           END IF;
        END
        $do$;

        CREATE ROLE "admin-api"
            WITH 
                NOLOGIN
                INHERIT
        ;

        GRANT USAGE ON SCHEMA auth TO "admin-api";
        GRANT USAGE ON SCHEMA sample TO "admin-api";
        GRANT USAGE ON SCHEMA scoring TO "admin-api";
        GRANT USAGE ON SCHEMA specification TO "admin-api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT SELECT, INSERT ON TABLES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT USAGE ON SEQUENCES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT EXECUTE ON FUNCTIONS TO "admin-api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT, INSERT ON TABLES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT USAGE ON SEQUENCES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT EXECUTE ON FUNCTIONS TO "admin-api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT SELECT, INSERT ON TABLES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT USAGE ON SEQUENCES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT EXECUTE ON FUNCTIONS TO "admin-api";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT, INSERT ON TABLES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT USAGE ON SEQUENCES TO "admin-api";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT EXECUTE ON FUNCTIONS TO "admin-api";

        -- for testing only
        DO
        $do$
        BEGIN
           IF EXISTS (
              SELECT FROM pg_catalog.pg_roles
              WHERE  rolname = 'service-admin-api') THEN
        
            GRANT "admin-api" TO "service-admin-api";
           ELSE
              CREATE ROLE "service-admin-api" LOGIN PASSWORD 'service-admin-api' in ROLE "admin-api";
           END IF;
        END
        $do$;


        CREATE ROLE "worker"
            WITH 
                NOLOGIN
                INHERIT
        ;
        
        GRANT USAGE ON SCHEMA auth TO "worker";
        GRANT USAGE ON SCHEMA sample TO "worker";
        GRANT USAGE ON SCHEMA scoring TO "worker";
        GRANT USAGE ON SCHEMA specification TO "worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT SELECT ON TABLES TO "worker";
        
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT, INSERT ON TABLES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT USAGE ON SEQUENCES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT EXECUTE ON FUNCTIONS TO "worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT SELECT, INSERT ON TABLES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT USAGE ON SEQUENCES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT EXECUTE ON FUNCTIONS TO "worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT, INSERT ON TABLES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT USAGE ON SEQUENCES TO "worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT EXECUTE ON FUNCTIONS TO "worker";
        
        -- for testing only
        DO
        $do$
        BEGIN
           IF EXISTS (
              SELECT FROM pg_catalog.pg_roles
              WHERE  rolname = 'service-worker') THEN
        
              GRANT "worker" TO "service-worker";
           ELSE
              CREATE ROLE "service-worker" LOGIN PASSWORD 'service-worker' in ROLE worker;
           END IF;
        END
        $do$;
        
        CREATE ROLE "admin-worker"
            WITH 
                NOLOGIN
                INHERIT
        ;

        GRANT USAGE ON SCHEMA auth TO "admin-worker";
        GRANT USAGE ON SCHEMA sample TO "admin-worker";
        GRANT USAGE ON SCHEMA scoring TO "admin-worker";
        GRANT USAGE ON SCHEMA specification TO "admin-worker";


        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT USAGE ON SEQUENCES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA auth GRANT EXECUTE ON FUNCTIONS TO "admin-worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT SELECT, INSERT ON TABLES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT USAGE ON SEQUENCES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA sample GRANT EXECUTE ON FUNCTIONS TO "admin-worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT SELECT, INSERT ON TABLES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT USAGE ON SEQUENCES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA scoring GRANT EXECUTE ON FUNCTIONS TO "admin-worker";

        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT SELECT, INSERT ON TABLES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT USAGE ON SEQUENCES TO "admin-worker";
        ALTER DEFAULT PRIVILEGES FOR ROLE "mc-bench-admin" IN SCHEMA specification GRANT EXECUTE ON FUNCTIONS TO "admin-worker";

        -- for testing only
        DO
        $do$
        BEGIN
           IF EXISTS (
              SELECT FROM pg_catalog.pg_roles
              WHERE  rolname = 'service-admin-worker') THEN
        
              GRANT "admin-worker" TO "service-admin-worker";
           ELSE
              CREATE ROLE "service-admin-worker" LOGIN PASSWORD 'service-admin-worker' in ROLE "admin-worker";
           END IF;
        END
        $do$;

    """)
    )


def downgrade() -> None:
    raise RuntimeError("Upgrades only")
    pass
