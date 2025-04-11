import textwrap

from sqlalchemy import text
from sqlalchemy.orm import Session
from mc_bench.util.logging import get_logger # Import logger

logger = get_logger(__name__) # Initialize logger

# --- Default/Random Query ---
# Renamed back to original name
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
            AND sample.test_set_id = $1 -- Expecting integer
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
            AND sample.test_set_id = $1 -- Expecting integer
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
                    AND sample_ids.comparison_sample_id != sample_1.comparison_sample_id
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

# --- New priority-based query ---
# Keep this name
COMPARISON_BATCH_QUERY_PRIORITY = textwrap.dedent("""\
    WITH approval_state AS (
        SELECT
            id approved_state_id
        FROM
            scoring.sample_approval_state
        WHERE
            name = 'APPROVED'
    ),
    avg_votes AS (
        SELECT
            AVG(vote_count) as avg_vote_count
        FROM
            scoring.model_leaderboard
        WHERE
            test_set_id = $1
            AND tag_id IS NULL
    ),
    model_priorities AS (
        SELECT
            model.id as model_id,
            model.name as model_name,
            COALESCE(ml.vote_count, 0) as vote_count,
            avg.avg_vote_count,
            CASE
                WHEN COALESCE(ml.vote_count, 0) = 0 THEN 200.0
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.1, 1) THEN
                    150.0 + (random() * 10.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.1, 1)))
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.9, 1) THEN
                    50.0 + (random() * 10.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.9, 1)))
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.99, 1) THEN
                    10.0 + (random() * 5.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.99, 1)))
                ELSE 1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count, 1))
            END as priority_score,
            CASE WHEN random() < 0.8 THEN true ELSE false END as use_priority
        FROM
            specification.model
            CROSS JOIN avg_votes avg
            LEFT JOIN scoring.model_leaderboard ml
                ON model.id = ml.model_id
                AND ml.test_set_id = $1
                AND ml.tag_id IS NULL
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
            join model_priorities mp
                on model.id = mp.model_id
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
            CASE WHEN bool_or(mp.use_priority) THEN avg(mp.priority_score) ELSE 0 END DESC,
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
            sample_1.run_id run_id,
            sample_1.model_id as model_1_id,
            sample_2.model_id as model_2_id
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
                    AND sample_ids.comparison_sample_id != sample_1.comparison_sample_id
                    AND sample_ids.model_id != sample_1.model_id
                ORDER BY
                    (SELECT mp.priority_score FROM model_priorities mp WHERE mp.model_id = sample_ids.model_id) DESC,
                    random()
                LIMIT 1
            ) sample_2 ON sample_2.comparison_correlation_id = correlation_ids.id
    )
    SELECT
        samples.sample_1,
        sample_1_data.key as sample_1_key,
        samples.sample_2,
        sample_2_data.key as sample_2_key,
        prompt.build_specification,
        (SELECT slug FROM specification.model WHERE id = samples.model_1_id) as model_1_slug,
        (SELECT COALESCE(ml.vote_count, 0) FROM scoring.model_leaderboard ml WHERE ml.model_id = samples.model_1_id AND ml.test_set_id = $1 AND ml.tag_id IS NULL) as model_1_votes,
        (SELECT mp.priority_score FROM model_priorities mp WHERE mp.model_id = samples.model_1_id) as model_1_priority,
        (SELECT slug FROM specification.model WHERE id = samples.model_2_id) as model_2_slug,
        (SELECT COALESCE(ml.vote_count, 0) FROM scoring.model_leaderboard ml WHERE ml.model_id = samples.model_2_id AND ml.test_set_id = $1 AND ml.tag_id IS NULL) as model_2_votes,
        (SELECT mp.priority_score FROM model_priorities mp WHERE mp.model_id = samples.model_2_id) as model_2_priority
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


def prepare_statements(db: Session) -> None:
    """Prepare SQL statements for the API."""
    try:
        # Prepare the original random batch query (using original name)
        db.execute(
            text(
                # Use original prepared statement name
                "PREPARE comparison_batch_query(integer, integer) AS "
                + COMPARISON_BATCH_QUERY # Use original variable name
            )
        )
        logger.info("Prepared statement: comparison_batch_query (standard/random)")
    except Exception as e:
         # Log specific error for this statement
        logger.error(f"Failed to prepare statement 'comparison_batch_query': {e}", exc_info=True)
        # Optionally re-raise or handle as needed

    try:
        # Prepare the new priority batch query (using specific name)
        db.execute(
            text(
                # Use specific prepared statement name for priority
                "PREPARE comparison_batch_query_priority(integer, integer) AS "
                + COMPARISON_BATCH_QUERY_PRIORITY # Use specific variable name
            )
        )
        logger.info("Prepared statement: comparison_batch_query_priority")
    except Exception as e:
        # Log specific error for this statement
        logger.error(f"Failed to prepare statement 'comparison_batch_query_priority': {e}", exc_info=True)
        # Optionally re-raise or handle as needed
