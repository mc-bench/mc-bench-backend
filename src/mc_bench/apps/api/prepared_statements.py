import textwrap

from sqlalchemy import text
from sqlalchemy.orm import Session


def prepare_statements(db: Session) -> None:
    """Prepare SQL statements for the API."""
    db.execute(
        text(
            "PREPARE comparison_batch_query(integer, integer) AS " + COMPARISON_BATCH_QUERY
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
    -- Get average vote count for all models in the leaderboard for this test set
    avg_votes AS (
        SELECT
            AVG(vote_count) as avg_vote_count
        FROM
            scoring.model_leaderboard
        WHERE
            test_set_id = $1
            AND tag_id IS NULL
    ),
    -- Calculate priority scores for models based on vote counts
    model_priorities AS (
        SELECT
            model.id as model_id,
            model.name as model_name,
            COALESCE(ml.vote_count, 0) as vote_count,
            avg.avg_vote_count,
            -- Calculate priority score (higher for models with fewer votes)
            CASE
                -- If no votes yet, give highest priority
                WHEN COALESCE(ml.vote_count, 0) = 0 THEN 200.0
                -- If extremely low votes (less than 10% of average), give super high priority
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.1, 1) THEN
                    -- Base priority of 150.0 to ensure these models appear very frequently
                    150.0 + (random() * 10.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.1, 1)))
                -- If below 90% of average, give high priority
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.9, 1) THEN
                    -- Base priority of 50.0 plus a small random factor to ensure models with similar vote counts
                    -- have similar but not identical chances (prevents always picking the lowest)
                    50.0 + (random() * 10.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.9, 1)))
                -- If between 90% and 99% of average, give medium priority
                WHEN COALESCE(ml.vote_count, 0) < GREATEST(avg.avg_vote_count * 0.99, 1) THEN
                    10.0 + (random() * 5.0) + (1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count * 0.99, 1)))
                -- Otherwise, give low priority based on how close to average
                ELSE 1.0 - (COALESCE(ml.vote_count, 0) / GREATEST(avg.avg_vote_count, 1))
            END as priority_score,
            -- 80% chance to use priority-based selection, 20% chance for random
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
        -- Use priority-based ordering if use_priority is true, otherwise use random
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
                    AND sample_ids.comparison_sample_id != sample_1.comparison_sample_id  -- Ensure we don't select the same sample twice
                    AND sample_ids.model_id != sample_1.model_id
                ORDER BY
                    -- Join with model_priorities to get priority score for this model
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
        -- Include model information for logging
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
