import textwrap

from sqlalchemy import text
from sqlalchemy.orm import Session


def prepare_statements(db: Session) -> None:
    """Prepare SQL statements for the API."""
    db.execute(
        text(
            "PREPARE comparison_batch_query(uuid, integer) AS " + COMPARISON_BATCH_QUERY
        )
    )


COMPARISON_BATCH_QUERY = textwrap.dedent("""\
    WITH approval_state AS (
        SELECT
            id approved_state_id
        FROM
            scoring.sample_approval_state
        WHERE
            name = 'APPROVED'
    ),
    correlation_ids AS (
        SELECT
            comparison_correlation_id id
        FROM
            sample.sample
            join specification.run
                on sample.run_id = run.id
            join specification.model
                on run.model_id = model.id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
        GROUP BY
            comparison_correlation_id,
            model.name
        HAVING
            COUNT(*) >= 2
        ORDER BY
            random()
        LIMIT $2
    ),
    sample_ids AS (
        SELECT
            sample.id sample_id,
            sample.comparison_correlation_id,
            sample.comparison_sample_id,
            sample.run_id,
            model.id model_id
        FROM
            sample.sample
            join specification.run
                on sample.run_id = run.id
            join specification.model
                on run.model_id = model.id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
    ), 
    samples as (
        SELECT
            sample_1.sample_id sample_1_id,
            sample_1.comparison_sample_id sample_1,
            sample_2.sample_id sample_2_id,
            sample_2.comparison_sample_id sample_2,
            sample_1.run_id run_id
        FROM
            correlation_ids
            JOIN LATERAL (
                SELECT
                    sample_ids.sample_id,
                    sample_ids.comparison_sample_id,
                    sample_ids.comparison_correlation_id,
                    sample_ids.run_id,
                    sample_ids.model_id
                FROM 
                    sample_ids
                WHERE
                    sample_ids.comparison_correlation_id = correlation_ids.id
                ORDER BY 
                    random()
                LIMIT 1
            ) sample_1 ON sample_1.comparison_correlation_id = correlation_ids.id
            JOIN LATERAL (
                SELECT 
                    sample_ids.sample_id,
                    sample_ids.comparison_sample_id,
                    sample_ids.comparison_correlation_id,
                    sample_ids.run_id,
                    sample_ids.model_id
                FROM 
                    sample_ids
                WHERE
                    sample_ids.comparison_correlation_id = correlation_ids.id
                    AND sample_ids.comparison_sample_id != sample_1.comparison_sample_id  -- Ensure we don't select the same sample twice
                    AND sample_ids.model_id != sample_1.model_id
                ORDER BY 
                    random()
                LIMIT 1
            ) sample_2 ON sample_2.comparison_correlation_id = correlation_ids.id
    )
    SELECT
        samples.sample_1,
        sample_1_data.key as sample_1_key,
        samples.sample_2,
        sample_2_data.key as sample_2_key,
        prompt.build_specification        
    FROM
        samples
        JOIN specification.run
            ON samples.run_id = run.id
        JOIN specification.prompt
            ON run.prompt_id = prompt.id
        JOIN LATERAL (
            SELECT
                artifact.sample_id,
                artifact.key
            FROM
                sample.artifact
                join sample.artifact_kind
                    ON artifact.artifact_kind_id = artifact_kind.id
            WHERE
                artifact.sample_id = samples.sample_1_id
                AND artifact_kind.name = 'RENDERED_MODEL_GLB_COMPARISON_SAMPLE'
            LIMIT 1
        ) sample_1_data
            ON samples.sample_1_id = sample_1_data.sample_id
        JOIN LATERAL (
            SELECT
                artifact.sample_id,
                artifact.key
            FROM
                sample.artifact
                join sample.artifact_kind
                    ON artifact.artifact_kind_id = artifact_kind.id
            WHERE
                artifact.sample_id = samples.sample_2_id
                AND artifact_kind.name = 'RENDERED_MODEL_GLB_COMPARISON_SAMPLE'
            LIMIT 1
        ) sample_2_data
            ON samples.sample_2_id = sample_2_data.sample_id
""")
