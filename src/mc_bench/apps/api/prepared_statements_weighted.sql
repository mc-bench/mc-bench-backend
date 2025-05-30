-- New weighted query that directly selects models based on weights
WITH approval_state AS (
    SELECT
        id approved_state_id
    FROM
        scoring.sample_approval_state
    WHERE
        name = 'APPROVED'
),
-- Get vote statistics for all models
model_vote_stats AS (
    SELECT
        model.id as model_id,
        model.name as model_name,
        COALESCE(ml.vote_count, 0) as total_votes
    FROM
        specification.model
        LEFT JOIN scoring.model_leaderboard ml ON 
            model.id = ml.model_id 
            AND ml.test_set_id = $1
            AND ml.tag_id IS NULL
        LEFT JOIN research.experimental_state es ON model.experimental_state_id = es.id
    WHERE
        (es.name IS NULL OR es.name != 'DEPRECATED')
),
-- Calculate percentiles for dynamic thresholds
vote_percentiles AS (
    SELECT
        PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY total_votes) as p75_votes
    FROM
        model_vote_stats
),
-- Calculate selection weights for each model
model_weights AS (
    SELECT
        mvs.model_id,
        mvs.model_name,
        mvs.total_votes as votes,
        CASE 
            WHEN vp.p75_votes IS NULL OR vp.p75_votes = 0 THEN {boost_factor}
            WHEN mvs.total_votes >= vp.p75_votes THEN 1.0
            ELSE 1.0 + ((vp.p75_votes - mvs.total_votes)::float / vp.p75_votes::float * ({boost_factor} - 1.0))
        END as selection_weight
    FROM
        model_vote_stats mvs
        CROSS JOIN vote_percentiles vp
),
-- Get all available samples with their models
available_samples AS (
    SELECT DISTINCT
        s.id as sample_id,
        s.comparison_sample_id,
        s.comparison_correlation_id,
        s.run_id,
        r.model_id,
        mw.model_name,
        mw.votes,
        mw.selection_weight,
        a.key as artifact_key
    FROM
        sample.sample s
        JOIN specification.run r ON s.run_id = r.id
        JOIN model_weights mw ON r.model_id = mw.model_id
        JOIN sample.artifact a ON s.id = a.sample_id
        JOIN sample.artifact_kind ak ON a.artifact_kind_id = ak.id
        CROSS JOIN approval_state
    WHERE
        s.approval_state_id = approval_state.approved_state_id
        AND s.test_set_id = $1
        AND ak.name = 'RENDERED_MODEL_GLB_COMPARISON_SAMPLE'
),
-- For each request, select pairs
selected_pairs AS (
    SELECT
        pair_num,
        model_1_sample,
        model_1_key,
        model_1_name,
        model_1_votes,
        model_2_sample,
        model_2_key,
        model_2_name,
        model_2_votes,
        build_spec
    FROM (
        SELECT 
            ROW_NUMBER() OVER () as pair_num,
            s1.comparison_sample_id as model_1_sample,
            s1.artifact_key as model_1_key,
            s1.model_name as model_1_name,
            s1.votes as model_1_votes,
            s2.comparison_sample_id as model_2_sample,
            s2.artifact_key as model_2_key,
            s2.model_name as model_2_name,
            s2.votes as model_2_votes,
            p.build_specification as build_spec,
            -- Use weighted random for BOTH model selections
            random() * (1.0 / (s1.selection_weight + 0.1)) as rand1,
            random() * (1.0 / (s2.selection_weight + 0.1)) as rand2
        FROM
            available_samples s1
            JOIN available_samples s2 ON 
                s1.comparison_correlation_id = s2.comparison_correlation_id
                AND s1.model_id != s2.model_id
                AND s1.comparison_sample_id < s2.comparison_sample_id -- Avoid duplicates
            JOIN specification.run r ON s1.run_id = r.id
            JOIN specification.prompt p ON r.prompt_id = p.id
        ORDER BY
            -- Order by the sum of weighted randoms to get diverse but weighted pairs
            rand1 + rand2
        LIMIT $2 * 5  -- Get extra to ensure we have enough unique pairs
    ) ranked_pairs
    WHERE pair_num <= $2
)
SELECT
    model_1_sample as sample_1,
    model_1_key as sample_1_key,
    model_2_sample as sample_2,
    model_2_key as sample_2_key,
    build_spec as build_specification
FROM
    selected_pairs
ORDER BY
    pair_num;