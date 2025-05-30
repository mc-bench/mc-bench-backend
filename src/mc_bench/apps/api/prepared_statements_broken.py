import textwrap

from sqlalchemy import text
from sqlalchemy.orm import Session

from .config import settings


# Original query without vote weighting
COMPARISON_BATCH_QUERY_ORIGINAL = textwrap.dedent("""\
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
            join research.experimental_state
                on model.experimental_state_id = experimental_state.id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
            AND (experimental_state.name IS NULL OR experimental_state.name != 'DEPRECATED')
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
            join research.experimental_state
                on model.experimental_state_id = experimental_state.id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
            AND (experimental_state.name IS NULL OR experimental_state.name != 'DEPRECATED')
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

# New query with vote weighting to prioritize models with fewer votes
COMPARISON_BATCH_QUERY_WEIGHTED = textwrap.dedent("""\
    WITH approval_state AS (
        SELECT
            id approved_state_id
        FROM
            scoring.sample_approval_state
        WHERE
            name = 'APPROVED'
    ),
    -- Get vote statistics for all models to calculate dynamic weights
    model_vote_stats AS (
        SELECT
            model_id,
            COALESCE(SUM(vote_count), 0) as total_votes,
            -- Calculate median votes across all models for dynamic threshold
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY COALESCE(SUM(vote_count), 0)) 
                OVER () as median_votes,
            -- Calculate 75th percentile for upper threshold
            PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY COALESCE(SUM(vote_count), 0)) 
                OVER () as p75_votes
        FROM
            scoring.model_leaderboard
        WHERE
            test_set_id = $1
            AND tag_id IS NULL  -- Only consider global leaderboard
        GROUP BY
            model_id
    ),
    -- Calculate selection weights for each model
    model_weights AS (
        SELECT
            model.id as model_id,
            model.name as model_name,
            COALESCE(mvs.total_votes, 0) as votes,
            COALESCE(mvs.median_votes, 100) as median_votes,
            COALESCE(mvs.p75_votes, 200) as p75_votes,
            -- Calculate weight: Models with fewer votes get higher weight
            -- Weight formula: max(1.0, (p75_votes - votes) / p75_votes * boost_factor)
            -- This gives models with 0 votes a weight of boost_factor (e.g., 10)
            -- Models at p75 or above get weight 1.0
            GREATEST(1.0, 
                CASE 
                    WHEN COALESCE(mvs.p75_votes, 200) = 0 THEN 10.0
                    ELSE (COALESCE(mvs.p75_votes, 200) - COALESCE(mvs.total_votes, 0))::float 
                         / COALESCE(mvs.p75_votes, 200)::float * 10.0
                END
            ) as selection_weight
        FROM
            specification.model
            LEFT JOIN model_vote_stats mvs ON model.id = mvs.model_id
            LEFT JOIN research.experimental_state 
                ON model.experimental_state_id = experimental_state.id
        WHERE
            (experimental_state.name IS NULL OR experimental_state.name != 'DEPRECATED')
    ),
    -- Select correlation IDs with weighted random selection
    correlation_ids AS (
        SELECT
            comparison_correlation_id id,
            -- Store the total weight for this correlation for later use
            SUM(mw.selection_weight) as total_weight
        FROM
            sample.sample
            join specification.run
                on sample.run_id = run.id
            join model_weights mw
                on run.model_id = mw.model_id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
        GROUP BY
            comparison_correlation_id
        HAVING
            COUNT(DISTINCT run.model_id) >= 2  -- Ensure we have at least 2 different models
        ORDER BY
            -- Weighted random selection: multiply random by inverse of total weight
            -- This gives higher chance to correlation IDs with models that have lower votes
            random() * (1.0 / (SUM(mw.selection_weight) + 1.0))
        LIMIT $2
    ),
    sample_ids AS (
        SELECT
            sample.id sample_id,
            sample.comparison_correlation_id,
            sample.comparison_sample_id,
            sample.run_id,
            model.id model_id,
            mw.selection_weight
        FROM
            sample.sample
            join specification.run
                on sample.run_id = run.id
            join specification.model
                on run.model_id = model.id
            join model_weights mw
                on model.id = mw.model_id
            join research.experimental_state
                on model.experimental_state_id = experimental_state.id
            cross join approval_state
        WHERE
            sample.approval_state_id = approval_state.approved_state_id
            AND sample.test_set_id = $1
            AND (experimental_state.name IS NULL OR experimental_state.name != 'DEPRECATED')
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
                    sample_ids.model_id,
                    sample_ids.selection_weight
                FROM 
                    sample_ids
                WHERE
                    sample_ids.comparison_correlation_id = correlation_ids.id
                ORDER BY 
                    -- Weighted random for sample selection within correlation
                    random() * (1.0 / (sample_ids.selection_weight + 1.0))
                LIMIT 1
            ) sample_1 ON sample_1.comparison_correlation_id = correlation_ids.id
            JOIN LATERAL (
                SELECT 
                    sample_ids.sample_id,
                    sample_ids.comparison_sample_id,
                    sample_ids.comparison_correlation_id,
                    sample_ids.run_id,
                    sample_ids.model_id,
                    sample_ids.selection_weight
                FROM 
                    sample_ids
                WHERE
                    sample_ids.comparison_correlation_id = correlation_ids.id
                    AND sample_ids.comparison_sample_id != sample_1.comparison_sample_id  -- Ensure we don't select the same sample twice
                    AND sample_ids.model_id != sample_1.model_id
                ORDER BY 
                    -- Uniform random for second model - prevents high-weight models from competing against each other
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